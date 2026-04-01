from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTES_DIR = REPO_ROOT / "api" / "routes"
SERVICES_DIR = REPO_ROOT / "api" / "services"
REPOSITORIES_DIR = REPO_ROOT / "api" / "repositories"
APPLICATION_SERVICES_DIR = REPO_ROOT / "application" / "services"
INFRA_REPOSITORIES_DIR = REPO_ROOT / "infrastructure" / "repositories"


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


def test_route_modules_do_not_import_runtime_or_scanner_modules():
    forbidden_imports = (
        "from market_scanner import",
        "import market_scanner",
        "from async_scanner import",
        "import async_scanner",
        "from scheduler import",
        "import scheduler",
        "from websocket_manager import",
        "import websocket_manager",
        "from bist_service import",
        "import bist_service",
        "from telegram_notify import",
        "import telegram_notify",
    )

    offenders: list[str] = []
    for file_path in ROUTES_DIR.glob("*_routes.py"):
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_imports):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "API route modules must stay thin and avoid runtime/scanner dependencies. "
        f"Offenders: {offenders}"
    )


def test_domain_modules_do_not_import_fastapi_layer():
    domain_files = [
        REPO_ROOT / "market_scanner.py",
        REPO_ROOT / "async_scanner.py",
        REPO_ROOT / "signals.py",
        REPO_ROOT / "strategy_inspector.py",
    ]
    forbidden_tokens = (
        "from fastapi import",
        "import fastapi",
        "from api.routes",
    )

    offenders: list[str] = []
    for file_path in domain_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(file_path.name)

    assert offenders == [], (
        "Domain modules should not depend on FastAPI presentation layer. " f"Offenders: {offenders}"
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


def test_route_modules_do_not_access_orm_directly():
    forbidden_tokens = (
        "from db_session import",
        "session.query(",
        "from models import",
    )

    offenders: list[str] = []
    for file_path in ROUTES_DIR.glob("*_routes.py"):
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "API routes should delegate ORM access to services/repositories. " f"Offenders: {offenders}"
    )


def test_service_modules_do_not_open_db_sessions_directly():
    forbidden_tokens = (
        "from db_session import",
        "get_session(",
    )

    offenders: list[str] = []
    for services_dir in (SERVICES_DIR, APPLICATION_SERVICES_DIR):
        for file_path in services_dir.glob("*.py"):
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            if any(token in source for token in forbidden_tokens):
                offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Services should use repository helpers instead of direct sessions. "
        f"Offenders: {offenders}"
    )


def test_route_modules_do_not_import_repositories_directly():
    forbidden_tokens = (
        "from api.repositories",
        "import api.repositories",
    )

    offenders: list[str] = []
    for file_path in ROUTES_DIR.glob("*_routes.py"):
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "API routes should access data via services, not repositories. " f"Offenders: {offenders}"
    )


def test_repository_modules_do_not_import_fastapi_layer():
    forbidden_tokens = (
        "from fastapi import",
        "import fastapi",
        "from api.routes",
    )

    offenders: list[str] = []
    for repository_dir in (REPOSITORIES_DIR, INFRA_REPOSITORIES_DIR):
        for file_path in repository_dir.glob("*.py"):
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            if any(token in source for token in forbidden_tokens):
                offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Repository modules should not depend on HTTP/API transport layers. "
        f"Offenders: {offenders}"
    )


def test_application_services_use_infrastructure_repositories():
    forbidden_tokens = (
        "from api.repositories",
        "import api.repositories",
    )

    offenders: list[str] = []
    for file_path in APPLICATION_SERVICES_DIR.glob("*.py"):
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Canonical application services must depend on infrastructure repositories, "
        f"not API wrapper repositories. Offenders: {offenders}"
    )


def test_api_service_modules_are_compatibility_wrappers():
    offenders: list[str] = []
    for file_path in SERVICES_DIR.glob("*_service.py"):
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if "from application.services." not in source:
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "api/services modules should be thin wrappers around application/services. "
        f"Offenders: {offenders}"
    )


def test_api_repository_modules_are_compatibility_wrappers():
    offenders: list[str] = []
    for file_path in REPOSITORIES_DIR.glob("*_repository.py"):
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if "from infrastructure.repositories." not in source:
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "api/repositories modules should be thin wrappers around infrastructure/repositories. "
        f"Offenders: {offenders}"
    )


def test_compatibility_wrappers_register_usage_telemetry():
    wrapper_files = [
        REPO_ROOT / "api" / "services" / "analysis_service.py",
        REPO_ROOT / "api" / "services" / "signal_trade_service.py",
        REPO_ROOT / "api" / "services" / "system_service.py",
        REPO_ROOT / "api" / "services" / "market_data_service.py",
        REPO_ROOT / "api" / "repositories" / "analysis_repository.py",
        REPO_ROOT / "api" / "repositories" / "signal_trade_repository.py",
        REPO_ROOT / "api" / "repositories" / "system_repository.py",
        REPO_ROOT / "signal_repository.py",
        REPO_ROOT / "trade_repository.py",
        REPO_ROOT / "ops_repository.py",
        REPO_ROOT / "scanner_events.py",
        REPO_ROOT / "scanner_side_effects.py",
    ]

    offenders: list[str] = []
    for file_path in wrapper_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if "register_wrapper_usage(" not in source:
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Compatibility wrappers must register usage telemetry for migration tracking. "
        f"Offenders: {offenders}"
    )


def test_backfill_script_uses_orm_repository_path():
    script_path = REPO_ROOT / "scripts" / "backfill_special_tags.py"
    source = script_path.read_text(encoding="utf-8", errors="ignore")

    assert "from infrastructure.persistence.ops_repository import" in source
    assert "backfill_special_tags" in source
    assert "get_special_tag_coverage" in source
    assert (
        "from ops_repository import backfill_special_tags, get_special_tag_coverage" not in source
    )
    assert "from database import backfill_special_tags, get_special_tag_coverage" not in source


def test_runtime_modules_use_canonical_persistence_imports():
    target_files = [
        REPO_ROOT / "api" / "main.py",
        REPO_ROOT / "market_scanner.py",
        REPO_ROOT / "async_scanner.py",
        REPO_ROOT / "health_api.py",
        REPO_ROOT / "scheduler.py",
        REPO_ROOT / "trade_manager.py",
        REPO_ROOT / "scripts" / "backfill_special_tags.py",
    ]
    forbidden_tokens = (
        "from signal_repository import",
        "from trade_repository import",
        "from ops_repository import",
    )

    offenders: list[str] = []
    for file_path in target_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(file_path.name)

    assert offenders == [], (
        "Runtime modules should import persistence via infrastructure layer. "
        f"Offenders: {offenders}"
    )


def test_runtime_modules_use_canonical_application_service_imports():
    target_files = [
        REPO_ROOT / "api" / "main.py",
        REPO_ROOT / "api" / "routes" / "system_routes.py",
    ]
    forbidden_tokens = (
        "from api.services.",
        "import api.services",
    )

    offenders: list[str] = []
    for file_path in target_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Runtime API modules should import services from application layer. "
        f"Offenders: {offenders}"
    )


def test_scanner_modules_use_domain_events_instead_of_legacy_wrapper():
    target_files = [
        REPO_ROOT / "market_scanner.py",
        REPO_ROOT / "async_scanner.py",
        REPO_ROOT / "scanner_side_effects.py",
    ]

    offenders: list[str] = []
    for file_path in target_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if "from scanner_events import SignalDomainEvent" in source:
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Scanner/runtime modules should use canonical domain event import path, "
        f"not legacy scanner_events wrapper. Offenders: {offenders}"
    )


def test_scanner_runtime_modules_use_canonical_side_effect_handlers():
    target_files = [
        REPO_ROOT / "market_scanner.py",
        REPO_ROOT / "async_scanner.py",
        REPO_ROOT / "application" / "scanner" / "signal_handlers.py",
    ]

    forbidden_tokens = (
        "from scanner_side_effects import",
        "import scanner_side_effects",
    )

    offenders: list[str] = []
    for file_path in target_files:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Scanner runtime should import side-effect handlers from canonical "
        "application.scanner.signal_handlers path, not legacy scanner_side_effects. "
        f"Offenders: {offenders}"
    )


def test_legacy_wrapper_imports_are_limited_to_compat_modules():
    compatibility_modules = {
        REPO_ROOT / "signal_repository.py",
        REPO_ROOT / "trade_repository.py",
        REPO_ROOT / "ops_repository.py",
        REPO_ROOT / "scanner_events.py",
        REPO_ROOT / "scanner_side_effects.py",
    }
    forbidden_tokens = (
        "from signal_repository import",
        "import signal_repository",
        "from trade_repository import",
        "import trade_repository",
        "from ops_repository import",
        "import ops_repository",
        "from scanner_events import",
        "import scanner_events",
        "from scanner_side_effects import",
        "import scanner_side_effects",
    )

    source_roots = [
        REPO_ROOT / "api",
        REPO_ROOT / "application",
        REPO_ROOT / "domain",
        REPO_ROOT / "infrastructure",
        REPO_ROOT / "scripts",
    ]

    candidate_files: set[Path] = set(REPO_ROOT.glob("*.py"))
    for root in source_roots:
        if root.exists():
            candidate_files.update(root.rglob("*.py"))

    offenders: list[str] = []
    for file_path in sorted(candidate_files):
        if file_path in compatibility_modules:
            continue

        source = file_path.read_text(encoding="utf-8", errors="ignore")
        if any(token in source for token in forbidden_tokens):
            offenders.append(str(file_path.relative_to(REPO_ROOT)))

    assert offenders == [], (
        "Legacy wrapper imports must not appear outside compatibility modules. "
        f"Offenders: {offenders}"
    )
