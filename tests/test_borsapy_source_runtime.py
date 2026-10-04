"""Offline source-selection and full accepted-runtime reuse publication gates."""

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import verify_borsapy_runtime as runtime
from scripts import verify_borsapy_source as source

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inventory():
    packages = {
        name: {
            "version": version,
            "file_count": 10,
            "files_sha256": hashlib.sha256(name.encode()).hexdigest(),
        }
        for name, version in (runtime.BASE_PINS | runtime.ADDED_PINS).items()
    }
    return {
        "schema_version": 1,
        "python": "3.12.8",
        "platform": "linux",
        "machine": "x86_64",
        "distributions": packages,
        "inventory_sha256": runtime.fingerprint(packages),
    }


@pytest.fixture
def layers():
    base = {
        "size_bytes": 2000,
        "layers": ["sha256:" + value * 64 for value in "abc"],
        "labels": {
            "org.opencontainers.image.revision": source.SOURCE_BASE,
            "io.rapot.runtime.extension": source.EXTENSION,
        },
    }
    after = {
        "size_bytes": 2100,
        "layers": base["layers"] + ["sha256:" + "d" * 64],
        "labels": {
            "org.opencontainers.image.base.name": source.SOURCE_IMAGE,
            "org.opencontainers.image.base.digest": source.SOURCE_IMAGE.split("@")[1],
            "io.rapot.runtime.extension": source.EXTENSION,
            "io.rapot.runtime.mode": "source-only",
        },
    }
    return base, after


@pytest.mark.parametrize("changed", [None, *source.RUNTIME_INPUTS])
def test_selector_uses_only_committed_inputs_and_falls_back_on_each_runtime_change(
    monkeypatch, changed
):
    calls = []

    def diff(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout=f"{changed}\n" if changed else "")

    monkeypatch.setattr(source.subprocess, "run", diff)
    plan = source.select_build(ROOT)
    assert plan["mode"] == ("additive-runtime" if changed else "source-only")
    assert plan["dockerfile"] == (
        "Dockerfile.borsapy-runtime" if changed else "Dockerfile.borsapy-source"
    )
    assert plan["direct_base_image"] == (source.ADDITIVE_IMAGE if changed else source.SOURCE_IMAGE)
    assert plan["changed_runtime_inputs"] == ([changed] if changed else [])
    assert calls[0][0] == [
        "git",
        "diff",
        "--name-only",
        "--no-renames",
        source.SOURCE_BASE,
        "HEAD",
        "--",
        *source.RUNTIME_INPUTS,
    ]
    assert calls[0][1]["check"] is True
    assert calls[0][1]["timeout"] == 30


def test_selector_git_error_cannot_silently_enable_either_publication_mode(
    monkeypatch, tmp_path, capsys
):
    def unavailable(*args, **kwargs):
        raise subprocess.CalledProcessError(128, ["git"], stderr="private-looking-content")

    monkeypatch.setattr(source.subprocess, "run", unavailable)
    output = tmp_path / "mode.json"
    github = tmp_path / "outputs"
    assert (
        source.main(
            [
                "select",
                "--root",
                str(ROOT),
                "--output",
                str(output),
                "--github-output",
                str(github),
            ]
        )
        == 1
    )
    assert not output.exists() and not github.exists()
    assert "private-looking-content" not in capsys.readouterr().err


def test_selector_records_exact_mode_without_replacing_existing_github_outputs(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        source.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="")
    )
    output = tmp_path / "mode.json"
    github = tmp_path / "outputs"
    github.write_text("sha=known-source\n", encoding="utf-8")
    assert (
        source.main(
            [
                "select",
                "--root",
                str(ROOT),
                "--output",
                str(output),
                "--github-output",
                str(github),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text())["mode"] == "source-only"
    assert github.read_text().splitlines() == [
        "sha=known-source",
        "mode=source-only",
        "dockerfile=Dockerfile.borsapy-source",
        f"direct_base_image={source.SOURCE_IMAGE}",
    ]


def test_all_120_packages_and_full_direct_base_layer_prefix_must_match(inventory, layers):
    result = source.verify_source_runtime(inventory, copy.deepcopy(inventory), *layers)
    assert result["status"] == "verified_source_only_runtime"
    assert result["distribution_count"] == 120
    assert result["installed_files"] == "unchanged"
    assert result["layers"]["base_layers_reused"] == 3
    assert result["layers"]["added_unpacked_bytes"] == 100
    assert result["additive_verification"] == "separate_98_plus_22_proof_required"


@pytest.mark.parametrize("package", ["numpy", "cryptography", "borsapy"])
@pytest.mark.parametrize("field", ["version", "file_count", "files_sha256"])
def test_any_old_or_additive_distribution_mutation_is_rejected(inventory, layers, package, field):
    after = copy.deepcopy(inventory)
    after["distributions"][package][field] = {
        "version": "99.0",
        "file_count": 11,
        "files_sha256": "f" * 64,
    }[field]
    after["inventory_sha256"] = runtime.fingerprint(after["distributions"])
    with pytest.raises(ValueError):
        source.verify_source_runtime(inventory, after, *layers)


@pytest.mark.parametrize(
    "mutation",
    [
        "base_package",
        "base_revision",
        "base_extension",
        "layer",
        "reordered",
        "missing_layer",
        "base_label",
        "digest_label",
        "mode",
        "extension",
    ],
)
def test_spoofed_base_and_incomplete_direct_base_reuse_are_rejected(inventory, layers, mutation):
    before, after = layers
    if mutation == "base_package":
        del inventory["distributions"]["borsapy"]
        inventory["inventory_sha256"] = runtime.fingerprint(inventory["distributions"])
    elif mutation == "base_revision":
        before["labels"]["org.opencontainers.image.revision"] = "f" * 40
    elif mutation == "base_extension":
        before["labels"].pop("io.rapot.runtime.extension")
    elif mutation == "layer":
        after["layers"][2] = "sha256:" + "f" * 64
    elif mutation == "reordered":
        after["layers"][0:2] = after["layers"][1::-1]
    elif mutation == "missing_layer":
        after["layers"].pop(2)
    else:
        label = {
            "base_label": "org.opencontainers.image.base.name",
            "digest_label": "org.opencontainers.image.base.digest",
            "mode": "io.rapot.runtime.mode",
            "extension": "io.rapot.runtime.extension",
        }[mutation]
        after["labels"].pop(label)
    with pytest.raises(ValueError):
        source.verify_source_runtime(inventory, inventory, before, after)


def test_source_proof_cli_writes_the_full_comparison(inventory, layers, tmp_path):
    arguments = ["verify", "--output", str(tmp_path / "proof.json")]
    for name, value in zip(
        ("before", "after", "base-layers", "image-layers"),
        [inventory, inventory, *layers],
        strict=True,
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        arguments.extend([f"--{name}", str(path)])
    assert source.main(arguments) == 0
    proof = json.loads((tmp_path / "proof.json").read_text())
    assert proof["distribution_count"] == 120
    assert proof["direct_base_image"] == source.SOURCE_IMAGE


def test_recipe_and_workflow_require_both_proofs_before_push():
    recipe = (ROOT / "Dockerfile.borsapy-source").read_text(encoding="utf-8")
    commands = [
        line.strip() for line in recipe.splitlines() if line.strip() and not line.startswith("#")
    ]
    assert commands[0] == f"FROM {source.SOURCE_IMAGE}"
    assert "pip install" not in recipe and "apt-get" not in recipe
    assert "source = pathlib.Path('/app')" in recipe
    assert "not source.is_symlink()" in recipe
    assert "COPY . ." in commands
    assert recipe.count("\nRUN ") == 1
    assert recipe.count("\nCOPY ") == 1
    assert "\nADD " not in recipe
    for label in (
        "org.opencontainers.image.base.name",
        "org.opencontainers.image.base.digest",
        "io.rapot.runtime.extension",
        "io.rapot.runtime.mode",
    ):
        assert label in recipe
    document = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8"))
    job = document["jobs"]["publish-borsapy-runtime"]
    steps = job["steps"]
    preparation = next(step for step in steps if step.get("id") == "source")
    assert "scripts.verify_borsapy_source select" in preparation["run"]
    assert "build-mode.json" in preparation["run"]
    assert all(
        name in preparation["run"]
        for name in ("Dockerfile.borsapy-runtime", "Dockerfile.borsapy-source")
    )
    build = next(
        step for step in steps if step.get("uses", "").startswith("docker/build-push-action")
    )
    assert "steps.source.outputs.dockerfile" in build["with"]["file"]
    assert build["with"]["push"] is False
    additive = next(i for i, step in enumerate(steps) if "exact additions" in step.get("name", ""))
    extra = next(i for i, step in enumerate(steps) if "source-only mode" in step.get("name", ""))
    smoke = next(i for i, step in enumerate(steps) if "imports, crypto" in step.get("name", ""))
    push = next(i for i, step in enumerate(steps) if "docker push" in step.get("run", ""))
    assert additive < extra < smoke < push
    assert not steps[additive].get("if")
    assert steps[extra]["if"] == "steps.source.outputs.mode == 'source-only'"
    assert "--network none" in steps[extra]["run"]
    assert "source-base-inventory.json" in steps[extra]["run"]
    assert "source-only-verification.json" in steps[extra]["run"]
    assert job["env"]["BORSAPY_SOURCE_IMAGE"] == source.SOURCE_IMAGE
