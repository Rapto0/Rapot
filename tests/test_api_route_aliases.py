import api.main as api_main


def test_market_analysis_routes_have_legacy_and_new_paths():
    routes = _route_paths()
    assert "/market/analysis" in routes
    assert "/api/market/analysis" in routes


def test_calendar_routes_have_legacy_and_new_paths():
    routes = _route_paths()
    assert "/calendar" in routes
    assert "/api/calendar" in routes


def test_symbols_routes_include_bist_and_crypto():
    routes = _route_paths()
    assert "/symbols/bist" in routes
    assert "/symbols/crypto" in routes


def _route_paths() -> set[str]:
    return {route.path for route in api_main.app.routes}
