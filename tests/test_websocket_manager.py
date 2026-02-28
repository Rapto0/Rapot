import pytest

from websocket_manager import BinanceWebSocketManager


@pytest.mark.asyncio
async def test_listen_skips_when_websocket_is_not_connected():
    manager = BinanceWebSocketManager()

    await manager._listen()

    assert manager._ws is None


@pytest.mark.asyncio
async def test_handle_message_processes_mini_ticker_array_payload():
    manager = BinanceWebSocketManager()
    events: list[tuple[str, dict]] = []

    async def fake_notify(event: str, data: dict):
        events.append((event, data))

    manager._notify = fake_notify  # type: ignore[method-assign]

    await manager._handle_message(
        {
            "stream": "!miniTicker@arr",
            "data": [
                {"s": "BTCUSDT", "c": "100", "h": "110", "l": "90", "v": "10", "q": "1000"},
                {"s": "ETHUSDT", "c": "200", "h": "210", "l": "190", "v": "20", "q": "2000"},
            ],
        }
    )

    assert [event for event, _ in events] == ["ticker", "ticker"]
    assert events[0][1]["symbol"] == "BTCUSDT"
    assert events[1][1]["symbol"] == "ETHUSDT"


@pytest.mark.asyncio
async def test_handle_message_ignores_unexpected_payload_types():
    manager = BinanceWebSocketManager()
    events: list[tuple[str, dict]] = []

    async def fake_notify(event: str, data: dict):
        events.append((event, data))

    manager._notify = fake_notify  # type: ignore[method-assign]

    await manager._handle_message({"stream": "!miniTicker@arr", "data": ["bad-payload", 123]})

    assert events == []
