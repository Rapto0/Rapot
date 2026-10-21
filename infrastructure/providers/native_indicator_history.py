"""One reusable, bounded WebSocket for the single native-history worker.

This transport is independent of live quote/chart sessions. Each request owns
one unique chart until ``series_completed``; no partial response is published.
The gateway still validates OHLC and account identity before returning a frame.
"""

import json
import threading
import time
import uuid
from contextlib import suppress

from infrastructure.providers.custom_indicator_history import (
    MAX_WIRE_BYTES,
    SESSION_KEYS,
    validate_native_request,
)

MIN_REQUEST_INTERVAL = 0.1  # At most ten chart creations/second on this socket.
HISTORY_TIMEOUT = 10.0


def _packet(payload):
    return f"~m~{len(payload)}~m~{payload}"


def _message(method, params):
    return _packet(json.dumps({"m": method, "p": params}, separators=(",", ":")))


def _stop_socket(ws):
    # Account revocation must not wait for the peer's close handshake or for
    # a writer holding websocket-client's send lock. Abort the dedicated TCP
    # stream first, then let WebSocketApp finish its local cleanup.
    ws.keep_running = False
    socket = getattr(ws, "sock", None)
    if socket is not None:
        with suppress(Exception):
            socket.abort()
        with suppress(Exception):
            socket.shutdown()
    with suppress(Exception):
        ws.close()


def _packets(raw):
    if not isinstance(raw, str) or len(raw.encode()) > MAX_WIRE_BYTES:
        raise ValueError("Native history framing invalid")
    position = 0
    count = 0
    while position < len(raw):
        if raw.startswith("~h~", position):
            if not raw[position + 3 :].isdigit():
                raise ValueError("Native history heartbeat invalid")
            yield raw[position:]
            return
        if not raw.startswith("~m~", position):
            raise ValueError("Native history framing invalid")
        boundary = raw.find("~m~", position + 3)
        if boundary < 0:
            raise ValueError("Native history framing invalid")
        length = int(raw[position + 3 : boundary])
        position = boundary + 3
        if not 0 < length <= MAX_WIRE_BYTES or position + length > len(raw) or count >= 2048:
            raise ValueError("Native history framing capacity exceeded")
        payload = raw[position : position + length]
        position += length
        count += 1
        if payload.startswith("~h~"):
            if not payload[3:].isdigit():
                raise ValueError("Native history heartbeat invalid")
            yield payload
        else:
            value = json.loads(payload)
            if not isinstance(value, dict):
                raise ValueError("Native history packet invalid")
            yield value


class NativeIndicatorHistory:
    def __init__(self, *, ws_factory=None, timeout=HISTORY_TIMEOUT, clock=time.monotonic):
        self._factory = ws_factory
        self._timeout = timeout
        self._clock = clock
        self._condition = threading.Condition(threading.RLock())
        self._request_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._ws = self._thread = None
        self._generation = 0
        self._connected = False
        self._closed = False
        self._failure = None
        self._token = self._epoch = None
        self._request = None
        self._next_request = 0.0
        self._opened = self._completed = self._failed = self._heartbeats = 0
        self._created = self._retired = 0

    def status(self):
        with self._condition:
            return {
                "connected": self._connected and not self._failure and not self._closed,
                "active_requests": int(self._request is not None),
                "connections_opened": self._opened,
                "requests_completed": self._completed,
                "requests_failed": self._failed,
                "charts_created": self._created,
                "charts_retired": self._retired,
                "heartbeats": self._heartbeats,
                "closed": self._closed,
            }

    def _fail(self, generation, reason):
        with self._condition:
            if generation == self._generation:
                self._failure = reason
                self._connected = False
                self._condition.notify_all()

    def _send(self, ws, text):
        with self._send_lock:
            if ws.send(text) is False:
                raise ValueError("Native history send failed")

    def _on_message(self, generation, ws, raw):
        try:
            with self._condition:
                if generation != self._generation or self._closed or self._failure:
                    return
                request = self._request
                if request is not None:
                    request["wire_bytes"] += len(raw.encode())
                    if request["wire_bytes"] > MAX_WIRE_BYTES:
                        raise ValueError
            for packet in _packets(raw):
                if isinstance(packet, str):
                    self._send(ws, _packet(packet))
                    with self._condition:
                        self._heartbeats += 1
                    continue
                method, params = packet.get("m"), packet.get("p", [])
                if not isinstance(params, list):
                    raise ValueError
                if method in {"critical_error", "protocol_error"}:
                    raise ValueError
                with self._condition:
                    if generation != self._generation or self._closed or self._failure:
                        return
                    request = self._request
                    if (
                        request is None
                        or request["complete"]
                        or not params
                        or params[0] != request["session"]
                    ):
                        continue
                    if method in {"symbol_error", "series_error"}:
                        raise ValueError
                    if method == "symbol_resolved":
                        if (
                            len(params) < 3
                            or params[1] != "symbol"
                            or not isinstance(params[2], dict)
                        ):
                            raise ValueError
                        request["metadata"] = {
                            key: value
                            for key in SESSION_KEYS
                            if isinstance((value := params[2].get(key)), str)
                            and len(value) <= 32768
                        }
                    elif method == "timescale_update":
                        if len(params) < 2 or not isinstance(params[1], dict):
                            raise ValueError
                        rows = params[1].get(request["series"], {}).get("s", [])
                        if not isinstance(rows, list) or len(rows) > request["bars"]:
                            raise ValueError
                        for row in rows:
                            values = row.get("v") if isinstance(row, dict) else None
                            if not isinstance(values, list) or len(values) < 5:
                                raise ValueError
                            stamp = float(values[0])
                            request["rows"][stamp] = tuple(values[1:5])
                        if len(request["rows"]) > request["bars"]:
                            raise ValueError
                    elif method == "series_completed":
                        if len(params) < 2 or params[1] != request["series"]:
                            continue
                        if (
                            request["metadata"] is None
                            or not 2 <= len(request["rows"]) <= request["bars"]
                        ):
                            raise ValueError
                        request["complete"] = True
                        self._condition.notify_all()
        except Exception:
            self._fail(generation, "Native history response invalid or unavailable")

    def _drop_transport(self):
        with self._condition:
            ws, thread = self._ws, self._thread
            self._generation += 1
            self._ws = None
            self._connected = False
            self._token = self._epoch = None
            self._condition.notify_all()
        if ws is not None:
            _stop_socket(ws)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)
        with self._condition:
            if thread is None or not thread.is_alive():
                self._thread = None

    def close(self):
        # May run under the gateway's account lock: never wait for a request.
        with self._condition:
            self._closed = True
            self._failure = "Native history cancelled"
            self._connected = False
            ws = self._ws
            self._condition.notify_all()
        if ws is not None:
            _stop_socket(ws)

    def _wait(self, predicate, deadline):
        with self._condition:
            while True:
                remaining = deadline - self._clock()
                if self._closed or self._failure or remaining <= 0:
                    raise ValueError("Native history cancelled, disconnected or timed out")
                if predicate():
                    return
                self._condition.wait(min(remaining, 0.1))

    def _connect(self, epoch, deadline):
        with self._condition:
            reconnect = self._epoch != epoch or not self._connected or self._failure
        if not reconnect:
            return
        self._drop_transport()
        with self._condition:
            if self._closed or self._thread is not None:
                raise ValueError("Native history transport cannot restart")
            self._failure = None
            generation = self._generation
            factory = self._factory
            if factory is None:
                import websocket

                factory = websocket.WebSocketApp

            def opened(_ws):
                # The dispatcher waits for readability separately; bound actual
                # frame reads/writes without changing process-global defaults.
                socket = getattr(_ws, "sock", None)
                if socket is not None:
                    socket.settimeout(self._timeout)
                with self._condition:
                    if generation == self._generation and not self._closed:
                        self._connected = True
                        self._condition.notify_all()
                        return
                # run_forever can begin after close/timeout and reset its own
                # keep_running flag. A late handshake must close the newly
                # created socket, not merely ignore its obsolete generation.
                _stop_socket(_ws)

            ws = factory(
                "wss://data.tradingview.com/socket.io/websocket?type=chart",
                on_open=opened,
                on_message=lambda socket, raw: self._on_message(generation, socket, raw),
                on_error=lambda *_args: self._fail(generation, "Native history transport failed"),
                on_close=lambda *_args: self._fail(generation, "Native history transport closed"),
            )
            self._ws = ws
            self._epoch = epoch
            self._opened += 1

            def receive():
                try:
                    with self._condition:
                        if self._closed or generation != self._generation:
                            return
                    ws.run_forever(origin="https://www.tradingview.com", reconnect=0)
                finally:
                    self._fail(generation, "Native history transport stopped")

            self._thread = threading.Thread(target=receive, name="native-history-ws", daemon=True)
            self._thread.start()
        self._wait(lambda: self._connected, deadline)

    def get_history(self, symbol, *, exchange, timeframe, bars, token, epoch):
        validate_native_request(symbol, exchange, timeframe, bars)
        if not token or token == "unauthorized_user_token":
            raise ValueError("Native history authentication required")
        if not self._request_lock.acquire(timeout=1):
            raise ValueError("Native history worker busy")
        try:
            deadline = self._clock() + self._timeout
            self._connect(epoch, deadline)
            self._wait(lambda: self._clock() >= self._next_request, deadline)
            with self._condition:
                ws = self._ws
                request = {
                    "session": "cs_" + uuid.uuid4().hex,
                    "series": "s_" + uuid.uuid4().hex,
                    "bars": bars,
                    "rows": {},
                    "metadata": None,
                    "wire_bytes": 0,
                    "complete": False,
                }
                self._request = request
            if token != self._token:
                self._send(ws, _message("set_auth_token", [token]))
                self._token = token
            session, series = request["session"], request["series"]
            self._next_request = self._clock() + MIN_REQUEST_INTERVAL
            self._send(ws, _message("chart_create_session", [session, ""]))
            self._created += 1
            descriptor = json.dumps(
                {"symbol": f"{exchange}:{symbol}", "adjustment": "splits", "session": "regular"},
                separators=(",", ":"),
            )
            self._send(ws, _message("resolve_symbol", [session, "symbol", "=" + descriptor]))
            self._send(
                ws,
                _message("create_series", [session, series, "s1", "symbol", timeframe, bars, ""]),
            )
            self._wait(lambda: request["complete"], deadline)
            self._send(ws, _message("remove_series", [session, series]))
            self._send(ws, _message("chart_delete_session", [session]))
            self._retired += 1
            import pandas as pd

            items = sorted(request["rows"].items())
            frame = pd.DataFrame(
                [values for _, values in items],
                index=pd.to_datetime([stamp for stamp, _ in items], unit="s", utc=True),
                columns=["Open", "High", "Low", "Close"],
            )
            frame.index = frame.index.tz_convert("Europe/Istanbul")
            frame.attrs.update(
                native_timeframe=timeframe, session_metadata=request["metadata"].copy()
            )
            self._completed += 1
            return frame
        except Exception:
            self._failed += 1
            self._drop_transport()
            raise ValueError("Native indicator history unavailable") from None
        finally:
            with self._condition:
                self._request = None
            self._request_lock.release()
