"""Fail-closed evidence for the one reviewed additive borsapy runtime image.

No production configuration is read. Captures expose only package names,
versions, file counts and hashes. The source-only API delta remains separate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

BASE_IMAGE = "ghcr.io/rapto0/rapot/backend@sha256:9be0fdb6097f52bf97730f44c86d28c24e2c0cea1fe181e7e8fd668177fdb034"
BASE_SOURCE = "279aa9fea99b520e661b43f104a2bf4791893ac3"

# Read-only inventory of that immutable linux/amd64 runtime, 4 October 2026.
_BASE_PINS = """
aiohappyeyeballs==2.6.1
aiohttp==3.14.3
aiosignal==1.4.0
alembic==1.18.1
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.12.1
attrs==25.4.0
bcrypt==5.0.0
beautifulsoup4==4.14.3
blinker==1.9.0
certifi==2026.1.4
cffi==2.0.0
charset-normalizer==3.4.4
click==8.3.3
curl-cffi==0.15.0
dateparser==1.2.2
deprecated==1.3.1
distro==1.9.0
et-xmlfile==2.0.0
fastapi==0.133.0
feedparser==6.0.12
flask==3.1.3
frozendict==2.4.7
frozenlist==1.8.0
google-auth==2.47.0
google-genai==1.68.0
greenlet==3.3.0
h11==0.16.0
httpcore==1.0.9
httptools==0.7.1
httpx==0.28.1
idna==3.18
isyatirimhisse==5.0.0
itsdangerous==2.2.0
jinja2==3.1.6
limits==5.6.0
lxml==6.1.0
mako==1.3.12
markdown-it-py==4.2.0
markupsafe==3.0.3
mdurl==0.1.2
multidict==6.7.0
multitasking==0.0.12
numpy==1.26.4
openpyxl==3.1.5
packaging==26.0
pandas==2.3.3
passlib==1.7.4
peewee==4.0.2
pip==24.3.1
platformdirs==4.5.1
propcache==0.4.1
protobuf==5.29.6
psycopg==3.3.2
psycopg-binary==3.3.2
pyasn1==0.6.4
pyasn1-modules==0.4.2
pycparser==3.0
pycryptodome==3.23.0
pydantic==2.12.5
pydantic-core==2.41.5
pydantic-settings==2.14.2
pygments==2.21.0
pyjwt==2.14.0
python-binance==1.0.34
python-dateutil==2.9.0.post0
python-dotenv==1.2.2
python-telegram-bot==22.5
pytz==2025.2
pyyaml==6.0.3
regex==2026.1.15
requests==2.33.0
rich==15.0.0
rsa==4.9.1
schedule==1.2.2
sgmllib3k==1.0.0
six==1.17.0
slowapi==0.1.9
sniffio==1.3.1
soupsieve==2.8.4
sqlalchemy==2.0.46
starlette==1.3.1
ta==0.11.0
tenacity==9.1.2
typing-extensions==4.15.0
typing-inspection==0.4.2
tzdata==2025.3
tzlocal==5.3.1
urllib3==2.7.0
uvicorn==0.40.0
uvloop==0.22.1
watchfiles==1.1.1
websockets==16.0
werkzeug==3.1.6
wrapt==2.0.1
yarl==1.22.0
yfinance==1.2.1
"""
BASE_PINS = dict(line.split("==") for line in _BASE_PINS.splitlines() if line)
ADDED_PINS = {
    "borsapy": "0.11.0",
    "cryptography": "50.0.2",
    "flatbuffers": "25.12.19",
    "httpcore2": "2.12.0",
    "httpx2": "2.12.0",
    "jiter": "0.17.0",
    "networkx": "3.7",
    "onnxruntime": "1.30.0",
    "openai": "3.24.0",
    "psutil": "7.2.2",
    "pymupdf": "1.28.2",
    "pymupdf-layout": "1.28.2",
    "pymupdf4llm": "1.28.2",
    "scweet": "5.8.1",
    "shellingham": "1.5.4",
    "sqlmodel": "0.0.47",
    "tabulate": "0.10.0",
    "tradingview-screener": "3.2.2",
    "truststore": "0.10.4",
    "typer": "0.27.2",
    "websocket-client": "1.9.2",
    "xclienttransaction": "1.0.3",
}


class VerificationError(ValueError):
    """A safe evidence failure without package metadata or credential values."""


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def capture_inventory() -> dict[str, Any]:
    """Hash installed files without importing third-party application packages."""
    packages = {}
    prefix = Path(sys.prefix).resolve()
    for distribution in importlib.metadata.distributions():
        name = canonicalize_name(distribution.metadata["Name"])
        if name in packages:
            raise VerificationError("Duplicate installed distribution")
        files = distribution.files
        if not files:
            raise VerificationError("Installed distribution has no file manifest")
        hashes = {}
        for relative in files:
            if relative.suffix == ".pyc" or "__pycache__" in relative.parts:
                continue
            path = Path(distribution.locate_file(relative)).resolve()
            if not path.is_relative_to(prefix) or not path.is_file():
                raise VerificationError("Installed file is missing or outside the Python prefix")
            # Canonical path keys detect file additions/deletions as well as content changes.
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            hashes[path.relative_to(prefix).as_posix()] = digest.hexdigest()
        if not hashes:
            raise VerificationError("Installed file manifest is empty")
        packages[name] = {
            "version": distribution.version,
            "file_count": len(hashes),
            "files_sha256": fingerprint(hashes),
        }
    return {
        "schema_version": 1,
        "python": platform.python_version(),
        "platform": sys.platform,
        "machine": platform.machine(),
        "distributions": packages,
        "inventory_sha256": fingerprint(packages),
    }


def _inventory_versions(inventory: dict[str, Any]) -> dict[str, str]:
    if not isinstance(inventory, dict) or inventory.get("schema_version") != 1:
        raise VerificationError("Unsupported inventory format")
    if (inventory.get("python"), inventory.get("platform"), inventory.get("machine")) != (
        "3.12.8",
        "linux",
        "x86_64",
    ):
        raise VerificationError("Runtime must be the pinned Python 3.12.8 linux/amd64 image")
    distributions = inventory.get("distributions")
    if not isinstance(distributions, dict) or not distributions:
        raise VerificationError("Empty installed-distribution inventory")
    versions = {}
    for name, record in distributions.items():
        if (
            not isinstance(name, str)
            or canonicalize_name(name) != name
            or not isinstance(record, dict)
            or set(record) != {"version", "file_count", "files_sha256"}
            or not isinstance(record["version"], str)
            or type(record["file_count"]) is not int
            or record["file_count"] < 1
            or not isinstance(record["files_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["files_sha256"])
        ):
            raise VerificationError("Invalid installed-distribution record")
        versions[name] = record["version"]
    if inventory.get("inventory_sha256") != fingerprint(distributions):
        raise VerificationError("Inventory fingerprint does not match its contents")
    return versions


def _requirements(text: str, *, allow_security_include: bool = False) -> list[Requirement]:
    requirements = []
    environment = default_environment()
    environment.update(
        {
            "sys_platform": "linux",
            "os_name": "posix",
            "platform_system": "Linux",
            "platform_machine": "x86_64",
            "python_version": "3.12",
            "python_full_version": "3.12.8",
        }
    )
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if allow_security_include and line == "-c requirements-security.txt":
            continue
        try:
            requirement = Requirement(line)
        except ValueError as error:
            raise VerificationError("Invalid dependency input") from error
        if requirement.url:
            raise VerificationError("Direct dependency URLs are not allowed")
        if not requirement.marker or requirement.marker.evaluate(environment):
            requirements.append(requirement)
    return requirements


def verify_extension(
    before: dict[str, Any], after: dict[str, Any], *, requirements: str, lock: str, security: str
) -> dict[str, Any]:
    """Require the exact base, exact additions and unchanged existing file hashes."""
    before_versions, after_versions = _inventory_versions(before), _inventory_versions(after)
    if before_versions != BASE_PINS:
        raise VerificationError("Base inventory does not match the reviewed immutable runtime")
    if after_versions != BASE_PINS | ADDED_PINS:
        raise VerificationError(
            "Runtime must preserve every base pin and add exactly the 22 reviewed pins"
        )
    for name in BASE_PINS:
        if before["distributions"][name] != after["distributions"][name]:
            raise VerificationError("An existing distribution's installed files changed")
    pins = {}
    for requirement in _requirements(lock):
        name = canonicalize_name(requirement.name)
        specifiers = list(requirement.specifier)
        if (
            name in pins
            or requirement.extras
            or len(specifiers) != 1
            or specifiers[0].operator != "=="
            or "*" in specifiers[0].version
        ):
            raise VerificationError("Lock must contain unique exact active pins")
        pins[name] = specifiers[0].version
    for name, version in after_versions.items():
        if name == "pip":  # inherited build tool, unchanged and not an application dependency
            continue
        if pins.get(name) != version:
            raise VerificationError("Installed runtime does not match the complete reviewed lock")
    direct = _requirements(requirements, allow_security_include=True)
    expected_direct_additions = {"borsapy", "cryptography"}
    if not expected_direct_additions.issubset({canonicalize_name(req.name) for req in direct}):
        raise VerificationError("Runtime extension requirements are missing")
    if not any(req.name.lower() == "borsapy" and req.extras == {"twitter"} for req in direct):
        raise VerificationError("The reviewed Twitter extra is required")
    for requirement in direct + _requirements(security):
        version = after_versions.get(canonicalize_name(requirement.name))
        if version is None or version not in requirement.specifier:
            raise VerificationError(
                "Installed package violates a runtime requirement or security constraint"
            )
    return {
        "status": "verified_additive_runtime",
        "base_image": BASE_IMAGE,
        "base_source": BASE_SOURCE,
        "base_distribution_count": len(BASE_PINS),
        "added_distribution_count": len(ADDED_PINS),
        "base_pins_sha256": fingerprint(BASE_PINS),
        "added_pins_sha256": fingerprint(ADDED_PINS),
        "before_inventory_sha256": before["inventory_sha256"],
        "after_inventory_sha256": after["inventory_sha256"],
        "existing_installed_files": "unchanged",
        "inputs_sha256": {
            "requirements": hashlib.sha256(requirements.encode()).hexdigest(),
            "lock": hashlib.sha256(lock.encode()).hexdigest(),
            "security": hashlib.sha256(security.encode()).hexdigest(),
        },
    }


def verify_layers(base: dict[str, Any], extension: dict[str, Any]) -> dict[str, Any]:
    """Prove all immutable base layers are reused, in their original order."""
    base_layers, extension_layers = base.get("layers"), extension.get("layers")
    if (
        not isinstance(base_layers, list)
        or not base_layers
        or not isinstance(extension_layers, list)
        or not all(
            isinstance(layer, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", layer)
            for layer in base_layers + extension_layers
        )
        or extension_layers[: len(base_layers)] != base_layers
        or len(extension_layers) <= len(base_layers)
    ):
        raise VerificationError(
            "Extension does not preserve the complete immutable base layer prefix"
        )
    for record in (base, extension):
        if type(record.get("size_bytes")) is not int or record["size_bytes"] <= 0:
            raise VerificationError("Invalid image size evidence")
    if extension["size_bytes"] < base["size_bytes"]:
        raise VerificationError("Invalid additive image size")
    return {
        "base_layers_reused": len(base_layers),
        "added_layer_count": len(extension_layers) - len(base_layers),
        "image_bytes": extension["size_bytes"],
        "added_unpacked_bytes": extension["size_bytes"] - base["size_bytes"],
        "capacity_status": "registry_compressed_layers_and_live_free_space_still_required",
    }


def pip_check() -> None:
    checked = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if checked.returncode != 0:
        raise VerificationError("Runtime pip check failed")


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--before", type=Path, required=True)
    verify.add_argument("--after", type=Path, required=True)
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--base-layers", type=Path, required=True)
    verify.add_argument("--extension-layers", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            _write(args.output, capture_inventory())
        else:

            def read(path: Path) -> dict[str, Any]:
                return json.loads(path.read_text(encoding="utf-8"))

            result = verify_extension(
                read(args.before),
                read(args.after),
                requirements=(args.root / "requirements.txt").read_text(encoding="utf-8"),
                lock=(args.root / "requirements-dev.lock").read_text(encoding="utf-8"),
                security=(args.root / "requirements-security.txt").read_text(encoding="utf-8"),
            )
            result["layers"] = verify_layers(read(args.base_layers), read(args.extension_layers))
            pip_check()
            result["pip_check"] = "passed"
            _write(args.output, result)
    except (
        VerificationError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        subprocess.SubprocessError,
    ):
        # Upstream exception text can contain paths or configuration: never print it.
        print("Runtime verification failed; publication is blocked.", file=sys.stderr)
        return 1
    print("Runtime verification completed; no server deployment performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
