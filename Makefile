# Virtual PnP - top level build and verification entry points.
#
# Every target is safe to run repeatedly and never modifies tracked sources.

SHELL      := /bin/bash
VENV       ?= .venv
PY         ?= $(VENV)/bin/python
PIP        ?= $(VENV)/bin/pip
PYTEST     ?= $(VENV)/bin/pytest
RUFF       ?= $(VENV)/bin/ruff
MYPY       ?= $(VENV)/bin/mypy

# Open-source EDA backend.  `yowasp-yosys` is a WASM build that needs no OS
# packages; a native `yosys` is used when present.
YOSYS      ?= $(shell command -v yosys 2>/dev/null || echo $(VENV)/bin/yowasp-yosys)
SBY        ?= $(shell command -v sby 2>/dev/null || echo $(VENV)/bin/yowasp-sby)
REPORTS    := verification/reports

.DEFAULT_GOAL := help
.PHONY: help bootstrap venv lint fmt typecheck test cov \
        cpp-test asm-test fw-test rust-test go-test \
        hdl-lint hdl-synth formal rtl-sim asic asic-all \
        verify-all clean reports web

help: ## show available targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

bootstrap: ## create .venv and install every dependency
	./scripts/bootstrap.sh

venv:
	test -x $(PY) || ./scripts/bootstrap.sh

# ---------------------------------------------------------------- software ---
lint: venv ## ruff static analysis
	$(RUFF) check pnp tools tests

fmt: venv ## auto-format python sources
	$(RUFF) format pnp tools tests
	$(RUFF) check --fix pnp tools tests

typecheck: venv ## mypy static typing
	$(MYPY) pnp || true

test: venv ## python unit + integration tests
	$(PYTEST) -q

cov: venv ## python tests with coverage report
	$(PYTEST) --cov=pnp --cov-report=term-missing --cov-report=xml

cpp-test: ## build and run the C++ optimiser tests
	$(MAKE) -C cpp test

asm-test: ## assemble and run the x86-64 kernel tests
	$(MAKE) -C asm test

fw-test: ## host-compiled firmware unit tests (no cross toolchain needed)
	$(MAKE) -C firmware test

rust-test: ## cargo test (skipped when cargo is unavailable)
	@command -v cargo >/dev/null && (cd rust && cargo test --quiet) || echo "cargo not installed - skipped"

go-test: ## go test (skipped when go is unavailable)
	@command -v go >/dev/null && (cd go && go test ./...) || echo "go not installed - skipped"

# --------------------------------------------------------------------- HDL ---
hdl-lint: ## elaborate and lint every RTL block with yosys
	$(PY) tools/hdl_flow.py lint --yosys "$(YOSYS)"

hdl-synth: ## synthesise every RTL block and write area/timing reports
	$(PY) tools/hdl_flow.py synth --yosys "$(YOSYS)"

formal: ## run the SymbiYosys property proofs
	$(PY) tools/hdl_flow.py formal --sby "$(SBY)" --yosys "$(YOSYS)"

rtl-sim: ## simulate the synthesised netlists and dump waveforms
	PYTHONPATH=tools $(PY) -m rtlsim.testbenches --all --waves $(REPORTS)/waves

DESIGN ?= crc16_ccitt

asic: ## RTL -> netlist -> place & route -> GDSII -> DRC/connectivity/timing
	$(PY) -m asic.miniflow.flow --design $(DESIGN) --out asic/build

asic-all: ## run the layout flow on every supported design
	$(PY) -m asic.miniflow.flow --all --out asic/build

web: ## serve the simulator on http://localhost:8000
	$(PY) -m http.server 8000 --bind 0.0.0.0

reports: ## regenerate every machine-readable report
	mkdir -p $(REPORTS)

verify-all: lint test cpp-test asm-test fw-test hdl-lint hdl-synth formal rtl-sim asic ## full CI-equivalent run
	@echo
	@echo "verification complete - see $(REPORTS)/ and asic/build/"

clean: ## remove generated artefacts
	rm -rf $(REPORTS)/waves $(REPORTS)/synth asic/build
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	$(MAKE) -C cpp clean 2>/dev/null || true
