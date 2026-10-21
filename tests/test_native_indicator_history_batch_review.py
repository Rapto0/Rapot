"""Independent adversarial checks for the bounded native-history batch path."""

import threading
import time

import pytest

from infrastructure.providers.native_indicator_history import NativeIndicatorHistory, _message
from tests.test_native_indicator_history import Wire

TIMEFRAMES = ("1D", "2D", "3D", "4D", "5D", "6D", "1W", "2W", "3W", "1M")


def batch(history, requests=None, **kwargs):
    return history.get_histories(
        "THYAO",
        exchange="BIST",
        requests=requests if requests is not None else dict.fromkeys(TIMEFRAMES, 519),
        token="synthetic-review-token",
        epoch=1,
        **kwargs,
    )


class ReversedWire(Wire):
    """Finish all series out of order, with different lengths and prices."""

    def __init__(self):
        super().__init__()
        self.series = []

    def sent(self, socket, packet):
        if not isinstance(packet, dict) or packet["m"] != "create_series":
            return super().sent(socket, packet)
        self.series.append(packet["p"])
        if len(self.series) != 10:
            return
        for index in reversed(range(10)):
            session, series, _, _, _, count, _ = self.series[index]
            rows = [
                {"v": [1700000000 + i * 86400, 100 + index, 102 + index, 98 + index, 101 + index]}
                for i in range(count)
            ]
            socket.push("timescale_update", [session, {series: {"s": rows}}])
            socket.push("series_completed", [session, series])


def test_ten_concurrent_charts_keep_each_native_timeframe_and_retire_all():
    wire = ReversedWire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=3)
    requests = {tf: 500 + index for index, tf in enumerate(TIMEFRAMES)}
    try:
        frames = batch(history, requests)
        assert frames.keys() == requests.keys()
        for index, (tf, count) in enumerate(requests.items()):
            assert len(frames[tf]) == count
            assert frames[tf].attrs["native_timeframe"] == tf
            assert frames[tf]["Close"].tolist() == [101 + index] * count
            assert list(frames[tf].columns) == ["Open", "High", "Low", "Close"]
        status = history.status()
        assert len(wire.sockets) == status["connections_opened"] == 1
        assert wire.max_charts == 10
        assert status["charts_created"] == status["charts_retired"] == 10
        assert status["requests_completed"] == 10 and status["batches_completed"] == 1
        assert status["active_requests"] == status["active_charts"] == 0
        assert not wire.sockets[0].charts
    finally:
        history.close()


@pytest.mark.parametrize("fault", ["half", "series_error", "symbol_error", "wrong_series"])
def test_one_failed_member_discards_completed_siblings_and_reconnects(fault):
    wire = Wire()
    original = wire.sent

    def sent(socket, packet):
        selected = isinstance(packet, dict) and packet["m"] == "create_series"
        wire.mode = fault if selected and packet["p"][4] == "3D" else "ok"
        original(socket, packet)

    wire.sent = sent
    history = NativeIndicatorHistory(ws_factory=wire, timeout=0.5)
    try:
        with pytest.raises(ValueError, match="^Native indicator history unavailable$"):
            batch(history, {"1D": 4, "2D": 4, "3D": 4})
        status = history.status()
        assert status["requests_completed"] == status["batches_completed"] == 0
        assert status["requests_failed"] == 3 and status["batches_failed"] == 1
        assert status["active_requests"] == status["active_charts"] == 0
        assert wire.sockets[0].closed.is_set() and not wire.sockets[0].charts
        wire.sent = original
        wire.mode = "ok"
        result = batch(history, {"1D": 4, "2D": 4})
        assert set(result) == {"1D", "2D"} and len(wire.sockets) == 2
    finally:
        history.close()


@pytest.mark.parametrize(
    "requests",
    [{}, {f"{i}D": 2 for i in range(1, 12)}, {"1D": 6000, "2D": 6001}, {"1D": True}],
)
def test_invalid_batch_is_rejected_before_opening_any_socket(requests):
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire)
    try:
        with pytest.raises(ValueError):
            batch(history, requests)
        assert not wire.sockets and history.status()["active_requests"] == 0
    finally:
        history.close()


def test_wire_byte_limit_is_shared_by_the_whole_batch(monkeypatch):
    limit = 1800
    monkeypatch.setattr("infrastructure.providers.native_indicator_history.MAX_WIRE_BYTES", limit)
    wire = Wire()
    original = wire.sent
    padding = _message("ignored_message", ["x" * 800])
    assert len(padding.encode()) < limit

    def sent(socket, packet):
        if isinstance(packet, dict) and packet["m"] == "create_series":
            socket.incoming.put(padding)
        original(socket, packet)

    wire.sent = sent
    history = NativeIndicatorHistory(ws_factory=wire, timeout=1)
    try:
        with pytest.raises(ValueError, match="^Native indicator history unavailable$"):
            batch(history, {"1D": 2, "2D": 2})
        assert history.status()["charts_created"] == 2
        assert history.status()["requests_completed"] == 0
        assert wire.sockets[0].closed.is_set()
    finally:
        history.close()


def test_account_close_during_batch_creation_does_not_open_remaining_charts():
    wire = Wire()
    original = wire.sent
    second_created, release = threading.Event(), threading.Event()
    errors = []

    def sent(socket, packet):
        if isinstance(packet, dict) and packet["m"] == "create_series" and packet["p"][4] == "2D":
            second_created.set()
            assert release.wait(2)
        original(socket, packet)

    wire.sent = sent
    history = NativeIndicatorHistory(ws_factory=wire, timeout=5)

    def run():
        try:
            batch(history)
        except ValueError as exc:
            errors.append(str(exc))

    caller = threading.Thread(target=run)
    caller.start()
    try:
        assert second_created.wait(1)
        history.close()
        assert wire.sockets[0].closed.is_set()
        release.set()
        caller.join(timeout=1)
        assert not caller.is_alive()
        assert errors == ["Native indicator history unavailable"]
        state = history.status()
        assert state["charts_created"] == 2 and state["requests_completed"] == 0
        assert state["active_requests"] == state["active_charts"] == 0
    finally:
        release.set()
        history.close()
        caller.join(timeout=1)


def test_chart_creation_rate_limit_continues_across_batch_boundary():
    wire = Wire()
    original = wire.sent
    starts = []

    def sent(socket, packet):
        if isinstance(packet, dict) and packet["m"] == "chart_create_session":
            starts.append(time.monotonic())
        original(socket, packet)

    wire.sent = sent
    history = NativeIndicatorHistory(ws_factory=wire, timeout=2)
    try:
        for _ in range(2):
            batch(history, {"1D": 3, "2D": 3, "3D": 3})
        assert len(starts) == 6
        assert all(right - left >= 0.095 for left, right in zip(starts, starts[1:]))
        assert history.status()["batches_completed"] == 2
        assert len(wire.sockets) == 1 and wire.max_charts == 3
    finally:
        history.close()


def test_delayed_chart_send_does_not_allow_a_catchup_creation_burst():
    wire = Wire()
    original = wire.sent
    delivered = []

    def sent(socket, packet):
        if isinstance(packet, dict) and packet["m"] == "chart_create_session":
            if not delivered:
                # A blocked write or heartbeat send lock may outlast the
                # intended interval. Rate limiting must follow its delivery.
                time.sleep(0.15)
            delivered.append(time.monotonic())
        original(socket, packet)

    wire.sent = sent
    history = NativeIndicatorHistory(ws_factory=wire, timeout=2)
    try:
        batch(history, {"1D": 3, "2D": 3, "3D": 3})
        assert len(delivered) == 3
        assert all(right - left >= 0.095 for left, right in zip(delivered, delivered[1:]))
    finally:
        history.close()
