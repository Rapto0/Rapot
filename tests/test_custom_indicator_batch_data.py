"""Batch prefetch preserves native validation, account boundaries and seed atomicity."""

from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

from application.services.borsapy_gateway import BorsapyGateway, BorsapyGatewayError
from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_advanced_alarm_gateway import Module, authenticate
from tests.test_custom_indicator_data import NOW, Provider, frame, rule


class BatchProvider(Provider):
    def __init__(self):
        super().__init__()
        self.batches = []
        self.hook = lambda: None

    def custom_indicator_histories(self, symbol, *, exchange, requests):
        self.batches.append((symbol, exchange, requests.copy()))
        self.hook()
        return {tf: self._frame(tf) for tf in requests}

    def _frame(self, timeframe):
        result = self.data.copy()
        result.attrs["native_timeframe"] = timeframe
        return result


def service_for(provider):
    provider.data = frame(count=519)
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    selected = rule()
    selected["trigger"] = "intrabar"
    selected["condition"]["left"].update(
        indicator="smi_votes", inputs={f"en{i}": True for i in range(1, 11)}
    )
    service.configure([selected])
    return service, service._next_job()


def test_batch_seed_equals_sequential_native_path_and_reuses_cached_frames():
    sequential, first_job = service_for(Provider())
    sequential.process(*first_job)
    provider = BatchProvider()
    service, job = service_for(provider)
    service.process(*job)
    assert not provider.calls and len(provider.batches) == 1
    assert len(provider.batches[0][2]) == len(sequential.provider.calls) == 10
    expected = sequential.live._compiled[first_job[0]]
    actual = service.live._compiled[job[0]]
    assert actual["buckets"] == expected["buckets"]
    assert actual["evaluator"].rows == expected["evaluator"].rows
    assert service._results[job[0]]["digest"] == sequential._results[first_job[0]]["digest"]
    service.process(*job)
    assert len(provider.batches) == 1
    for timeframe in ("2D", "3D"):
        service._native.pop(("BIST", "THYAO", timeframe))
    service.process(*job)
    assert set(provider.batches[-1][2]) == {"2D", "3D"}
    assert len(provider.batches) == 2 and not provider.calls


def test_batch_preserves_shared_requested_count_after_raw_eviction():
    provider = BatchProvider()
    service, job = service_for(provider)
    service.process(*job)
    native_key = ("BIST", "THYAO", "2D")
    service._history_summaries[native_key] = replace(
        service._history_summaries[native_key], requested=800
    )
    service._native.pop(native_key)
    service.process(*job)
    assert provider.batches[-1][2] == {"2D": 800}
    assert service._native[native_key].requested == 800


def test_large_native_demand_splits_without_exceeding_total_batch_memory_bound():
    provider = BatchProvider()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    demand = {f"{i}D": 2000 for i in range(1, 12)}
    entries = service._native_entries("BIST", "THYAO", demand, 1, (0, 0))
    assert set(entries) == set(demand)
    assert [len(requests) for _, _, requests in provider.batches] == [6, 5]
    assert all(sum(requests.values()) <= 12000 for _, _, requests in provider.batches)
    assert not provider.calls


@pytest.mark.parametrize("change", ["gap", "account", "removed", "stopped"])
def test_batch_fetched_before_source_change_cannot_install_or_cache_old_seed(change):
    provider = BatchProvider()
    service, job = service_for(provider)

    def changed():
        if change == "gap":
            service.live_gap("Synthetic source gap", job[0][:2])
        elif change == "account":
            provider.generation += 1
        elif change == "removed":
            service.configure([])
        else:
            service._stop.set()

    provider.hook = changed
    service.process(*job)
    assert not service.live.has_seed(job[0], provider.memory_epoch())
    assert not service._native
    assert job[0] not in service._results or service._results[job[0]]["error"]
    if change == "gap":
        assert job[0] in service._seed_queued


@pytest.mark.parametrize("mode", ["missing", "wrong_timeframe", "bad_ohlc"])
def test_bad_batch_cannot_publish_partial_indicator_seed(mode):
    provider = BatchProvider()
    service, job = service_for(provider)
    original = provider.custom_indicator_histories

    def broken(*args, **kwargs):
        frames = original(*args, **kwargs)
        if mode == "missing":
            frames.pop("2D")
        elif mode == "wrong_timeframe":
            frames["2D"].attrs["native_timeframe"] = "3D"
        else:
            frames["2D"].iloc[0, 1] = -1
        return frames

    provider.custom_indicator_histories = broken
    service.process(*job)
    assert job[0] not in service.live._compiled
    assert service._results[job[0]]["error"]
    assert service._history_retries[job[0]] == NOW + 30


def test_gateway_batch_is_atomic_and_checks_account_after_all_frames(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        borsapy_credentials_path=str(tmp_path / "credentials.enc"),
        jwt_secret_key="synthetic-account-key-never-a-real-key",
        database_path=str(tmp_path / "main.sqlite3"),
        borsapy_max_streams=3,
        borsapy_stream_idle_seconds=120,
    )
    gateway = BorsapyGateway(settings, loader=lambda: Module(), version_reader=lambda: "0.11.0")
    authenticate(gateway)
    frames = {"1D": frame(), "2D": frame("2D")}
    transport = SimpleNamespace(get_histories=lambda *_args, **_kw: frames, close=lambda: None)
    monkeypatch.setattr(
        "infrastructure.providers.native_indicator_history.NativeIndicatorHistory",
        lambda: transport,
    )
    try:
        result = gateway.custom_indicator_histories(
            "THYAO", exchange="BIST", requests={"1D": 60, "2D": 60}
        )
        for tf in frames:
            pd.testing.assert_frame_equal(result[tf], frames[tf][["Open", "High", "Low", "Close"]])
            assert result[tf].attrs["native_timeframe"] == tf
        frames["2D"].iloc[0, 1] = -1
        with pytest.raises(BorsapyGatewayError) as error:
            gateway.custom_indicator_histories(
                "THYAO", exchange="BIST", requests={"1D": 60, "2D": 60}
            )
        assert error.value.status_code == 502
        frames["2D"] = frame("2D")
        original = gateway._validated_custom_history

        def changed_account(frame):
            result = original(frame)
            if frame.attrs["native_timeframe"] == "2D":
                gateway.clear()
            return result

        monkeypatch.setattr(gateway, "_validated_custom_history", changed_account)
        with pytest.raises(BorsapyGatewayError) as error:
            gateway.custom_indicator_histories(
                "THYAO", exchange="BIST", requests={"1D": 60, "2D": 60}
            )
        assert error.value.status_code == 409
    finally:
        gateway.close()
