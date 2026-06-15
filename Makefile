# Cross-platform entry points (macOS/Linux). Windows users: use run_web.bat.
# Targets assume a POSIX shell with python3, node, and npm on PATH.

PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

.PHONY: help venv install pipeline check export web build clean

help:
	@echo "Targets:"
	@echo "  make install   Create .venv and install Python requirements"
	@echo "  make pipeline  Run the Python pipeline (data -> detectors -> alerts -> evaluation)"
	@echo "  make check     Run scenario robustness + output smoke check"
	@echo "  make export    Export pipeline CSVs to dashboard JSON"
	@echo "  make web       Full run: install + pipeline + check + export + start dashboard"
	@echo "  make build     Production build of the React dashboard"
	@echo "  make clean     Remove generated data/report outputs and the venv"

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

venv: $(VENV_PYTHON)

install: venv
	$(VENV_PYTHON) -m pip install --quiet --disable-pip-version-check --upgrade -r requirements.txt

pipeline: install
	$(VENV_PYTHON) run_pipeline.py

check: install
	$(VENV_PYTHON) -m src.scenario_robustness
	$(VENV_PYTHON) tests/smoke_check_outputs.py

export: install
	$(VENV_PYTHON) scripts/export_web_data.py

web:
	bash scripts/run_web.sh

build: pipeline check export
	cd web && npm install && npm run build

clean:
	rm -rf $(VENV)
	rm -f data/raw/*.csv data/processed/*.csv data/outputs/*.csv reports/*.csv
	rm -rf web/node_modules web/dist
