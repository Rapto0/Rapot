"""Production topology invariants that can be checked without Docker or real data."""

from pathlib import Path, PurePosixPath

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def services() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]


def test_published_services_are_loopback_only(services: dict) -> None:
    for service in services.values():
        for port in service.get("ports", []):
            assert port.startswith("127.0.0.1:"), "Public exposure needs an explicit reverse proxy"
    assert not services["postgres"].get("ports"), (
        "Middleware database stays on the internal network"
    )


def test_bot_has_one_owner_and_api_cannot_start_an_embedded_bot(services: dict) -> None:
    bot_services = [
        service for service in services.values() if service.get("command", [])[-1:] == ["bot"]
    ]
    assert len(bot_services) == 1
    assert bot_services[0].get("container_name"), "Compose must reject scaling this singleton"
    assert services["api"]["environment"]["RUN_EMBEDDED_BOT"] == "false"


def test_schema_jobs_finish_before_database_consumers_start(services: dict) -> None:
    for name in ("api", "bot"):
        assert services[name]["depends_on"]["main-init"] == {
            "condition": "service_completed_successfully"
        }
    assert services["middleware"]["depends_on"]["middleware-migrate"] == {
        "condition": "service_completed_successfully"
    }
    assert services["middleware-migrate"]["depends_on"]["postgres"] == {
        "condition": "service_healthy"
    }
    for name in ("main-init", "middleware-migrate"):
        assert services[name]["restart"] == "no"


def test_main_sqlite_directory_is_shared_but_middleware_storage_is_separate(services: dict) -> None:
    main_mount = services["main-init"]["volumes"][0]
    assert main_mount["type"] == "bind"
    mount_target = PurePosixPath(main_mount["target"])
    assert mount_target != PurePosixPath("/app"), "Production code must come from the built image"
    assert not mount_target.suffix, "SQLite WAL/SHM and process locks require a directory mount"
    for name in ("main-init", "api", "bot"):
        service = services[name]
        assert service["volumes"] == [main_mount]
        for setting in ("DATABASE_PATH", "CACHE_DATABASE_PATH"):
            assert PurePosixPath(service["environment"][setting]).parent == mount_target
        assert not service["environment"]["DATABASE_URL"]
    assert services["postgres"]["volumes"] == ["middleware_postgres:/var/lib/postgresql/data"]
    for name in ("middleware", "middleware-migrate"):
        assert main_mount not in services[name].get("volumes", [])


def test_optional_middleware_rollout_cannot_enable_live_trading_from_an_env_file(
    services: dict,
) -> None:
    for name in ("postgres", "middleware-migrate", "middleware"):
        assert services[name]["profiles"] == ["middleware"]
    for name in ("middleware", "middleware-migrate"):
        environment = services[name]["environment"]
        assert environment["MW_EXECUTION_MODE"] == "DRY_RUN"
        assert environment["MW_TRADING_ENABLED"] == "false"
        assert environment["MW_BINANCE_LIVE_ENABLED"] == "false"
