PYTHON ?= python3
PYTHON_CACHE ?= /tmp/cadloop-pycache
SMOKE_OUTPUT ?= runs/smoke-$(shell date -u +%Y%m%dT%H%M%SZ)

.PHONY: help bootstrap bootstrap-dry-run bootstrap-doctor provider-check doctor test check smoke paper cadbench-inspect cadbench-demo

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
