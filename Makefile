PYTHON ?= python3
SMOKE_OUTPUT ?= runs/smoke-$(shell date -u +%Y%m%dT%H%M%SZ)

.PHONY: help doctor test check smoke paper

help:
	@echo "make doctor  - inspect the local smoke environment"
	@echo "make check   - compile Python and run offline tests"
	@echo "make smoke   - run synthetic tasks and save a new local run"
	@echo "make paper   - build the paper with latexmk (optional)"

doctor:
	PYTHONPATH=src $(PYTHON) -m cadloop doctor

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

check:
	$(PYTHON) -m compileall -q src tests
	$(MAKE) test

smoke:
	PYTHONPATH=src $(PYTHON) -m cadloop run --config configs/experiments/smoke.json --output-dir $(SMOKE_OUTPUT)

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
