#!/usr/bin/env python3
"""Provision the reproducible uv environment used by CADloop integrations.

The default ``sync`` command creates a Python 3.12 environment and installs
the pinned Harbor and mini-SWE-agent extras from ``pyproject.toml``.  The
``index`` command downloads only the public CAD Bench V3 task index; it never
fetches task images, reference geometry, or evaluator files.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENV = ROOT / ".venv"
DEFAULT_CACHE = ROOT / "data" / "cache" / "uv"
DEFAULT_PYTHON_DIR = ROOT / "data" / "cache" / "uv-python"
DEFAULT_INDEX = ROOT / "runs" / "cadbench-v3-index" / "tasks.jsonl"
REQUIRED_PACKAGES = {"harbor": "0.23.0", "mini-swe-agent": "2.4.6"}


def uv_executable() -> str:
    configured = os.environ.get("CADLOOP_UV")
    if configured:
        return configured
    found = shutil.which("uv")
    if found:
        return found
    raise SystemExit(
        "uv is not on PATH; install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` "
        "or set CADLOOP_UV to its absolute path"
    )


def run(command: Sequence[str], env: Optional[Dict[str, str]] = None) -> None:
    print("$ {}".format(" ".join(command)))
    subprocess.run(list(command), cwd=ROOT, env=env, check=True)


def uv_env() -> Dict[str, str]:
    env = os.environ.copy()
    # Keep uv's cache in an ignored workspace directory so setup is portable
    # in restricted environments and does not depend on a user's home path.
    cache = Path(env.get("UV_CACHE_DIR", str(DEFAULT_CACHE))).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    env["UV_CACHE_DIR"] = str(cache)
    python_dir = Path(env.get("UV_PYTHON_INSTALL_DIR", str(DEFAULT_PYTHON_DIR))).expanduser()
    python_dir.mkdir(parents=True, exist_ok=True)
    env["UV_PYTHON_INSTALL_DIR"] = str(python_dir)
    return env


def sync(python: str, venv: Path) -> None:
    uv = uv_executable()
    env = uv_env()
    venv = Path(venv)
    if not venv.is_absolute():
        venv = ROOT / venv
    run([uv, "venv", "--allow-existing", "--python", python, str(venv)], env=env)
    run([uv, "sync", "--locked", "--python", str(venv / "bin" / "python"), "--extra", "agents", "--extra", "benchmark"], env=env)


def doctor(venv: Path) -> Dict[str, object]:
    venv = Path(venv)
    if not venv.is_absolute():
        venv = ROOT / venv
    python = venv / "bin" / "python"
    venv_bin = venv / "bin"
    env = os.environ.copy()
    config_dir = ROOT / "data" / "cache" / "mini-swe-agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    env["MSWEA_GLOBAL_CONFIG_DIR"] = str(config_dir)
    env["MSWEA_SILENT_STARTUP"] = "1"
    report: Dict[str, object] = {
        "uv": shutil.which("uv") or os.environ.get("CADLOOP_UV"),
        "python": str(python) if python.exists() else None,
        "packages": {
            "cadloop": None,
            "harbor": None,
            "mini-swe-agent": None,
        },
        "executables": {
            "harbor": str(venv_bin / "harbor") if (venv_bin / "harbor").exists() else shutil.which("harbor"),
            "mini": str(venv_bin / "mini") if (venv_bin / "mini").exists() else shutil.which("mini"),
            "codex": shutil.which("codex"),
            "claude": shutil.which("claude"),
            "freecad": shutil.which("FreeCAD") or shutil.which("freecad"),
        },
    }
    if python.exists():
        probe = [
            str(python),
            "-c",
            "import importlib.metadata as m; print(';'.join(f'{n}={m.version(n)}' for n in ('cadloop','harbor','mini-swe-agent')))" ,
        ]
        completed = subprocess.run(probe, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode == 0:
            packages: Dict[str, str] = {}
            for item in completed.stdout.strip().split(";"):
                if "=" in item:
                    name, version = item.split("=", 1)
                    packages[name] = version
            report["packages"] = packages
        else:
            report["probe_error"] = completed.stderr.strip()[-500:]
    return report


def doctor_issues(report: Dict[str, object]) -> list[str]:
    issues = []
    packages = report.get("packages", {})
    executables = report.get("executables", {})
    for name, expected in REQUIRED_PACKAGES.items():
        actual = packages.get(name) if isinstance(packages, dict) else None
        if actual != expected:
            issues.append("{} version is {}, expected {}".format(name, actual or "missing", expected))
    for name in ("harbor", "mini"):
        executable = executables.get(name) if isinstance(executables, dict) else None
        if not executable or not Path(str(executable)).is_file():
            issues.append("{} executable is missing".format(name))
    return issues


def fetch_index(output: Path, limit: Optional[int]) -> None:
    command = [sys.executable, str(ROOT / "scripts" / "cadbench.py"), "index", "--output", str(output)]
    if limit is not None:
        command.extend(["--limit", str(limit)])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "scripts")
    run(command, env=env)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sync_parser = sub.add_parser("sync", help="create a Python 3.12 uv environment and install pinned integrations")
    sync_parser.add_argument("--python", default="3.12")
    sync_parser.add_argument("--venv", type=Path, default=DEFAULT_VENV)
    doctor_parser = sub.add_parser("doctor", help="report installed integration versions without secrets")
    doctor_parser.add_argument("--venv", type=Path, default=DEFAULT_VENV)
    index_parser = sub.add_parser("index", help="download only the public CAD Bench V3 task index")
    index_parser.add_argument("--output", type=Path, default=DEFAULT_INDEX)
    index_parser.add_argument("--limit", type=int)
    all_parser = sub.add_parser("all", help="sync the environment, inspect it, and fetch the public task index")
    all_parser.add_argument("--python", default="3.12")
    all_parser.add_argument("--venv", type=Path, default=DEFAULT_VENV)
    all_parser.add_argument("--output", type=Path, default=DEFAULT_INDEX)
    all_parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)

    if args.command == "sync":
        sync(args.python, args.venv)
        return 0
    if args.command == "doctor":
        report = doctor(args.venv)
        issues = doctor_issues(report)
        report["validation"] = {"ok": not issues, "issues": issues}
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if not issues else 1
    if args.command == "index":
        fetch_index(args.output, args.limit)
        return 0
    sync(args.python, args.venv)
    report = doctor(args.venv)
    issues = doctor_issues(report)
    report["validation"] = {"ok": not issues, "issues": issues}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    if issues:
        return 1
    fetch_index(args.output, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
