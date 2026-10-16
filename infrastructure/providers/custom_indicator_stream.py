"""Bounded, multiplexed native TradingView charts and matching price events.

The upstream convenience stream uses one fixed ``$prices`` identifier. This
adapter gives every native series its own identifier and chart session. The
provider allows one price series per chart session; all of a symbol's sessions
and its single quote subscription still share one ordered WebSocket.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from contextlib import suppress

from infrastructure.providers.custom_indicator_history import SESSION_KEYS, validate_native_request

MAX_LIVE_SERIES = 8192
MAX_LIVE_CONNECTIONS = 4
MAX_CHARTS_PER_CONNECTION = 500
MAX_PROVIDER_SERIES = MAX_CHARTS_PER_CONNECTION * MAX_LIVE_CONNECTIONS
MAX_SERIES_PER_RECONCILE = 16
MAX_PACKET_BYTES = 2 * 1024 * 1024
TRANSPORT_TIMEOUT = 90


def _preferred_slot(member):
    market, symbol = member
    return (
        int.from_bytes(hashlib.sha256(f"{market}:{symbol}".encode()).digest()[:4])
        % MAX_LIVE_CONNECTIONS
    )


def plan_native_subscriptions(requested, previous_slots=None):
    """Plan whole symbols within verified per-socket capacity, without moving incumbents.

    The local 8,192 request budget is distinct from the provider's measured
    500 chart-session boundary on each of four sockets. A refused member is
    never partially subscribed or represented as admitted.
    """
    members = {}
    for key in set(requested):
        members.setdefault(key[:2], set()).add(key)
    previous = previous_slots or {}
    groups, slots, refused = {}, {}, set()
    for member in sorted(members):
        if member not in previous:
            continue
        slot = previous[member]
        if type(slot) is not int or not 0 <= slot < MAX_LIVE_CONNECTIONS:
            raise ValueError("Native bağlantı yerleşimi geçersiz.")
        keys = members[member]
        if len(groups.get(slot, ())) + len(keys) > MAX_CHARTS_PER_CONNECTION:
            refused.add(member)
            continue
        groups.setdefault(slot, set()).update(keys)
        slots[member] = slot
    for member in sorted(set(members) - set(previous)):
        keys = members[member]
        candidates = [
            slot
            for slot in range(MAX_LIVE_CONNECTIONS)
            if len(groups.get(slot, ())) + len(keys) <= MAX_CHARTS_PER_CONNECTION
        ]
        if not candidates:
            refused.add(member)
            continue
        preferred = _preferred_slot(member)
        slot = min(
            candidates,
            key=lambda value: (
                len(groups.get(value, ())),
                (value - preferred) % MAX_LIVE_CONNECTIONS,
            ),
        )
        groups.setdefault(slot, set()).update(keys)
        slots[member] = slot
    return groups, slots, refused


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def stream_class(base):
    class NativeStream(base):
        WS_URL = "wss://data.tradingview.com/socket.io/websocket"

        def __init__(self, token, callback, clock):
            super().__init__(auth_token=token)
            self.callback, self.clock = callback, clock
            self.sessions, self.series, self.quotes = {}, {}, {}
            self.sessions_by_id = {}
            self.members_by_full = {}
            self.daily_identity = {}
            self.counter = 0
            self.failed = self.auth_failed = self.closed = False
            self.failure_code = None
            self.protocol_errors = 0
            self.last_message = clock()
            self._should_reconnect = False

        @property
        def healthy(self):
            if self.clock() - self.last_message >= TRANSPORT_TIMEOUT:
                self.failed = True
            return self.is_connected and not (self.failed or self.closed)

        def _on_open(self, ws):
            self._ws = ws
            self._should_reconnect = False
            self._quote_session = self._generate_session_id("qs")
            try:
                ws.send(self._create_message("set_auth_token", [self._auth_token]))
                ws.send(self._create_message("quote_create_session", [self._quote_session]))
                ws.send(
                    self._create_message("quote_set_fields", [self._quote_session, "lp", "lp_time"])
                )
            except Exception:
                self.failed = True
                self._connected.clear()
                raise ValueError("Native gösterge bağlantısı başlatılamadı.") from None
            self.last_message = self.clock()
            self._connected.set()

        def _send(self, message):
            try:
                if not self.is_connected or self.closed or self.failed or self._ws is None:
                    raise ValueError
                if self._ws.send(message) is False:
                    raise ValueError
                return True
            except Exception:
                self.failed = True
                self._connected.clear()
                raise ValueError("Native gösterge bağlantısına veri gönderilemedi.") from None

        def _parse_packets(self, raw):
            """Strict bounded framing; never log malformed provider payloads."""
            packets, position = [], 0
            try:
                while position < len(raw):
                    if raw.startswith("~h~", position):
                        if not raw[position + 3 :].isdigit():
                            raise ValueError
                        packets.append(raw[position:])
                        break
                    if not raw.startswith("~m~", position):
                        raise ValueError
                    boundary = raw.find("~m~", position + 3)
                    if boundary < 0:
                        raise ValueError
                    length = int(raw[position + 3 : boundary])
                    position = boundary + 3
                    if not 0 < length <= MAX_PACKET_BYTES or position + length > len(raw):
                        raise ValueError
                    payload = raw[position : position + length]
                    position += length
                    packet = payload if payload.startswith("~h~") else json.loads(payload)
                    if not isinstance(packet, (dict, str)) or len(packets) >= 2048:
                        raise ValueError
                    packets.append(packet)
                return packets
            except (TypeError, ValueError, OverflowError):
                self.failed = True
                self._connected.clear()
                return []

        def _on_close(self, *_args):
            self.failed = True
            self._connected.clear()

        def _on_error(self, *_args):
            self.failed = True
            self._connected.clear()

        def _emit(self, event):
            if not self.closed and not self.failed:
                self.callback(event)

        def reconcile(self, wanted, *, additions_limit=None):
            """Called by the single control worker, never from a socket callback."""
            wanted = set(wanted)
            if len(wanted) > MAX_CHARTS_PER_CONNECTION:
                raise ValueError("Native bağlantı başına doğrulanmış mum kapasitesi aşıldı.")
            removed = []
            removed_quotes = []
            with self._lock:
                for sid, item in list(self.series.items()):
                    if item["key"] not in wanted:
                        removed.append((sid, item["session"]))
                        self.sessions.pop(item["key"], None)
                        self.sessions_by_id.pop(item["session"], None)
                        del self.series[sid]
                present = {item["key"] for item in self.series.values()}
                active_symbols = {key[:2] for key in wanted}
                for full, member in list(self.members_by_full.items()):
                    if member not in active_symbols:
                        removed_quotes.append(full)
                        self.members_by_full.pop(full)
                        self.quotes.pop(full, None)
                        self.daily_identity.pop(member, None)
            # Sending can block on the network. Never retain the receiver lock
            # across I/O: otherwise a large watchlist prevents native metadata,
            # quotes and heartbeat-following packets from being consumed.
            for sid, session in removed:
                self._send(self._create_message("remove_series", [session, sid]))
                self._send(self._create_message("chart_delete_session", [session]))
            for full in removed_quotes:
                self._send(
                    self._create_message("quote_remove_symbols", [self._quote_session, full])
                )
            additions = sorted(wanted - present)
            if additions_limit is not None:
                additions = additions[:additions_limit]
            for market, symbol, timeframe in additions:
                exchange = "BIST" if market == "BIST" else "BINANCE"
                member = market, symbol
                full = f"{exchange}:{symbol}"
                with self._lock:
                    session = self._generate_session_id("cs")
                    item = {"id": session, "full": full, "metadata": {}}
                    self.sessions[(market, symbol, timeframe)] = item
                    self.sessions_by_id[session] = item
                    add_quote = full not in self.members_by_full
                    if add_quote:
                        self.members_by_full[full] = member
                    self.counter += 1
                    sid = f"r{self.counter}"
                    item["series_id"] = sid
                    self.series[sid] = {
                        "key": (market, symbol, timeframe),
                        "session": item["id"],
                        "rows": {},
                        "complete": False,
                    }
                self._send(self._create_message("chart_create_session", [session, ""]))
                config = json.dumps({"symbol": full, "adjustment": "splits", "session": "regular"})
                self._send(self._create_message("resolve_symbol", [session, "sym", f"={config}"]))
                if add_quote:
                    self._send(
                        self._create_message("quote_add_symbols", [self._quote_session, full])
                    )
                self._send(
                    self._create_message("create_series", [session, sid, "s1", "sym", timeframe, 2])
                )

        def _on_message(self, ws, message):
            if self.closed or self.failed:
                return
            if (
                len(message) > MAX_PACKET_BYTES
                or self.clock() - self.last_message >= TRANSPORT_TIMEOUT
            ):
                self.failed = True
                return
            self.last_message = self.clock()
            for packet in self._parse_packets(message):
                if isinstance(packet, str) and packet.startswith("~h~"):
                    self._handle_heartbeat(packet)
                    continue
                if not isinstance(packet, dict):
                    continue
                method, params = packet.get("m"), packet.get("p", [])
                if not isinstance(params, list):
                    continue
                if method in {"critical_error", "protocol_error"}:
                    self.failed = True
                    self.protocol_errors += 1
                    self.auth_failed = any(
                        isinstance(value, str)
                        and any(
                            marker in value.lower()
                            for marker in (
                                "authentication",
                                "auth_token",
                                "auth token",
                                "unauthorized",
                            )
                        )
                        for value in params
                    )
                    # Only fixed categories cross the provider boundary. Error
                    # arguments can contain session IDs or other private data.
                    if self.auth_failed:
                        self.failure_code = "authentication_failed"
                    elif any(
                        isinstance(value, str) and "max sessions rate reached" in value.lower()
                        for value in params
                    ):
                        self.failure_code = "session_rate_limited"
                    elif any(
                        isinstance(value, str)
                        and "max charts per connection reached" in value.lower()
                        for value in params
                    ):
                        self.failure_code = "chart_capacity_exceeded"
                    else:
                        self.failure_code = f"provider_{method}"
                    self._connected.clear()
                    return
                events = []
                with self._lock:
                    if method in {"symbol_error", "series_error"}:
                        rejected = [
                            item
                            for sid, item in self.series.items()
                            if params
                            and item["session"] == params[0]
                            and (method == "symbol_error" or len(params) > 1 and sid == params[1])
                        ]
                        for item in rejected:
                            item["rejected"] = True
                            events.append({"kind": "rejected", "key": item["key"]})
                    elif (
                        method == "symbol_resolved"
                        and len(params) >= 3
                        and isinstance(params[2], dict)
                    ):
                        item = self.sessions_by_id.get(params[0])
                        if item is not None:
                            item["metadata"] = {
                                key: value
                                for key in SESSION_KEYS
                                if isinstance((value := params[2].get(key)), str)
                                and len(value) <= 32768
                            }
                            series = self.series.get(item["series_id"])
                            if series and series["complete"]:
                                event = self._bar_event(series)
                                if event is not None:
                                    events.append(event)
                    elif (
                        method in {"timescale_update", "du"}
                        and len(params) >= 2
                        and isinstance(params[1], dict)
                    ):
                        for sid, data in params[1].items():
                            item = self.series.get(sid)
                            if (
                                item is None
                                or item.get("rejected")
                                or item["session"] != params[0]
                                or not isinstance(data, dict)
                            ):
                                continue
                            rows = data.get("s", data.get("st", []))
                            if not isinstance(rows, list) or len(rows) > 100:
                                self.failed = True
                                return
                            for raw in rows:
                                values = raw.get("v") if isinstance(raw, dict) else None
                                if not isinstance(values, list) or len(values) < 5:
                                    continue
                                values = tuple(_number(value) for value in values[:5])
                                if any(value is None or value <= 0 for value in values):
                                    self.failed = True
                                    return
                                stamp, op, hi, lo, cl = values
                                if hi < max(op, lo, cl) or lo > min(op, hi, cl):
                                    self.failed = True
                                    return
                                item["rows"][stamp] = values
                            item["rows"] = {
                                stamp: item["rows"][stamp] for stamp in sorted(item["rows"])[-2:]
                            }
                            if item["complete"]:
                                event = self._bar_event(item)
                                if event is not None:
                                    events.append(event)
                    elif method == "series_completed" and len(params) >= 2:
                        item = self.series.get(params[1])
                        if item and item["session"] == params[0]:
                            item["complete"] = True
                            event = self._bar_event(item)
                            if event is not None:
                                events.append(event)
                    elif method == "qsd" and len(params) >= 2 and isinstance(params[1], dict):
                        data = params[1]
                        full, values = data.get("n"), data.get("v")
                        if data.get("s") != "ok" or not isinstance(values, dict):
                            continue
                        member = self.members_by_full.get(full)
                        if member is None:
                            continue
                        quote = self.quotes.setdefault(full, {})
                        quote.update(
                            {key: values[key] for key in ("lp", "lp_time") if key in values}
                        )
                        if not {"lp", "lp_time"}.intersection(values):
                            continue
                        price, source = _number(quote.get("lp")), _number(quote.get("lp_time"))
                        if price is not None and source is not None:
                            events.append(
                                {
                                    "kind": "quote",
                                    "member": member,
                                    "price": price,
                                    "source_timestamp": source,
                                    "received_at": self.clock(),
                                }
                            )
                for event in events:
                    self._emit(event)

        def _bar_event(self, item):
            rows = tuple(item["rows"].values())
            metadata = self.sessions[item["key"]]["metadata"].copy()
            member = item["key"][:2]
            if item["key"][0] == "BIST" and item["key"][2] == "1D" and rows:
                self.daily_identity[member] = rows[-1][0]
            # Current prices arrive through the ordered quote subscription.
            # Native witnesses need the full closed predecessor plus the open
            # bar's identity/O/H/L, not every change of its developing Close.
            # Keep all wire rows above so a later rollover uses the last close.
            signature = (
                rows[:-1],
                rows[-1][:4] if rows else (),
                tuple(sorted(metadata.items())),
                # After an observed native 1D rollover, a real new HTF packet
                # must witness that its open bucket still applies. Do not emit
                # cached HTF rows merely because the daily identity changed.
                self.daily_identity.get(member),
            )
            if item.get("emitted_signature") == signature:
                return None
            item["emitted_signature"] = signature
            return {
                "kind": "bars",
                "key": item["key"],
                "rows": rows,
                "metadata": metadata,
                "received_at": self.clock(),
            }

        def disconnect(self):
            self.closed = True
            super().disconnect()

    return NativeStream


class NativeStreamPool:
    """Fixed connection ceiling, dynamic subscriptions and no hidden reconnect."""

    def __init__(self, base, token, epoch, callback, *, clock=None):
        self._class = stream_class(base)
        self._token, self.epoch, self._callback = token, epoch, callback
        self._clock = clock or time.time
        self._streams = {}
        self._wanted_by_slot = {}
        self._wanted_by_member = {}
        self._member_slots = {}
        self.closed = False
        self._lock = threading.Lock()

    @property
    def connected(self):
        return (
            not self.closed
            and bool(self._streams)
            and all(stream.healthy for stream in tuple(self._streams.values()))
        )

    @property
    def auth_failed(self):
        return any(stream.auth_failed for stream in tuple(self._streams.values()))

    @staticmethod
    def _slot(member):
        return _preferred_slot(member)

    @property
    def needs_reconcile(self):
        if self.closed:
            return False
        for slot, wanted in tuple(self._wanted_by_slot.items()):
            stream = self._streams.get(slot)
            if stream is None:
                return True
            with stream._lock:
                if set(stream.sessions) != wanted:
                    return True
        return False

    def member_ready(self, member):
        """Transport admission only; callers must also verify native bar witnesses."""
        member = tuple(member)
        slot = self._member_slots.get(member)
        stream = self._streams.get(slot)
        if self.closed or stream is None or not stream.healthy:
            return False
        wanted = self._wanted_by_member.get(member, set())
        with stream._lock:
            return bool(wanted) and all(key in stream.sessions for key in wanted)

    def configure(self, requested, *, member_slots=None):
        requested = sorted(set(requested))
        if len(requested) > MAX_LIVE_SERIES:
            raise ValueError("Native canlı gösterge abonelik sınırı aşıldı.")
        members = {}
        for market, symbol, timeframe in requested:
            exchange = "BIST" if market == "BIST" else "BINANCE"
            validate_native_request(symbol, exchange, timeframe, 2)
            members.setdefault((market, symbol), set()).add((market, symbol, timeframe))
        if member_slots is None:
            groups, member_slots, refused = plan_native_subscriptions(requested, self._member_slots)
            if refused:
                raise ValueError("Native sağlayıcı kapasitesi aşıldı; semboller planlanamadı.")
        else:
            if set(member_slots) != set(members):
                raise ValueError("Native bağlantı yerleşimi sembollerle eşleşmiyor.")
            groups = {}
            for member, slot in member_slots.items():
                if type(slot) is not int or not 0 <= slot < MAX_LIVE_CONNECTIONS:
                    raise ValueError("Native bağlantı yerleşimi geçersiz.")
                if member in self._member_slots and self._member_slots[member] != slot:
                    raise ValueError(
                        "Native sembol bağlantısı devamlılık sıfırlanmadan değiştirilemez."
                    )
                groups.setdefault(slot, set()).update(members[member])
            if any(len(wanted) > MAX_CHARTS_PER_CONNECTION for wanted in groups.values()):
                raise ValueError("Native bağlantı başına doğrulanmış mum kapasitesi aşıldı.")
        # Every plan is validated before transport creation/removal or writes.
        self._wanted_by_slot = groups
        self._wanted_by_member = members
        self._member_slots = dict(member_slots)
        for slot in list(self._streams):
            if slot not in groups:
                self._streams.pop(slot).disconnect()
        for slot, wanted in groups.items():
            stream = self._streams.get(slot)
            if stream is None:
                stream = self._class(self._token, self._callback, self._clock)
                self._streams[slot] = stream
                stream.connect(timeout=5)
                stream._should_reconnect = False
            if not stream.healthy:
                raise ValueError("Native canlı gösterge bağlantısı kesildi.")
            # A control turn starts only a bounded number of chart sessions per
            # socket. Existing quotes and series keep flowing while a large
            # watchlist is admitted over subsequent turns.
            stream.reconcile(wanted, additions_limit=MAX_SERIES_PER_RECONCILE)

    def status(self):
        return {
            "connections": len(self._streams),
            "connected": sum(stream.healthy for stream in tuple(self._streams.values())),
            "subscriptions": sum(len(stream.series) for stream in tuple(self._streams.values())),
            "subscriptions_pending": sum(map(len, self._wanted_by_slot.values()))
            - sum(len(stream.series) for stream in tuple(self._streams.values())),
            "protocol_errors": sum(
                stream.protocol_errors for stream in tuple(self._streams.values())
            ),
            "failure_codes": sorted(
                {
                    stream.failure_code
                    for stream in tuple(self._streams.values())
                    if stream.failure_code
                }
            ),
        }

    def close(self):
        self.closed = True
        for stream in list(self._streams.values()):
            with suppress(Exception):
                stream.disconnect()
        self._streams.clear()
        self._wanted_by_slot.clear()
        self._wanted_by_member.clear()
        self._member_slots.clear()
