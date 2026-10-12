"""Behavioral, offline gates for the fresh API-only dependency image."""

import builtins
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import verify_server_runtime as verifier

ROOT = Path(__file__).resolve().parents[1]
SHA = "1" * 40
ENV = {
    "sys_platform": "linux",
    "platform_machine": "x86_64",
    "python_version": "3.12",
    "python_full_version": "3.12.8",
    "implementation_name": "cpython",
    "extra": "",
}


@pytest.fixture
def clean(tmp_path, monkeypatch):
    root = tmp_path / "app"
    root.mkdir()
    for name in verifier.SOURCE_INPUTS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic source\n", encoding="utf-8")
    (root / "requirements.txt").write_text("-c requirements-security.txt\napi[stream]>=2\n")
    (root / "requirements-dev.lock").write_text(
        "api==2.0\ntransport==1.0\npytest==9.0.3\ntransport==99 ; sys_platform == 'win32'\n"
    )
    (root / "requirements-security.txt").write_text("transport>=1.0\nwerkzeug>=3.1.6\n")
    packages = {
        "pip": {"version": "24.3.1", "requires": [], "extras": []},
        "api": {
            "version": "2.0",
            "requires": ["transport>=1; extra == 'stream'"],
            "extras": ["stream"],
        },
        "transport": {"version": "1.0", "requires": [], "extras": []},
    }
    monkeypatch.setattr(verifier.platform, "python_version", lambda: "3.12.8")
    monkeypatch.setattr(verifier.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(verifier.sys, "platform", "linux")
    monkeypatch.setattr(verifier, "default_environment", lambda: ENV.copy())
    monkeypatch.setattr(verifier.importlib.util, "find_spec", lambda _: None)
    monkeypatch.setattr(verifier, "installed_inventory", lambda: packages)
    return root, packages


def manifest(root, tmp_path):
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps(hashes))
    return target


def test_clean_runtime_matches_lock_without_requiring_development_packages(
    clean, tmp_path, monkeypatch
):
    root, _ = clean
    source = manifest(root, tmp_path)
    original = builtins.__import__

    def no_app_import(name, *args, **kwargs):
        if name.split(".")[0] in {"api", "settings", "db_session", "borsapy", "telegram"}:
            pytest.fail("Verifier must not import application, provider or database code")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_app_import)
    receipt = verifier.verify(root, SHA, source)
    assert receipt["status"] == "verified_clean_server_runtime"
    assert receipt["source_sha"] == SHA and receipt["errors"] == []
    assert receipt["distribution_count"] == 3
    assert "pytest" not in receipt["distributions"]
    assert receipt["source_manifest"]["verified"] is True
    assert receipt["source_manifest"]["file_count"] == len(verifier.SOURCE_INPUTS)


@pytest.mark.parametrize("name", verifier.RETIRED_FILES)
def test_each_retired_runtime_file_blocks_even_when_unimported(clean, name):
    root, _ = clean
    (root / name).write_text("# old runtime")
    with pytest.raises(verifier.VerificationError, match="retired_runtime_file_present"):
        verifier.verify(root, SHA)


@pytest.mark.parametrize("name", sorted(verifier.RETIRED_DISTRIBUTIONS))
def test_removed_distribution_is_not_accepted_even_if_forged_into_lock(clean, name):
    root, packages = clean
    packages[name] = {"version": "1.0", "requires": [], "extras": []}
    with (root / "requirements-dev.lock").open("a") as file:
        file.write(f"{name}==1.0\n")
    with pytest.raises(verifier.VerificationError, match="retired_distribution_present"):
        verifier.verify(root, SHA)


@pytest.mark.parametrize("name", verifier.RETIRED_MODULES)
def test_unmanaged_retired_module_blocks_without_importing_it(clean, monkeypatch, name):
    monkeypatch.setattr(
        verifier.importlib.util, "find_spec", lambda x: object() if x == name else None
    )
    with pytest.raises(verifier.VerificationError, match="retired_module_present"):
        verifier.verify(clean[0], SHA)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("new_package", "installed_lock_mismatch"),
        ("version", "installed_lock_mismatch"),
        ("pip", "base_pip_mismatch"),
        ("missing_extra_dependency", "missing_dependency"),
        ("missing_extra", "missing_extra"),
        ("missing_base_dependency", "missing_dependency"),
        ("url", "dependency_url_forbidden"),
        ("duplicate_pin", "invalid_exact_lock"),
        ("wildcard_pin", "invalid_exact_lock"),
        ("security", "security_constraint_failed"),
    ],
)
def test_dependency_and_extra_failures_are_fail_closed(clean, mutation, code):
    root, packages = clean
    if mutation == "new_package":
        packages["unreviewed"] = {"version": "1.0", "requires": [], "extras": []}
    elif mutation == "version":
        packages["transport"]["version"] = "2.0"
    elif mutation == "pip":
        packages["pip"]["version"] = "25.0"
    elif mutation == "missing_extra_dependency":
        del packages["transport"]
    elif mutation == "missing_extra":
        packages["api"]["extras"] = []
    elif mutation == "missing_base_dependency":
        packages["transport"]["requires"] = ["missing>=1"]
    elif mutation == "url":
        packages["transport"]["requires"] = ["foreign @ https://secret.invalid/private"]
    elif mutation == "duplicate_pin":
        with (root / "requirements-dev.lock").open("a") as file:
            file.write("transport==1.0\n")
    elif mutation == "wildcard_pin":
        path = root / "requirements-dev.lock"
        path.write_text(path.read_text().replace("transport==1.0", "transport==1.*"))
    else:
        (root / "requirements-security.txt").write_text("transport>=3\n")
    with pytest.raises(verifier.VerificationError, match=code):
        verifier.verify(root, SHA)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("changed", "source_hash_mismatch"),
        ("missing", "source_file_missing"),
        ("omit", "incomplete_source_manifest"),
        ("traversal", "invalid_source_entry"),
    ],
)
def test_source_manifest_is_checked_against_image_bytes(clean, tmp_path, mutation, code):
    root, _ = clean
    source = manifest(root, tmp_path)
    if mutation == "changed":
        (root / "api/main.py").write_text("changed")
    elif mutation == "missing":
        (root / "api/main.py").unlink()
    else:
        expected = json.loads(source.read_text())
        if mutation == "omit":
            del expected["api/main.py"]
        else:
            expected["../outside.py"] = "a" * 64
        source.write_text(json.dumps(expected))
    with pytest.raises(verifier.VerificationError, match=code):
        verifier.verify(root, SHA, source)


def test_cli_success_and_failure_are_json_without_raw_exception_details(
    clean, tmp_path, capsys, monkeypatch
):
    root, _ = clean
    output = tmp_path / "receipt.json"
    args = ["--root", str(root), "--source-sha", SHA]
    assert verifier.main([*args, "--output", str(output)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text()) == printed
    assert printed["source_manifest"]["verified"] is False

    def fail(*_):
        raise RuntimeError("TOKEN=private-provider-error")

    monkeypatch.setattr(verifier, "verify", fail)
    assert verifier.main(args) == 1
    printed = capsys.readouterr()
    assert "private-provider-error" not in printed.out + printed.err
    assert json.loads(printed.out)["errors"] == ["verification_error"]


def test_distribution_inventory_rejects_duplicate_normalized_names(monkeypatch):
    class Metadata(dict):
        def get_all(self, key):
            return []

    distributions = [
        SimpleNamespace(metadata=Metadata(Name=name), version="1.0", requires=[])
        for name in ("Some_Package", "some-package")
    ]
    monkeypatch.setattr(verifier.importlib.metadata, "distributions", lambda: distributions)
    with pytest.raises(verifier.VerificationError, match="duplicate_distribution"):
        verifier.installed_inventory()


def test_current_clean_lock_explicitly_omits_all_retired_distributions():
    pins = {
        verifier.canonicalize_name(x.name)
        for x in verifier.requirements((ROOT / "requirements-dev.lock").read_text(), ENV)
    }
    assert not pins & verifier.RETIRED_DISTRIBUTIONS
