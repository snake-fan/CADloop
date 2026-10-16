"""Strict configuration and synthetic task validation using the standard library."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .contracts import PublicTask, Task


class ValidationError(ValueError):
    """An unsupported or malformed experiment cannot be run."""


def object_fields(value: Any, required: set, context: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("{} must be a JSON object".format(context))
    missing, extra = required - set(value), set(value) - required
    if missing or extra:
        raise ValidationError(
            "{} fields invalid (missing={}, unknown={})".format(
                context, sorted(missing), sorted(extra)
            )
        )
    return value


def positive_number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("{} must be a finite positive number".format(context))
    if not math.isfinite(value) or value <= 0:
        raise ValidationError("{} must be a finite positive number".format(context))
    return float(value)


def dimensions(value: Any, context: str) -> Dict[str, float]:
    values = object_fields(value, {"length", "width", "height"}, context)
    return {key: positive_number(item, "{}.{}".format(context, key)) for key, item in values.items()}


@dataclass(frozen=True)
class ExperimentConfig:
    source_path: Path
    raw: Mapping[str, Any]
    tasks_path: Path
    seed: int
    max_steps: int
    timeout_seconds: float


def load_config(path: Path, source_text: Optional[str] = None) -> ExperimentConfig:
    path = Path(path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8") if source_text is None else source_text)
    except (OSError, ValueError) as exc:
        raise ValidationError("Cannot read config {}: {}".format(path, exc)) from exc
    obj = object_fields(
        payload,
        {"schema_version", "experiment_id", "seed", "benchmark", "agent", "backend", "budget"},
        "config",
    )
    if type(obj["schema_version"]) is not int or obj["schema_version"] != 1:
        raise ValidationError("Only schema_version=1 is supported")
    if not isinstance(obj["experiment_id"], str) or not obj["experiment_id"].strip():
        raise ValidationError("experiment_id must be a non-empty string")
    if type(obj["seed"]) is not int or obj["seed"] < 0:
        raise ValidationError("seed must be a non-negative integer")
    benchmark = object_fields(obj["benchmark"], {"name", "tasks_path"}, "benchmark")
    agent = object_fields(obj["agent"], {"name"}, "agent")
    backend = object_fields(obj["backend"], {"name"}, "backend")
    for section, supported in (
        (benchmark, "synthetic_boxes_v1"),
        (agent, "scripted_smoke"),
        (backend, "mock_metadata"),
    ):
        if section["name"] != supported:
            raise ValidationError(
                "Unsupported name {!r}; only {!r} is implemented".format(section["name"], supported)
            )
    if not isinstance(benchmark["tasks_path"], str) or not benchmark["tasks_path"].strip():
        raise ValidationError("benchmark.tasks_path must be a non-empty string")
    tasks_path = (path.parent / benchmark["tasks_path"]).resolve()
    budget = object_fields(obj["budget"], {"max_steps", "timeout_seconds"}, "budget")
    if type(budget["max_steps"]) is not int or budget["max_steps"] <= 0:
        raise ValidationError("budget.max_steps must be a positive integer")
    timeout = positive_number(budget["timeout_seconds"], "budget.timeout_seconds")
    return ExperimentConfig(path, obj, tasks_path, obj["seed"], budget["max_steps"], timeout)


def load_tasks(path: Path, source_text: Optional[str] = None) -> List[Task]:
    tasks = []
    seen = set()
    try:
        lines = (Path(path).read_text(encoding="utf-8") if source_text is None else source_text).splitlines()
    except OSError as exc:
        raise ValidationError("Cannot read tasks {}: {}".format(path, exc)) from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        context = "task line {}".format(number)
        try:
            obj = object_fields(
                json.loads(line), {"task_id", "instruction", "public_input", "evaluation"}, context
            )
        except ValueError as exc:
            raise ValidationError("{}: {}".format(context, exc)) from exc
        task_id = obj["task_id"]
        if not isinstance(task_id, str) or not task_id.strip() or task_id in seen:
            raise ValidationError("{} needs a unique non-empty task_id".format(context))
        if not isinstance(obj["instruction"], str) or not obj["instruction"].strip():
            raise ValidationError("{} needs a non-empty instruction".format(context))
        public = object_fields(obj["public_input"], {"dimensions", "units"}, context + ".public_input")
        public_dims = dimensions(public["dimensions"], context + ".public_input.dimensions")
        if public["units"] != "mm":
            raise ValidationError("{} only supports units='mm'".format(context))
        expected = object_fields(obj["evaluation"], {"expected_dimensions"}, context + ".evaluation")
        expected_dims = dimensions(expected["expected_dimensions"], context + ".evaluation.expected_dimensions")
        tasks.append(Task(PublicTask(task_id, obj["instruction"], {"dimensions": public_dims, "units": "mm"}), {"expected_dimensions": expected_dims}))
        seen.add(task_id)
    if not tasks:
        raise ValidationError("Task file must contain at least one task")
    return tasks
