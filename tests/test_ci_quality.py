"""Offline coverage for the CI security policy; no advisory service is contacted."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ci_quality as quality


def bandit_report() -> dict:
    return {"errors": [], "metrics": {"a.py": {}, "_totals": {}}, "results": []}


def audit_report() -> dict:
    return {"dependencies": [{"name": "demo", "version": "1.0", "vulns": []}], "fixes": []}


def test_tracked_source_scope_includes_middleware_tests_and_excludes_workspaces(
    tmp_path, monkeypatch
):
    names = [
        "a.py",
        "middleware/tests/test_a.py",
        "types.pyi",
        ".claude/a.py",
        ".venv/a.py",
        "README.md",
    ]
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff]\nextend-exclude = [".claude", ".venv"]\n', encoding="utf-8"
    )
    monkeypatch.setattr(
        quality.subprocess, "check_output", lambda *a, **kw: "\0".join(names).encode()
    )
    assert quality.tracked_python_files(tmp_path) == [
        "a.py",
        "middleware/tests/test_a.py",
        "types.pyi",
    ]
    (tmp_path / "a.py").unlink()
    with pytest.raises(quality.ScanError, match="missing"):
        quality.tracked_python_files(tmp_path)


def test_lock_normalizes_names_and_uses_active_environment_markers():
    text = "# exact lock\nDemo_Package==1.0\nother==2.0 ; sys_platform == 'not-real'\n"
    assert quality.locked_requirements(text) == {"demo-package": "1.0"}


@pytest.mark.parametrize(
    "text",
    [
        "demo>=1.0",
        "demo==1.*",
        "demo[a]==1.0",
        "demo @ https://example.com/a.whl",
        "-r x.txt",
        "demo==1\ndemo==1",
        "# empty",
    ],
)
def test_lock_rejects_inputs_that_cannot_establish_exact_coverage(text):
    with pytest.raises(quality.ScanError):
        quality.locked_requirements(text)


def test_bandit_findings_are_report_only_with_exact_coverage():
    report = bandit_report()
    assert quality.validate_bandit(report, ["a.py"], 0)["findings"] == 0
    report["results"] = [{"filename": "./a.py", "issue_severity": "HIGH", "test_id": "B301"}]
    result = quality.validate_bandit(report, ["a.py"], 1)
    assert result == {"files_scanned": 1, "findings": 1, "severity": {"HIGH": 1}}


@pytest.mark.parametrize(
    "mutation", ["errors", "missing", "extra", "malformed", "exit", "fake_finding"]
)
def test_bandit_rejects_errors_and_incomplete_reports(mutation):
    report = bandit_report()
    code = 0
    if mutation == "errors":
        report["errors"] = [{"filename": "a.py", "reason": "syntax error"}]
    elif mutation == "missing":
        del report["metrics"]["a.py"]
    elif mutation == "extra":
        report["metrics"]["untracked.py"] = {}
    elif mutation == "malformed":
        report["results"] = None
    elif mutation == "exit":
        code = 1
    else:
        report["results"] = [{"filename": "other.py", "issue_severity": "HIGH", "test_id": "B301"}]
        code = 1
    with pytest.raises(quality.ScanError):
        quality.validate_bandit(report, ["a.py"], code)


def test_pip_audit_findings_are_report_only_with_exact_lock_coverage():
    report = audit_report()
    assert quality.validate_pip_audit(report, {"demo": "1.0"}, 0)["findings"] == 0
    report["dependencies"][0]["vulns"] = [{"id": "PYSEC-example", "fix_versions": ["2.0"]}]
    assert quality.validate_pip_audit(report, {"demo": "1.0"}, 1) == {
        "packages_scanned": 1,
        "affected_packages": 1,
        "findings": 1,
    }


@pytest.mark.parametrize(
    "mutation", ["skipped", "missing", "duplicate", "version", "malformed", "exit", "fix"]
)
def test_pip_audit_rejects_incomplete_or_invalid_results(mutation):
    report = audit_report()
    code = 0
    dependency = report["dependencies"][0]
    if mutation == "skipped":
        dependency["skip_reason"] = "not found"
    elif mutation == "missing":
        report["dependencies"] = []
    elif mutation == "duplicate":
        report["dependencies"].append(dict(dependency))
    elif mutation == "version":
        dependency["version"] = "2.0"
    elif mutation == "malformed":
        dependency["vulns"] = [{}]
    elif mutation == "exit":
        code = 1
    else:
        report["fixes"] = [{"name": "demo"}]
    with pytest.raises(quality.ScanError):
        quality.validate_pip_audit(report, {"demo": "1.0"}, code)


@pytest.mark.parametrize("contents", [None, "", "invalid", "[]"])
def test_missing_or_invalid_json_cannot_pass(tmp_path, contents):
    path = tmp_path / "report.json"
    if contents is not None:
        path.write_text(contents, encoding="utf-8")
    with pytest.raises(quality.ScanError):
        quality.read_report(path)


def test_scanner_plugin_error_with_zero_exit_is_an_operational_failure(tmp_path, monkeypatch):
    def run(*args, **kwargs):
        kwargs["stdout"].write("[tester] ERROR internal plugin exception\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(quality.subprocess, "run", run)
    with pytest.raises(quality.ScanError, match="operational error"):
        quality.run_scanner(["fake"], tmp_path, tmp_path / "scanner.log")


def test_scanner_timeout_is_not_a_report_only_finding(tmp_path, monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("fake", 180)

    monkeypatch.setattr(quality.subprocess, "run", run)
    with pytest.raises(quality.ScanError, match="TimeoutExpired"):
        quality.run_scanner(["fake"], tmp_path, tmp_path / "scanner.log")


def test_security_runs_second_scan_after_first_failure_and_preserves_summary(tmp_path, monkeypatch):
    (tmp_path / "requirements-dev.lock").write_text("demo==1.0\n", encoding="utf-8")
    monkeypatch.setattr(quality, "tracked_python_files", lambda root: ["a.py"])
    monkeypatch.setattr(quality, "version", lambda name: "test-version")
    calls = []

    def run(command, root, log):
        calls.append(command)
        if "bandit" in command:
            raise quality.ScanError("Simulated tool failure")
        assert "--no-deps" in command and "--disable-pip" in command and "--strict" in command
        assert "--fix" not in command
        path = Path(command[command.index("--output") + 1])
        path.write_text(json.dumps(audit_report()), encoding="utf-8")
        return 0

    monkeypatch.setattr(quality, "run_scanner", run)
    reports = tmp_path / "reports"
    assert quality.run_security(tmp_path, reports) == 1
    assert len(calls) == 2
    summary = quality.read_report(reports / "summary.json")
    assert summary["bandit"]["status"] == "error"
    assert summary["pip-audit"]["status"] == "complete"
    assert "not evidence of zero" in (reports / "summary.md").read_text(encoding="utf-8")


def test_summary_warns_for_findings_without_failing_or_hiding_counts(tmp_path, capsys):
    results = {"bandit": {"status": "complete", "findings": 3}}
    assert quality.write_security_summary(tmp_path, results) is False
    assert "::warning" in capsys.readouterr().out
    assert quality.read_report(tmp_path / "summary.json") == results


def test_existing_report_directory_is_never_reused_as_fresh_evidence(tmp_path):
    with pytest.raises(FileExistsError):
        quality.run_security(tmp_path, tmp_path)
