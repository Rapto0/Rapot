"""Offline proof for a clean API image; never import the application or providers.

The development lock constrains installed runtime packages, but does not require
development tools. Dependency metadata checks the direct requirements and their
active extras. The caller separately runs pip check and verifies the image CMD.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import sys
from pathlib import Path, PurePosixPath

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

RETIRED_FILES = (
    "main.py",
    "scheduler.py",
    "command_handler.py",
    "telegram_notify.py",
    "trade_manager.py",
    "news_manager.py",
    "market_scanner.py",
    "async_scanner.py",
    "health_api.py",
    "prometheus_metrics.py",
)
RETIRED_DISTRIBUTIONS = frozenset(
    {
        "blinker",
        "feedparser",
        "flask",
        "itsdangerous",
        "jinja2",
        "python-telegram-bot",
        "schedule",
        "sgmllib3k",
        "werkzeug",
    }
)
RETIRED_MODULES = ("flask", "telegram", "schedule")
BASE_PINS = {"pip": "24.3.1"}
SOURCE_INPUTS = frozenset(
    {
        "Dockerfile",
        ".python-version",
        "requirements.txt",
        "requirements-security.txt",
        "requirements-dev.lock",
        "api/main.py",
        "scripts/runtime.py",
        "settings.py",
        "scripts/verify_server_runtime.py",
    }
)


class VerificationError(ValueError):
    """Only fixed diagnostic codes may cross the CLI boundary."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise VerificationError(code)


def requirements(text: str, environment: dict[str, str], *, include: bool = False):
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if include and line == "-c requirements-security.txt":
            continue
        try:
            item = Requirement(line)
        except ValueError:
            raise VerificationError("invalid_dependency_input") from None
        require(not item.url, "dependency_url_forbidden")
        if not item.marker or item.marker.evaluate(environment):
            yield item


def installed_inventory() -> dict[str, dict]:
    result = {}
    for distribution in importlib.metadata.distributions():
        name = canonicalize_name(distribution.metadata["Name"])
        version = distribution.version
        require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)), "invalid_package_name")
        require(isinstance(version, str) and len(version) < 100, "invalid_package_version")
        require(name not in result, "duplicate_distribution")
        result[name] = {
            "version": version,
            "requires": list(distribution.requires or ()),
            "extras": list(distribution.metadata.get_all("Provides-Extra") or ()),
        }
    require(bool(result), "empty_distribution_inventory")
    return result


def verify_dependencies(root: Path, inventory: dict[str, dict], environment: dict[str, str]):
    pins = {}
    for item in requirements((root / "requirements-dev.lock").read_text(), environment):
        name = canonicalize_name(item.name)
        specs = list(item.specifier)
        require(
            name not in pins
            and not item.extras
            and len(specs) == 1
            and specs[0].operator == "=="
            and "*" not in specs[0].version,
            "invalid_exact_lock",
        )
        pins[name] = specs[0].version
    require(not (RETIRED_DISTRIBUTIONS & inventory.keys()), "retired_distribution_present")
    require(inventory.get("pip", {}).get("version") == BASE_PINS["pip"], "base_pip_mismatch")
    for name, record in inventory.items():
        require((pins | BASE_PINS).get(name) == record["version"], "installed_lock_mismatch")

    direct = list(requirements((root / "requirements.txt").read_text(), environment, include=True))
    require(bool(direct), "empty_runtime_requirements")
    pending = direct[:]
    # Check all installed dependency metadata, including extras propagated by
    # runtime roots (borsapy[twitter], uvicorn[standard], psycopg[binary]).
    pending += [Requirement(name) for name in inventory]
    checked = set()
    while pending:
        item = pending.pop()
        name = canonicalize_name(item.name)
        record = inventory.get(name)
        require(record is not None and record["version"] in item.specifier, "missing_dependency")
        extras = {canonicalize_name(extra) for extra in item.extras}
        require(extras <= {canonicalize_name(x) for x in record["extras"]}, "missing_extra")
        for extra in {"", *extras}:
            if (name, extra) in checked:
                continue
            checked.add((name, extra))
            pending.extend(
                requirements("\n".join(record["requires"]), environment | {"extra": extra})
            )
    for item in requirements((root / "requirements-security.txt").read_text(), environment):
        record = inventory.get(canonicalize_name(item.name))
        require(record is None or record["version"] in item.specifier, "security_constraint_failed")


def verify_source(root: Path, manifest: Path | None) -> dict:
    if manifest is None:
        return {"verified": False, "reason": "manifest_not_supplied", "file_count": 0}
    require(manifest.stat().st_size <= 2 * 1024 * 1024, "source_manifest_too_large")
    raw = manifest.read_bytes()
    expected = json.loads(raw)
    require(isinstance(expected, dict) and 0 < len(expected) <= 10000, "invalid_source_manifest")
    require(expected.keys() >= SOURCE_INPUTS, "incomplete_source_manifest")
    for name, digest in expected.items():
        require(isinstance(name, str) and isinstance(digest, str), "invalid_source_entry")
        relative = PurePosixPath(name)
        require(
            relative.as_posix() == name
            and not relative.is_absolute()
            and ".." not in relative.parts
            and "\\" not in name
            and ":" not in name
            and (name in SOURCE_INPUTS or (name.endswith(".py") and not name.startswith(".")))
            and bool(re.fullmatch(r"[a-f0-9]{64}", digest)),
            "invalid_source_entry",
        )
        path = root.joinpath(*relative.parts)
        require(
            not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent),
            "source_symlink_forbidden",
        )
        require(
            path.resolve().is_relative_to(root.resolve()) and path.is_file(), "source_file_missing"
        )
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, "source_hash_mismatch")
    return {
        "verified": True,
        "file_count": len(expected),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def verify(root: Path, source_sha: str, manifest: Path | None = None) -> dict:
    require(bool(re.fullmatch(r"[a-f0-9]{40}", source_sha)), "invalid_source_sha")
    require(
        (platform.python_version(), sys.platform, platform.machine())
        == ("3.12.8", "linux", "x86_64"),
        "unsupported_python_platform",
    )
    require(root.is_dir(), "source_root_missing")
    for name in RETIRED_FILES:
        path = root / name
        require(not path.exists() and not path.is_symlink(), "retired_runtime_file_present")
    for name in RETIRED_MODULES:
        require(importlib.util.find_spec(name) is None, "retired_module_present")
    inventory = installed_inventory()
    environment = default_environment() | {"extra": ""}
    verify_dependencies(root, inventory, environment)
    source = verify_source(root, manifest)
    distributions = {name: item["version"] for name, item in sorted(inventory.items())}
    return {
        "schema": "rapot-server-runtime-v1",
        "status": "verified_clean_server_runtime",
        "source_sha": source_sha,
        "python": platform.python_version(),
        "platform": sys.platform,
        "machine": platform.machine(),
        "distributions": distributions,
        "distribution_count": len(distributions),
        "source_manifest": source,
        "retired_files_absent": list(RETIRED_FILES),
        "retired_distributions_absent": sorted(RETIRED_DISTRIBUTIONS),
        "retired_modules_absent": list(RETIRED_MODULES),
        "errors": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/app"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.root, args.source_sha, args.source_manifest)
    except Exception as exc:
        # No upstream metadata, exception messages, environment or paths in errors.
        result = {
            "schema": "rapot-server-runtime-v1",
            "status": "blocked",
            "errors": [str(exc) if isinstance(exc, VerificationError) else "verification_error"],
        }
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(rendered)
    print(rendered, end="")
    return 0 if result["status"] == "verified_clean_server_runtime" else 1


if __name__ == "__main__":
    raise SystemExit(main())
