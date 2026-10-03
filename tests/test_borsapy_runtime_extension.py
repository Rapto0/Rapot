"""Offline, fail-closed gates for the narrowly reviewed additive runtime."""

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest
import yaml

from scripts import verify_borsapy_runtime as verifier

ROOT = Path(__file__).resolve().parents[1]


def inventory(pins):
    records = {
        name: {
            "version": version,
            "file_count": 1,
            "files_sha256": hashlib.sha256(f"{name}=={version}".encode()).hexdigest(),
        }
        for name, version in pins.items()
    }
    return {
        "schema_version": 1,
        "python": "3.12.8",
        "platform": "linux",
        "machine": "x86_64",
        "distributions": records,
        "inventory_sha256": verifier.fingerprint(records),
    }


@pytest.fixture
def snapshots():
    return inventory(verifier.BASE_PINS), inventory(verifier.BASE_PINS | verifier.ADDED_PINS)


@pytest.fixture
def inputs():
    return {
        "requirements": (ROOT / "requirements.txt").read_text(encoding="utf-8"),
        "lock": (ROOT / "requirements-dev.lock").read_text(encoding="utf-8"),
        "security": (ROOT / "requirements-security.txt").read_text(encoding="utf-8"),
    }


def refresh(snapshot):
    snapshot["inventory_sha256"] = verifier.fingerprint(snapshot["distributions"])


def test_exact_reviewed_extension_matches_current_full_requirements(snapshots, inputs):
    result = verifier.verify_extension(*snapshots, **inputs)
    assert result["status"] == "verified_additive_runtime"
    assert result["added_distribution_count"] == 22
    assert result["existing_installed_files"] == "unchanged"
    assert {"httpx2", "httpcore2", "truststore"}.issubset(verifier.ADDED_PINS)
    assert verifier.BASE_PINS.keys().isdisjoint(verifier.ADDED_PINS)
    assert result["base_pins_sha256"] == verifier.fingerprint(verifier.BASE_PINS)


@pytest.mark.parametrize(
    "mutation",
    [
        "change_base",
        "remove_base",
        "missing_added",
        "unexpected_added",
        "changed_file",
        "deleted_file",
        "fingerprint",
        "base_spoof",
        "wrong_platform",
        "wrong_python",
    ],
)
def test_any_base_change_or_unreviewed_addition_blocks_publication(snapshots, inputs, mutation):
    before, after = snapshots
    if mutation == "change_base":
        after["distributions"]["numpy"]["version"] = "2.0.0"
    elif mutation == "remove_base":
        del after["distributions"]["numpy"]
    elif mutation == "missing_added":
        del after["distributions"]["httpx2"]
    elif mutation == "unexpected_added":
        after["distributions"]["unreviewed"] = copy.deepcopy(after["distributions"]["numpy"])
    elif mutation == "changed_file":
        after["distributions"]["numpy"]["files_sha256"] = "f" * 64
    elif mutation == "deleted_file":
        after["distributions"]["numpy"]["file_count"] = 2
    elif mutation == "base_spoof":
        before["distributions"]["numpy"]["version"] = "2.0.0"
        refresh(before)
    elif mutation == "wrong_platform":
        after["machine"] = "aarch64"
    elif mutation == "wrong_python":
        after["python"] = "3.12.9"
    refresh(after)
    if mutation == "fingerprint":
        after["inventory_sha256"] = "f" * 64
    with pytest.raises(verifier.VerificationError):
        verifier.verify_extension(before, after, **inputs)


@pytest.mark.parametrize(
    "mutation",
    [
        "pin_version",
        "missing_pin",
        "duplicate_pin",
        "wildcard",
        "url",
        "security_floor",
        "missing_twitter",
        "unmet_direct",
    ],
)
def test_full_lock_runtime_and_security_constraints_are_checked(snapshots, inputs, mutation):
    if mutation == "pin_version":
        inputs["lock"] = inputs["lock"].replace("cryptography==50.0.2", "cryptography==50.0.3")
    elif mutation == "missing_pin":
        inputs["lock"] = inputs["lock"].replace("httpx2==2.12.0", "")
    elif mutation == "duplicate_pin":
        inputs["lock"] += "\nnumpy==1.26.4\n"
    elif mutation == "wildcard":
        inputs["lock"] = inputs["lock"].replace("numpy==1.26.4", "numpy==1.26.*")
    elif mutation == "url":
        inputs["requirements"] += "\nforeign @ https://example.test/private\n"
    elif mutation == "security_floor":
        inputs["security"] += "\ncryptography>=99.0\n"
    elif mutation == "missing_twitter":
        inputs["requirements"] = inputs["requirements"].replace("borsapy[twitter]", "borsapy")
    else:
        inputs["requirements"] += "\nnumpy>=2\n"
    with pytest.raises(verifier.VerificationError):
        verifier.verify_extension(*snapshots, **inputs)


def test_linux_markers_are_used_even_when_tests_run_on_windows(snapshots, inputs):
    inputs["lock"] += "\nnumpy==9.9 ; sys_platform == 'win32'\n"
    assert verifier.verify_extension(*snapshots, **inputs)["status"] == "verified_additive_runtime"
    inputs["lock"] += "\nnumpy==9.9 ; sys_platform == 'linux'\n"
    with pytest.raises(verifier.VerificationError):
        verifier.verify_extension(*snapshots, **inputs)


def test_capture_hashes_file_contents_ignores_bytecode_and_exposes_no_contents(
    tmp_path, monkeypatch
):
    prefix = tmp_path / "python"
    prefix.mkdir()
    (prefix / "module.py").write_text("sensitive-looking-content", encoding="utf-8")
    (prefix / "module.pyc").write_bytes(b"bytecode")
    distribution = SimpleNamespace(
        metadata={"Name": "Test_Package"},
        version="1.0",
        files=[PurePosixPath("module.py"), PurePosixPath("module.pyc")],
        locate_file=lambda value: prefix / value,
    )
    monkeypatch.setattr(verifier.sys, "prefix", str(prefix))
    monkeypatch.setattr(verifier.importlib.metadata, "distributions", lambda: [distribution])
    first = verifier.capture_inventory()
    assert first["distributions"]["test-package"]["file_count"] == 1
    assert "sensitive-looking-content" not in json.dumps(first)
    (prefix / "module.py").write_text("changed", encoding="utf-8")
    assert verifier.capture_inventory()["inventory_sha256"] != first["inventory_sha256"]


def test_capture_rejects_missing_manifest_and_paths_outside_python_prefix(tmp_path, monkeypatch):
    prefix = tmp_path / "python"
    prefix.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("outside", encoding="utf-8")
    distribution = SimpleNamespace(
        metadata={"Name": "test"},
        version="1.0",
        files=[PurePosixPath("../outside.py")],
        locate_file=lambda value: prefix / value,
    )
    monkeypatch.setattr(verifier.sys, "prefix", str(prefix))
    monkeypatch.setattr(verifier.importlib.metadata, "distributions", lambda: [distribution])
    with pytest.raises(verifier.VerificationError, match="outside"):
        verifier.capture_inventory()
    distribution.files = None
    with pytest.raises(verifier.VerificationError, match="manifest"):
        verifier.capture_inventory()


def test_layer_prefix_and_incremental_size_evidence():
    base = {"size_bytes": 1200, "layers": ["sha256:" + "a" * 64, "sha256:" + "b" * 64]}
    extension = {"size_bytes": 1450, "layers": base["layers"] + ["sha256:" + "c" * 64]}
    result = verifier.verify_layers(base, extension)
    assert result["added_unpacked_bytes"] == 250
    assert result["base_layers_reused"] == 2
    assert "still_required" in result["capacity_status"]
    extension["layers"][0] = "sha256:" + "d" * 64
    with pytest.raises(verifier.VerificationError):
        verifier.verify_layers(base, extension)


def test_pip_check_failure_is_not_reported_as_verified(monkeypatch):
    calls = []

    def run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=1, stderr="secret-looking-upstream-message")

    monkeypatch.setattr(verifier.subprocess, "run", run)
    with pytest.raises(verifier.VerificationError, match="pip check failed"):
        verifier.pip_check()
    assert calls[0][0][0][-3:] == ["-m", "pip", "check"]


def test_cli_writes_combined_proof_only_after_pip_check(snapshots, tmp_path, monkeypatch):
    before, after = snapshots
    documents = {
        "before": before,
        "after": after,
        "base-layers": {"size_bytes": 1200, "layers": ["sha256:" + "a" * 64]},
        "extension-layers": {
            "size_bytes": 1400,
            "layers": ["sha256:" + "a" * 64, "sha256:" + "b" * 64],
        },
    }
    arguments = ["verify", "--root", str(ROOT), "--output", str(tmp_path / "proof.json")]
    for flag, data in documents.items():
        path = tmp_path / f"{flag}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        arguments.extend([f"--{flag}", str(path)])
    checked = []
    monkeypatch.setattr(verifier, "pip_check", lambda: checked.append(True))
    assert verifier.main(arguments) == 0
    proof = json.loads((tmp_path / "proof.json").read_text(encoding="utf-8"))
    assert checked == [True]
    assert proof["pip_check"] == "passed"
    assert proof["layers"]["added_unpacked_bytes"] == 200


def test_cli_failure_never_outputs_exception_or_credentials(tmp_path, monkeypatch, capsys):
    def fail():
        raise OSError("credential=must-not-appear")

    monkeypatch.setattr(verifier, "capture_inventory", fail)
    output = tmp_path / "proof.json"
    assert verifier.main(["capture", "--output", str(output)]) == 1
    result = capsys.readouterr()
    assert "must-not-appear" not in result.err + result.out
    assert "blocked" in result.err
    assert not output.exists()


def test_separate_workflow_preserves_source_only_guard_and_requires_verification():
    document = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8"))
    source_only = document["jobs"]["publish-api-delta"]
    text = "\n".join(step.get("run", "") for step in source_only["steps"])
    assert (
        "Dockerfile requirements.txt requirements-security.txt requirements-dev.lock .python-version"
        in text
    )
    assert 'cmp "$RUNNER_TEMP/api-delta-proof/base-distributions.json"' in text
    extension = document["jobs"]["publish-borsapy-runtime"]
    assert "inputs.publish_borsapy_runtime" in extension["if"]
    steps = extension["steps"]
    verify_index = next(
        i for i, step in enumerate(steps) if "exact additions" in step.get("name", "")
    )
    smoke_index = next(
        i for i, step in enumerate(steps) if "imports, crypto" in step.get("name", "")
    )
    push_index = next(i for i, step in enumerate(steps) if "docker push" in step.get("run", ""))
    assert verify_index < smoke_index < push_index
    assert "--network none" in steps[verify_index]["run"]
    assert "--network none" in steps[smoke_index]["run"]
    assert "docker run" not in steps[push_index]["run"]
    smoke_source = steps[smoke_index]["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    compile(smoke_source, "workflow-offline-smoke", "exec")
    recipe = (ROOT / "Dockerfile.borsapy-runtime").read_text(encoding="utf-8")
    assert f"FROM {verifier.BASE_IMAGE}" in recipe
    assert "--no-cache-dir --no-compile --only-binary=:all:" in recipe
    assert (
        "-r /tmp/runtime-inputs/requirements.txt -c /tmp/runtime-inputs/requirements-dev.lock"
        in recipe
    )
    assert "--no-deps" not in recipe and "--force-reinstall" not in recipe
