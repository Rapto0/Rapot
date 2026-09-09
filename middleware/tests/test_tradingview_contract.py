"""Webhook boundaries and v1 identity, using isolated DBs and the fake broker only."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from middleware.domain.constants import MAX_BAR_INDEX, MAX_EVENT_TIMESTAMP_MS
from middleware.domain.events import TradingViewWebhookPayload
from middleware.infra.settings import settings
from middleware.infra.time import UTC, datetime_from_unix_ms
from middleware.repositories.signal_repository import SignalRepository


@pytest.mark.parametrize("route", ["/webhooks/tradingview", "/admin/replay-signal"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("barTime", 0),
        ("barTime", -1),
        ("barTime", MAX_EVENT_TIMESTAMP_MS + 1),
        ("barTime", 2**63),
        ("barTime", True),
        ("barTime", 1713772800000.0),
        ("barTime", "1713772800000"),
        ("barIndex", -1),
        ("barIndex", MAX_BAR_INDEX + 1),
        ("barIndex", False),
        ("barIndex", 1.5),
        ("barIndex", "12345"),
    ],
)
def test_invalid_timestamp_or_index_never_reaches_processing(
    route, field, value, client, sample_buy_payload, monkeypatch
) -> None:
    processing = Mock(side_effect=AssertionError("invalid payload reached processing"))
    monkeypatch.setattr(
        "middleware.services.trading_service.TradingService.process_webhook", processing
    )
    payload = {**sample_buy_payload, field: value}
    body = {"payload": payload} if route.startswith("/admin") else payload

    response = client.post(route, json=body)

    assert response.status_code == 422
    processing.assert_not_called()
    assert client.get("/signals").json() == []
    assert client.get("/orders").json() == []


@pytest.mark.parametrize(
    "symbol",
    [
        "BTCUSDT.P",
        "BTCUSDT.PS",
        "BTC-USDT",
        "BINANCE:BTCUSDT",
        "BTC_USDT",
        "BТCUSDT",
        "btcuſdt",
        "ßUSDT",
        "btcusdı",
    ],
)
def test_non_spot_symbol_shapes_are_rejected_before_processing(
    symbol, client, sample_buy_payload, monkeypatch
) -> None:
    processing = Mock(side_effect=AssertionError("invalid symbol reached processing"))
    monkeypatch.setattr(
        "middleware.services.trading_service.TradingService.process_webhook", processing
    )

    response = client.post(
        "/webhooks/tradingview", json={**sample_buy_payload, "symbol": symbol, "ticker": symbol}
    )

    assert response.status_code == 422
    processing.assert_not_called()
    assert client.get("/signals").json() == []


@pytest.mark.parametrize("symbol", ["BTCUSDT", "1INCHUSDT", "ETHBTC", "  btcusdt  "])
def test_spot_symbol_normalization_preserves_base_and_quote(symbol, sample_buy_payload) -> None:
    payload = TradingViewWebhookPayload(
        **{**sample_buy_payload, "symbol": symbol, "ticker": symbol}
    )
    assert payload.symbol == payload.ticker == symbol.strip().upper()


@pytest.mark.parametrize(
    "timestamp_ms,expected",
    [
        (1, datetime(1970, 1, 1, 0, 0, 0, 1000, tzinfo=UTC)),
        (1713772800123, datetime(2024, 4, 22, 8, 0, 0, 123000, tzinfo=UTC)),
        (MAX_EVENT_TIMESTAMP_MS, datetime(9999, 12, 31, 23, 59, 59, 999000, tzinfo=UTC)),
    ],
)
def test_millisecond_boundaries_round_trip_through_webhook_and_storage(
    timestamp_ms, expected, client, sample_buy_payload
) -> None:
    assert datetime_from_unix_ms(timestamp_ms) == expected
    response = client.post(
        "/webhooks/tradingview",
        json={**sample_buy_payload, "barTime": timestamp_ms, "barIndex": MAX_BAR_INDEX},
    )

    assert response.status_code == 200
    stored = client.get("/signals").json()[0]
    assert datetime.fromisoformat(stored["bar_time"]).replace(tzinfo=UTC) == expected
    assert stored["bar_index"] == MAX_BAR_INDEX
    if timestamp_ms == MAX_EVENT_TIMESTAMP_MS:
        assert response.json()["status"] == "rejected"
        assert "future" in response.json()["risk_reason"]


@pytest.mark.parametrize(
    "offset_ms,expected_reason",
    [(-60_001, "freshness"), (-60_000, None), (0, None), (120_000, None), (120_001, "future")],
)
def test_freshness_uses_emission_time_with_exact_millisecond_boundaries(
    offset_ms, expected_reason, client, sample_buy_payload, monkeypatch
) -> None:
    now = datetime(2026, 9, 9, 12, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz)

    monkeypatch.setattr("middleware.services.trading_service.datetime", FrozenDateTime)
    settings.max_signal_age_seconds = 60
    settings.max_signal_future_skew_seconds = 120
    emission_time = now + timedelta(milliseconds=offset_ms)
    response = client.post(
        "/webhooks/tradingview",
        json={**sample_buy_payload, "barTime": int(emission_time.timestamp() * 1000)},
    )

    assert response.status_code == 200
    if expected_reason:
        assert response.json()["status"] == "rejected"
        assert expected_reason in response.json()["risk_reason"]
    else:
        assert response.json()["status"] == "filled"


def test_v1_hash_stays_compatible_with_preexisting_events(sample_buy_payload) -> None:
    original = TradingViewWebhookPayload(**sample_buy_payload)
    # Captured from the unchanged v1 implementation before the P1-3 validation changes.
    expected = "959a7aec4504d5259b46eab4a1e2f04e42e9d2b356dd442bb3ab2f929117f091"
    assert SignalRepository.build_event_hash(original) == expected
    equivalent = TradingViewWebhookPayload(
        **{
            **sample_buy_payload,
            "schemaVersion": 1,
            "source": "combo+hunter",
            "symbol": " btcusdt ",
            "ticker": "btcusdt",
            "signalCode": "h_bls",
            "timeframe": "1h",
        }
    )
    assert SignalRepository.build_event_hash(equivalent) == expected


@pytest.mark.parametrize(
    "change",
    [
        {"signalCode": "C_BLS"},
        {"barTime": 1713772800001},
        {"barIndex": 12346, "barTime": 1713859200000},
        {"price": "50000.0"},
        {"signalText": "A separately generated event"},
        {"timeframe": "60"},
    ],
    ids=[
        "different-code-same-bar",
        "new-emission-same-bar",
        "next-bar",
        "price-format",
        "text",
        "timeframe-alias",
    ],
)
def test_v1_distinct_buy_events_keep_separate_orders_and_tranches(
    change, client, sample_buy_payload
) -> None:
    first = client.post("/webhooks/tradingview", json=sample_buy_payload)
    second_payload = {**sample_buy_payload, **change}
    second = client.post("/webhooks/tradingview", json=second_payload)
    retry = client.post("/webhooks/tradingview", json=second_payload)

    assert first.status_code == second.status_code == retry.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "filled"
    assert second.json()["duplicate"] is False
    assert retry.json()["duplicate"] is True
    assert len(client.get("/signals").json()) == 2
    assert len(client.get("/orders").json()) == 2
    assert client.get("/positions").json()[0]["open_tranche_count"] == 2
