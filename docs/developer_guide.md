# Developer Guide

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Running tests
```bash
.venv/bin/pytest -q
.venv/bin/ruff check pnp tests
```

## Running the ASIC mini-flow
```bash
.venv/bin/python -m asic.miniflow.flow --design pnp_core --out build/flow
```

## Running formal verification
```bash
sby -f verification/formal/watchdog_props.sby
```

## Adding a new module
1. Create module in appropriate package.
2. Add tests in tests/.
3. Update docs/TRACEABILITY.md.
4. Run ruff + pytest.
