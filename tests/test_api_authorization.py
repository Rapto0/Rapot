import sys
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from tests.test_api_market_analysis import _analysis_json, _build_report

PROTECTED = [
    ("POST", "/analyze/THYAO"),
    ("GET", "/logs"),
    ("GET", "/ops/strategy-inspector?symbol=THYAO&strategy=COMBO"),
    ("GET", "/market/analysis?symbol=THYAO"),
    ("GET", "/api/market/analysis?symbol=THYAO"),
]


@pytest.fixture
def manual_analysis(monkeypatch):
    analyze = Mock()
    monkeypatch.setitem(sys.modules, "command_handler", SimpleNamespace(analyze_manual=analyze))
    return analyze


@pytest.mark.parametrize("method,path", PROTECTED)
@pytest.mark.parametrize("credential", ["missing", "invalid", "expired", "no_expiry", "disabled"])
def test_protected_routes_reject_before_work(
    method, path, credential, api_auth_users, monkeypatch, manual_analysis
):
    inspect = Mock(side_effect=AssertionError("unauthorized work"))
    monkeypatch.setattr(api_main, "inspect_strategy", inspect)
    headers = {}
    if credential != "missing":
        token = "not-a-token"
        if credential == "expired":
            token = api_auth_users.create_access_token({"sub": "user"}, timedelta(seconds=-10))
        if credential == "no_expiry":
            auth_globals = api_auth_users.create_access_token.__globals__
            token = auth_globals["jwt"].encode(
                {"sub": "user"}, auth_globals["SECRET_KEY"], algorithm=auth_globals["ALGORITHM"]
            )
        if credential == "disabled":
            token = api_auth_users.create_access_token({"sub": "disabled"})
        headers["Authorization"] = f"Bearer {token}"
    client = TestClient(api_main.app)
    response = client.request(method, path, headers=headers)
    assert response.status_code == (403 if credential == "disabled" else 401)
    manual_analysis.assert_not_called()
    inspect.assert_not_called()


@pytest.mark.parametrize("method,path", PROTECTED[:2])
def test_regular_user_cannot_access_admin_operations(
    method, path, authenticated_api_client, manual_analysis
):
    assert authenticated_api_client.request(method, path).status_code == 403
    manual_analysis.assert_not_called()


def test_login_and_admin_operations(api_auth_users, manual_analysis, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "trading_bot.log").write_text("2026-09-06 | INFO | test log\n", encoding="utf-8")
    client = TestClient(api_main.app)
    login = client.post("/auth/token", json={"username": "admin", "password": "test-password"})
    assert login.status_code == 200
    assert login.json()["expires_in"] > 0
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    assert client.get("/auth/me").json()["is_admin"] is True
    assert client.get("/logs").json()[0]["message"] == "test log"
    assert client.get("/logs?limit=-1").status_code == 422
    assert client.post("/analyze/THYAO").status_code == 200
    manual_analysis.assert_called_once_with("THYAO")


@pytest.mark.parametrize("username,password", [("admin", "wrong"), ("disabled", "test-password")])
def test_invalid_or_disabled_login_is_rejected(username, password, api_auth_users):
    response = TestClient(api_main.app).post(
        "/auth/token", json={"username": username, "password": password}
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_login_attempts_are_rate_limited(api_auth_users):
    client = TestClient(api_main.app)
    responses = [
        client.post("/auth/token", json={"username": "admin", "password": "wrong"})
        for _ in range(6)
    ]
    assert [response.status_code for response in responses] == [401] * 5 + [429]


def test_ai_aliases_share_rate_limit(authenticated_api_client, monkeypatch):
    inspect = Mock(return_value=_build_report())
    ai = Mock(return_value=_analysis_json())
    monkeypatch.setattr(api_main, "inspect_strategy", inspect)
    monkeypatch.setattr("ai_analyst.analyze_with_gemini", ai)
    results = [
        authenticated_api_client.get(path, params={"symbol": "THYAO"})
        for path in ("/market/analysis", "/api/market/analysis", "/market/analysis")
    ]
    assert [response.status_code for response in results] == [200, 200, 429]
    assert ai.call_count == 2


def test_manual_analysis_rate_limit(api_auth_users, manual_analysis):
    token = api_auth_users.create_access_token({"sub": "admin"})
    client = TestClient(api_main.app, headers={"Authorization": f"Bearer {token}"})
    assert [client.post("/analyze/THYAO").status_code for _ in range(3)] == [200, 200, 429]
    assert manual_analysis.call_count == 2


@pytest.mark.parametrize("operation", ["manual", "ai"])
def test_provider_errors_do_not_expose_secrets(
    operation, api_auth_users, monkeypatch, manual_analysis, caplog
):
    secret = "injected-private-provider-secret"
    token = api_auth_users.create_access_token({"sub": "admin"})
    client = TestClient(api_main.app, headers={"Authorization": f"Bearer {token}"})
    if operation == "manual":
        manual_analysis.side_effect = RuntimeError(secret)
        response = client.post("/analyze/THYAO")
    else:
        monkeypatch.setattr(api_main, "inspect_strategy", Mock(side_effect=RuntimeError(secret)))
        response = client.get("/market/analysis?symbol=THYAO")
    assert response.status_code == 500
    assert secret not in response.text
    assert secret not in caplog.text


def test_public_market_reads_remain_available():
    client = TestClient(api_main.app)
    assert client.get("/").status_code == 200
    assert client.get("/signals").status_code == 200
