from __future__ import annotations

from middleware.infra.settings import settings


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


def test_osmanli_proxy_rejects_payload_without_supported_signal_code(client):
    raw_payload = {
        "symbol": "THYAO",
        "side": "BUY",
        "price": 287.25,
    }

    response = client.post("/webhooks/tradingview/osmanli-proxy", json=raw_payload)

    assert response.status_code == 422
    assert "signalCode" in response.json()["detail"]


def test_osmanli_proxy_runtime_config_requires_forward_url():
    settings.osmanli_forward_enabled = True
    settings.osmanli_tv_webhook_url = None

    try:
        settings.validate_runtime_configuration()
    except ValueError as exc:
        assert "MW_OSMANLI_TV_WEBHOOK_URL" in str(exc)
    else:
        raise AssertionError("validate_runtime_configuration should reject missing forward URL")
