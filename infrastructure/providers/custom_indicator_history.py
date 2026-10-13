"""Request-local TradingView native resolutions, with no default-daily fallback.

The existing borsapy adapter closes after its first timescale packet. Custom
history buffers bounded packets until the provider confirms the whole series,
and preserves only the session metadata needed to interpret native bar ends.
"""

import re

MAX_NATIVE_BARS = 12000
MAX_WIRE_BYTES = 12 * 1024 * 1024
SESSION_KEYS = ("timezone", "session", "session_regular", "session_holidays", "corrections")


def validate_native_request(symbol, exchange, timeframe, bars):
    pattern = r"[A-Z0-9]{1,20}" if exchange == "BIST" else r"[A-Z0-9]{2,20}USDT"
    if exchange not in {"BIST", "BINANCE"} or not re.fullmatch(pattern, symbol):
        raise ValueError("Özel gösterge sembolü desteklenmiyor.")
    match = re.fullmatch(r"([1-9][0-9]*)([SDWM]?)", timeframe)
    if not match:
        raise ValueError("Native gösterge periyodu desteklenmiyor.")
    number, unit = int(match[1]), match[2]
    valid = (
        number in {1, 5, 10, 15, 30, 45}
        if unit == "S"
        else number <= {"": 1440, "D": 365, "W": 52, "M": 12}[unit]
    )
    if (
        not valid
        or isinstance(bars, bool)
        or not isinstance(bars, int)
        or not 2 <= bars <= MAX_NATIVE_BARS
    ):
        raise ValueError("Native gösterge geçmişi kapasite sınırını aşıyor.")


def history_provider(token, timeframe, bars):
    from borsapy._providers.tradingview import TradingViewProvider

    class NativeHistory(TradingViewProvider):
        # Instance-specific subclass: never mutate borsapy's global dictionary.
        TIMEFRAMES = {timeframe: timeframe}

        def __init__(self):
            self._session_id = self._chart_session_id = None
            self.metadata = {}
            self.complete = False
            self._packets = []
            self._wire_bytes = 0

        def _get_auth_token(self):
            return token

        def _calculate_bars(self, *_args, **_kwargs):
            return bars

        def _parse_packets(self, raw):
            self._wire_bytes += len(raw.encode() if isinstance(raw, str) else raw)
            if self._wire_bytes > MAX_WIRE_BYTES:
                return [{"m": "critical_error", "p": ["Native history capacity exceeded"]}]
            packets = super()._parse_packets(raw)
            output = []
            for packet in packets:
                if not isinstance(packet, dict):
                    continue
                method, params = packet.get("m"), packet.get("p", [])
                if method in {"critical_error", "symbol_error", "series_error"}:
                    return [{"m": "critical_error", "p": ["Native history unavailable"]}]
                if method == "symbol_resolved" and len(params) >= 3 and isinstance(params[2], dict):
                    self.metadata = {
                        key: value
                        for key in SESSION_KEYS
                        if isinstance((value := params[2].get(key)), str) and len(value) <= 32768
                    }
                if method == "timescale_update":
                    self._packets.append(packet)
                elif method == "series_completed":
                    self.complete = True
                    output.extend(self._packets)
                    self._packets.clear()
                    output.append(packet)
                else:
                    output.append(packet)
            return output

        def get_history(self, symbol, **kwargs):
            if kwargs.get("interval") != timeframe:
                raise ValueError("Native history interval mismatch")
            frame = super().get_history(symbol, **kwargs)
            if not self.complete or len(frame) > bars:
                raise ValueError("Native history was not completed within its bound")
            frame.attrs.update(native_timeframe=timeframe, session_metadata=self.metadata.copy())
            return frame

        def close(self):
            return None

    return NativeHistory()
