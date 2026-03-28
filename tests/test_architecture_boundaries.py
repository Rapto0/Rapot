from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_scanners_do_not_import_api_realtime_directly():
    scanner_files = [
        REPO_ROOT / "market_scanner.py",
        REPO_ROOT / "async_scanner.py",
    ]

    offenders: list[str] = []
    for file_path in scanner_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if "from api.realtime import publish_signal" in source:
            offenders.append(file_path.name)

    assert offenders == [], (
        "Domain scanner modules must not import API transport directly. " f"Offenders: {offenders}"
    )


def test_frontend_has_no_direct_binance_vendor_calls():
    frontend_src = REPO_ROOT / "frontend" / "src"
    offenders: list[str] = []

    for extension in ("*.ts", "*.tsx"):
        for file_path in frontend_src.rglob(extension):
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            if "https://api.binance.com" in source:
                offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Frontend should use backend API contracts instead of direct vendor calls. "
        f"Offenders: {offenders}"
    )
