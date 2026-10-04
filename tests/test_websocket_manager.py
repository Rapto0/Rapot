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


def test_mini_ticker_uses_rolling_day_open_on_first_and_successive_packets():
    manager = BinanceWebSocketManager()
    first = manager._parse_mini_ticker({"s": "BTCUSDT", "c": "110", "o": "100"})
    second = manager._parse_mini_ticker({"s": "BTCUSDT", "c": "120", "o": "100"})
    shifted = manager._parse_mini_ticker({"s": "BTCUSDT", "c": "90", "o": "120"})
    assert (first.price_change, first.price_change_percent) == (10, 10)
    assert (second.price_change, second.price_change_percent) == (20, 20)
    assert (shifted.price_change, shifted.price_change_percent) == (-30, -25)
    unchanged = manager._parse_mini_ticker({"s": "BTCUSDT", "c": "90", "o": "90"})
    assert unchanged.price_change == unchanged.price_change_percent == 0


@pytest.mark.parametrize("opening", [None, "0", "-1", "bad", "nan", "inf", True])
def test_mini_ticker_unknown_day_open_preserves_price_but_not_invented_return(opening):
    manager = BinanceWebSocketManager()
    ticker = manager._parse_mini_ticker({"s": "BTCUSDT", "c": "110", "o": opening}).to_dict()
    assert ticker["price"] == 110
    assert ticker["priceChange"] is ticker["priceChangePercent"] is None
    missing = manager._parse_mini_ticker({"s": "BTCUSDT", "c": "110"}).to_dict()
    assert missing["priceChange"] is missing["priceChangePercent"] is None


@pytest.mark.parametrize("closing", ["0", "-1", "nan", "inf", True])
def test_invalid_mini_ticker_price_never_enters_cache(closing):
    manager = BinanceWebSocketManager()
    with pytest.raises(ValueError):
        manager._parse_mini_ticker({"s": "BTCUSDT", "c": closing, "o": "100"})
