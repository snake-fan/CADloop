#!/usr/bin/env python3
"""Run small public CAD prompts through installed agent CLIs.

The default mode is a dry run. Pass ``--execute`` to make external model
requests. This script is a provider/CLI smoke harness, never an official
CADBench evaluator, and never uploads Harbor jobs.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from cadbench import load_public_tasks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "examples/cadbench_demo_tasks.jsonl"
DEFAULT_ENV_FILE = ROOT / ".env"


def load_env_file(path: Path) -> Dict[str, str]:
    """Read simple KEY=VALUE entries without executing or logging the file."""
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[name] = value
    return values


def prompt_for(task: Dict[str, object]) -> str:
    public_input = task.get("public_input") or {}
    track = public_input.get("track", "unknown") if isinstance(public_input, dict) else "unknown"
    return (
        "You are answering a small CAD harness demo. This is not an official benchmark submission. "
        "Produce a concise plan and, when possible, executable FreeCAD Python. Do not claim to have "
        "run FreeCAD if it is unavailable. Preserve missing dimensions as explicit assumptions.\n\n"
        "Task ID: {}\nTrack: {}\nPublic task:\n{}"
    ).format(task["task_id"], track, task["prompt"])


def safe_command(command: Sequence[str], prompt: str) -> List[str]:
    return ["<prompt>" if part == prompt else ("<prompt on stdin>" if part == "-" else part) for part in command]


def openai_base_url(url: str) -> str:
    """Normalize a gateway root to the OpenAI-compatible API prefix."""
    value = url.rstrip("/")
    return value if value.endswith("/v1") else value + "/v1"


def isolated_codex_env(
    env: Dict[str, str], model: str, base_url: Optional[str], codex_home: Optional[str]
) -> Tuple[Dict[str, str], Optional[tempfile.TemporaryDirectory]]:
    """Point Codex at an explicit provider without persisting credentials.

    The generated config contains no token. Codex reads ``OPENAI_API_KEY`` from
    the child environment when the provider requires authentication.
    """
    if codex_home:
        env["CODEX_HOME"] = codex_home
        return env, None
    if not base_url:
        return env, None
    temporary = tempfile.TemporaryDirectory(prefix="cadloop-codex-")
    home = Path(temporary.name)
    config = home / "config.toml"
    config.write_text(
        "model_provider = \"cadloop_custom\"\n"
        "model = \"{}\"\n\n"
        "[model_providers.cadloop_custom]\n"
        "name = \"CADloop temporary gateway\"\n"
        "wire_api = \"responses\"\n"
        "requires_openai_auth = true\n"
        "base_url = \"{}\"\n".format(model, openai_base_url(base_url) + "/"),
        encoding="utf-8",
    )
    env["CODEX_HOME"] = str(home)
    return env, temporary


def run_process(command: List[str], env: Dict[str, str], cwd: Path, timeout: int, prompt: str, stdin_prompt: bool) -> Dict[str, object]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            input=prompt if stdin_prompt else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "status": "completed" if completed.returncode == 0 else "error",
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_seconds": round(time.monotonic() - started, 3),
            "command": safe_command(command, prompt),
        }
    except FileNotFoundError as exc:
        return {"status": "unavailable", "error": str(exc), "duration_seconds": round(time.monotonic() - started, 3), "command": safe_command(command, prompt)}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "status": "timeout",
            "error": f"timeout after {timeout}s",
            "stdout": stdout,
            "stderr": stderr,
            "duration_seconds": round(time.monotonic() - started, 3),
            "command": safe_command(command, prompt),
        }


def run_agent(agent: str, task: Dict[str, object], args: argparse.Namespace, out_dir: Path) -> Dict[str, object]:
    prompt = prompt_for(task)
    env = os.environ.copy()
    file_env = load_env_file(args.env_file)
    # CADLOOP_API_KEY is the repository-wide name. Map it only to the
    # OpenAI-compatible child process used by Codex/mini-SWE-agent.
    if agent in ("codex", "mini-swe-agent") and not env.get("OPENAI_API_KEY"):
        configured_key = file_env.get("OPENAI_API_KEY") or file_env.get("CADLOOP_API_KEY")
        if configured_key:
            env["OPENAI_API_KEY"] = configured_key
    if args.base_url:
        env.setdefault("OPENAI_BASE_URL", openai_base_url(args.base_url))
    if args.claude_base_url:
        env.setdefault("ANTHROPIC_BASE_URL", args.claude_base_url.rstrip("/"))
    mini_model = args.model if "/" in args.model else "openai/{}".format(args.model)
    env["MSWEA_MODEL_NAME"] = mini_model
    task_dir = out_dir / agent / str(task["task_id"])
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    temporary_codex_home = None
    try:
        if agent == "mini-swe-agent":
            executable = shutil.which("mini") or shutil.which("mini-swe-agent")
            if executable is None:
                return {"status": "unavailable", "reason": "mini-swe-agent is not installed", "agent": agent, "task_id": task["task_id"]}
            command = [executable, "--task", prompt, "--model", mini_model, "--yolo", "--exit-immediately", "--output", str(task_dir / "trajectory.json")]
            stdin_prompt = False
        elif agent == "codex":
            executable = shutil.which("codex")
            if executable is None:
                return {"status": "unavailable", "reason": "codex CLI is not installed", "agent": agent, "task_id": task["task_id"]}
            env, temporary_codex_home = isolated_codex_env(
                env, args.model, args.base_url, args.codex_home
            )
            command = [executable, "exec", "--ephemeral", "--model", args.model, "--sandbox", "workspace-write", "--ask-for-approval", "never", "--json", "-C", str(task_dir), "-"]
            stdin_prompt = True
        elif agent == "claude-code":
            if args.execute and not args.claude_base_url:
                return {
                    "status": "incompatible_endpoint",
                    "reason": "Claude Code requires an explicitly configured Anthropic Messages-compatible endpoint",
                    "agent": agent,
                    "task_id": task["task_id"],
                }
            executable = shutil.which("claude")
            if executable is None:
                return {"status": "unavailable", "reason": "Claude Code CLI is not installed", "agent": agent, "task_id": task["task_id"]}
            command = [executable, "-p", "--model", args.model, "--output-format", "json", "--no-session-persistence", "--permission-mode", "acceptEdits", "--permission-prompts", "none", prompt]
            stdin_prompt = False
        else:
            raise ValueError(agent)

        if not args.execute:
            result: Dict[str, object] = {"status": "planned", "duration_seconds": 0.0, "command": safe_command(command, prompt)}
        else:
            result = run_process(command, env, task_dir, args.timeout, prompt, stdin_prompt)
        result.update({"agent": agent, "task_id": task["task_id"], "model": args.model})
        (task_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
    finally:
        if temporary_codex_home is not None:
            temporary_codex_home.cleanup()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--agents", nargs="+", choices=["mini-swe-agent", "codex", "claude-code"], default=["mini-swe-agent", "codex", "claude-code"])
    parser.add_argument("--agent", choices=["mini-swe-agent", "codex", "claude-code", "all"], help="Compatibility alias for one agent or all")
    parser.add_argument("--model", default="gpt-5.6-sol")
    file_env = load_env_file(DEFAULT_ENV_FILE)
    parser.add_argument("--base-url", default=os.environ.get("CADLOOP_BASE_URL") or file_env.get("CADLOOP_BASE_URL"), help="OpenAI-compatible URL for Codex/LiteLLM only")
    parser.add_argument("--claude-base-url", default=os.environ.get("CADLOOP_CLAUDE_BASE_URL") or file_env.get("CADLOOP_CLAUDE_BASE_URL"), help="Anthropic Messages-compatible URL; never inferred")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="Simple ignored KEY=VALUE file for child-process configuration")
    parser.add_argument("--codex-home", help="Existing Codex home; otherwise --base-url gets a temporary provider config")
    parser.add_argument("--output-dir", default="runs/cadbench-agent-demos")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--execute", action="store_true", help="Actually invoke external agent CLIs")
    args = parser.parse_args(argv)
    if args.agent:
        args.agents = ["mini-swe-agent", "codex", "claude-code"] if args.agent == "all" else [args.agent]
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    tasks = load_public_tasks(Path(args.tasks), args.limit)
    output = Path(args.output_dir)
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Refusing to overwrite non-empty output directory: {}".format(output))
    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_kind": "cadbench_agent_demo",
        "official_benchmark": False,
        "synthetic_only": True,
        "rankable": False,
        "model": args.model,
        "base_url": args.base_url,
        "tasks": [task["task_id"] for task in tasks],
        "agents": args.agents,
        "execute": args.execute,
        "note": "Prompts are local demo tasks, not the held-out Harbor V3 task suite.",
    }
    (output / "manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    results = [run_agent(agent, task, args, output) for agent in args.agents for task in tasks]
    (output / "results.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in results), encoding="utf-8")
    print(json.dumps({"output_dir": str(output.resolve()), "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
