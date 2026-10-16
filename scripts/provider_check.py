#!/usr/bin/env python3
"""Check an OpenAI-compatible provider without recording credentials.

The command is deliberately small and read-only by default. It calls GET
``/v1/models`` and, when requested, sends one bounded smoke prompt to either
Chat Completions or Responses. The key is read from an environment variable
and is never printed or written to the report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


def normalize_base_url(value: str) -> str:
    value = value.rstrip("/")
    return value if value.endswith("/v1") else value + "/v1"


def load_env_file(path: Path) -> Dict[str, str]:
    """Read simple KEY=VALUE lines without executing the file or logging values."""
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[name] = value
    return values


def request_json(
    url: str,
    api_key: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    body = None
    headers = {"Accept": "application/json", "Authorization": "Bearer " + api_key}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(4096).decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw)
            except ValueError:
                parsed = {"raw_prefix": raw[:500]}
            response_summary: Dict[str, Any] = {"type": type(parsed).__name__}
            if isinstance(parsed, dict):
                response_summary["keys"] = sorted(str(key) for key in parsed.keys())[:40]
                data = parsed.get("data")
                if isinstance(data, list):
                    response_summary["data_count"] = len(data)
                    ids = [item.get("id") for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]
                    if ids:
                        response_summary["model_ids"] = ids[:20]
            return {
                "status": "ok",
                "http_status": response.status,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "response_summary": response_summary,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read(4096).decode("utf-8", errors="replace")
        return {
            "status": "http_error",
            "http_status": exc.code,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "response_prefix": raw[:500],
        }
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return {
            "status": "network_error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def main(argv: Optional[list[str]] = None) -> int:
    default_env_file = Path(".env")
    default_file_env = load_env_file(default_env_file)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("CADLOOP_BASE_URL") or default_file_env.get("CADLOOP_BASE_URL") or "https://us.ruiyumaas.com/v1",
    )
    parser.add_argument("--key-env", default="OPENAI_API_KEY")
    parser.add_argument("--env-file", type=Path, default=default_env_file)
    parser.add_argument("--no-env-file", action="store_true", help="Do not read the repository .env file")
    parser.add_argument("--model", default=os.getenv("CADLOOP_MODEL") or default_file_env.get("CADLOOP_MODEL") or "gpt-5.6-sol")
    parser.add_argument("--protocol", choices=("models", "chat", "responses", "all"), default="models")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    file_env = {} if args.no_env_file else load_env_file(args.env_file)
    key = os.getenv(args.key_env) or file_env.get(args.key_env)
    actual_key_env = args.key_env
    if not key and args.key_env == "OPENAI_API_KEY":
        key = os.getenv("CADLOOP_API_KEY") or file_env.get("CADLOOP_API_KEY")
        if key:
            actual_key_env = "CADLOOP_API_KEY"
    report: Dict[str, Any] = {
        "base_url": normalize_base_url(args.base_url),
        "model": args.model,
        "key_env": actual_key_env,
        "key_present": bool(key),
        "requests": [],
    }
    if not key:
        report["status"] = "missing_key"
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 2
    base = report["base_url"]
    report["requests"].append({"endpoint": "/models", **request_json(base + "/models", key, timeout=args.timeout)})
    if args.protocol in ("chat", "all"):
        payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": "Reply with exactly: CADLOOP_PROVIDER_OK"}],
            "max_tokens": 16,
        }
        report["requests"].append({"endpoint": "/chat/completions", **request_json(base + "/chat/completions", key, "POST", payload, args.timeout)})
    if args.protocol in ("responses", "all"):
        payload = {
            "model": args.model,
            "input": "Reply with exactly: CADLOOP_PROVIDER_OK",
            "max_output_tokens": 16,
        }
        report["requests"].append({"endpoint": "/responses", **request_json(base + "/responses", key, "POST", payload, args.timeout)})
    statuses = [item.get("status") for item in report["requests"]]
    report["status"] = "ok" if statuses and all(item == "ok" for item in statuses) else "failed"
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
