import api.main as api_main


def test_frontend_http_contracts_exist_in_openapi():
    openapi_paths: dict[str, dict] = api_main.app.openapi().get("paths", {})

    expected_contracts = {
        ("get", "/signals"),
        ("get", "/signals/{signal_id}"),
        ("get", "/trades"),
        ("get", "/stats"),
        ("get", "/symbols/bist"),
        ("get", "/symbols/crypto"),
        ("get", "/candles/{symbol}"),
        ("get", "/market/ticker"),
        ("get", "/market/overview"),
        ("get", "/market/indices"),
        ("get", "/market/metrics"),
        ("get", "/calendar"),
        ("get", "/scans"),
        ("get", "/logs"),
        ("get", "/ops/special-tag-health"),
        ("get", "/ops/strategy-inspector"),
        ("post", "/analyze/{symbol}"),
        ("get", "/analyses"),
        ("get", "/analyses/{analysis_id}"),
        ("get", "/signals/{signal_id}/analysis"),
        ("get", "/market/analysis"),
    }

    missing: list[str] = []
    for method, path in sorted(expected_contracts):
        path_ops = openapi_paths.get(path)
        if not path_ops or method not in path_ops:
            missing.append(f"{method.upper()} {path}")

    assert missing == [], f"Missing frontend contracts in OpenAPI: {missing}"
