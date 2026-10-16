"""CLI entry points. A successful smoke run provides no CAD benchmark score."""

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .config import ValidationError
from .runner import run_experiment, summarize_run


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CADloop research scaffold: offline metadata smoke tests only")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Report the available offline smoke capability")
    run = commands.add_parser("run", help="Run the scripted smoke agent against the mock metadata backend")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    summary = commands.add_parser("summarize", help="Verify and summarize a completed run directory")
    summary.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = {
                "cadloop_version": __version__, "python": platform.python_version(),
                "python_supported": sys.version_info >= (3, 9),
                "run_kind": "smoke", "official_benchmark": False,
                "synthetic_only": True, "rankable": False,
                "implemented": {"benchmark": ["synthetic_boxes_v1"], "agent": ["scripted_smoke"], "backend": ["mock_metadata"]},
                "capability": "Offline metadata plumbing only. Real CAD kernels, model providers, and official benchmarks are not implemented.",
                "runtime_dependencies": [],
            }
        elif args.command == "run":
            result = run_experiment(args.config, args.output_dir)
        else:
            result = summarize_run(args.run_dir)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if result.get("all_passed", result.get("python_supported", True)) else 1
    except (ValidationError, OSError, UnicodeError, ValueError) as exc:
        print("cadloop: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
