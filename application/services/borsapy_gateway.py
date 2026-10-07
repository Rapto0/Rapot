"""Bounded, authenticated access to borsapy without exposing its global credentials."""

import importlib
import importlib.metadata
import json
import logging
import math
import re
import threading
import time
import traceback
from collections.abc import Callable
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from application.services.market_volume_quality import native_volume, volume_quality
from infrastructure.providers.tradingview_session_auth import authenticate_session
from infrastructure.repositories.borsapy_secret_store import BorsapySecretStore, SecretStoreError
from settings import get_settings

VERSION = "0.11.0"
INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1mo"}
PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
SECRET_FIELDS = {"session", "session_sign", "evds_key", "twitter_auth_token", "twitter_ct0"}
ALARM_TRANSPORT_SILENCE_SECONDS = 90
_AUTH_LOCK = threading.RLock()


class BorsapyGatewayError(Exception):
    """Safe error suitable for an authenticated API response."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


class AlarmQuoteConnection:
    """Opaque server-owned connection; credentials never leave the gateway."""

    def __init__(self, entry: dict, epoch: int, *, clock: Callable):
        self._entry = entry
        self.epoch = epoch
        self._clock = clock

    @property
    def connected(self) -> bool:
        if self._clock() - self._entry["last_message"] >= ALARM_TRANSPORT_SILENCE_SECONDS:
            # Latch expiry: a late packet cannot revive an observation generation
            # after a transport gap. The hub will close/reconnect with its backoff.
            self._entry["transport_expired"] = True
        return bool(
            not self._entry.get("closed")
            and not self._entry.get("transport_expired")
            and not self._entry["error"]
            and not self._entry["auth_error"]
            and self._entry["stream"].is_connected
        )

    @property
    def auth_failed(self) -> bool:
        return bool(self._entry["auth_error"])

    def close(self) -> None:
        self._entry["closed"] = True
        with suppress(Exception):
            self._entry["stream"].disconnect()


class _Redact(logging.Filter):
    def __init__(self):
        super().__init__()
        self.secrets: tuple[str, ...] = ()

    def filter(self, record: logging.LogRecord) -> bool:
        text = record.getMessage()
        exception = (
            "".join(traceback.format_exception(*record.exc_info))
            if record.exc_info
            else record.exc_text
        )
        for secret in self.secrets:
            if secret:
                text = text.replace(secret, "[REDACTED]")
                text = text.replace(quote(secret, safe=""), "[REDACTED]")
                if exception:
                    exception = exception.replace(secret, "[REDACTED]")
                    exception = exception.replace(quote(secret, safe=""), "[REDACTED]")
        record.msg, record.args = text, ()
        if exception:
            # Preserve useful tracebacks while redacting authenticated request details.
            record.exc_info, record.exc_text = None, exception
        return True


def _utc(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, UTC).isoformat().replace("+00:00", "Z")


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


class BorsapyGateway:
    def __init__(
        self, settings=None, *, loader=None, version_reader=None, clock=None, session_auth=None
    ):
        self.settings = settings or get_settings()
        path = self.settings.borsapy_credentials_path
        self._store = BorsapySecretStore(
            Path(path)
            if path
            else Path(self.settings.database_path).parent / ".borsapy/credentials.enc",
            self.settings.jwt_secret_key or "",
        )
        self._loader = loader or (lambda: importlib.import_module("borsapy"))
        # A custom module loader is an injected provider; it can also inject its
        # auth adapter. The production loader always uses the pinned redirect fix.
        self._session_auth = session_auth or (
            authenticate_session
            if loader is None
            else lambda bp, **values: bp.set_tradingview_auth(**values)
        )
        self._version_reader = version_reader or (lambda: importlib.metadata.version("borsapy"))
        self._clock = clock or time.monotonic
        self._module = None
        self._credentials: dict[str, str] = {}
        self._authenticated = False
        self._token: str | None = None
        self._blocked = False
        self._state = "unconfigured"
        self._message = "TradingView bağlantısı yapılandırılmamış."
        self._streams: dict[tuple, dict] = {}
        self._quotes: dict | None = None
        self._alarm_quotes: list[AlarmQuoteConnection] = []
        self._alarm_history_slots = threading.BoundedSemaphore(2)
        self._quote_retry_after = 0.0
        self._data_epoch = 0
        self._retry_after: dict[tuple, float] = {}
        self._stop = threading.Event()
        self._janitor: threading.Thread | None = None
        self._redactor = _Redact()
        self._credentials_revision = object()
        with suppress(BorsapyGatewayError):
            self._reload_credentials()

    def _reload_credentials(self) -> None:
        """Pick up another API/bot process's atomic update before using cached auth."""
        try:
            revision = self._store.revision()
            if revision == self._credentials_revision:
                return
            self._close_streams()
            self._authenticated, self._token = False, None
            if self._module:
                self._module.clear_tradingview_auth()
                self._module.clear_evds_key()
                self._module.clear_twitter_auth()
            # Refuse a mixed snapshot if another writer replaces the file while reading.
            for _ in range(2):
                revision = self._store.revision()
                values = self._store.load()
                if revision == self._store.revision():
                    break
            else:
                raise SecretStoreError("Bağlantı bilgileri güncelleniyor; yeniden deneyin.")
            self._credentials, self._credentials_revision = values, revision
            self._blocked = False
            self._state, self._message = (
                ("auth_needed", "Kayıtlı oturum henüz doğrulanmadı.")
                if values.get("session")
                else ("unconfigured", "TradingView bağlantısı yapılandırılmamış.")
            )
            self._protect_logs()
        except SecretStoreError as exc:
            self._close_streams()
            if self._module:
                self._module.clear_tradingview_auth()
                self._module.clear_evds_key()
                self._module.clear_twitter_auth()
            self._credentials, self._token, self._authenticated = {}, None, False
            self._blocked = True
            self._state, self._message = "storage_error", str(exc)
            raise BorsapyGatewayError(str(exc), 409) from None

    def _protect_logs(self, additional: str = "") -> None:
        self._redactor.secrets = tuple(self._credentials.values()) + (self._token or "", additional)
        names = {"httpx", "httpcore", "urllib3.connectionpool", "websocket"}
        names.update(
            name
            for name in list(logging.Logger.manager.loggerDict)
            if name.startswith(("borsapy", "httpcore", "httpx", "websocket", "urllib3"))
        )
        for name in names:
            logger = logging.getLogger(name)
            if self._redactor not in logger.filters:
                logger.addFilter(self._redactor)
        # Handler filters also cover lazily created child loggers (logger filters do not).
        loggers = [logging.getLogger()] + [logging.getLogger(name) for name in names]
        for logger in loggers:
            for handler in logger.handlers:
                if self._redactor not in handler.filters:
                    handler.addFilter(self._redactor)

    def status(self) -> dict:
        # A local snapshot must remain available while a provider call owns the auth lock.
        try:
            version = self._version_reader()
        except Exception:
            version = None
        credentials, state = self._credentials, self._state
        return {
            "installed": version == VERSION,
            "version": version,
            "configured": bool(credentials.get("session")),
            "authenticated": self._authenticated and state == "authenticated",
            "evds_configured": bool(credentials.get("evds_key")),
            "twitter_configured": bool(credentials.get("twitter_auth_token")),
            "state": state if version == VERSION else "unavailable",
            "message": self._message if version == VERSION else "borsapy 0.11.0 gerekli.",
        }

    def _load(self):
        if self._module is None:
            try:
                if self._version_reader() != VERSION:
                    raise ValueError
                self._module = self._loader()
            except Exception:
                raise BorsapyGatewayError("borsapy 0.11.0 yüklenemedi.") from None
        self._protect_logs()
        return self._module

    def _auxiliary_auth(self, bp) -> None:
        if self._credentials.get("evds_key"):
            bp.set_evds_key(self._credentials["evds_key"])
        else:
            bp.clear_evds_key()
        if self._credentials.get("twitter_auth_token"):
            bp.set_twitter_auth(
                auth_token=self._credentials["twitter_auth_token"],
                ct0=self._credentials.get("twitter_ct0", ""),
            )
        else:
            bp.clear_twitter_auth()

    def _authenticate(self, bp) -> None:
        self._authenticated = False
        self._token = None
        self._protect_logs()
        try:
            bp.clear_tradingview_auth()
            result = self._session_auth(
                bp,
                session=self._credentials["session"],
                session_sign=self._credentials["session_sign"],
            )
            token = result.get("auth_token") if isinstance(result, dict) else None
            if not isinstance(token, str) or not token or token == "unauthorized_user_token":
                raise ValueError
            self._token = token
            self._authenticated, self._blocked = True, False
            self._state = "authenticated"
            self._message = "Oturum doğrulandı; gerçek zamanlı veri henüz ölçülmedi."
            self._protect_logs()
        except Exception:
            bp.clear_tradingview_auth()
            self._blocked = True
            self._state, self._message = "auth_needed", "TradingView oturumu doğrulanamadı."
            raise BorsapyGatewayError(self._message, 409) from None

    def _prepare(self, *, require_auth: bool = False, tradingview: bool = True):
        self._reload_credentials()
        bp = self._load()
        if not tradingview:
            if require_auth or self._state == "storage_error":
                raise BorsapyGatewayError("Bağlantı kimlikleri kullanılamıyor.", 409)
            self._auxiliary_auth(bp)
            return bp
        if self._blocked:
            raise BorsapyGatewayError(self._message, 409)
        if self._credentials.get("session"):
            if not self._authenticated:
                self._authenticate(bp)
            current = bp.get_tradingview_auth() or {}
            if current.get("auth_token") != self._token:
                self._authenticated = False
                self._authenticate(bp)
        elif require_auth:
            raise BorsapyGatewayError("Önce TradingView bağlantısını kaydedin.", 409)
        else:
            bp.clear_tradingview_auth()
        self._auxiliary_auth(bp)
        return bp

    def configure(self, values: dict[str, str]) -> dict:
        if not values or set(values) - SECRET_FIELDS:
            raise BorsapyGatewayError("Geçersiz bağlantı alanları.", 422)
        if ("session" in values) != ("session_sign" in values):
            raise BorsapyGatewayError("Oturum ve imza birlikte verilmelidir.", 422)
        if ("twitter_auth_token" in values) != ("twitter_ct0" in values):
            raise BorsapyGatewayError("Twitter oturum alanları birlikte verilmelidir.", 422)
        if bool(values.get("session")) != bool(values.get("session_sign")):
            raise BorsapyGatewayError("Oturum ve imza birlikte verilmelidir.", 422)
        for value in values.values():
            if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 33 for c in value):
                raise BorsapyGatewayError("Kimlik alanı geçersiz.", 422)
        with _AUTH_LOCK:
            # A complete replacement can recover an unreadable encrypted file.
            with suppress(BorsapyGatewayError):
                self._reload_credentials()
            self._close_streams()
            updated = {**self._credentials, **values}
            updated = {key: value for key, value in updated.items() if value}
            self._credentials = updated
            self._authenticated, self._blocked = False, False
            self._token = None
            self._protect_logs()
            try:
                self._store.save(updated)
                # Read the committed file again so a concurrent replacement cannot be
                # mistaken for our own in-memory values with its newer file revision.
                self._credentials_revision = object()
                self._reload_credentials()
                updated = self._credentials
            except SecretStoreError as exc:
                self._blocked = True
                self._state, self._message = "storage_error", str(exc)
                raise BorsapyGatewayError(str(exc)) from None
            bp = self._load()
            if updated.get("session"):
                self._authenticate(bp)
            else:
                bp.clear_tradingview_auth()
                self._state, self._message = (
                    "unconfigured",
                    "TradingView oturumu yapılandırılmamış.",
                )
            self._auxiliary_auth(bp)
            return self.status()

    def verify(self) -> dict:
        with _AUTH_LOCK:
            self._reload_credentials()
            if not self._credentials.get("session"):
                raise BorsapyGatewayError("Kayıtlı TradingView oturumu yok.", 409)
            self._close_streams()
            self._authenticate(self._load())
            return self.status()

    def clear(self) -> dict:
        with _AUTH_LOCK:
            self._close_streams()
            try:
                self._store.clear()
                self._credentials_revision = self._store.revision()
            except SecretStoreError as exc:
                raise BorsapyGatewayError(str(exc)) from None
            self._credentials = {}
            self._token = None
            self._authenticated = self._blocked = False
            if self._module:
                self._module.clear_tradingview_auth()
                self._module.clear_evds_key()
                self._module.clear_twitter_auth()
            self._state, self._message = "unconfigured", "Bağlantı bilgileri silindi."
            return self.status()

    @staticmethod
    @contextmanager
    def _account_lock():
        if not _AUTH_LOCK.acquire(timeout=1):
            raise BorsapyGatewayError("Veri servisi meşgul; yeniden deneyin.", 429)
        try:
            yield
        finally:
            _AUTH_LOCK.release()

    def run(self, callback: Callable, *, require_auth: bool = False, tradingview: bool = True):
        with self._account_lock():
            bp = self._prepare(require_auth=require_auth, tradingview=tradingview)
            try:
                return callback(bp)
            except BorsapyGatewayError:
                raise
            except Exception:
                raise BorsapyGatewayError("Veri sağlayıcı isteği tamamlanamadı.", 502) from None

    def run_public(self, callback: Callable):
        """Only stateless public KAP/company and economic-calendar adapters.

        These providers do not consult TradingView/EVDS/X credentials. Their slow
        HTTP calls must not hold the global credential lock and stop quote reads.
        Authenticated or credential-dependent callbacks must continue using run().
        """
        if not _AUTH_LOCK.acquire(timeout=1):
            raise BorsapyGatewayError("Veri servisi meşgul; yeniden deneyin.", 429)
        try:
            bp = self._load()
        finally:
            _AUTH_LOCK.release()
        try:
            return callback(bp)
        except BorsapyGatewayError:
            raise
        except Exception:
            raise BorsapyGatewayError("Genel piyasa verisi alınamadı.", 502) from None

    def history(self, symbol: str, interval="1d", period="1mo", start=None, end=None):
        symbol = self._validate_subscription(symbol, interval, None)
        if period not in PERIODS:
            raise BorsapyGatewayError("Desteklenmeyen veri dönemi.", 422)
        frame = self.run(
            lambda bp: bp.Ticker(symbol).history(
                interval=interval, period=period, start=start, end=end
            ),
            require_auth=True,
        )
        return self._validated_history(frame)

    @staticmethod
    def _new_alarm_history_provider(token: str):
        # A request-local provider never consults or changes borsapy's global
        # account while the bounded WebSocket history request is in flight.
        from borsapy._providers.tradingview import TradingViewProvider

        class AuthenticatedHistory(TradingViewProvider):
            def __init__(self):
                super().__init__()
                self._volume_quality = {}

            def _get_auth_token(self):
                return token

            def _calculate_bars(self, *args, **kwargs):
                return min(500, super()._calculate_bars(*args, **kwargs))

            def _parse_packets(self, raw):
                packets = super()._parse_packets(raw)
                for packet in packets:
                    if not isinstance(packet, dict) or packet.get("m") != "timescale_update":
                        continue
                    params = packet.get("p", [])
                    if len(params) < 2 or not isinstance(params[1], dict):
                        continue
                    for candle in params[1].get("$prices", {}).get("s", []):
                        values = candle.get("v", [])
                        if len(values) < 5:
                            continue
                        stamp = _number(values[0])
                        volume = _number(values[5]) if len(values) >= 6 else None
                        self._volume_quality[stamp] = volume is not None and 0 <= volume < 1e99
                return packets

            def get_history(self, *args, **kwargs):
                frame = super().get_history(*args, **kwargs)
                verified = [
                    self._volume_quality.get(stamp.timestamp(), False) for stamp in frame.index
                ]
                # Upstream may default an absent field to zero. Preserve price
                # history, but never authenticate that placeholder for volume rules.
                for stamp, valid in zip(frame.index, verified, strict=True):
                    if not valid:
                        frame.loc[stamp, "Volume"] = 0.0
                frame.attrs["volume_verified"] = bool(verified) and all(verified)
                frame.attrs["volume_unavailable_rows"] = sum(not valid for valid in verified)
                return frame

        return AuthenticatedHistory()

    def alarm_history(self, symbol: str, interval="1m", period="5d"):
        """Isolate autonomous history I/O from dashboard/account lock ownership."""
        symbol = self._validate_subscription(symbol, interval, None)
        if period not in PERIODS:
            raise BorsapyGatewayError("Desteklenmeyen veri dönemi.", 422)
        if not self._alarm_history_slots.acquire(timeout=1):
            raise BorsapyGatewayError("Alarm geçmişi iş kuyruğu dolu.", 429)
        provider = None
        try:
            with self._account_lock():
                self._prepare(require_auth=True)
                token, epoch, revision = self._token, self._data_epoch, self._credentials_revision
                if not token or token == "unauthorized_user_token":
                    raise BorsapyGatewayError("TradingView hesabı doğrulanmalı.", 409)
            provider = self._new_alarm_history_provider(token)
            frame = provider.get_history(symbol, interval=interval, period=period)
            with self._account_lock():
                if (
                    self._data_epoch != epoch
                    or self._store.revision() != revision
                    or self._token != token
                    or not self._authenticated
                    or self._blocked
                ):
                    raise BorsapyGatewayError("Hesap değişti; yeni geçmiş bekleniyor.", 409)
            return self._validated_history(frame)
        except BorsapyGatewayError:
            raise
        except Exception:
            raise BorsapyGatewayError("Alarm geçmişi alınamadı.", 502) from None
        finally:
            if provider is not None:
                with suppress(Exception):
                    provider.close()
            self._alarm_history_slots.release()

    @staticmethod
    def _validated_history(frame):
        try:
            import numpy as np
            import pandas as pd

            required = ["Open", "High", "Low", "Close", "Volume"]
            if frame.empty or not set(required).issubset(frame.columns):
                raise ValueError
            result = frame[required].copy()
            result = result.apply(pd.to_numeric, errors="raise").astype(float)
            if not isinstance(result.index, pd.DatetimeIndex) or result.index.tz is None:
                raise ValueError
            if (
                result.index.hasnans
                or result.index.has_duplicates
                or not np.isfinite(result.to_numpy(dtype=float)).all()
            ):
                raise ValueError
            if (result[required[:4]] <= 0).any().any() or (result.Volume < 0).any():
                raise ValueError
            result = result.sort_index()
            if (
                (result.High < result[["Open", "Close", "Low"]].max(axis=1))
                | (result.Low > result[["Open", "Close", "High"]].min(axis=1))
            ).any():
                raise ValueError
            result.attrs.update(
                source="borsapy_tradingview", adjustment="splits", open_quality="provider"
            )
            result.attrs["volume_verified"] = frame.attrs.get("volume_verified") is True
            result.attrs["volume_unavailable_rows"] = frame.attrs.get("volume_unavailable_rows")
            return result
        except Exception:
            raise BorsapyGatewayError("Sağlayıcı geçerli OHLCV verisi döndürmedi.", 502) from None

    @staticmethod
    def _validate_subscription(
        symbol: str, interval: str, study: str | None, *, streaming=False
    ) -> str:
        symbol = symbol.upper().removesuffix(".IS")
        intervals = INTERVALS | {"2h"} if streaming else INTERVALS
        if not re.fullmatch(r"[A-Z0-9]{1,20}", symbol) or interval not in intervals:
            raise BorsapyGatewayError("Desteklenmeyen sembol veya periyot.", 422)
        if study and not re.fullmatch(
            r"(?:[A-Za-z][A-Za-z0-9_]{0,39}|(?:STD|PUB|USER);[A-Za-z0-9_.-]{1,120})", study
        ):
            raise BorsapyGatewayError("Geçersiz gösterge kimliği.", 422)
        return symbol

    def _close_streams(self) -> None:
        self._data_epoch += 1
        self._close_quotes()
        for connection in self._alarm_quotes:
            connection.close()
        self._alarm_quotes.clear()
        self._quote_retry_after = 0
        for entry in self._streams.values():
            with suppress(Exception):
                entry["stream"].disconnect()
        self._streams.clear()
        self._retry_after.clear()

    def close_streams(self) -> None:
        with _AUTH_LOCK:
            self._close_streams()

    def _cleanup(self) -> None:
        now = self._clock()
        if self._quotes:
            entry = self._quotes
            for symbol, (exchange, touched) in list(entry["symbols"].items()):
                if now - touched > self.settings.borsapy_stream_idle_seconds:
                    with suppress(Exception):
                        entry["stream"].unsubscribe(symbol, exchange=exchange)
                    entry["symbols"].pop(symbol, None)
                    entry["received"].pop(symbol, None)
                    entry["errors"].discard(symbol)
            if not entry["symbols"]:
                self._close_quotes()
        for key, entry in list(self._streams.items()):
            entry["subscribers"] = {
                subscriber: touched
                for subscriber, touched in entry["subscribers"].items()
                if now - touched <= self.settings.borsapy_stream_idle_seconds
            }
            if not entry["subscribers"]:
                with suppress(Exception):
                    entry["stream"].disconnect()
                del self._streams[key]
        self._retry_after = {
            key: value
            for key, value in self._retry_after.items()
            if value > now or key in self._streams
        }

    def data_epoch(self) -> int:
        """Process-local cache generation; contains no credential-derived material."""
        try:
            if self._store.revision() == self._credentials_revision:
                return self._data_epoch

        except SecretStoreError:
            pass
        if not _AUTH_LOCK.acquire(timeout=1):
            raise BorsapyGatewayError("Bağlantı bilgileri güncelleniyor.", 429)
        try:
            self._reload_credentials()
            return self._data_epoch
        finally:
            _AUTH_LOCK.release()

    def memory_epoch(self) -> int:
        """Local account generation only; no file/stat/network I/O for alarm snapshots."""
        return self._data_epoch

    def _close_quotes(self) -> None:
        if self._quotes:
            with suppress(Exception):
                self._quotes["stream"].disconnect()
            self._quotes = None

    def _new_quotes(self, bp) -> dict:
        transport_clock = self._clock
        entry = {
            "symbols": {},
            "received": {},
            "errors": set(),
            "error": False,
            "auth_error": False,
            "last_message": transport_clock(),
        }

        class QuoteStream(bp.TradingViewStream):
            WS_URL = "wss://data.tradingview.com/socket.io/websocket"

            def _on_close(self, ws, close_status, close_msg):
                self._connected.clear()

            def _on_error(self, ws, error):
                entry["error"] = True
                self._connected.clear()

            def _on_message(self, ws, message):
                # Transport health includes heartbeat/control frames, independently
                # of whether this market is trading or any fresh quote arrived.
                received = transport_clock()
                if (
                    entry.get("alarm_owned")
                    and received - entry["last_message"] >= ALARM_TRANSPORT_SILENCE_SECONDS
                ):
                    entry["transport_expired"] = True
                entry["last_message"] = received
                for packet in self._parse_packets(message):
                    if isinstance(packet, dict) and packet.get("m") == "critical_error":
                        entry["auth_error"] = True
                        return
                super()._on_message(ws, message)

            def _handle_quote_data(self, params):
                if len(params) < 2 or not isinstance(params[1], dict):
                    return
                data = params[1]
                full = data.get("n", "")
                if not isinstance(full, str) or ":" not in full:
                    return
                exchange, symbol = full.split(":", 1)
                if entry["symbols"].get(symbol, (None,))[0] != exchange:
                    return
                if data.get("s") == "error":
                    entry["errors"].add(symbol)
                    return
                with self._lock:
                    cached = self._quotes.get(symbol, {})
                    if cached.get("_full_symbol") not in {None, full}:
                        self._quotes.pop(symbol, None)
                entry["errors"].discard(symbol)
                super()._handle_quote_data(params)

        stream = QuoteStream(auth_token=self._token)
        entry["stream"] = stream
        stream._should_reconnect = False

        def received(symbol, quote):
            # Only a quote update changes receipt time, never a browser poll.
            entry["received"][symbol] = time.time()

        stream.on_any_quote(received)
        try:
            stream.connect(timeout=3)
            stream._should_reconnect = False
            if not stream.is_connected:
                raise ValueError
            # Allow the full first-heartbeat grace period after connection setup.
            entry["last_message"] = transport_clock()
        except Exception:
            stream.disconnect()
            raise BorsapyGatewayError("Fiyat akışı bağlantısı kurulamadı.", 502) from None
        return entry

    def create_alarm_quote_stream(
        self, symbols: list[str], on_quote: Callable
    ) -> AlarmQuoteConnection:
        """Create an authenticated, autonomous BIST feed, separate from browser leases.

        The alarm hub owns reconnect/backoff and close. Credential edits close this
        handle immediately. Callbacks contain numeric observations, never raw packets.
        """
        if not 1 <= len(symbols) <= 2000 or len(set(symbols)) != len(symbols):
            raise BorsapyGatewayError("Alarm fiyat evreni 1–2000 benzersiz sembol olmalı.", 422)
        if any(not re.fullmatch(r"[A-Z0-9]{1,20}", symbol) for symbol in symbols):
            raise BorsapyGatewayError("Alarm fiyat evreninde geçersiz sembol var.", 422)

        def create(bp):
            for item in self._alarm_quotes:
                if not item.connected:
                    item.close()
            self._alarm_quotes = [item for item in self._alarm_quotes if item.connected]
            if self._alarm_quotes:
                raise BorsapyGatewayError("Kalıcı alarm fiyat bağlantısı zaten açık.", 429)
            epoch = self._data_epoch
            entry = self._new_quotes(bp)
            entry["alarm_owned"] = True
            connection = AlarmQuoteConnection(entry, epoch, clock=self._clock)

            def received(symbol, raw):
                if (
                    epoch != self._data_epoch
                    or entry.get("closed")
                    or entry.get("transport_expired")
                ):
                    return
                if symbol not in entry["symbols"]:
                    return
                on_quote(
                    symbol,
                    {
                        "price": _number(raw.get("last")),
                        "source_timestamp": _number(raw.get("timestamp")),
                        "received_at": time.time(),
                    },
                )

            entry["stream"].on_any_quote(received)
            self._alarm_quotes.append(connection)
            try:
                for symbol in symbols:
                    entry["symbols"][symbol] = ("BIST", self._clock())
                    entry["stream"].subscribe(symbol, exchange="BIST")
            except Exception:
                connection.close()
                raise BorsapyGatewayError("Alarm fiyat abonelikleri kurulamadı.", 502) from None
            return connection

        return self.run(create, require_auth=True)

    def reset_alarm_auth(self, expected_epoch: int) -> None:
        """Refresh a rejected stream token once through the existing auth boundary."""
        with self._account_lock():
            if self._data_epoch != expected_epoch:
                return
            self._close_streams()
            self._authenticated, self._token, self._blocked = False, None, False
            self._state, self._message = "auth_needed", "Alarm bağlantısı yeniden doğrulanacak."

    def quote_snapshot(self, symbols: list[tuple[str, str]]) -> dict[str, dict]:
        """One account-scoped socket for bounded dashboard/watchlist batches.

        Keys are exchange:symbol. Upstream indexes by the bare symbol, so a
        conflicting exchange is rejected instead of returning the wrong market.
        The pool is separate from chart sessions and expires unused subscriptions.
        """
        allowed = {"BIST", "NASDAQ", "NYSE", "SP", "TVC", "CBOE", "FX", "OANDA"}
        if not 1 <= len(symbols) <= 50 or any(
            exchange not in allowed or not re.fullmatch(r"[A-Z0-9.]{1,20}", symbol)
            for exchange, symbol in symbols
        ):
            raise BorsapyGatewayError("Geçersiz fiyat listesi.", 422)
        if len({symbol for _, symbol in symbols}) != len(set(symbols)):
            raise BorsapyGatewayError("Aynı sembol için farklı borsalar birlikte istenemez.", 422)
        if not _AUTH_LOCK.acquire(timeout=1):
            # Read an existing, account-matching socket while a history request
            # owns the provider auth lock. Never connect/subscribe/authenticate here.
            entry, epoch = self._quotes, self._data_epoch
            try:
                same_revision = self._store.revision() == self._credentials_revision
                if (
                    same_revision
                    and self._authenticated
                    and not self._blocked
                    and entry
                    and not entry["error"]
                    and not entry["auth_error"]
                    and entry["stream"].is_connected
                    and all(
                        entry["symbols"].get(symbol, (None,))[0] == exchange
                        for exchange, symbol in symbols
                    )
                ):
                    result = self._read_quotes(entry, symbols)
                    if (
                        self._quotes is entry
                        and self._data_epoch == epoch
                        and self._store.revision() == self._credentials_revision
                        and all(
                            entry["symbols"].get(symbol, (None,))[0] == exchange
                            for exchange, symbol in symbols
                        )
                    ):
                        # Do not resurrect a lease being removed by the lock owner.
                        # Normal locked polls renew it once the provider is available.
                        return result
            except SecretStoreError:
                pass
            raise BorsapyGatewayError("Veri servisi meşgul; yeniden denenecek.", 429)
        try:
            bp = self._prepare(require_auth=True)
            self._cleanup()
            entry = self._quotes
            if entry and entry["auth_error"]:
                self._close_quotes()
                self._authenticated, self._blocked = False, True
                self._state, self._message = "auth_needed", "TradingView oturumu yenilenmeli."
                raise BorsapyGatewayError(self._message, 409)
            if entry and (entry["error"] or not entry["stream"].is_connected):
                self._close_quotes()
                self._quote_retry_after = self._clock() + 30
                entry = None
            if self._clock() < self._quote_retry_after:
                raise BorsapyGatewayError("Fiyat akışı yeniden bağlanmayı bekliyor.", 502)
            if entry is None:
                try:
                    entry = self._new_quotes(bp)
                except BorsapyGatewayError:
                    self._quote_retry_after = self._clock() + 30
                    raise
                self._quotes = entry
            additions = {symbol for _, symbol in symbols} - set(entry["symbols"])
            if len(entry["symbols"]) + len(additions) > 200:
                raise BorsapyGatewayError("200 etkin fiyat sınırı; izlenen listeyi daraltın.", 429)
            if any(
                symbol in entry["symbols"] and entry["symbols"][symbol][0] != exchange
                for exchange, symbol in symbols
            ):
                raise BorsapyGatewayError(
                    "Sembol başka borsada izleniyor; önce akışı kapatın.", 409
                )
            for exchange, symbol in symbols:
                if symbol not in entry["symbols"]:
                    entry["symbols"][symbol] = (exchange, self._clock())
                    entry["stream"].subscribe(symbol, exchange=exchange)
                entry["symbols"][symbol] = (exchange, self._clock())
            if not self._janitor or not self._janitor.is_alive():
                self._stop.clear()
                self._janitor = threading.Thread(target=self._watch_leases, daemon=True)
                self._janitor.start()
            return self._read_quotes(entry, symbols)
        except BorsapyGatewayError:
            raise
        except Exception:
            self._close_quotes()
            self._quote_retry_after = self._clock() + 30
            raise BorsapyGatewayError("Fiyatlar alınamadı; yeniden denenecek.", 502) from None
        finally:
            _AUTH_LOCK.release()

    @staticmethod
    def _read_quotes(entry: dict, symbols: list[tuple[str, str]]) -> dict[str, dict]:
        result = {}
        for exchange, symbol in symbols:
            raw = entry["stream"].get_quote(symbol) or {}
            if raw.get("_raw", {}).get("_full_symbol") not in {None, f"{exchange}:{symbol}"}:
                raw = {}
            failed = symbol in entry["errors"]
            if failed:
                raw = {}
            received = entry["received"].get(symbol)
            price = _number(raw.get("last"))
            price = price if price is not None and price > 0 else None
            timestamp = _number(raw.get("timestamp"))
            timestamp = timestamp if timestamp and 0 < timestamp <= time.time() + 300 else None
            stale = bool(
                received is None
                or time.time() - received > 120
                or timestamp is None
                or time.time() - timestamp > 120
            )
            result[f"{exchange}:{symbol}"] = {
                "price": price,
                "change": _number(raw.get("change")),
                "change_pct": _number(raw.get("change_percent")),
                "provider_time": _utc(timestamp),
                "received_at": _utc(received),
                "state": "error"
                if failed
                else "waiting"
                if price is None
                else "stale"
                if stale
                else "ok",
                "source": "borsapy_tradingview",
                "realtime_verified": False,
            }
        return result

    def _watch_leases(self) -> None:
        while not self._stop.wait(5):
            with _AUTH_LOCK, suppress(BorsapyGatewayError):
                self._reload_credentials()
                self._cleanup()

    def _new_stream(
        self, bp, symbol: str, interval: str, study: str | None, exchange: str, inputs: dict
    ) -> dict:
        entry = {
            "subscribers": {},
            "received": None,
            "error": False,
            "auth_error": False,
            "volume_observations": {},
        }

        class IsolatedStream(bp.TradingViewStream):
            # Upstream appends ?type=chart itself. Recreate whole sessions on reconnect.
            WS_URL = "wss://data.tradingview.com/socket.io/websocket"

            def _on_close(self, ws, close_status, close_msg):
                self._connected.clear()

            def _on_error(self, ws, error):
                entry["error"] = True
                self._connected.clear()

            def _on_message(self, ws, message):
                for packet in self._parse_packets(message):
                    if isinstance(packet, dict) and packet.get("m") in {
                        "critical_error",
                        "symbol_error",
                        "series_error",
                        "study_error",
                    }:
                        entry["error"] = True
                        entry["auth_error"] = packet.get("m") == "critical_error"
                        return
                    if not isinstance(packet, dict) or packet.get("m") not in {
                        "timescale_update",
                        "du",
                    }:
                        continue
                    params = packet.get("p", [])
                    if len(params) < 2 or not isinstance(params[1], dict):
                        continue
                    series = params[1].get("$prices", {})
                    if not isinstance(series, dict):
                        continue
                    native_candles = series.get("s", series.get("st", []))
                    if not isinstance(native_candles, list):
                        continue
                    # Observe the native field before borsapy fills absent v[5]
                    # with zero. Each entry owns exactly one chart subscription.
                    with self._lock:
                        observations = entry["volume_observations"]
                        for candle in native_candles:
                            values = candle.get("v", []) if isinstance(candle, dict) else []
                            if not isinstance(values, list) or len(values) < 5:
                                continue
                            stamp = _number(values[0])
                            if stamp is not None and stamp > 0:
                                observations[stamp] = (
                                    native_volume(values[5]) if len(values) > 5 else None
                                )
                        for stamp in sorted(observations)[:-300]:
                            del observations[stamp]
                super()._on_message(ws, message)

            def _update_chart_data(self, symbol, interval, candles):
                # Upstream only replaces the last bar. Merge corrections to older bars too.
                with self._lock:
                    target = self._chart_data.setdefault(symbol, {})
                    merged = {item["time"]: item for item in target.get(interval, [])}
                    merged.update({item["time"]: item for item in candles})
                    target[interval] = [merged[t] for t in sorted(merged)[-300:]]
                key = f"{symbol}:{interval}"
                if candles:
                    callbacks = self._chart_callbacks.get(key, []) + self._global_chart_callbacks
                    for callback in callbacks:
                        with suppress(Exception):
                            callback(symbol, interval, candles[-1])
                    if key in self._chart_events:
                        self._chart_events[key].set()

        stream = IsolatedStream(auth_token=self._token)
        entry["stream"] = stream
        stream._should_reconnect = False

        def received(*args):
            entry["received"] = time.time()

        stream.on_quote(symbol, received)
        stream.on_candle(symbol, interval, received)
        try:
            stream.connect(timeout=8)
            stream._should_reconnect = False
            stream.subscribe(symbol, exchange=exchange)
            stream.subscribe_chart(symbol, interval, exchange=exchange)
            if study:
                stream.add_study(symbol, interval, study, **inputs)
        except Exception:
            stream.disconnect()
            raise BorsapyGatewayError("Akış bağlantısı kurulamadı.", 502) from None
        return entry

    def _stream_key(
        self, symbol: str, interval="1m", study: str | None = None, study_inputs: dict | None = None
    ) -> tuple:
        exchange = "BIST"
        if ":" in symbol:
            exchange, symbol = symbol.upper().split(":", 1)
        if exchange not in {"BIST", "VIOP"} or not re.fullmatch(r"[A-Za-z0-9_!.]{1,60}", symbol):
            raise BorsapyGatewayError("Desteklenmeyen akış sembolü.", 422)
        # VIOP contracts contain underscores; history() remains restricted to BIST equities.
        self._validate_subscription("THYAO", interval, study, streaming=True)
        symbol = symbol.upper().removesuffix(".IS")
        inputs = {} if study_inputs is None else study_inputs
        if not isinstance(inputs, dict) or len(inputs) > 16 or (inputs and not study):
            raise BorsapyGatewayError("Gösterge girdileri geçersiz.", 422)
        for name, value in inputs.items():
            if (
                not isinstance(name, str)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,39}", name)
                or not isinstance(value, (str, int, float, bool))
            ):
                raise BorsapyGatewayError("Gösterge girdileri geçersiz.", 422)
            if isinstance(value, str) and (len(value) > 80 or any(ord(c) < 32 for c in value)):
                raise BorsapyGatewayError("Gösterge girdileri geçersiz.", 422)
            if isinstance(value, (int, float)) and (
                not math.isfinite(value) or abs(value) > 10000000
            ):
                raise BorsapyGatewayError("Gösterge girdileri geçersiz.", 422)
        return (exchange, symbol, interval, study, json.dumps(inputs, sort_keys=True))

    @staticmethod
    def _validate_subscriber(subscriber_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", subscriber_id):
            raise BorsapyGatewayError("Geçersiz akış abonesi.", 422)

    def close_stream(
        self,
        symbol: str,
        interval="1m",
        study: str | None = None,
        study_inputs: dict | None = None,
        subscriber_id="shared",
    ) -> dict:
        self._validate_subscriber(subscriber_id)
        key = self._stream_key(symbol, interval, study, study_inputs)
        with self._account_lock():
            entry = self._streams.get(key)
            if entry:
                entry["subscribers"].pop(subscriber_id, None)
                if not entry["subscribers"]:
                    with suppress(Exception):
                        entry["stream"].disconnect()
                    del self._streams[key]
                    self._retry_after.pop(key, None)
            return {"closed": key not in self._streams, "released": True}

    def stream_snapshot(
        self,
        symbol: str,
        interval="1m",
        study: str | None = None,
        study_inputs: dict | None = None,
        subscriber_id="shared",
    ) -> dict:
        self._validate_subscriber(subscriber_id)
        key = self._stream_key(symbol, interval, study, study_inputs)
        exchange, symbol, interval, study, encoded_inputs = key
        inputs = json.loads(encoded_inputs)
        if not _AUTH_LOCK.acquire(timeout=1):
            entry, epoch = self._streams.get(key), self._data_epoch
            try:
                if (
                    self._store.revision() == self._credentials_revision
                    and self._authenticated
                    and not self._blocked
                    and entry
                    and subscriber_id in entry["subscribers"]
                    and not entry["error"]
                    and not entry["auth_error"]
                    and entry["stream"].is_connected
                ):
                    result = self._read_stream(entry, symbol, interval, study)
                    if (
                        self._streams.get(key) is entry
                        and self._data_epoch == epoch
                        and self._store.revision() == self._credentials_revision
                        and subscriber_id in entry["subscribers"]
                    ):
                        return result
            except SecretStoreError:
                pass
            raise BorsapyGatewayError("Veri servisi meşgul; yeniden deneyin.", 429)
        try:
            bp = self._prepare(require_auth=True)
            self._cleanup()
            entry = self._streams.get(key)
            if entry:
                if subscriber_id not in entry["subscribers"] and len(entry["subscribers"]) >= 16:
                    raise BorsapyGatewayError("Akış abone sınırına ulaşıldı.", 409)
                entry["subscribers"][subscriber_id] = self._clock()
            if entry and (entry["error"] or not entry["stream"].is_connected):
                if entry["auth_error"]:
                    self._blocked, self._authenticated = True, False
                    self._state, self._message = "auth_needed", "Akış oturumu yeniden doğrulanmalı."
                    raise BorsapyGatewayError(self._message, 409)
                if key not in self._retry_after:
                    with suppress(Exception):
                        entry["stream"].disconnect()
                    self._retry_after[key] = self._clock() + 30
                    raise BorsapyGatewayError("Akış kesildi; yeniden bağlanma bekleniyor.", 502)
                if self._retry_after[key] <= self._clock():
                    subscribers = entry["subscribers"].copy()
                    try:
                        entry = self._new_stream(bp, symbol, interval, study, exchange, inputs)
                    except BorsapyGatewayError:
                        self._retry_after[key] = self._clock() + 30
                        raise
                    entry["subscribers"] = subscribers
                    self._streams[key] = entry
                    self._retry_after.pop(key, None)
            if self._retry_after.get(key, 0) > self._clock():
                raise BorsapyGatewayError("Yeniden bağlantı için 30 saniye bekleyin.", 429)
            if entry is None:
                if len(self._streams) >= self.settings.borsapy_max_streams:
                    raise BorsapyGatewayError("Eşzamanlı grafik akışı sınırına ulaşıldı.", 409)
                try:
                    entry = self._new_stream(bp, symbol, interval, study, exchange, inputs)
                except BorsapyGatewayError:
                    self._retry_after[key] = self._clock() + 30
                    raise
                self._streams[key] = entry
                if not self._janitor or not self._janitor.is_alive():
                    self._stop.clear()
                    self._janitor = threading.Thread(target=self._watch_leases, daemon=True)
                    self._janitor.start()
            entry["subscribers"][subscriber_id] = self._clock()
            return self._read_stream(entry, symbol, interval, study)
        finally:
            _AUTH_LOCK.release()

    @staticmethod
    def _read_stream(entry: dict, symbol: str, interval: str, study: str | None) -> dict:
        stream = entry["stream"]
        raw_quote = stream.get_quote(symbol) or {}
        fields = ("last", "bid", "ask", "volume", "timestamp", "change", "change_percent")
        quote = {field: _number(raw_quote.get(field)) for field in fields} if raw_quote else None
        if quote is not None:
            quote["volume"] = native_volume(raw_quote.get("volume"))
        with stream._lock:
            volume_observations = dict(entry.get("volume_observations", {}))
        candles = []
        for candle in stream.get_candles(symbol, interval, count=300):
            item = {
                name: _number(candle.get(name))
                for name in ("time", "open", "high", "low", "close", "volume")
            }
            if all(item[name] is not None for name in ("time", "open", "high", "low", "close")):
                item["volume"] = volume_observations.get(item["time"])
                candles.append(item)
        missing_volumes = sum(
            item["time"] in volume_observations and item["volume"] is None for item in candles
        )
        verified_volume = bool(candles) and all(item["volume"] is not None for item in candles)
        quality = volume_quality(verified_volume, missing_volumes or None)
        study_values = stream.get_study(symbol, interval, study) if study else None
        safe_study = {str(k)[:80]: _number(v) for k, v in (study_values or {}).items()}
        has_data = bool(candles or (quote and quote.get("last") is not None))
        stale = bool(entry["received"] and time.time() - entry["received"] > 120)
        return {
            "state": "stale" if stale else "active_unverified" if has_data else "connecting",
            "message": "Veri alınıyor; gerçek zamanlı erişim henüz ölçülmedi."
            if has_data and not stale
            else "Son veri güncellemesi iki dakikadan eski."
            if stale
            else "İlk veri bekleniyor.",
            "quote": quote,
            "candles": candles,
            "volume_quality": quality,
            "study": safe_study or None,
            "source": "TradingView / borsapy",
            "received_at": _utc(entry["received"]),
            "realtime_verified": False,
        }

    def close(self) -> None:
        self._stop.set()
        self.close_streams()
        if self._janitor and self._janitor is not threading.current_thread():
            self._janitor.join(timeout=6)


_gateway: BorsapyGateway | None = None


def get_borsapy_gateway() -> BorsapyGateway:
    global _gateway
    if _gateway is not None:
        return _gateway
    with _AUTH_LOCK:
        if _gateway is None:
            _gateway = BorsapyGateway()
        return _gateway
