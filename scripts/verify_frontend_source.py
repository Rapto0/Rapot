"""Gate a thin frontend image against a normally built, immutable candidate.

Only existing local images are inspected. Stopped, network-disabled containers
are exported without starting application code; tar entries are hashed without
filesystem extraction. Each temporary container is removed by its exact ID.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path
from typing import Any, BinaryIO

BASE_SOURCE = "876f3f37b9d56624d17c46ab924684de559c5530"
BASE_IMAGE = "ghcr.io/rapto0/rapot/frontend@sha256:18a15abed812a356df102980c8a520b8f03707d1ef2d8e84a739d1c879903787"
REVISION = "org.opencontainers.image.revision"
REPLACED_PATHS = ("/app/.next", "/app/public", "/app/server.js", "/app/package.json")
_IMAGE = re.compile(r"ghcr\.io/rapto0/rapot/frontend@sha256:[0-9a-f]{64}")
_SHA = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_MAX_ENTRIES = 250_000
_MAX_BYTES = 4 * 1024**3
_IGNORED_PAX = {
    "mtime",
    "atime",
    "ctime",
    "path",
    "linkpath",
    "size",
    "uid",
    "gid",
    "uname",
    "gname",
}


class FrontendVerificationError(ValueError):
    """A publication failure with no command output or file contents attached."""


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise FrontendVerificationError(message)


def fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(raw).hexdigest()


def _archive_path(value: str) -> str:
    _require(
        isinstance(value, str)
        and 0 < len(value) <= 4096
        and not value.startswith("/")
        and "\\" not in value
        and not any(ord(char) < 32 or ord(char) == 127 for char in value),
        "Unsafe archive path",
    )
    while value.startswith("./"):
        value = value[2:]
    value = value.rstrip("/")
    if value in {"", "."}:
        return "/"
    parts = value.split("/")
    _require(all(part not in {"", ".", ".."} for part in parts), "Unsafe archive path")
    _require(not re.match(r"^[A-Za-z]:", value), "Unsafe archive path")
    return "/" + value


def inventory_tar(
    incoming: BinaryIO, *, max_entries: int = _MAX_ENTRIES, max_bytes: int = _MAX_BYTES
) -> dict[str, dict[str, Any]]:
    """Hash a streamed rootfs export without extracting or following any links."""
    entries: dict[str, dict[str, Any]] = {}
    hardlinks: dict[str, str] = {}
    total_bytes = 0
    with tarfile.open(fileobj=incoming, mode="r|*") as archive:
        for member in archive:
            path = _archive_path(member.name)
            _require(path != "/" or member.isdir(), "Archive root must be a directory")
            _require(path not in entries, "Duplicate archive path")
            _require(len(entries) < max_entries, "Archive entry limit exceeded")
            _require(not member.issparse(), "Sparse archive entries are unsupported")
            _require(
                member.uid >= 0 and member.gid >= 0 and 0 <= member.mode <= 0o7777,
                "Invalid archive ownership or mode",
            )
            item: dict[str, Any] = {"mode": member.mode, "uid": member.uid, "gid": member.gid}
            pax = {
                key: value for key, value in member.pax_headers.items() if key not in _IGNORED_PAX
            }
            _require(len(json.dumps(pax)) <= 65_536, "Archive metadata limit exceeded")
            if pax:
                item["pax"] = pax
            if member.isdir():
                item["type"] = "directory"
            elif member.isreg():
                _require(0 <= member.size <= max_bytes - total_bytes, "Archive byte limit exceeded")
                total_bytes += member.size
                content = archive.extractfile(member)
                _require(content is not None, "Archive file contents unavailable")
                digest = hashlib.sha256()
                observed = 0
                while chunk := content.read(1024 * 1024):
                    observed += len(chunk)
                    _require(observed <= member.size, "Archive file size mismatch")
                    digest.update(chunk)
                _require(observed == member.size, "Truncated archive file")
                item.update(type="file", size=observed, sha256=digest.hexdigest())
            elif member.issym():
                _require(
                    0 < len(member.linkname) <= 4096
                    and not any(ord(char) < 32 or ord(char) == 127 for char in member.linkname),
                    "Invalid symlink target",
                )
                item.update(type="symlink", target=member.linkname)
            elif member.islnk():
                item["type"] = "hardlink"
                hardlinks[path] = _archive_path(member.linkname)
            elif member.ischr() or member.isblk():
                _require(member.devmajor >= 0 and member.devminor >= 0, "Invalid device entry")
                item.update(
                    type="character" if member.ischr() else "block",
                    major=member.devmajor,
                    minor=member.devminor,
                )
            elif member.isfifo():
                item["type"] = "fifo"
            else:
                raise FrontendVerificationError("Unsupported archive entry type")
            entries[path] = item
    _require(bool(entries), "Empty archive")
    # Hardlink direction can change when archive ordering changes. Compare the
    # effective inode groups and contents rather than tar's arbitrary first name.
    groups: dict[str, set[str]] = {}
    for path in hardlinks:
        target, seen = path, set()
        while target in hardlinks:
            _require(target not in seen, "Cyclic hardlink")
            seen.add(target)
            target = hardlinks[target]
        _require(target in entries and entries[target]["type"] == "file", "Missing hardlink file")
        original = entries[target]
        for key in ("mode", "uid", "gid", "pax"):
            _require(entries[path].get(key) == original.get(key), "Conflicting hardlink metadata")
        groups.setdefault(target, {target}).add(path)
    for target, names in groups.items():
        for path in names:
            entries[path] = {**entries[target], "hardlink_group": min(names)}
    # An export must never hide content below a symlink or a regular file.
    for path in entries:
        parent = path.rsplit("/", 1)[0]
        while parent:
            if parent in entries:
                _require(entries[parent]["type"] == "directory", "Non-directory archive parent")
            parent = parent.rsplit("/", 1)[0]
    return entries


def _runtime_inventory(inventory: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        path: item
        for path, item in inventory.items()
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in REPLACED_PATHS)
    }


def _validate_assets(inventory: dict[str, dict[str, Any]]) -> None:
    expected = dict(zip(REPLACED_PATHS, ("directory", "directory", "file", "file")))
    _require(
        all(inventory.get(path, {}).get("type") == kind for path, kind in expected.items()),
        "Expected candidate application paths are missing or have different types",
    )
    _require(
        inventory.get("/app/node_modules", {}).get("type") == "directory", "Node runtime missing"
    )
    # A hardlink spanning an overlay boundary would be split by COPY.
    group_scopes: dict[str, set[str]] = {}
    for path, item in inventory.items():
        if "hardlink_group" in item:
            scope = next(
                (
                    prefix
                    for prefix in REPLACED_PATHS
                    if path == prefix or path.startswith(prefix + "/")
                ),
                "runtime",
            )
            group_scopes.setdefault(item["hardlink_group"], set()).add(scope)
    _require(all(len(scopes) == 1 for scopes in group_scopes.values()), "Cross-boundary hardlink")


def _image_config(
    info: dict[str, Any], source: str, reference: str | None = None
) -> dict[str, Any]:
    _require(
        info.get("Os") == "linux" and info.get("Architecture") == "amd64", "Image platform differs"
    )
    _require(_DIGEST.fullmatch(info.get("Id", "")), "Image config digest missing")
    if reference:
        _require(reference in info.get("RepoDigests", []), "Immutable image reference mismatch")
    config = info.get("Config")
    _require(isinstance(config, dict), "Image configuration missing")
    labels = config.get("Labels")
    _require(
        isinstance(labels, dict) and labels.get(REVISION) == source, "Image source revision differs"
    )
    _require(not config.get("Volumes"), "Volumes would hide image files during export")
    _require(
        config.get("User") == "nextjs" and config.get("WorkingDir") == "/app",
        "Frontend identity differs",
    )
    layers = info.get("RootFS", {}).get("Layers")
    _require(
        info.get("RootFS", {}).get("Type") == "layers"
        and isinstance(layers, list)
        and bool(layers)
        and all(_DIGEST.fullmatch(layer) for layer in layers),
        "Image layer inventory missing",
    )
    return config


def verify_candidate(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    base_image: dict[str, Any],
    candidate_image: dict[str, Any],
    candidate_reference: str,
    expected_source: str,
) -> dict[str, Any]:
    _require(
        _SHA.fullmatch(expected_source) and expected_source != BASE_SOURCE,
        "Invalid source revision",
    )
    _require(_IMAGE.fullmatch(candidate_reference), "Immutable candidate digest required")
    base_config = _image_config(base_image, BASE_SOURCE, BASE_IMAGE)
    candidate_config = _image_config(candidate_image, expected_source, candidate_reference)
    comparable = copy.deepcopy(candidate_config)
    comparable["Labels"][REVISION] = BASE_SOURCE
    _require(
        comparable == base_config, "Candidate changed runtime configuration beyond source revision"
    )
    _validate_assets(base)
    _validate_assets(candidate)
    preserved = _runtime_inventory(base)
    _require(
        preserved == _runtime_inventory(candidate),
        "Candidate changed files outside the four application paths",
    )
    return {
        "schema": "rapot-frontend-source-v1",
        "status": "verified_candidate_runtime",
        "source_sha": expected_source,
        "platform": "linux/amd64",
        "base_image": BASE_IMAGE,
        "base_source": BASE_SOURCE,
        "base_image_id": base_image["Id"],
        "candidate_image": candidate_reference,
        "candidate_image_id": candidate_image["Id"],
        "replacement_paths": list(REPLACED_PATHS),
        "base_inventory_sha256": fingerprint(base),
        "candidate_inventory_sha256": fingerprint(candidate),
        "preserved_inventory_sha256": fingerprint(preserved),
        "preserved_entry_count": len(preserved),
        "candidate_entry_count": len(candidate),
        "candidate_config_sha256": fingerprint(candidate_config),
        "files_outside_replacement_paths_unchanged": True,
        "config_change_from_base": "source_revision_label_only",
        "application_started": False,
    }


def verify_source(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    result: dict[str, dict[str, Any]],
    base_image: dict[str, Any],
    candidate_image: dict[str, Any],
    source_image: dict[str, Any],
    candidate_reference: str,
    source_reference: str,
    expected_source: str,
) -> dict[str, Any]:
    proof = verify_candidate(
        base, candidate, base_image, candidate_image, candidate_reference, expected_source
    )
    config = _image_config(source_image, expected_source)
    _require(
        config == candidate_image["Config"], "Source image configuration differs from candidate"
    )
    _require(result == candidate, "Source image root filesystem differs from candidate")
    prefix = base_image["RootFS"]["Layers"]
    layers = source_image["RootFS"]["Layers"]
    _require(
        len(layers) > len(prefix) and layers[: len(prefix)] == prefix,
        "Source image lost its complete base layer prefix",
    )
    proof.update(
        status="verified_frontend_source",
        source_image=source_reference,
        source_image_id=source_image["Id"],
        source_inventory_sha256=fingerprint(result),
        source_config_sha256=fingerprint(config),
        rootfs_equal_to_candidate=True,
        base_layer_count=len(prefix),
        source_layer_count=len(layers),
        base_layers_sha256=fingerprint(prefix),
        source_layers_sha256=fingerprint(layers),
        complete_base_layer_prefix=True,
    )
    return proof


def _docker(arguments: list[str], *, timeout: int = 60) -> bytes:
    result = subprocess.run(
        ["docker", *arguments], capture_output=True, timeout=timeout, check=False
    )
    _require(
        result.returncode == 0 and len(result.stdout) <= 2 * 1024**2,
        "Docker evidence command failed",
    )
    return result.stdout


def capture_image(reference: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Inspect/export an existing image; never pull it or start application code."""
    values = json.loads(_docker(["image", "inspect", reference]))
    _require(isinstance(values, list) and len(values) == 1, "Image inspection failed")
    info = values[0]
    _require(not (info.get("Config") or {}).get("Volumes"), "Cannot export an image with volumes")
    image_id = info.get("Id", "")
    _require(_DIGEST.fullmatch(image_id), "Invalid local image identity")
    container = (
        _docker(
            [
                "create",
                "--pull",
                "never",
                "--network",
                "none",
                "--read-only",
                "--hostname",
                "rapot-frontend-proof",
                "--name",
                "rapot-frontend-proof-" + uuid.uuid4().hex,
                "--entrypoint",
                "/bin/true",
                image_id,
            ]
        )
        .decode()
        .strip()
    )
    _require(re.fullmatch(r"[0-9a-f]{64}", container), "Invalid temporary container identity")
    try:
        with tempfile.TemporaryDirectory(prefix="rapot-frontend-export-") as directory:
            archive = Path(directory) / "rootfs.tar"
            _docker(["export", "--output", str(archive), container], timeout=240)
            _require(
                archive.is_file() and archive.stat().st_size <= _MAX_BYTES,
                "Export size exceeds bound",
            )
            with archive.open("rb") as incoming:
                inventory = inventory_tar(incoming)
    finally:
        _docker(["rm", container])
    return info, inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("candidate", "verify"))
    parser.add_argument("--base-image", required=True)
    parser.add_argument("--candidate-image", required=True)
    parser.add_argument("--source-image")
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _require(args.base_image == BASE_IMAGE, "Unreviewed frontend base")
        _require(_IMAGE.fullmatch(args.candidate_image), "Immutable candidate image required")
        _require(_SHA.fullmatch(args.expected_source), "Exact source SHA required")
        _require(not args.output.exists(), "Refuse to overwrite prior verification")
        if args.command == "verify":
            _require(
                isinstance(args.source_image, str)
                and re.fullmatch(r"[a-z0-9][a-z0-9._/:@-]{0,255}", args.source_image),
                "Local source image reference required",
            )
        else:
            _require(args.source_image is None, "Candidate check does not use a source image")
        base_image, base = capture_image(args.base_image)
        candidate_image, candidate = capture_image(args.candidate_image)
        if args.command == "candidate":
            proof = verify_candidate(
                base,
                candidate,
                base_image,
                candidate_image,
                args.candidate_image,
                args.expected_source,
            )
        else:
            source_image, result = capture_image(args.source_image)
            proof = verify_source(
                base,
                candidate,
                result,
                base_image,
                candidate_image,
                source_image,
                args.candidate_image,
                args.source_image,
                args.expected_source,
            )
        args.output.write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except FrontendVerificationError as error:
        print(f"Frontend source verification blocked: {error}.", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError, subprocess.SubprocessError):
        print("Frontend source verification failed; publication is blocked.", file=sys.stderr)
        return 1
    print("Frontend source verification passed; no application was started or published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
