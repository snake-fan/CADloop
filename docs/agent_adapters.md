# Agent CLI adapters

`scripts/run_agent_demo.py` is the compatibility entry point for the
implementation in `scripts/run_agent_demos.py`. It consumes public tasks from a
JSON/JSONL file or the included synthetic demos, writes prompt and manifest
snapshots, and can optionally invoke a locally installed agent CLI. It is an
orchestration demo, not an official CADBench evaluator. The generated manifest
is always marked `official_benchmark: false` and `rankable: false`.

## One-command project preparation

Run `make prepare` to create the Python 3.12 `.venv` with `uv`, install the
locked mini-SWE-agent and Harbor versions, inspect local agent/tool availability,
and download the public CAD Bench V3 task index. The task index contains public
IDs and revisions only; Harbor obtains task images when a benchmark run starts.
No API credentials are read during setup. Use `make bootstrap` separately when
you only need the ignored workspace directories. `make check` remains the
required repository validation.

Use `make provider-check` (or `npm run provider:check`) to probe the configured
OpenAI-compatible endpoint. The checker reads process environment variables
first and then simple `KEY=VALUE` entries from the ignored root `.env`; it maps
`CADLOOP_API_KEY` to the OpenAI check when `OPENAI_API_KEY` is absent. Its report
contains only key presence, request status and bounded response metadata.

## Safe dry run

Use a loader-produced public task file and inspect the exact prompts and
commands without making a model request:

```bash
PYTHONPATH=scripts python3 scripts/run_agent_demo.py \
  --tasks examples/cadbench_demo_tasks.jsonl \
  --agent all \
  --limit 2 \
  --output-dir runs/cadbench-agent-plan
```

The task file may be JSONL or a JSON list. Records are loaded through
`scripts/cadbench.py`, which strips common evaluator-only fields before making
prompts. The included examples are synthetic and do not belong to Harbor V3.

## Local CLI status

The project environment pins mini-SWE-agent `2.4.6` and Harbor `0.23.0` in
`uv.lock`; mini-SWE-agent requires Python 3.10 or newer and Harbor 0.23.0
requires Python 3.12. `make prepare` selects Python 3.12, while Codex CLI and
Claude Code remain external user-installed executables.

Codex runs in non-interactive JSONL mode:

```bash
codex exec --model gpt-5.6-sol --json --ephemeral \
  -C "$PWD" --sandbox workspace-write --ask-for-approval never -
```

The prompt is sent on stdin. A third-party OpenAI Responses endpoint must be
configured in Codex's provider settings; when `--base-url` is supplied, the
runner creates a temporary `CODEX_HOME/config.toml` containing only the model
and URL, then removes it. The bearer token remains in `OPENAI_API_KEY` in the
child process and is never written to the repository, command line, manifest,
or logs. Use `--codex-home` only when an existing isolated Codex configuration
has already been prepared.

Claude Code runs with `claude -p --output-format json`. Claude Code expects the
Anthropic Messages API. An OpenAI-compatible `/v1/responses` or
`/v1/chat/completions` gateway is not automatically compatible; only run it
against a gateway that explicitly exposes the Anthropic protocol and configure
`ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY` in the child environment.

mini-SWE-agent uses LiteLLM. Its custom OpenAI-compatible endpoint can be
provided through `OPENAI_BASE_URL`; a local YAML file outside Git is preferable
for a frozen reproduction, for example:

```yaml
model:
  model_name: openai/gpt-5.6-sol
  model_kwargs:
    custom_llm_provider: openai
    api_base: https://example.invalid/v1
```

Provide the API key through `OPENAI_API_KEY` in the process environment. The
`mini` command writes a trajectory file per task. The third-party endpoint
must support the Chat Completions shape that LiteLLM sends.

## Executing a demo

Execution is opt-in. Set credentials in the shell or an external secret
manager, then run a small slice. The OpenAI-compatible URL is passed only to
Codex/LiteLLM; Claude needs an explicitly separate Anthropic-compatible base
URL and credential.

```bash
OPENAI_API_KEY='...' ANTHROPIC_API_KEY='...' \
PYTHONPATH=scripts python3 scripts/run_agent_demo.py \
  --tasks examples/cadbench_demo_tasks.jsonl \
  --agent codex \
  --limit 1 \
  --base-url https://example.invalid/v1 \
  --claude-base-url https://anthropic-compatible.example/v1 \
  --output-dir runs/cadbench-codex-demo \
  --execute
```

The runner records stdout, prompts, public-task snapshots, return codes and
the exact non-secret command shape. It does not record environment variables,
API keys, private benchmark references, or an official score. Failures and
timeouts are preserved as demo results. `--execute` is required to invoke a
provider; dry-run is the default.

