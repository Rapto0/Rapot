from __future__ import annotations

from middleware.infra.settings import settings


class _FakeOsmanliResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


def test_osmanli_proxy_shadow_processes_supported_payload(client):
    raw_payload = {
        "symbol": "THYAO",
        "ticker": "THYAO",
        "signalCode": "H_BLS",
        "signalText": "Hunter Beles",
        "side": "BUY",
        "price": 287.25,
        "timeframe": "1D",
        "barTime": 1713772800000,
        "barIndex": 12345,
        "isRealtime": True,
        "apiKey": "secret-like-value",
        "token": "broker-token-like-value",
    }

    response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["forward_enabled"] is False
    assert body["forwarded"] is False
    assert body["extracted_signal"]["symbol"] == "THYAO"
    assert body["extracted_signal"]["signalCode"] == "H_BLS"
    assert body["process_result"]["status"] == "filled"


def test_osmanli_proxy_supports_osmanli_wizard_buy_payload(client):
    raw_payload = {
        "name": "test",
        "symbol": "THYAO",
        "orderSide": "buy",
        "orderType": "lmt",
        "price": "287.25",
        "quantity": "1",
        "timeInForce": "day",
        "apiKey": "secret-like-value",
        "timenow": "2026-04-24T11:00:00Z",
        "token": "broker-token-like-value",
    }

    response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["extracted_signal"]["symbol"] == "THYAO"
    assert body["extracted_signal"]["side"] == "BUY"
    assert body["extracted_signal"]["signalCode"] == "H_BLS"
    assert body["process_result"]["status"] == "filled"


def test_osmanli_proxy_supports_osmanli_wizard_sell_payload(client):
    raw_payload = {
        "name": "test C_PAH",
        "symbol": "THYAO",
        "orderSide": "sell",
        "orderType": "lmt",
        "price": "287.25",
        "quantity": "1",
        "timeInForce": "day",
        "apiKey": "secret-like-value",
        "timenow": "2026-04-24T11:00:00Z",
        "token": "broker-token-like-value",
    }

    response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["extracted_signal"]["side"] == "SELL"
    assert body["extracted_signal"]["signalCode"] == "C_PAH"
    assert body["process_result"]["status"] == "rejected"
    assert body["process_result"]["risk_reason"] == "sell lots < 1"


def test_osmanli_proxy_forwards_buy_and_eligible_sell_when_enabled(client, monkeypatch):
    settings.osmanli_forward_enabled = True
    settings.osmanli_tv_webhook_url = "https://osmanli.example/webhook"
    calls = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeOsmanliResponse(200)

    monkeypatch.setattr(
        "middleware.services.osmanli_proxy_service.requests.post",
        fake_post,
    )

    buy_payload = {
        "name": "test H_BLS",
        "symbol": "THYAO",
        "orderSide": "buy",
        "orderType": "lmt",
        "price": "287.25",
        "quantity": "1",
        "timeInForce": "day",
        "apiKey": "secret-like-value",
        "timenow": "2026-04-24T11:00:00Z",
        "token": "broker-token-like-value",
    }
    sell_payload = {
        "name": "test H_PAH",
        "symbol": "THYAO",
        "orderSide": "sell",
        "orderType": "lmt",
        "price": "290.00",
        "quantity": "1",
        "timeInForce": "day",
        "apiKey": "secret-like-value",
        "timenow": "2026-04-24T11:01:00Z",
        "token": "broker-token-like-value",
    }

    buy_response = client.post("/webhooks/tradingview/osmanli-proxy", json=buy_payload)
    sell_response = client.post("/webhooks/tradingview/osmanli-proxy", json=sell_payload)

    assert buy_response.status_code == 200
    assert sell_response.status_code == 200
    assert buy_response.json()["forwarded"] is True
    assert sell_response.json()["forwarded"] is True
    assert [call["json"]["orderSide"] for call in calls] == ["buy", "sell"]
    assert {call["url"] for call in calls} == {"https://osmanli.example/webhook"}


def test_osmanli_proxy_skips_forward_when_risk_rejects(client, monkeypatch):
    settings.osmanli_forward_enabled = True
    settings.osmanli_tv_webhook_url = "https://osmanli.example/webhook"

    def fail_if_called(*args, **kwargs):
        raise AssertionError("risk-rejected signals must not be forwarded")

    monkeypatch.setattr(
        "middleware.services.osmanli_proxy_service.requests.post",
        fail_if_called,
    )

    raw_payload = {
        "name": "test C_PAH",
        "symbol": "THYAO",
        "orderSide": "sell",
        "orderType": "lmt",
        "price": "287.25",
        "quantity": "1",
        "timeInForce": "day",
        "apiKey": "secret-like-value",
        "timenow": "2026-04-24T11:00:00Z",
        "token": "broker-token-like-value",
    }

    response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["forward_enabled"] is True
    assert body["forwarded"] is False
    assert body["message"] == "forward skipped: signal rejected by risk checks"
    assert body["process_result"]["risk_reason"] == "sell lots < 1"


def test_osmanli_proxy_skips_forward_for_duplicate_signals(client, monkeypatch):
    settings.osmanli_forward_enabled = True
    settings.osmanli_tv_webhook_url = "https://osmanli.example/webhook"
    calls = []

    def fake_post(url, json, timeout):
        calls.append(json)
        return _FakeOsmanliResponse(200)

    monkeypatch.setattr(
        "middleware.services.osmanli_proxy_service.requests.post",
        fake_post,
    )

    raw_payload = {
        "name": "test H_BLS",
        "symbol": "THYAO",
        "orderSide": "buy",
        "orderType": "lmt",
        "price": "287.25",
        "quantity": "1",
        "timeInForce": "day",
        "apiKey": "secret-like-value",
        "timenow": "2026-04-24T11:00:00Z",
        "token": "broker-token-like-value",
    }

    first_response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)
    second_response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["forwarded"] is True
    assert second_response.json()["forwarded"] is False
    assert second_response.json()["message"] == "forward skipped: duplicate signal ignored"
    assert len(calls) == 1


def test_osmanli_proxy_reports_forward_http_failure(client, monkeypatch):
    settings.osmanli_forward_enabled = True
    settings.osmanli_tv_webhook_url = "https://osmanli.example/webhook"

    def fake_post(url, json, timeout):
        return _FakeOsmanliResponse(401)

    monkeypatch.setattr(
        "middleware.services.osmanli_proxy_service.requests.post",
        fake_post,
    )

    raw_payload = {
        "name": "test H_BLS",
        "symbol": "THYAO",
        "orderSide": "buy",
        "orderType": "lmt",
        "price": "287.25",
        "quantity": "1",
        "timeInForce": "day",
        "apiKey": "secret-like-value",
        "timenow": "2026-04-24T11:00:00Z",
        "token": "broker-token-like-value",
    }

    response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["forwarded"] is False
    assert body["forward_status_code"] == 401
    assert body["forward_error"] == "upstream returned HTTP 401"


def test_osmanli_proxy_rejects_payload_without_side(client):
    raw_payload = {
        "symbol": "THYAO",
        "price": 287.25,
    }

    response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert response.status_code == 422
    assert "side" in response.json()["detail"]


def test_osmanli_proxy_runtime_config_requires_forward_url():
    settings.osmanli_forward_enabled = True
    settings.osmanli_tv_webhook_url = None

    try:
        settings.validate_runtime_configuration()
    except ValueError as exc:
        assert "MW_OSMANLI_TV_WEBHOOK_URL" in str(exc)
    else:
        raise AssertionError("validate_runtime_configuration should reject missing forward URL")
