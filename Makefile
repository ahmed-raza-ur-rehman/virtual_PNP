.PHONY: test lint fmt
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check pnp tests
fmt:
	.venv/bin/ruff format pnp tests
