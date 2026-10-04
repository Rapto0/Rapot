"""Select and verify a source-only derivative of the accepted Borsapy runtime.

Selection uses committed dependency inputs, not installed packages or host state.
The additional image proof complements, and never replaces, the 98+22 verifier.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SOURCE_BASE = "4b15335f00f30e65a21899e73af47c508f395706"
SOURCE_IMAGE = "ghcr.io/rapto0/rapot/backend@sha256:b9695f5f78ccb6f16112578c54fb9fb2de7ce6a3dc4c0836c3da7deacf7adf14"
ADDITIVE_IMAGE = "ghcr.io/rapto0/rapot/backend@sha256:9be0fdb6097f52bf97730f44c86d28c24e2c0cea1fe181e7e8fd668177fdb034"
EXTENSION = "borsapy-0.11.0-v1"
RUNTIME_INPUTS = (
    "requirements.txt",
    "requirements-security.txt",
    "requirements-dev.lock",
    ".python-version",
    "Dockerfile.borsapy-runtime",
)


class SourceVerificationError(ValueError):
    """A safe publication gate failure without upstream output."""


def select_build(root: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", SOURCE_BASE, "HEAD", "--", *RUNTIME_INPUTS],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    changed = sorted(set(result.stdout.splitlines()))
    if not set(changed).issubset(RUNTIME_INPUTS):
        raise SourceVerificationError("Unexpected runtime input comparison")
    return {
        "mode": "additive-runtime" if changed else "source-only",
        "dockerfile": "Dockerfile.borsapy-runtime" if changed else "Dockerfile.borsapy-source",
        "direct_base_image": ADDITIVE_IMAGE if changed else SOURCE_IMAGE,
        "source_base_revision": SOURCE_BASE,
        "compared_inputs": list(RUNTIME_INPUTS),
        "changed_runtime_inputs": changed,
    }


def verify_source_runtime(
    before: dict[str, Any],
    after: dict[str, Any],
    base_layers: dict[str, Any],
    image_layers: dict[str, Any],
) -> dict[str, Any]:
    # Kept out of the selector path: runner-side selection needs only the stdlib.
    from scripts import verify_borsapy_runtime as runtime

    expected = runtime.BASE_PINS | runtime.ADDED_PINS
    if runtime._inventory_versions(before) != expected:
        raise SourceVerificationError("Source base does not contain the reviewed 120 packages")
    if runtime._inventory_versions(after) != expected or before != after:
        raise SourceVerificationError("Source-only image changed installed runtime files")
    base_labels = base_layers.get("labels")
    image_labels = image_layers.get("labels")
    if not isinstance(base_labels, dict) or not isinstance(image_labels, dict):
        raise SourceVerificationError("Image label evidence is missing")
    if (
        base_labels.get("org.opencontainers.image.revision") != SOURCE_BASE
        or base_labels.get("io.rapot.runtime.extension") != EXTENSION
    ):
        raise SourceVerificationError("Source base labels do not match the accepted runtime")
    required = {
        "org.opencontainers.image.base.name": SOURCE_IMAGE,
        "org.opencontainers.image.base.digest": SOURCE_IMAGE.split("@", 1)[1],
        "io.rapot.runtime.extension": EXTENSION,
        "io.rapot.runtime.mode": "source-only",
    }
    if any(image_labels.get(key) != value for key, value in required.items()):
        raise SourceVerificationError("Source-only image labels do not identify the direct base")
    return {
        "status": "verified_source_only_runtime",
        "mode": "source-only",
        "direct_base_image": SOURCE_IMAGE,
        "direct_base_source": SOURCE_BASE,
        "distribution_count": len(expected),
        "installed_files": "unchanged",
        "before_inventory_sha256": before["inventory_sha256"],
        "after_inventory_sha256": after["inventory_sha256"],
        "layers": runtime.verify_layers(base_layers, image_layers),
        "additive_verification": "separate_98_plus_22_proof_required",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("--root", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)
    select.add_argument("--github-output", type=Path)
    verify = commands.add_parser("verify")
    for name in ("before", "after", "base-layers", "image-layers", "output"):
        verify.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "select":
            result = select_build(args.root)
        else:

            def read(path: Path) -> dict[str, Any]:
                return json.loads(path.read_text(encoding="utf-8"))

            result = verify_source_runtime(
                read(args.before), read(args.after), read(args.base_layers), read(args.image_layers)
            )
        args.output.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        if args.command == "select" and args.github_output:
            with args.github_output.open("a", encoding="utf-8") as output:
                for key in ("mode", "dockerfile", "direct_base_image"):
                    output.write(f"{key}={result[key]}\n")
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("Borsapy source runtime gate failed; publication is blocked.", file=sys.stderr)
        return 1
    print("Borsapy source runtime gate completed; no publication or deployment performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
