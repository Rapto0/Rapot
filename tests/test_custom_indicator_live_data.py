"""Live native event/seed integration without external providers or deliveries."""

from dataclasses import replace

import pytest

from application.services.advanced_alarm_conditions import condition_fields
from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_data import NOW, Provider, inputs, rule


def ready_service(indicator="rsi_votes"):
    clock = [NOW + 0.2]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    selected = rule()
    selected["condition"]["left"]["indicator"] = indicator
    selected["trigger"] = "intrabar"
    service.configure([selected])
    service.process(*service._next_job())
    service.live._enabled = True
    key = next(iter(service.live._configs))
    bars = service._native[("BIST", "THYAO", "1D")].bars
    service.live._buckets[("BIST", "THYAO", "1D")] = (
        (replace(bars[-2], confirmed=True), bars[-1]),
        clock[0],
    )
    ref = condition_fields(selected["condition"], "1d")[0]
    return clock, provider, service, selected, key, ref


def quote(service, clock, price, source=None):
    service.live.enqueue(
        {
            "kind": "quote",
            "member": ("BIST", "THYAO"),
            "price": price,
            "source_timestamp": source if source is not None else clock[0],
            "received_at": clock[0],
        }
    )


def test_provider_failure_diagnostics_survive_pool_replacement_without_raw_payloads():
    from types import SimpleNamespace

    _, _, service, _, _, _ = ready_service()
    service.live._remember_transport_failure(
        SimpleNamespace(
            status=lambda: {
                "failure_codes": ["session_rate_limited", "untrusted provider session identifier"]
            }
        )
    )
    service.live._remember_transport_failure(SimpleNamespace(status=lambda: {}))
    assert service.live.status()["last_native_failure_codes"] == ["session_rate_limited"]


def observation(service, selected, ref, clock):
    return service.observation(ref, selected["symbols"][0], "intrabar", clock[0])


def test_live_prices_cross_and_return_before_next_timer_without_history_io():
    clock, provider, service, selected, key, ref = ready_service()
    clock[0] = NOW + 1
    seen = []
    service.live.set_listener(lambda *_: seen.append(observation(service, selected, ref, clock)))
    for price in (200, 20, 200, 20):
        quote(service, clock, price)
    while service.live.process_event():
        pass
    assert [item["current"] for item in seen] == [0, 1, 0, 1]
    assert len(provider.calls) == 1
    assert len({item["observation_id"] for item in seen}) == 4
    assert all(item["source_timestamp"] == clock[0] for item in seen)
    assert service._results[key]["live_price"] == 20
    assert service._results[key]["previous"]["live_price"] == 200
    assert service.status()["live_processed"] == 4
    preview = service.preview("rsi_votes", inputs(), "THYAO")
    assert preview["observation_price"] == 20
    assert preview["latest"]["observed_at"] == clock[0]


def test_unknown_native_bucket_never_projects_old_multiday_identity():
    clock, _, service, selected, _, ref = ready_service()
    clock[0] += 1
    old = service.live._buckets[("BIST", "THYAO", "1D")]
    service.live._buckets[("BIST", "THYAO", "1D")] = (
        (old[0][0], replace(old[0][1], time=old[0][1].time + 1)),
        old[1],
    )
    quote(service, clock, 20)
    service.live.process_event()
    assert not observation(service, selected, ref, clock)["ready"]


def test_gap_between_calculation_and_publish_cannot_restore_old_ready_values(monkeypatch):
    clock, _, service, selected, _, ref = ready_service()
    clock[0] += 1
    original = service.publish_live

    def race(*args, **kwargs):
        service.live.invalidate()
        service.live_gap("Synthetic disconnect")
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "publish_live", race)
    quote(service, clock, 20)
    service.live.process_event()
    assert not observation(service, selected, ref, clock)["ready"]
    assert service.status()["live_processed"] == 0


def test_queue_overflow_is_counted_and_resets_comparison_baseline(monkeypatch):
    from application.services import custom_indicator_live

    clock, _, service, selected, _, ref = ready_service()
    monkeypatch.setattr(custom_indicator_live, "MAX_LIVE_EVENTS", 2)
    for price in (200, 20, 200):
        quote(service, clock, price)
    assert service.status()["live_overflow_count"] == 1
    service.live.process_event()
    assert not observation(service, selected, ref, clock)["ready"]
    assert service.live._compiled == {}


def test_bootstrap_same_second_quote_extreme_is_retained_without_emitting_signal():
    clock, _, service, selected, key, ref = ready_service()
    quote(service, clock, 1000, source=NOW)
    service.live.process_event()
    assert not observation(service, selected, ref, clock)["ready"]
    assert service.live._compiled[key]["buckets"]["1D"].high == 1000
    clock[0] = NOW + 1
    quote(service, clock, 150)
    service.live.process_event()
    assert observation(service, selected, ref, clock)["ready"]


def test_late_native_high_does_not_leak_into_older_price_observation():
    clock, _, service, _, key, _ = ready_service()
    frozen = service.live._compiled[key]["buckets"]["1D"].high
    existing = service.live._buckets[("BIST", "THYAO", "1D")]
    service.live._buckets[("BIST", "THYAO", "1D")] = (
        (existing[0][0], replace(existing[0][1], high=10000)),
        clock[0] + 1,
    )
    clock[0] = NOW + 1
    quote(service, clock, 150)
    service.live.process_event()
    assert service.live._compiled[key]["buckets"]["1D"].high == frozen


def test_expired_preview_releases_live_demand_without_another_browser_request():
    clock = [NOW]
    service = CustomIndicatorData(provider=Provider(), clock=lambda: clock[0])
    service.preview("rsi_votes", inputs(), "THYAO")
    assert service.live._wanted
    clock[0] += 121
    service.live.control_step()
    assert not service.live._wanted


def test_control_continues_paced_subscriptions_without_resetting_existing_seed():
    from types import SimpleNamespace

    clock, provider, service, _, key, _ = ready_service()
    prepared = service.live._compiled[key]
    batches = []
    connection = SimpleNamespace(
        connected=True,
        epoch=provider.data_epoch(),
        needs_reconcile=True,
        close=lambda: pytest.fail("A healthy paced connection must stay open"),
    )

    def configure(wanted, *, member_slots):
        assert member_slots == service.live._member_slots
        batches.append(wanted.copy())
        connection.needs_reconcile = len(batches) < 3

    connection.configure = configure
    service.live._connection = connection
    service.live._subscribed = service.live._wanted.copy()
    for _ in range(4):
        clock[0] += 1
        service.live.control_step()
    assert len(batches) == 3
    assert service.live._compiled[key] is prepared
    assert service.live._failures == 0


def test_callback_failure_is_not_counted_as_completed_observation():
    clock, _, service, _, _, _ = ready_service()
    clock[0] += 1
    service.live.set_listener(
        lambda *_: (_ for _ in ()).throw(RuntimeError("synthetic delivery failure"))
    )
    quote(service, clock, 150)
    with pytest.raises(RuntimeError):
        service.live.process_event()
    assert service.status()["live_processed"] == 0


def native_extreme(service, clock, high):
    points = service.live._buckets[("BIST", "THYAO", "1D")][0]
    rows = [
        (bar.time, bar.open, high if i == 1 else bar.high, bar.low, bar.close)
        for i, bar in enumerate(points)
    ]
    from tests.test_custom_indicator_data import SESSION

    service.live._bars(
        {
            "kind": "bars",
            "key": ("BIST", "THYAO", "1D"),
            "rows": rows,
            "metadata": SESSION,
            "received_at": clock[0],
        }
    )


def test_unseen_native_smi_extreme_waits_for_safe_source_time_then_matures():
    clock, _, service, selected, key, ref = ready_service("smi_votes")
    clock[0] = NOW + 2.2
    native_extreme(service, clock, 1000)
    quote(service, clock, 150, source=NOW + 2)
    service.live.process_event()
    assert not observation(service, selected, ref, clock)["ready"]
    assert service.live._compiled[key]["buckets"]["1D"].high == 150
    assert service.status()["native_extreme_waits"] == 1
    clock[0] = NOW + 3
    quote(service, clock, 160)
    service.live.process_event()
    assert observation(service, selected, ref, clock)["ready"]
    assert service.live._compiled[key]["buckets"]["1D"].high == 1000


def test_repeated_bar_then_quote_extreme_is_ready_without_starving_smi():
    clock, _, service, selected, key, ref = ready_service("smi_votes")
    for number in range(2, 8):
        clock[0] = NOW + number + 0.2
        price = 200 + number
        native_extreme(service, clock, price)
        quote(service, clock, price, source=NOW + number)
        service.live.process_event()
        assert observation(service, selected, ref, clock)["ready"]
        assert service.live._compiled[key]["pending_extremes"] == {}
    assert service.status()["native_extreme_waits"] == 0


def test_account_change_between_calculation_and_publish_rejects_old_account(monkeypatch):
    clock, provider, service, selected, _, ref = ready_service()
    clock[0] += 1
    original = service.publish_live

    def race(*args, **kwargs):
        provider.generation += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "publish_live", race)
    quote(service, clock, 20)
    service.live.process_event()
    assert not observation(service, selected, ref, clock)["ready"]
    assert service.status()["live_rejected"] == 1


def test_another_symbols_refresh_does_not_discard_transient_signal(monkeypatch):
    clock, _, service, selected, _, ref = ready_service()
    clock[0] += 1
    original = service.publish_live

    def race(*args, **kwargs):
        service.native_refresh(("BIST", "OTHER", "1D"))
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "publish_live", race)
    quote(service, clock, 200)
    service.live.process_event()
    quote(service, clock, 20)
    service.live.process_event()
    assert observation(service, selected, ref, clock)["current"] == 1
    assert service.status()["live_rejected"] == 0


def test_actual_watchlist_engine_records_intrabar_transient_without_timer(tmp_path):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from api.routes.advanced_alarm_routes import AlarmWrite
    from application.services.advanced_alarm_market_data import AdvancedMarketData
    from application.services.advanced_alarm_service import AdvancedAlarmEngine
    from infrastructure.repositories import advanced_alarm_repository as repository
    from tests.test_advanced_alarm_backend import payload
    from tests.test_advanced_alarm_market_data import MemoryCache

    clock, _, service, selected, _, _ = ready_service()
    settings = SimpleNamespace(
        database_path=str(tmp_path / "synthetic.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    hub = AdvancedMarketData(settings, cache=MemoryCache(), clock=lambda: clock[0])
    hub._custom = service
    watchlist = repository.save_watchlist(
        "admin", {"name": "Synthetic live list", "symbols": selected["symbols"]}
    )
    value = AlarmWrite(
        **payload(
            category="watchlist",
            scope="watchlist",
            watchlist_id=watchlist["id"],
            symbols=[],
            condition=selected["condition"],
            trigger="intrabar",
            timeframe="1d",
            mode="on_enter",
            cooldown_seconds=1,
            notify_telegram=False,
        )
    ).model_dump()
    repository.save_rule("admin", value)
    engine = AdvancedAlarmEngine(
        hub, clock=lambda: 10, wall_clock=lambda: datetime.fromtimestamp(clock[0], UTC)
    )
    engine.bind_live_updates()
    engine.tick()
    clock[0] = NOW + 1
    for price in (200, 20, 200):
        quote(service, clock, price)
    while service.live.process_event():
        pass
    events = repository.events("admin")["events"]
    assert len(events) == 1
    assert events[0]["symbol"] == "THYAO"
    assert events[0]["delivery_status"] == "not_requested"
    assert repository.delivery_status("admin")["pending"] == 0


def test_native_rollover_advances_live_seed_without_provider_history():
    clock, provider, service, selected, key, ref = ready_service()
    old = service.live._buckets[("BIST", "THYAO", "1D")][0][-1]
    from tests.test_custom_indicator_data import SESSION

    clock[0] = old.time + 86400 + 1
    following = replace(
        old,
        time=old.time + 86400,
        end=old.end + 86400,
        open=old.close,
        high=old.close + 1,
        low=old.close - 1,
        close=old.close,
    )
    rows = [(bar.time, bar.open, bar.high, bar.low, bar.close) for bar in (old, following)]
    service.live._bars(
        {
            "kind": "bars",
            "key": ("BIST", "THYAO", "1D"),
            "rows": rows,
            "metadata": SESSION,
            "received_at": clock[0],
        }
    )
    assert service.live._compiled[key]["buckets"]["1D"].time == following.time
    assert service._native[("BIST", "THYAO", "1D")].bars[-1].time == following.time
    assert service.status()["native_seed_advances"] == 1
    quote(service, clock, following.close)
    service.live.process_event()
    assert observation(service, selected, ref, clock)["ready"]
    assert len(provider.calls) == 1
    # This assertion isolates rollover demand from the separate six-hour
    # reconciliation, which is naturally due in this next-day fixture.
    service._results[key]["seed_received"] = clock[0]
    assert service._next_job() is None


def test_new_settings_reuse_advanced_native_cache_after_rollover():
    from copy import deepcopy

    from tests.test_custom_indicator_data import SESSION

    clock, provider, service, selected, _, _ = ready_service()
    native_key = ("BIST", "THYAO", "1D")
    old = service._native[native_key].bars[-1]
    clock[0] = old.time + 86400 + 1
    # A recent reconciliation is independent from the rollover under test.
    service._native[native_key] = replace(service._native[native_key], received=clock[0])
    following = replace(old, time=old.time + 86400, end=old.end + 86400)
    service.live._bars(
        {
            "kind": "bars",
            "key": native_key,
            "rows": [
                (bar.time, bar.open, bar.high, bar.low, bar.close) for bar in (old, following)
            ],
            "metadata": SESSION,
            "received_at": clock[0],
        }
    )
    second = deepcopy(selected)
    second["id"] = "second-native-settings"
    second["condition"]["left"]["inputs"]["len1"] = 3
    service.configure([selected, second])
    for _ in range(4):
        job = service._next_job()
        if job is None:
            break
        service.process(*job)
    clock[0] += 1
    quote(service, clock, 20)
    service.live.process_event()
    ref = condition_fields(second["condition"], "1d")[0]
    assert observation(service, second, ref, clock)["ready"]
    assert len(provider.calls) == 1


def test_native_rollover_during_seed_preparation_cannot_replace_newer_live_state(monkeypatch):
    clock, _, service, _, key, _ = ready_service()
    clock[0] += 1
    quote(service, clock, 20)
    service.live.process_event()
    previous = service._results[key]
    original = service.live.prepare_seed

    def prepare(*args, **kwargs):
        seed = original(*args, **kwargs)
        native_key = ("BIST", "THYAO", "1D")
        old = service._native[native_key].bars[-1]
        following = replace(old, time=old.time + 86400, end=old.end + 86400)
        service.native_advanced(native_key, replace(old, confirmed=True), following)
        return seed

    monkeypatch.setattr(service.live, "prepare_seed", prepare)
    service.process(key, service.live._configs[key], service._generation)
    assert service._results[key] is previous
    assert service._results[key]["live_price"] == 20


def test_live_quote_during_history_preparation_keeps_current_range_and_edge_state(monkeypatch):
    clock, _, service, _, key, _ = ready_service("smi_votes")
    clock[0] += 1
    quote(service, clock, 20)
    service.live.process_event()
    existing = service.live._compiled[key]
    original = service.live.prepare_seed

    def prepare(*args, **kwargs):
        seed = original(*args, **kwargs)
        clock[0] += 1
        quote(service, clock, 400)
        service.live.process_event()
        return seed

    monkeypatch.setattr(service.live, "prepare_seed", prepare)
    service.process(key, service.live._configs[key], service._generation)
    assert service._results[key]["live_price"] == 400
    assert service.live._compiled[key] is existing
    assert existing["evaluator"].current_range("1D")[0] == 400
    assert service._results[key]["seed_received"] == clock[0]


def test_actual_history_revision_clears_compact_seed_before_rebootstrap():
    clock, provider, service, selected, key, ref = ready_service()
    clock[0] += 1
    quote(service, clock, 20)
    service.live.process_event()
    old = service.live._compiled[key]
    provider.data.iloc[-10, provider.data.columns.get_loc("Close")] += 0.1
    native_key = ("BIST", "THYAO", "1D")
    service._native.pop(native_key)
    service.process(key, service.live._configs[key], service._generation)
    assert key not in service.live._compiled
    assert not observation(service, selected, ref, clock)["ready"]
    service.process(key, service.live._configs[key], service._generation)
    assert service.live._compiled[key] is not old


def test_history_http_failure_preserves_valid_live_seed_and_has_bounded_retry(monkeypatch):
    clock, provider, service, _, key, _ = ready_service()
    clock[0] += 1
    quote(service, clock, 20)
    service.live.process_event()
    existing, result = service.live._compiled[key], service._results[key]
    service._native.clear()

    def fail(*_args, **_kwargs):
        raise RuntimeError("Synthetic history HTTP failure")

    monkeypatch.setattr(provider, "custom_indicator_history", fail)
    service.process(key, service.live._configs[key], service._generation)
    assert service.live._compiled[key] is existing
    assert service._results[key] is result
    assert service._results[key]["live_price"] == 20
    assert service.status()["history_last_error"]
    assert service._next_job() is None
    clock[0] += 1
    quote(service, clock, 200)
    service.live.process_event()
    assert service._results[key]["previous"]["live_price"] == 20
    assert service._results[key]["history_retry_at"] > clock[0]
    clock[0] += 30
    assert service._next_job()[0] == key


def test_continuous_native_stream_history_reconciliation_checks_hash_not_summary_age():
    from types import SimpleNamespace

    clock, _, service, _, key, _ = ready_service()
    clock[0] += 1
    quote(service, clock, 20)
    service.live.process_event()
    existing = service.live._compiled[key]
    native_key = ("BIST", "THYAO", "1D")
    service._history_summaries[native_key] = replace(
        service._history_summaries[native_key], received=clock[0] - 21600
    )
    service.live._connection = SimpleNamespace(connected=True)
    service._native.pop(native_key)
    service.process(key, service.live._configs[key], service._generation)
    assert service.live._compiled[key] is existing
    assert service._results[key]["live_price"] == 20


def test_seed_installation_rejects_a_native_bucket_that_changed_after_preparation():
    clock, _, service, _, key, _ = ready_service()
    existing = service.live._compiled[key]
    native_key = ("BIST", "THYAO", "1D")
    pair, received = service.live._buckets[native_key]
    service.live._buckets[native_key] = (
        (pair[-1], replace(pair[-1], time=pair[-1].time + 86400)),
        received,
    )
    stale = {**existing, "pending_extremes": {}}
    with service._publication_lock, service._lock:
        service.live.install_seed(key, stale, generation=service._generation)
    assert service.live._compiled[key] is existing
    assert key in service._seed_due
    assert service._results[key]["native_wait"]


def test_new_bist_daily_bucket_requires_fresh_unknown_end_htf_witness():
    from application.services.custom_indicator_data import with_native_ends
    from tests.test_custom_indicator_data import SESSION

    clock, provider, service, selected, key, ref = ready_service()
    # Reconfigure with actual native 3D identity; no duration-based ND grouping.
    selected["condition"]["left"]["inputs"].update(en2=True, tf2="3D")
    service.configure([selected])
    service.process(*service._next_job())
    daily = service._native[("BIST", "THYAO", "1D")].bars
    nd = with_native_ends(
        service._native[("BIST", "THYAO", "3D")].bars, daily, "3D", "BIST", clock[0]
    )
    service.live._buckets[("BIST", "THYAO", "3D")] = (nd[-2:], clock[0])
    ref = condition_fields(selected["condition"], "1d")[0]
    old = daily[-1]
    clock[0] = old.time + 86400 + 1
    following = replace(
        old,
        time=old.time + 86400,
        end=old.end + 86400,
        open=old.close,
        high=old.close + 1,
        low=old.close - 1,
        close=old.close,
    )
    service.live._bars(
        {
            "kind": "bars",
            "key": ("BIST", "THYAO", "1D"),
            "rows": [
                (bar.time, bar.open, bar.high, bar.low, bar.close) for bar in (old, following)
            ],
            "metadata": SESSION,
            "received_at": clock[0],
        }
    )
    quote(service, clock, following.close)
    service.live.process_event()
    assert not observation(service, selected, ref, clock)["ready"]
    # A provider packet explicitly witnesses that 3D still uses the same bucket.
    old_pair = service.live._buckets[("BIST", "THYAO", "3D")][0]
    service.live._buckets[("BIST", "THYAO", "3D")] = (old_pair, clock[0] + 0.1)
    clock[0] += 1
    quote(service, clock, following.close + 0.1)
    service.live.process_event()
    assert observation(service, selected, ref, clock)["ready"]
    assert len(provider.calls) == 2
