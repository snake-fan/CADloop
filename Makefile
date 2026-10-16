PYTHON ?= python3
PYTHON_CACHE ?= /tmp/cadloop-pycache
SMOKE_OUTPUT ?= runs/smoke-$(shell date -u +%Y%m%dT%H%M%SZ)
UV ?= uv
UV_PYTHON ?= 3.12
UV_VENV ?= .venv
UV_CACHE_DIR ?= data/cache/uv
INTEGRATION_PYTHON ?= $(UV_VENV)/bin/python
CADBENCH_INDEX ?= runs/cadbench-v3-index/tasks.jsonl
HARBOR_AGENT ?= codex
HARBOR_MODEL ?= gpt-5.6-sol

.PHONY: help bootstrap bootstrap-dry-run bootstrap-doctor provider-check doctor test check smoke paper cadbench-inspect cadbench-demo uv-sync uv-doctor benchmark-index prepare cadbench-run

help:
	@echo "make doctor  - inspect the local smoke environment"
	@echo "make bootstrap - create ignored workspace directories and inspect tools"
	@echo "make bootstrap-dry-run - preview bootstrap without writing"
	@echo "make bootstrap-doctor - inspect Python, CAD and agent CLI availability"
	@echo "make provider-check - probe the configured OpenAI-compatible /v1 endpoint"
	@echo "make check   - compile Python and run offline tests"
	@echo "make smoke   - run synthetic tasks and save a new local run"
	@echo "make paper   - build the paper with latexmk (optional)"
	@echo "make cadbench-inspect - inspect pinned Parametric CAD Bench V3 metadata"
	@echo "make cadbench-demo - run local synthetic prompts through installed agent CLIs"
	@echo "make uv-sync - create .venv with Python 3.12 and install pinned agent/benchmark tools"
	@echo "make uv-doctor - verify uv integration versions and local CLIs"
	@echo "make benchmark-index - download public CAD Bench V3 task metadata only"
	@echo "make prepare - sync integrations, inspect versions, and fetch the public task index"
	@echo "make cadbench-run - run the pinned full CAD Bench V3 suite locally (no upload)"

doctor:
	PYTHONPATH=src $(PYTHON) -m cadloop doctor

bootstrap:
	$(PYTHON) scripts/bootstrap.py bootstrap

bootstrap-dry-run:
	$(PYTHON) scripts/bootstrap.py bootstrap --dry-run

bootstrap-doctor:
	$(PYTHON) scripts/bootstrap.py doctor

provider-check:
	$(PYTHON) scripts/provider_check.py --protocol all --output runs/provider-check.json

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

check:
	PYTHONPYCACHEPREFIX=$(PYTHON_CACHE) $(PYTHON) -m compileall -q src scripts tests
	$(MAKE) test

smoke:
	PYTHONPATH=src $(PYTHON) -m cadloop run --config configs/experiments/smoke.json --output-dir $(SMOKE_OUTPUT)

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

cadbench-inspect:
	PYTHONPATH=scripts $(PYTHON) scripts/cadbench.py inspect

cadbench-demo:
	$(PYTHON) scripts/run_agent_demo.py \
		--tasks examples/cadbench_demo_tasks.jsonl \
		--agent all \
		--limit 3 \
		--output-dir runs/cadbench-agent-plan

uv-sync:
	UV_CACHE_DIR=$(UV_CACHE_DIR) CADLOOP_UV=$(UV) $(PYTHON) scripts/setup_uv.py sync \
		--python $(UV_PYTHON) --venv $(UV_VENV)

uv-doctor:
	MSWEA_GLOBAL_CONFIG_DIR=data/cache/mini-swe-agent \
		CADLOOP_UV=$(UV) $(PYTHON) scripts/setup_uv.py doctor --venv $(UV_VENV)

benchmark-index:
	PYTHONPATH=scripts $(PYTHON) scripts/cadbench.py index --output $(CADBENCH_INDEX)

prepare: uv-sync uv-doctor benchmark-index

cadbench-run:
	MSWEA_GLOBAL_CONFIG_DIR=data/cache/mini-swe-agent \
		PATH="$(UV_VENV)/bin:$$PATH" $(UV_VENV)/bin/harbor run \
		-d gnucleus-ai/cad-bench@v3 -a $(HARBOR_AGENT) -m $(HARBOR_MODEL) \
		--n-concurrent 4 --n-attempts 1 --max-retries 0
