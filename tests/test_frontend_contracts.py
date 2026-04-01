from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
ECONOMIC_CALENDAR_COMPONENT = FRONTEND_SRC / "components" / "dashboard" / "economic-calendar.tsx"
API_CORE_FILE = FRONTEND_SRC / "lib" / "api" / "core.ts"
API_CLIENT_FACADE_FILE = FRONTEND_SRC / "lib" / "api" / "client.ts"
REALTIME_CONNECTION_FILE = FRONTEND_SRC / "lib" / "realtime" / "use-realtime-connection.ts"


def _iter_frontend_source_files():
    for extension in ("*.ts", "*.tsx"):
        yield from FRONTEND_SRC.rglob(extension)


def test_frontend_has_no_hardcoded_local_backend_urls():
    disallowed_values = ("http://localhost:8000", "http://api:8000")
    offenders: list[str] = []

    for file_path in _iter_frontend_source_files():
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(value in source for value in disallowed_values):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Hardcoded local backend URL bulundu. Ortak API base/rewrite kullanilmali. "
        f"Offenders: {offenders}"
    )


def test_economic_calendar_uses_shared_api_client():
    source = ECONOMIC_CALENDAR_COMPONENT.read_text(encoding="utf-8", errors="ignore")

    assert "fetchEconomicCalendar" in source
    assert "http://localhost:8000" not in source


def test_api_client_normalizes_public_base_urls():
    source = API_CORE_FILE.read_text(encoding="utf-8", errors="ignore")

    assert "function normalizeBaseUrl" in source
    assert "const API_BASE_URL = normalizeBaseUrl" in source


def test_realtime_hook_uses_dedicated_signal_channel():
    source = REALTIME_CONNECTION_FILE.read_text(encoding="utf-8", errors="ignore")

    assert "/realtime/ws/signals" in source or "/signals" in source


def test_api_client_file_is_thin_facade():
    source = API_CLIENT_FACADE_FILE.read_text(encoding="utf-8", errors="ignore")

    assert "export * from './signals-api';" in source
    assert "export * from './market-api';" in source
    assert "export * from './ops-api';" in source
    assert "export * from './analysis-api';" in source
    assert "fetch(" not in source
