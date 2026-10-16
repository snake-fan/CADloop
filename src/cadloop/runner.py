"""Budgeted smoke execution and inspectable, hashed run artifacts."""

import copy
import hashlib
import json
import platform
import subprocess
import time
import uuid
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from . import __version__
from .config import ValidationError, load_config, load_tasks
from .contracts import Agent, Backend, Evaluator, Observation, Task, TaskResult
from .smoke import MockMetadataBackend, ScriptedSmokeAgent, SyntheticBoxEvaluator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json_bytes(value))


def git_state(directory: Path) -> Dict[str, Any]:
    def git(*args: str) -> Optional[str]:
        try:
            return subprocess.run(
                ["git", "-C", str(directory), *args], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
    commit = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--untracked-files=normal")
    return {"commit": commit, "dirty": None if dirty is None else bool(dirty)}


def run_task(
    task: Task,
    agent: Agent,
    backend: Backend,
    evaluator: Evaluator,
    max_steps: int,
    timeout_seconds: float,
    emit: Callable[[Mapping[str, Any]], None],
    clock: Callable[[], float] = time.monotonic,
) -> TaskResult:
    """Count each attempted backend call and record its observation.

    Timeout checks are cooperative between synchronous steps; this function
    cannot interrupt an executing model or CAD kernel. Future real adapters
    need process isolation before relying on a hard wall-time limit.
    """
    started = clock()
    history: List[Observation] = []
    calls = 0

    def finish(status: str, error: Optional[str] = None, evaluation: Any = None) -> TaskResult:
        return TaskResult(task.public.task_id, status, calls, max(0.0, clock() - started), evaluation, error)

    while True:
        if clock() - started >= timeout_seconds:
            return finish("timeout", "Cooperative task timeout exceeded")
        try:
            # Give adapters copies so they cannot mutate evaluator expectations
            # or alter observations already recorded in traces.
            action = agent.next_action(copy.deepcopy(task.public), copy.deepcopy(history))
        except Exception as exc:
            return finish("error", "Agent error: {}: {}".format(type(exc).__name__, exc))
        if clock() - started >= timeout_seconds:
            return finish("timeout", "Cooperative task timeout exceeded")
        if action is None:
            try:
                evaluation = evaluator.evaluate(task, history)
            except Exception as exc:
                return finish("error", "Evaluator error: {}: {}".format(type(exc).__name__, exc))
            return finish("passed" if evaluation.passed else "failed", evaluation=evaluation)
        if calls >= max_steps:
            return finish("budget_exhausted", "max_steps={} exhausted before next tool call".format(max_steps))
        calls += 1
        call_started = clock()
        try:
            observation = backend.execute(action)
        except Exception as exc:
            observation = Observation(False, error="Backend error: {}: {}".format(type(exc).__name__, exc))
        emit({
            "task_id": task.public.task_id,
            "step": calls,
            "event": "tool_call",
            "action": asdict(action),
            "observation": asdict(observation),
            "elapsed_seconds": max(0.0, clock() - call_started),
            "timestamp": utc_now(),
            "synthetic_only": True,
        })
        history.append(copy.deepcopy(observation))
        if clock() - started >= timeout_seconds:
            return finish("timeout", "Cooperative task timeout exceeded")
        if not observation.success:
            return finish("tool_error", observation.error or "Backend returned an unsuccessful observation")


def build_summary(results: List[Mapping[str, Any]], run_id: str) -> Dict[str, Any]:
    counts = dict(sorted(Counter(item["status"] for item in results).items()))
    return {
        "schema_version": 1,
        "run_id": run_id,
        "run_kind": "smoke",
        "official_benchmark": False,
        "synthetic_only": True,
        "rankable": False,
        "interpretation": "Offline mock metadata checks only; no model, CAD geometry, or benchmark score.",
        "tasks_total": len(results),
        "status_counts": counts,
        "tool_calls_total": sum(item["tool_calls"] for item in results),
        "all_passed": bool(results) and all(item["status"] == "passed" for item in results),
    }


def run_experiment(config_path: Path, output_dir: Path) -> Dict[str, Any]:
    config_path, output_dir = Path(config_path).resolve(), Path(output_dir).resolve()
    # Validate all inputs before creating an output directory.
    config_source = config_path.read_bytes()
    config = load_config(config_path, config_source.decode("utf-8"))
    tasks_source = config.tasks_path.read_bytes()
    tasks = load_tasks(config.tasks_path, tasks_source.decode("utf-8"))
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise ValidationError("Refusing to overwrite non-empty output: {}".format(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    config_snapshot = json_bytes(config.raw)
    (output_dir / "config.snapshot.json").write_bytes(config_snapshot)
    (output_dir / "tasks.snapshot.jsonl").write_bytes(tasks_source)
    run_id = uuid.uuid4().hex
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "experiment_id": config.raw["experiment_id"],
        "run_kind": "smoke",
        "official_benchmark": False,
        "synthetic_only": True,
        "rankable": False,
        "status": "running",
        "started_at": utc_now(),
        "finished_at": None,
        "seed": config.seed,
        "config": config.raw,
        "config_source": {"path": str(config_path), "sha256": sha256(config_source)},
        "tasks_source": {"path": str(config.tasks_path), "sha256": sha256(tasks_source), "count": len(tasks)},
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "cadloop": __version__, "git": git_state(config_path.parent)},
        "budget": {"max_steps_per_task": config.max_steps, "timeout_seconds_per_task": config.timeout_seconds, "timeout_enforcement": "cooperative_between_steps"},
        "artifacts": {},
    }
    write_json(output_dir / "manifest.json", manifest)
    results = []
    try:
        with (output_dir / "trace.jsonl").open("w", encoding="utf-8") as traces, (output_dir / "results.jsonl").open("w", encoding="utf-8") as result_file:
            def emit(event: Mapping[str, Any]) -> None:
                traces.write(json.dumps(dict(event, run_id=run_id), ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
                traces.flush()
            for task in tasks:
                result = asdict(run_task(task, ScriptedSmokeAgent(), MockMetadataBackend(), SyntheticBoxEvaluator(), config.max_steps, config.timeout_seconds, emit))
                result["run_id"] = run_id
                results.append(result)
                result_file.write(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
                result_file.flush()
        summary = build_summary(results, run_id)
        write_json(output_dir / "summary.json", summary)
        manifest["status"] = "completed"
        manifest["artifacts"] = {
            name: {"sha256": sha256((output_dir / name).read_bytes())}
            for name in ("config.snapshot.json", "tasks.snapshot.jsonl", "trace.jsonl", "results.jsonl", "summary.json")
        }
        return summary
    except Exception as exc:
        manifest["status"] = "error"
        manifest["error"] = "{}: {}".format(type(exc).__name__, exc)
        raise
    finally:
        manifest["finished_at"] = utc_now()
        write_json(output_dir / "manifest.json", manifest)


def summarize_run(output_dir: Path) -> Dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    try:
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "completed":
            raise ValidationError("Only a completed run can be summarized")
        if manifest.get("run_kind") != "smoke" or manifest.get("official_benchmark") is not False:
            raise ValidationError("Only offline smoke run artifacts are supported")
        required = {"config.snapshot.json", "tasks.snapshot.jsonl", "trace.jsonl", "results.jsonl", "summary.json"}
        if set(manifest["artifacts"]) != required:
            raise ValidationError("Run manifest has missing or unsupported artifacts")
        for name in required:
            if sha256((output_dir / name).read_bytes()) != manifest["artifacts"][name]["sha256"]:
                raise ValidationError("Artifact hash mismatch: {}".format(name))
        results = [json.loads(line) for line in (output_dir / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        traces = [json.loads(line) for line in (output_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(results) != manifest["tasks_source"]["count"]:
            raise ValidationError("Result count does not match the task snapshot")
        task_ids = [item["task_id"] for item in results]
        if len(set(task_ids)) != len(task_ids):
            raise ValidationError("Duplicate result task_id")
        if any(item.get("run_id") != manifest["run_id"] for item in results + traces):
            raise ValidationError("Artifact run_id does not match manifest")
        trace_counts = Counter(item["task_id"] for item in traces)
        if set(trace_counts) - set(task_ids) or any(trace_counts[item["task_id"]] != item["tool_calls"] for item in results):
            raise ValidationError("Tool-call totals do not match traces")
        summary = build_summary(results, manifest["run_id"])
        if summary != json.loads((output_dir / "summary.json").read_text(encoding="utf-8")):
            raise ValidationError("Stored summary does not match results")
        return summary
    except ValidationError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValidationError("Cannot summarize run {}: {}".format(output_dir, exc)) from exc
