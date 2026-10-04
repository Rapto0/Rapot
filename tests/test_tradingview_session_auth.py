"""Real pinned borsapy/httpx auth contracts; all HTTP uses MockTransport."""

import json
import logging
from types import SimpleNamespace

import borsapy as bp
import httpx
import pytest
from borsapy._providers import tradingview
from borsapy.exceptions import AuthenticationError

from application.services.borsapy_gateway import BorsapyGateway, BorsapyGatewayError, _Redact
from infrastructure.providers import tradingview_session_auth as auth

SESSION = "synthetic-session-for-redirect-test"
SIGN = "synthetic-sign%2Bopaque%3D"
TOKEN = "synthetic-auth-token-for-redirect-test"
COOKIE = f"sessionid={SESSION}; sessionid_sign={SIGN}"
PAGE = json.dumps({"auth_token": TOKEN, "id": 123, "username": "synthetic-user"})


@pytest.fixture
def real_provider(monkeypatch):
    clients = []
    bp.clear_tradingview_auth()

    def make(handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        clients.append(client)
        provider = tradingview.TradingViewProvider.__new__(tradingview.TradingViewProvider)
        provider._client = client
        monkeypatch.setattr(tradingview, "_provider", provider)
        return provider, client

    yield make
    bp.clear_tradingview_auth()
    for client in clients:
        client.close()


@pytest.fixture
def gateway(tmp_path):
    settings = SimpleNamespace(
        borsapy_credentials_path=str(tmp_path / "credentials.enc"),
        jwt_secret_key="synthetic-jwt-for-auth-tests-more-than-32-chars",
        database_path=str(tmp_path / "main.sqlite3"),
        borsapy_max_streams=2,
        borsapy_stream_idle_seconds=120,
    )
    item = BorsapyGateway(settings)
    yield item
    item.close()


def test_native_borsapy_drops_manual_cookie_on_redirect(real_provider):
    """Pin the upstream regression independently of the application adapter."""
    cookies = []

    def handler(request):
        cookies.append(request.headers.get("cookie"))
        if len(cookies) == 1:
            return httpx.Response(302, headers={"location": "https://tr.tradingview.com/"})
        return httpx.Response(200, text=PAGE if cookies[-1] == COOKIE else "<html>Login</html>")

    provider, _ = real_provider(handler)
    with pytest.raises(AuthenticationError):
        provider.get_user(SESSION, SIGN)
    assert cookies == [COOKIE, None]


@pytest.mark.parametrize(
    "destination", [None, "www.tradingview.com", "tr.tradingview.com", "tradingview.com"]
)
def test_gateway_uses_real_parser_and_auth_globals_with_scoped_cookie_preservation(
    destination, real_provider, gateway
):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["cookie"] == COOKIE  # Encoded signature is preserved verbatim.
        if destination and len(requests) == 1:
            return httpx.Response(
                302,
                headers={
                    "location": f"https://{destination}/",
                    "set-cookie": "sessionid=must-not-replace-input; Path=/; Domain=.tradingview.com",
                },
            )
        return httpx.Response(200, text=PAGE, headers={"set-cookie": "transient=discard; Path=/"})

    provider, client = real_provider(handler)
    client.cookies.set("existing", "preserve", domain="www.tradingview.com", path="/")
    status = gateway.configure({"session": SESSION, "session_sign": SIGN})
    assert status["configured"] and status["authenticated"]
    assert bp.get_tradingview_auth()["auth_token"] == TOKEN
    assert bp.get_tradingview_auth()["user"]["username"] == "synthetic-user"
    assert provider._client is client
    assert dict(client.cookies) == {"existing": "preserve"}
    assert len(requests) == (2 if destination else 1)
    assert all(request.extensions["timeout"]["read"] <= 10 for request in requests)
    assert all(secret not in json.dumps(status) for secret in (SESSION, SIGN, TOKEN))


@pytest.mark.parametrize(
    "destination",
    [
        "https://untrusted.example/",
        "https://www.tradingview.com.untrusted.example/",
        "http://tr.tradingview.com/",
        "https://tr.tradingview.com:443/",
        f"https://{SESSION}@tr.tradingview.com/",
        "https://www.tradingview.com/chart/",
        "/accounts/signin/",
        f"https://tr.tradingview.com/?session={SESSION}",
        "?",
        "#",
        f"https://tr.tradingview.com/#{SIGN}",
        "https://tr.tradingview.com/\t",
        "",
    ],
)
def test_redirect_outside_exact_auth_roots_never_receives_credentials(
    destination, real_provider, gateway, caplog
):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"location": destination})

    provider, client = real_provider(handler)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(BorsapyGatewayError) as failure:
        gateway.configure({"session": SESSION, "session_sign": SIGN})
    assert len(requests) == 1
    assert requests[0].url == "https://www.tradingview.com/"
    assert provider._client is client
    assert bp.get_tradingview_auth() is None
    assert gateway.status()["state"] == "auth_needed"
    assert gateway.status()["configured"]
    output = str(failure.value) + caplog.text + json.dumps(gateway.status())
    assert all(secret not in output for secret in (SESSION, SIGN, TOKEN))


def test_invalid_initial_url_is_rejected_before_transport(real_provider):
    def handler(request):
        pytest.fail("Invalid auth URL reached HTTP transport")

    provider, client = real_provider(handler)
    with pytest.raises(auth.SessionAuthError), auth.session_client(provider):
        provider._client.get(
            f"https://untrusted.example/?token={TOKEN}",
            headers={"Cookie": COOKIE},
            follow_redirects=True,
        )
    assert provider._client is client


@pytest.mark.parametrize(
    "page", ['{"id":123}', '{"auth_token":"unauthorized_user_token"}', "<html>Login</html>"]
)
def test_missing_or_anonymous_token_clears_auth_and_restores_client(page, real_provider, gateway):
    provider, client = real_provider(lambda request: httpx.Response(200, text=page))
    tradingview._auth_credentials = {"auth_token": "previous-account-token"}
    with pytest.raises(BorsapyGatewayError):
        gateway.configure({"session": SESSION, "session_sign": SIGN})
    assert bp.get_tradingview_auth() is None
    assert gateway.status()["configured"] and not gateway.status()["authenticated"]
    assert provider._client is client


def test_expired_verification_preserves_encrypted_saved_pair(real_provider, gateway):
    expired = [False]

    def handler(request):
        return httpx.Response(200, text="<html>Login</html>" if expired[0] else PAGE)

    provider, client = real_provider(handler)
    gateway.configure({"session": SESSION, "session_sign": SIGN})
    ciphertext = gateway._store.path.read_bytes()
    expired[0] = True
    with pytest.raises(BorsapyGatewayError):
        gateway.verify()
    assert bp.get_tradingview_auth() is None
    assert gateway.status()["configured"] and not gateway.status()["authenticated"]
    assert gateway._store.path.read_bytes() == ciphertext
    assert gateway._store.load() == {"session": SESSION, "session_sign": SIGN}
    assert provider._client is client


def test_chained_account_redactors_also_scrub_already_formatted_exceptions():
    old, current = _Redact(), _Redact()
    old.secrets = ("old-account-secret",)
    current.secrets = (SIGN,)
    error = ValueError(f"provider detail {SIGN}")
    record = logging.LogRecord(
        "borsapy.synthetic", logging.ERROR, __file__, 1, "Failure", (), (ValueError, error, None)
    )
    assert old.filter(record)
    assert record.exc_info is None and SIGN in record.exc_text
    assert current.filter(record)
    assert SIGN not in record.exc_text and "[REDACTED]" in record.exc_text


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_error_http_response_cannot_authenticate_even_with_token_in_body(
    status, real_provider, gateway
):
    provider, client = real_provider(lambda request: httpx.Response(status, text=PAGE))
    with pytest.raises(BorsapyGatewayError):
        gateway.configure({"session": SESSION, "session_sign": SIGN})
    assert provider._client is client
    assert bp.get_tradingview_auth() is None


def test_transport_error_restores_client_and_hides_exception_secrets(
    real_provider, gateway, caplog
):
    def handler(request):
        raise httpx.ReadTimeout(f"Private request included {SESSION} {SIGN}", request=request)

    provider, client = real_provider(handler)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(BorsapyGatewayError) as failure:
        gateway.configure({"session": SESSION, "session_sign": SIGN})
    assert provider._client is client
    assert bp.get_tradingview_auth() is None
    assert all(secret not in str(failure.value) + caplog.text for secret in (SESSION, SIGN, TOKEN))


def test_redirect_loop_is_limited_to_four_requests(real_provider, gateway):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"location": "/"})

    provider, client = real_provider(handler)
    with pytest.raises(BorsapyGatewayError):
        gateway.configure({"session": SESSION, "session_sign": SIGN})
    assert len(requests) == 4
    assert all(request.headers["cookie"] == COOKIE for request in requests)
    assert provider._client is client


def test_deadline_reduces_request_timeout_and_stops_remaining_hops(real_provider):
    clock = [0.0]
    timeouts = []

    def handler(request):
        timeouts.append(request.extensions["timeout"]["read"])
        clock[0] += 14
        return httpx.Response(302, headers={"location": "https://tr.tradingview.com/"})

    provider, client = real_provider(handler)
    with (
        pytest.raises(auth.SessionAuthError, match="süresi doldu"),
        auth.session_client(provider, clock=lambda: clock[0]),
    ):
        provider.get_user(SESSION, SIGN)
    assert timeouts == [10.0, 10.0, 2.0]
    assert provider._client is client


def test_page_size_limit_restores_client_without_authentication(
    real_provider, gateway, monkeypatch
):
    monkeypatch.setattr(auth, "_MAX_PAGE_BYTES", 32)
    provider, client = real_provider(lambda request: httpx.Response(200, text=PAGE))
    with pytest.raises(BorsapyGatewayError):
        gateway.configure({"session": SESSION, "session_sign": SIGN})
    assert provider._client is client
    assert bp.get_tradingview_auth() is None
