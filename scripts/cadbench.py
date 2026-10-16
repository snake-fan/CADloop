#!/usr/bin/env python3
"""Inspect and load public Parametric CAD Bench task metadata.

The official V3 suite is a Harbor dataset. This adapter intentionally reads
only public task inputs from a local export and strips evaluator/reference
fields before producing JSONL for an agent. It does not download held-out
assets or claim to reproduce the official scorer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "configs/benchmarks/cadbench_v3.json"
HARBOR_INDEX_URL = "https://hub.harborframework.com/api/datasets/gnucleus-ai/cad-bench/v3/tasks"
PUBLIC_KEYS = ("prompt", "instruction", "task", "description", "input", "question")
SENSITIVE_KEYS = {
    "answer", "answers", "expected", "evaluator", "evaluation", "ground_truth",
    "reference", "reference_cad", "reference_geometry", "reward", "verifier",
    "scorer", "solution", "target", "hidden", "private",
}


def load_spec() -> Dict[str, Any]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_public(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): redact_public(item)
            for key, item in value.items()
            if str(key).lower() not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [redact_public(item) for item in value]
    return value


def prompt_from_record(record: Dict[str, Any]) -> str:
    for key in PUBLIC_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    public = redact_public(record)
    return json.dumps(public, ensure_ascii=False, sort_keys=True)


def records_from_file(path: Path) -> Iterator[Dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            yield value
        return
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict) and isinstance(value.get("tasks"), list):
        value = value["tasks"]
    if not isinstance(value, list):
        raise ValueError(f"{path}: expected a JSON list or an object with tasks")
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{path}: every task must be an object")
        yield item


def records_from_directory(path: Path) -> Iterator[Dict[str, Any]]:
    candidates: List[Path] = []
    for name in ("tasks.jsonl", "tasks.json", "manifest.jsonl", "manifest.json"):
        candidate = path / name
        if candidate.is_file():
            candidates.append(candidate)
    if candidates:
        yield from records_from_file(candidates[0])
        return

    public_files = {"instruction.md", "task.md", "prompt.md", "prompt.txt", "description.txt"}
    for directory in sorted(item for item in path.rglob("*") if item.is_dir()):
        for filename in public_files:
            candidate = directory / filename
            if candidate.is_file():
                yield {
                    "task_id": directory.relative_to(path).as_posix(),
                    "prompt": candidate.read_text(encoding="utf-8"),
                    "source_path": str(candidate.relative_to(path)),
                }
                break


def load_public_tasks(source: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not source.exists():
        raise FileNotFoundError(source)
    records = records_from_file(source) if source.is_file() else records_from_directory(source)
    output: List[Dict[str, Any]] = []
    seen = set()
    for index, record in enumerate(records):
        task_id = str(record.get("task_id") or record.get("id") or f"task-{index:04d}")
        if task_id in seen:
            raise ValueError(f"duplicate task_id: {task_id}")
        seen.add(task_id)
        output.append({
            "task_id": task_id,
            "prompt": prompt_from_record(record),
            "public_input": redact_public(record),
        })
        if limit is not None and len(output) >= limit:
            break
    if not output:
        raise ValueError(f"no public tasks found under {source}")
    return output


def harbor_available() -> Optional[str]:
    return shutil.which("harbor")


def official_command(agent: str, model: str, upload: bool = False) -> List[str]:
    command = [
        "harbor", "run", "-d", "gnucleus-ai/cad-bench@v3",
        "-a", agent, "-m", model,
        "--n-attempts", "1", "--max-retries", "0",
    ]
    if upload:
        command.extend(["--upload", "--public"])
    return command


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "CADloop-cadbench-loader/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError) as exc:
        raise RuntimeError(f"cannot fetch {url}: {exc}") from exc


def cmd_inspect(_: argparse.Namespace) -> int:
    spec = load_spec()
    print(json.dumps({
        "benchmark": spec["name"],
        "dataset": spec["source"]["harbor_dataset"],
        "task_count": spec["task_count"],
        "task_groups": spec["task_groups"],
        "digest": spec["dataset_digest"],
        "harbor_cli": harbor_available(),
        "freecad": shutil.which("FreeCAD") or shutil.which("freecad") or None,
        "official_runner": " ".join(official_command("<agent>", "<model>")),
        "official_submission": "requires a complete 100-task public job; this adapter never uploads",
    }, indent=2))
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    tasks = load_public_tasks(Path(args.source), args.limit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for task in tasks:
            handle.write(json.dumps(task, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"source": str(Path(args.source).resolve()), "output": str(output.resolve()), "tasks": len(tasks)}, indent=2))
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    payload = fetch_json(args.url)
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Harbor task index response is not a list or {items: [...]}")
    rows = []
    for item in items[: args.limit or len(items)]:
        if not isinstance(item, dict):
            continue
        rows.append({
            "task_id": item.get("id") or item.get("task_id"),
            "task_version_id": item.get("task_version_id"),
            "org_name": item.get("org_name", "gnucleus-ai"),
            "task_name": item.get("task_name"),
            "revision": item.get("revision"),
            "source": args.url,
        })
    if not rows:
        raise ValueError("Harbor task index contained no task records")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"url": args.url, "output": str(output.resolve()), "tasks": len(rows), "note": "Index metadata only; task instructions and hidden evaluator files were not fetched."}, indent=2))
    return 0


def cmd_command(args: argparse.Namespace) -> int:
    print(" ".join(official_command(args.agent, args.model, args.upload)))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect = subparsers.add_parser("inspect", help="show pinned V3 metadata and local capabilities")
    inspect.set_defaults(func=cmd_inspect)
    load = subparsers.add_parser("load", help="convert a local public task export to redacted JSONL")
    load.add_argument("source", help="JSON/JSONL file or local task directory")
    load.add_argument("--output", required=True)
    load.add_argument("--limit", type=int)
    load.set_defaults(func=cmd_load)
    index = subparsers.add_parser("index", help="fetch the public Harbor task index without evaluator files")
    index.add_argument("--url", default=HARBOR_INDEX_URL)
    index.add_argument("--output", required=True)
    index.add_argument("--limit", type=int)
    index.set_defaults(func=cmd_index)
    command = subparsers.add_parser("command", help="print the official Harbor command without executing it")
    command.add_argument("--agent", required=True)
    command.add_argument("--model", required=True)
    command.add_argument("--upload", action="store_true", help="include upload flags; never used by demo runner")
    command.set_defaults(func=cmd_command)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
