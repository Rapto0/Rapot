"""Offline publication gates for reusing the accepted frontend runtime."""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml

from scripts import verify_frontend_source as gate

SOURCE = "a" * 40
CANDIDATE = "ghcr.io/rapto0/rapot/frontend@sha256:" + "b" * 64
SOURCE_IMAGE = "ghcr.io/rapto0/rapot/frontend:" + SOURCE + "-source"
ROOT = Path(__file__).resolve().parents[1]


def archive(rows: list[tuple[str, str, bytes | str, dict]]) -> io.BytesIO:
    output = io.BytesIO()
    kinds = {
        "directory": tarfile.DIRTYPE,
        "file": tarfile.REGTYPE,
        "symlink": tarfile.SYMTYPE,
        "hardlink": tarfile.LNKTYPE,
        "character": tarfile.CHRTYPE,
        "fifo": tarfile.FIFOTYPE,
    }
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, kind, value, attributes in rows:
            info = tarfile.TarInfo(name)
            info.type = kinds[kind]
            info.mode = 0o755 if kind == "directory" else 0o644
            info.uid = info.gid = 1001
            info.mtime = 100
            for key, setting in attributes.items():
                setattr(info, key, setting)
            if kind == "file":
                assert isinstance(value, bytes)
                info.size = len(value)
                tar.addfile(info, io.BytesIO(value))
            else:
                if kind in {"symlink", "hardlink"}:
                    info.linkname = value
                tar.addfile(info)
    output.seek(0)
    return output


def filesystem(version: bytes = b"old") -> dict:
    rows = [
        (name, "directory", b"", {})
        for name in (
            ".",
            "app",
            "app/.next",
            "app/public",
            "app/node_modules",
            "usr",
            "usr/bin",
            "etc",
        )
    ]
    rows += [
        (name, "file", version, {})
        for name in (
            "app/.next/build.js",
            "app/public/logo.svg",
            "app/server.js",
            "app/package.json",
        )
    ]
    rows += [
        (name, "file", b"preserved", {})
        for name in (
            "app/node_modules/library.js",
            "usr/bin/node",
            "etc/hosts",
            "etc/hostname",
            "etc/resolv.conf",
            ".dockerenv",
        )
    ]
    rows.append(("usr/bin/nodejs", "symlink", "node", {}))
    return gate.inventory_tar(archive(rows))


def image(source: str, reference: str, identity: str) -> dict:
    return {
        "Id": "sha256:" + identity * 64,
        "Os": "linux",
        "Architecture": "amd64",
        "RepoDigests": [reference],
        "Config": {
            "User": "nextjs",
            "WorkingDir": "/app",
            "Env": ["NODE_ENV=production", "PORT=3000"],
            "Cmd": ["node", "server.js"],
            "Entrypoint": ["docker-entrypoint.sh"],
            "ExposedPorts": {"3000/tcp": {}},
            "Labels": {gate.REVISION: source},
            "Volumes": None,
            "Healthcheck": {"Test": ["NONE"]},
            "StopSignal": "SIGTERM",
        },
        "RootFS": {"Type": "layers", "Layers": ["sha256:" + "1" * 64, "sha256:" + "2" * 64]},
    }


@pytest.fixture
def evidence() -> dict:
    base = image(gate.BASE_SOURCE, gate.BASE_IMAGE, "3")
    candidate = image(SOURCE, CANDIDATE, "4")
    source = image(SOURCE, SOURCE_IMAGE, "5")
    source["RootFS"]["Layers"].append("sha256:" + "6" * 64)
    return {
        "base": filesystem(),
        "candidate": filesystem(b"new"),
        "result": filesystem(b"new"),
        "base_image": base,
        "candidate_image": candidate,
        "source_image": source,
        "candidate_reference": CANDIDATE,
        "source_reference": SOURCE_IMAGE,
        "expected_source": SOURCE,
    }


def candidate_proof(evidence: dict) -> dict:
    return gate.verify_candidate(
        **{
            key: value
            for key, value in evidence.items()
            if key not in {"result", "source_image", "source_reference"}
        }
    )


def test_tar_order_times_and_user_names_do_not_change_filesystem_identity():
    rows = [("root", "directory", b"", {}), ("root/a", "file", b"hello", {})]
    reordered = [
        (name, kind, value, {"mtime": 999, "uname": "another", "gname": "other"})
        for name, kind, value, _ in reversed(rows)
    ]
    assert gate.inventory_tar(archive(rows)) == gate.inventory_tar(archive(reordered))


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("mode", 0o600),
        ("uid", 0),
        ("gid", 0),
        ("pax_headers", {"SCHILY.xattr.security.capability": "different"}),
    ],
)
def test_tar_retains_security_metadata(attribute, value):
    original = gate.inventory_tar(archive([("app/file", "file", b"same", {})]))
    changed = gate.inventory_tar(archive([("app/file", "file", b"same", {attribute: value})]))
    assert gate.fingerprint(original) != gate.fingerprint(changed)


def test_tar_retains_symlink_and_device_identity_without_following_them():
    rows = [
        ("link", "symlink", "/outside", {}),
        ("device", "character", b"", {"devmajor": 1, "devminor": 3}),
        ("pipe", "fifo", b"", {}),
    ]
    inventory = gate.inventory_tar(archive(rows))
    assert inventory["/link"]["target"] == "/outside"
    assert inventory["/device"]["major"] == 1
    assert inventory["/device"]["minor"] == 3
    assert inventory["/pipe"]["type"] == "fifo"


def test_hardlinks_compare_inode_groups_independently_of_archive_direction():
    first = gate.inventory_tar(archive([("a", "file", b"content", {}), ("b", "hardlink", "a", {})]))
    reverse = gate.inventory_tar(
        archive([("a", "hardlink", "b", {}), ("b", "file", b"content", {})])
    )
    copies = gate.inventory_tar(
        archive([("a", "file", b"content", {}), ("b", "file", b"content", {})])
    )
    assert first == reverse
    assert first != copies
    assert first["/b"]["hardlink_group"] == "/a"


@pytest.mark.parametrize(
    "rows",
    [
        [("a", "hardlink", "missing", {})],
        [("a", "hardlink", "b", {}), ("b", "hardlink", "a", {})],
        [("a", "file", b"same", {}), ("b", "hardlink", "a", {"mode": 0o600})],
        [("a", "symlink", "../elsewhere", {}), ("a/hidden", "file", b"hidden", {})],
        [(".", "file", b"root", {})],
        [("a", "file", b"first", {}), ("./a", "file", b"second", {})],
    ],
)
def test_ambiguous_or_invalid_archive_structure_is_rejected(rows):
    with pytest.raises(gate.FrontendVerificationError):
        gate.inventory_tar(archive(rows))


@pytest.mark.parametrize(
    "path", ["../escape", "/absolute", "a/../b", "a\\b", "C:/drive", "a//b", "a\nsecret"]
)
def test_unsafe_paths_fail_without_extracting(path):
    with pytest.raises(gate.FrontendVerificationError, match="Unsafe archive path"):
        gate.inventory_tar(archive([(path, "file", b"value", {})]))


def test_archive_bounds_are_enforced():
    with pytest.raises(gate.FrontendVerificationError, match="byte limit"):
        gate.inventory_tar(archive([("a", "file", b"four", {})]), max_bytes=3)
    with pytest.raises(gate.FrontendVerificationError, match="entry limit"):
        gate.inventory_tar(archive([("a", "file", b"", {}), ("b", "file", b"", {})]), max_entries=1)
    with pytest.raises(gate.FrontendVerificationError, match="Empty archive"):
        gate.inventory_tar(archive([]))


def test_expected_source_changes_produce_compact_complete_evidence(evidence):
    proof = gate.verify_source(**evidence)
    assert proof["status"] == "verified_frontend_source"
    assert proof["complete_base_layer_prefix"] is True
    assert proof["rootfs_equal_to_candidate"] is True
    assert proof["files_outside_replacement_paths_unchanged"] is True
    assert proof["application_started"] is False
    assert proof["source_inventory_sha256"] == proof["candidate_inventory_sha256"]
    assert proof["source_config_sha256"] == proof["candidate_config_sha256"]
    assert proof["base_layer_count"] == 2
    assert proof["source_layer_count"] == 3
    assert len(json.dumps(proof)) < 5000


@pytest.mark.parametrize(
    "path",
    [
        "/app/node_modules/library.js",
        "/usr/bin/node",
        "/etc/hosts",
        "/etc/hostname",
        "/etc/resolv.conf",
        "/.dockerenv",
    ],
)
def test_no_runtime_or_daemon_generated_path_is_silently_excluded(evidence, path):
    evidence["candidate"][path]["sha256"] = "changed"
    with pytest.raises(gate.FrontendVerificationError, match="outside the four"):
        candidate_proof(evidence)


@pytest.mark.parametrize(
    "attribute,value",
    [("mode", 0o777), ("uid", 0), ("gid", 0), ("type", "symlink"), ("target", "elsewhere")],
)
def test_runtime_metadata_changes_block_reuse(evidence, attribute, value):
    evidence["candidate"]["/usr/bin/nodejs"][attribute] = value
    if attribute == "type":
        evidence["candidate"]["/usr/bin/nodejs"][attribute] = "file"
    with pytest.raises(gate.FrontendVerificationError, match="outside the four"):
        candidate_proof(evidence)


def test_additions_and_removals_are_allowed_only_under_application_roots(evidence):
    del evidence["candidate"]["/app/.next/build.js"]
    evidence["candidate"]["/app/.next/new.js"] = evidence["candidate"]["/app/server.js"].copy()
    assert candidate_proof(evidence)["status"] == "verified_candidate_runtime"
    evidence["candidate"]["/app/new-runtime.js"] = evidence["candidate"]["/app/server.js"].copy()
    with pytest.raises(gate.FrontendVerificationError, match="outside the four"):
        candidate_proof(evidence)


@pytest.mark.parametrize("path", [*gate.REPLACED_PATHS, "/app/node_modules"])
def test_required_application_paths_cannot_disappear(evidence, path):
    del evidence["candidate"][path]
    with pytest.raises(gate.FrontendVerificationError):
        candidate_proof(evidence)


@pytest.mark.parametrize("other", ["/app/node_modules/library.js", "/app/public/logo.svg"])
def test_hardlink_may_not_span_independent_copy_boundaries(evidence, other):
    for path in ("/app/.next/build.js", other):
        evidence["candidate"][path]["hardlink_group"] = "/app/.next/build.js"
    with pytest.raises(gate.FrontendVerificationError, match="Cross-boundary hardlink"):
        candidate_proof(evidence)


@pytest.mark.parametrize(
    "key,value",
    [
        ("Env", ["NODE_ENV=production", "UNREVIEWED=1"]),
        ("Cmd", ["other"]),
        ("Entrypoint", ["other"]),
        ("User", "root"),
        ("WorkingDir", "/other"),
        ("ExposedPorts", {"80/tcp": {}}),
        ("Healthcheck", {"Test": ["CMD", "other"]}),
        ("StopSignal", "SIGKILL"),
        ("Volumes", {"/app": {}}),
    ],
)
def test_entire_runtime_configuration_is_preserved(evidence, key, value):
    evidence["candidate_image"]["Config"][key] = value
    with pytest.raises(gate.FrontendVerificationError):
        candidate_proof(evidence)


@pytest.mark.parametrize(
    "mutation", ["label", "revision", "architecture", "digest", "base_revision"]
)
def test_provenance_and_platform_are_bound_to_reviewed_images(evidence, mutation):
    if mutation == "label":
        evidence["candidate_image"]["Config"]["Labels"]["extra"] = "value"
    elif mutation == "revision":
        evidence["candidate_image"]["Config"]["Labels"][gate.REVISION] = "0" * 40
    elif mutation == "architecture":
        evidence["candidate_image"]["Architecture"] = "arm64"
    elif mutation == "digest":
        evidence["candidate_image"]["RepoDigests"] = []
    else:
        evidence["base_image"]["Config"]["Labels"][gate.REVISION] = SOURCE
    with pytest.raises(gate.FrontendVerificationError):
        candidate_proof(evidence)


@pytest.mark.parametrize("mutation", ["file", "config", "prefix", "no_new_layers"])
def test_final_image_must_match_candidate_and_retain_full_base(evidence, mutation):
    if mutation == "file":
        evidence["result"]["/app/server.js"]["sha256"] = "wrong"
    elif mutation == "config":
        evidence["source_image"]["Config"]["Env"].append("WRONG=1")
    elif mutation == "prefix":
        evidence["source_image"]["RootFS"]["Layers"][0] = "sha256:" + "9" * 64
    else:
        evidence["source_image"]["RootFS"]["Layers"].pop()
    with pytest.raises(gate.FrontendVerificationError):
        gate.verify_source(**evidence)


def cli_args(output: Path, command: str = "verify") -> list[str]:
    result = [
        command,
        "--base-image",
        gate.BASE_IMAGE,
        "--candidate-image",
        CANDIDATE,
        "--expected-source",
        SOURCE,
        "--output",
        str(output),
    ]
    if command == "verify":
        result += ["--source-image", SOURCE_IMAGE]
    return result


def test_cli_writes_evidence_but_never_replaces_prior_evidence(evidence, tmp_path, monkeypatch):
    values = {
        gate.BASE_IMAGE: (evidence["base_image"], evidence["base"]),
        CANDIDATE: (evidence["candidate_image"], evidence["candidate"]),
        SOURCE_IMAGE: (evidence["source_image"], evidence["result"]),
    }
    seen = []

    def capture(reference):
        seen.append(reference)
        return values[reference]

    monkeypatch.setattr(gate, "capture_image", capture)
    output = tmp_path / "proof.json"
    assert gate.main(cli_args(output)) == 0
    assert seen == [gate.BASE_IMAGE, CANDIDATE, SOURCE_IMAGE]
    original = output.read_bytes()
    assert json.loads(original)["status"] == "verified_frontend_source"
    seen.clear()
    assert gate.main(cli_args(output)) == 1
    assert seen == []
    assert output.read_bytes() == original


def test_cli_rejects_unpinned_reference_before_docker(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gate, "capture_image", lambda _: pytest.fail("Docker must not be called"))
    args = cli_args(tmp_path / "proof.json")
    args[args.index(CANDIDATE)] = "ghcr.io/rapto0/rapot/frontend:latest"
    assert gate.main(args) == 1
    assert "Immutable candidate image required" in capsys.readouterr().err


def test_cli_diagnostics_never_echo_raw_tool_output(tmp_path, monkeypatch, capsys):
    def unavailable(_):
        raise subprocess.CalledProcessError(1, "docker", output="PRIVATE_FIXTURE")

    monkeypatch.setattr(gate, "capture_image", unavailable)
    assert gate.main(cli_args(tmp_path / "proof.json")) == 1
    captured = capsys.readouterr()
    assert "PRIVATE_FIXTURE" not in captured.err + captured.out
    assert "publication is blocked" in captured.err


@pytest.mark.parametrize("fail_export", [False, True])
def test_capture_never_starts_application_and_removes_only_its_stopped_container(
    tmp_path, monkeypatch, fail_export
):
    container_id = "c" * 64
    info = image(SOURCE, CANDIDATE, "4")
    calls = []

    def docker(arguments, **_):
        calls.append(arguments)
        if arguments[:2] == ["image", "inspect"]:
            return json.dumps([info]).encode()
        if arguments[0] == "create":
            return (container_id + "\n").encode()
        if arguments[0] == "export":
            if fail_export:
                raise gate.FrontendVerificationError("Docker evidence command failed")
            Path(arguments[2]).write_bytes(archive([("file", "file", b"content", {})]).getvalue())
        return b""

    monkeypatch.setattr(gate, "_docker", docker)
    if fail_export:
        with pytest.raises(gate.FrontendVerificationError):
            gate.capture_image(CANDIDATE)
    else:
        captured, inventory = gate.capture_image(CANDIDATE)
        assert captured == info
        assert inventory["/file"]["size"] == 7
    assert [call[0] for call in calls] == ["image", "create", "export", "rm"]
    creation = calls[1]
    assert creation[-1] == info["Id"]
    for flag, value in (
        ("--pull", "never"),
        ("--network", "none"),
        ("--hostname", "rapot-frontend-proof"),
        ("--entrypoint", "/bin/true"),
    ):
        assert creation[creation.index(flag) + 1] == value
    assert "--read-only" in creation
    assert calls[-1] == ["rm", container_id]


def test_dockerfile_replaces_only_verified_assets_and_inherits_runtime():
    instructions = [
        line.strip()
        for line in (ROOT / "Dockerfile.frontend-source").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert f"FROM {gate.BASE_IMAGE}" in instructions
    copies = [line for line in instructions if line.startswith("COPY ")]
    assert {line.split()[-1] for line in copies} == set(gate.REPLACED_PATHS)
    assert len(copies) == 4
    assert all(
        "--from=candidate" in line and line.split()[-2] == line.split()[-1] for line in copies
    )
    assert instructions[-1] == "USER nextjs"
    assert not any(
        line.startswith(("ENV ", "CMD ", "ENTRYPOINT ", "VOLUME ", "EXPOSE "))
        for line in instructions
    )


def test_workflow_requires_candidate_verification_and_both_smokes_before_source_publication():
    document = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
    job = document["jobs"]["publish-frontend-source"]
    assert job["needs"] == "publish-images"
    assert job["if"] == "github.event_name == 'workflow_dispatch' && inputs.publish_frontend_source"
    assert job["env"]["FRONTEND_BASE_IMAGE"] == gate.BASE_IMAGE
    assert (
        "@${{ needs.publish-images.outputs.frontend_digest }}"
        in job["env"]["FRONTEND_CANDIDATE_IMAGE"]
    )
    steps = job["steps"]
    commands = [step.get("run", "") for step in steps]
    preflight = next(
        index
        for index, command in enumerate(commands)
        if "verify_frontend_source candidate" in command
    )
    build = next(
        index for index, command in enumerate(commands) if "docker build --network none" in command
    )
    verify = next(
        index
        for index, command in enumerate(commands)
        if "verify_frontend_source verify" in command
    )
    smoke = next(
        index for index, command in enumerate(commands) if "for kind in candidate source" in command
    )
    push = next(index for index, command in enumerate(commands) if "docker push" in command)
    assert preflight < build < verify < smoke < push
    assert sum("docker push" in command for command in commands) == 1
    assert "--network none" in commands[smoke]
    assert "'/chart', '/research', '/login'" in commands[smoke]
    assert "assert.ok(assets.size > 0)" in commands[smoke]
    assert "assert.equal(response.status, 200)" in commands[smoke]
    for index in (preflight, build, verify, smoke, push):
        assert "set -euo pipefail" in commands[index]
        assert steps[index].get("continue-on-error") is not True
        assert "always()" not in steps[index].get("if", "")
    assert steps[-1]["if"] == "always()"
    assert steps[-1]["with"]["if-no-files-found"] == "error"
