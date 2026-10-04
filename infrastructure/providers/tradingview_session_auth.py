"""Preserve session cookies across the pinned borsapy authentication redirects.

The caller must hold the gateway's account lock. Only the temporary HTTP client
facade changes; borsapy still parses the user page and owns its auth globals.
"""

import importlib
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

_HOSTS = frozenset({"www.tradingview.com", "tr.tradingview.com", "tradingview.com"})
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_MAX_REQUESTS = 4
_BUDGET_SECONDS = 30.0
_MAX_PAGE_BYTES = 8 * 1024 * 1024


class SessionAuthError(RuntimeError):
    """A fixed, credential-free failure; never include upstream exception text."""


def _root_url(value: str) -> str:
    if not isinstance(value, str) or any(ord(char) <= 32 or ord(char) == 127 for char in value):
        raise SessionAuthError("Oturum doğrulama adresi geçersiz.")
    try:
        parts = urlsplit(value)
    except ValueError:
        raise SessionAuthError("Oturum doğrulama adresi geçersiz.") from None
    # Exact netloc also refuses userinfo, explicit ports and lookalike suffixes.
    if (
        parts.scheme != "https"
        or parts.netloc not in _HOSTS
        or parts.path not in {"", "/"}
        or "?" in value
        or "#" in value
    ):
        raise SessionAuthError("Oturum doğrulama yönlendirmesine izin verilmiyor.")
    return f"https://{parts.netloc}/"


class _SessionClient:
    def __init__(self, client: httpx.Client, clock: Callable[[], float]):
        self._client = client
        self._clock = clock
        self._deadline = clock() + _BUDGET_SECONDS

    def _remaining(self) -> float:
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise SessionAuthError("Oturum doğrulama süresi doldu.")
        return remaining

    def get(self, url: str, *, headers: dict[str, str], follow_redirects: bool) -> httpx.Response:
        # Do not let httpx rebuild Cookie from its unrelated client cookie jar.
        if follow_redirects is not True:
            raise SessionAuthError("Oturum doğrulama isteği desteklenmiyor.")
        current = _root_url(url)
        for _ in range(_MAX_REQUESTS):
            timeout = min(10.0, self._remaining())
            try:
                with self._client.stream(
                    "GET", current, headers=dict(headers), follow_redirects=False, timeout=timeout
                ) as response:
                    self._remaining()
                    if response.status_code in _REDIRECTS:
                        location = response.headers.get("location", "")
                        if (
                            not location
                            or "?" in location
                            or "#" in location
                            or any(ord(char) <= 32 or ord(char) == 127 for char in location)
                        ):
                            raise SessionAuthError("Oturum doğrulama yönlendirmesi geçersiz.")
                        current = _root_url(urljoin(current, location))
                        continue
                    if response.status_code != 200:
                        raise SessionAuthError("Oturum doğrulama hizmeti yanıt vermedi.")
                    body = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65_536):
                        self._remaining()
                        if len(body) + len(chunk) > _MAX_PAGE_BYTES:
                            raise SessionAuthError("Oturum doğrulama yanıtı çok büyük.")
                        body.extend(chunk)
                    self._remaining()
                    # iter_bytes has already decoded HTTP content encodings. Retain only
                    # the content type needed by borsapy's existing HTML parser.
                    return httpx.Response(
                        200,
                        content=bytes(body),
                        headers={"content-type": response.headers.get("content-type", "text/html")},
                        request=response.request,
                    )
            except httpx.HTTPError:
                raise SessionAuthError("Oturum doğrulama hizmetine ulaşılamadı.") from None
        raise SessionAuthError("Oturum doğrulama yönlendirme sınırı aşıldı.")


@contextmanager
def session_client(provider: Any, *, clock: Callable[[], float] = time.monotonic) -> Iterator[None]:
    """Temporarily adapt one provider under the caller's account lock."""
    original = provider._client
    cookies = httpx.Cookies(original.cookies)
    provider._client = _SessionClient(original, clock)
    try:
        yield
    finally:
        provider._client = original
        # The temporary auth request must not persist response cookies or seed an
        # account-specific jar used later by other provider operations.
        original.cookies = cookies


def authenticate_session(bp: Any, *, session: str, session_sign: str) -> dict:
    """Use borsapy 0.11's native parser and auth globals with safe redirects."""
    provider = importlib.import_module("borsapy._providers.tradingview").get_tradingview_provider()
    with session_client(provider):
        return bp.set_tradingview_auth(session=session, session_sign=session_sign)
