from pathlib import Path


def test_market_analysis_routes_have_legacy_and_new_paths():
    source = _read_api_main_source()
    assert '@app.get("/market/analysis"' in source
    assert '@app.get("/api/market/analysis"' in source


def test_calendar_routes_have_legacy_and_new_paths():
    source = _read_api_main_source()
    assert '@app.get("/calendar"' in source
    assert '@app.get("/api/calendar"' in source


def _read_api_main_source() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    api_main_path = repo_root / "api" / "main.py"
    return api_main_path.read_text(encoding="utf-8", errors="ignore")
