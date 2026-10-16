#!/usr/bin/env python3
"""Prepare and inspect the local CADloop development environment.

This module intentionally has no third-party dependencies and never installs
large packages.  ``bootstrap`` only creates ignored workspace directories;
``doctor`` reports the tools that are available on the current PATH.  API
credentials are represented by boolean presence flags only and are never
printed, copied, or written to disk.

Examples::

    python scripts/bootstrap.py bootstrap --dry-run
    python scripts/bootstrap.py bootstrap
    python scripts/bootstrap.py doctor --json

The command is a local preparation helper.  It does not download Harbor,
FreeCAD, model weights, benchmark data, or invoke an agent.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]

# Every path is ignored by the repository and is safe for local run products.
# Keeping this list small makes bootstrap fast and avoids silently downloading
# or installing anything.
WORKSPACE_DIRECTORIES = (
    Path("runs"),
    Path("artifacts"),
    Path("data/raw"),
    Path("data/processed"),
    Path("data/cache"),
    Path("third_party/checkouts"),
    Path("results/local"),
)


def _version(command: Sequence[str], timeout: float = 3.0) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(version, error)`` for a local executable.

    Version commands are deliberately short, have no shell interpolation, and
    are run with a bounded timeout so a GUI-oriented FreeCAD binary cannot
    block the preparation command indefinitely.
    """

    try:
        completed = subprocess.run(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "{}: {}".format(type(exc).__name__, exc)
    output = (completed.stdout or "").strip()
    # Keep diagnostics bounded.  Output can contain a path or a provider
    # message, so it is not copied to a secret-bearing log; this is only a
    # local doctor report.
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    # Some CLIs print a warning before their version (Codex may warn about
    # PATH aliases on a managed macOS installation). Prefer a line that looks
    # like a version, while retaining the first line for other tools.
    first_line = next(
        (line for line in lines if any(character.isdigit() for character in line)),
        lines[0] if lines else "",
    )[:240]
    if completed.returncode != 0:
        return first_line or None, "exit code {}".format(completed.returncode)
    return first_line or "available", None


def _find(candidates: Iterable[str]) -> Tuple[Optional[str], Optional[str]]:
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return candidate, resolved
    return None, None


def _tool_record(
    name: str, candidates: Sequence[str], version_args: Sequence[str] = ("--version",)
) -> Dict[str, Any]:
    command_name, executable = _find(candidates)
    record: Dict[str, Any] = {
        "name": name,
        "available": executable is not None,
        "command": command_name,
        "path": executable,
        "version": None,
        "error": None,
    }
    if executable is not None:
        version, error = _version([executable, *version_args])
        record["version"] = version
        record["error"] = error
    return record


def doctor_report(root: Path = ROOT) -> Dict[str, Any]:
    """Collect a non-secret, JSON-serializable environment report."""

    python_supported = sys.version_info >= (3, 9)
    tools = {
        "git": _tool_record("git", ("git",)),
        "make": _tool_record("make", ("make",)),
        "npm": _tool_record("npm", ("npm",)),
        "uv": _tool_record("uv", ("uv",)),
        "harbor": _tool_record("harbor", ("harbor",)),
        "freecad": _tool_record("freecad", ("freecad", "FreeCAD")),
        "codex": _tool_record("codex", ("codex",)),
        "claude_code": _tool_record("claude", ("claude",)),
        "mini_swe_agent": _tool_record("mini-swe-agent", ("mini", "mini-swe-agent")),
    }
    env_names = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CADLOOP_API_KEY",
    )
    # Never include values.  Presence is sufficient to tell the user whether
    # a later, explicitly requested agent demo can be configured.
    credentials = {name: {"present": bool(os.environ.get(name))} for name in env_names}
    recommendations: List[str] = []
    if not python_supported:
        recommendations.append("Use Python 3.9 or newer.")
    if not tools["harbor"]["available"]:
        recommendations.append("Install Harbor separately before official CAD Bench runs (not done by bootstrap).")
    if not tools["freecad"]["available"]:
        recommendations.append("Install FreeCAD separately before geometry execution (not needed for offline checks).")
    if not tools["mini_swe_agent"]["available"]:
        recommendations.append("mini-SWE-agent is optional; install it in a Python 3.10+ environment when needed.")
    if not tools["codex"]["available"]:
        recommendations.append("Codex CLI is optional and required only for Codex agent demos.")
    if not tools["claude_code"]["available"]:
        recommendations.append("Claude Code is optional and required only for Claude demos.")
    return {
        "schema_version": 1,
        "root": str(Path(root).resolve()),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "supported": python_supported,
        },
        "tools": tools,
        "credentials": credentials,
        "workspace_directories": [str(path) for path in WORKSPACE_DIRECTORIES],
        "recommendations": recommendations,
        "network_probe": "not run",
        "installations_performed": [],
        "note": "Tool availability is informational; bootstrap does not install dependencies or contact providers.",
    }


def prepare_workspace(root: Path = ROOT, dry_run: bool = False) -> Dict[str, Any]:
    """Create ignored local directories, or report what would be created."""

    root = Path(root).resolve()
    records: List[Dict[str, Any]] = []
    errors: List[str] = []
    for relative in WORKSPACE_DIRECTORIES:
        target = root / relative
        if target.exists():
            if not target.is_dir():
                message = "path exists but is not a directory: {}".format(target)
                records.append({"path": str(relative), "status": "error", "error": message})
                errors.append(message)
            else:
                records.append({"path": str(relative), "status": "existing"})
            continue
        if dry_run:
            records.append({"path": str(relative), "status": "planned"})
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            records.append({"path": str(relative), "status": "created"})
        except OSError as exc:
            message = "{}: {}".format(type(exc).__name__, exc)
            records.append({"path": str(relative), "status": "error", "error": message})
            errors.append("{} ({})".format(target, message))
    return {
        "root": str(root),
        "dry_run": dry_run,
        "directories": records,
        "errors": errors,
        "success": not errors,
    }


def _human_report(report: Mapping[str, Any]) -> str:
    lines = ["CADloop environment report", "root: {}".format(report.get("root", ""))]
    python = report.get("python", {})
    lines.append("python: {} ({})".format(python.get("version"), "ok" if python.get("supported") else "unsupported"))
    tools = report.get("tools", {})
    for key in ("harbor", "freecad", "codex", "claude_code", "mini_swe_agent", "make", "npm", "uv"):
        item = tools.get(key, {})
        state = "available" if item.get("available") else "missing"
        detail = item.get("version") or item.get("path") or ""
        lines.append("{}: {}{}".format(key, state, " ({})".format(detail) if detail else ""))
    credentials = report.get("credentials", {})
    present = [name for name, value in credentials.items() if value.get("present")]
    lines.append("credentials: {}".format(", ".join(present) if present else "none detected"))
    recommendations = report.get("recommendations", [])
    if recommendations:
        lines.append("recommendations:")
        lines.extend("- {}".format(item) for item in recommendations)
    lines.append("note: {}".format(report.get("note", "")))
    return "\n".join(lines)


def _emit(value: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        if value.get("action") == "doctor":
            print(_human_report(value))
        else:
            print("CADloop bootstrap ({})".format("dry-run" if value.get("dry_run") else "workspace setup"))
            for item in value.get("directories", []):
                print("{}: {}".format(item["status"], item["path"]))
            print("doctor: use `make bootstrap-doctor` for tool details")
            if value.get("errors"):
                for error in value["errors"]:
                    print("error: {}".format(error))


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("bootstrap", "doctor"), default="bootstrap")
    parser.add_argument("--dry-run", action="store_true", help="Report planned directory creation without writing")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (defaults to the current checkout)")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when required Python/tools are missing")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "doctor":
        report = doctor_report(root)
        report = dict(report, action="doctor")
        _emit(report, args.json)
        required_ok = bool(report["python"]["supported"] and report["tools"]["make"]["available"])
        return 0 if required_ok or not args.strict else 1

    workspace = prepare_workspace(root, args.dry_run)
    report = doctor_report(root)
    result = dict(workspace, action="bootstrap", doctor=report)
    _emit(result, args.json)
    required_ok = bool(report["python"]["supported"] and report["tools"]["make"]["available"])
    return 0 if workspace["success"] and (required_ok or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
