"""CI-only source checks and explicit, report-only security findings.

Security findings are not a release gate yet. Scanner failures, incomplete coverage
and invalid reports are failures; a green result does not mean zero findings.
"""

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import tomllib
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version


class ScanError(ValueError):
    """The scanner did not establish a complete, valid result."""


def tracked_python_files(root: Path) -> list[str]:
    """Select committed Python sources, respecting the shared workspace exclusions."""
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root, timeout=30)
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    exclusions = config["tool"]["ruff"].get("extend-exclude", [])
    files = []
    for path in paths.decode("utf-8").split("\0"):
        if not path.endswith((".py", ".pyi")):
            continue
        if any(
            fnmatch.fnmatchcase(path, pattern)
            or any(fnmatch.fnmatchcase(part, pattern) for part in Path(path).parts)
            for pattern in exclusions
        ):
            continue
        source = root / path
        if source.is_symlink() or not source.is_file():
            raise ScanError("Tracked Python input is missing or a symbolic link")
        files.append(path)
    if not files:
        raise ScanError("No tracked Python sources selected")
    return sorted(set(files))


def locked_requirements(text: str) -> dict[str, str]:
    """Validate exact public-package pins, applying this CI environment's markers."""
    pins: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            requirement = Requirement(line)
        except ValueError as error:
            raise ScanError("Invalid lock requirement") from error
        specifiers = list(requirement.specifier)
        if (
            requirement.url
            or requirement.extras
            or len(specifiers) != 1
            or specifiers[0].operator != "=="
            or "*" in specifiers[0].version
        ):
            raise ScanError("Audit requires exact package pins without URLs or extras")
        if requirement.marker and not requirement.marker.evaluate():
            continue
        name = canonicalize_name(requirement.name)
        pinned = str(Version(specifiers[0].version))
        if name in pins:
            raise ScanError("Duplicate active lock requirement")
        pins[name] = pinned
    if not pins:
        raise ScanError("No active lock requirements selected")
    return pins


def validate_exit_code(returncode: int, findings: int) -> None:
    if returncode != (1 if findings else 0):
        raise ScanError("Scanner exit code does not match its validated report")


def validate_bandit(report: dict[str, Any], files: list[str], returncode: int) -> dict:
    if report.get("errors") != []:
        raise ScanError("Bandit reported skipped files or scan errors")
    metrics = report.get("metrics")
    findings = report.get("results")
    if not isinstance(metrics, dict) or not isinstance(findings, list):
        raise ScanError("Invalid Bandit report structure")
    scanned = {Path(name).as_posix().removeprefix("./") for name in metrics if name != "_totals"}
    if scanned != set(files):
        raise ScanError("Bandit file coverage differs from the tracked source manifest")
    severity: Counter[str] = Counter()
    for finding in findings:
        if (
            not isinstance(finding, dict)
            or finding.get("issue_severity") not in {"LOW", "MEDIUM", "HIGH", "UNDEFINED"}
            or not isinstance(finding.get("filename"), str)
            or Path(finding["filename"]).as_posix().removeprefix("./") not in scanned
            or not isinstance(finding.get("test_id"), str)
        ):
            raise ScanError("Invalid Bandit finding")
        severity[finding["issue_severity"]] += 1
    validate_exit_code(returncode, len(findings))
    return {"files_scanned": len(scanned), "findings": len(findings), "severity": dict(severity)}


def validate_pip_audit(report: dict[str, Any], expected: dict[str, str], returncode: int) -> dict:
    dependencies = report.get("dependencies")
    if not isinstance(dependencies, list) or report.get("fixes") != []:
        raise ScanError("Invalid pip-audit report structure or unexpected fixes")
    actual = {}
    findings = 0
    affected = 0
    for dependency in dependencies:
        if (
            not isinstance(dependency, dict)
            or "skip_reason" in dependency
            or not isinstance(dependency.get("name"), str)
            or not isinstance(dependency.get("version"), str)
            or not isinstance(dependency.get("vulns"), list)
        ):
            raise ScanError("Invalid or skipped pip-audit dependency")
        name = canonicalize_name(dependency["name"])
        if name in actual:
            raise ScanError("Duplicate pip-audit dependency")
        actual[name] = str(Version(dependency["version"]))
        for vulnerability in dependency["vulns"]:
            if (
                not isinstance(vulnerability, dict)
                or not isinstance(vulnerability.get("id"), str)
                or not vulnerability["id"]
                or not isinstance(vulnerability.get("fix_versions"), list)
            ):
                raise ScanError("Invalid pip-audit vulnerability")
        findings += len(dependency["vulns"])
        affected += bool(dependency["vulns"])
    if actual != expected:
        raise ScanError("pip-audit package coverage differs from the active exact lock pins")
    validate_exit_code(returncode, findings)
    return {"packages_scanned": len(actual), "affected_packages": affected, "findings": findings}


def read_report(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScanError("Scanner report is missing or invalid JSON") from error
    if not isinstance(report, dict):
        raise ScanError("Scanner report must be a JSON object")
    return report


def run_scanner(command: list[str], root: Path, log: Path) -> int:
    with log.open("w", encoding="utf-8") as output:
        try:
            result = subprocess.run(
                command, cwd=root, stdout=output, stderr=output, timeout=180, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ScanError(f"Scanner invocation failed ({type(error).__name__})") from error
    # Bandit can log a plugin exception without placing it in JSON's skipped-file errors.
    logged = log.read_text(encoding="utf-8")
    if "Traceback (most recent call last):" in logged or any(
        "ERROR" in line.split() for line in logged.splitlines()
    ):
        raise ScanError("Scanner logged an operational error; inspect its log artifact")
    return result.returncode


def write_security_summary(directory: Path, results: dict[str, dict]) -> bool:
    failed = any(result["status"] == "error" for result in results.values())
    lines = [
        "## Python security scans",
        "",
        "Known findings are **report-only**; tool errors and incomplete scans fail CI.",
        "A green job is not evidence of zero security findings.",
        "",
        "Scope: tracked Python sources (including tests and middleware), and the exact",
        "requirements-dev.lock pins active for this runner's Python/platform markers.",
        "npm, container OS packages, credentials and runtime configuration are not scanned.",
        "",
    ]
    for name, result in results.items():
        lines.append(f"- **{name}**: {json.dumps(result, sort_keys=True)}")
        if result["status"] == "error":
            print(f"::error title={name} scan incomplete::{result['error']}")
        elif result.get("findings"):
            print(
                f"::warning title={name} report-only findings::{result['findings']} findings; see artifacts."
            )
    summary = "\n".join(lines) + "\n"
    (directory / "summary.md").write_text(summary, encoding="utf-8")
    (directory / "summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as output:
            output.write(summary)
    print(summary)
    return failed


def run_security(root: Path, directory: Path) -> int:
    directory.mkdir(parents=True, exist_ok=False)
    results: dict[str, dict] = {}
    try:
        files = tracked_python_files(root)
        pins = locked_requirements((root / "requirements-dev.lock").read_text(encoding="utf-8"))
        (directory / "source-files.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
        (directory / "locked-packages.json").write_text(
            json.dumps(pins, indent=2), encoding="utf-8"
        )
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        results["inputs"] = {
            "status": "error",
            "error": f"Input validation failed ({type(error).__name__})",
        }
        write_security_summary(directory, results)
        return 1

    scans = [
        (
            "bandit",
            [
                sys.executable,
                "-m",
                "bandit",
                "--format",
                "json",
                "--output",
                str(directory / "bandit.json"),
                "--",
                *files,
            ],
            lambda report, code: validate_bandit(report, files, code),
        ),
        (
            "pip-audit",
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--requirement",
                "requirements-dev.lock",
                "--no-deps",
                "--disable-pip",
                "--strict",
                "--vulnerability-service",
                "pypi",
                "--progress-spinner",
                "off",
                "--desc",
                "off",
                "--timeout",
                "15",
                "--format",
                "json",
                "--output",
                str(directory / "pip-audit.json"),
            ],
            lambda report, code: validate_pip_audit(report, pins, code),
        ),
    ]
    for name, command, validate in scans:
        try:
            tool_version = version(name)
            code = run_scanner(command, root, directory / f"{name}.log")
            results[name] = {
                "status": "complete",
                "version": tool_version,
                **validate(read_report(directory / f"{name}.json"), code),
            }
        except (OSError, ValueError, KeyError, TypeError, PackageNotFoundError) as error:
            message = (
                str(error)
                if isinstance(error, ScanError)
                else f"Report validation failed ({type(error).__name__})"
            )
            results[name] = {"status": "error", "error": message}
    return int(write_security_summary(directory, results))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["lint", "security"])
    parser.add_argument("--reports", type=Path, default=Path("security-reports"))
    args = parser.parse_args()
    root = Path.cwd()
    if args.command == "security":
        return run_security(root, args.reports.resolve())
    files = tracked_python_files(root)
    print(f"Checking all {len(files)} tracked Python sources, including middleware and tests.")
    for options in (["check", "--output-format=github"], ["format", "--check", "--diff"]):
        subprocess.run([sys.executable, "-m", "ruff", *options, "--", *files], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
