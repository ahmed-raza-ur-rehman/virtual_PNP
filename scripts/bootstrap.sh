#!/usr/bin/env bash
# Bootstrap a complete development environment for the Virtual PnP platform.
#
#   ./scripts/bootstrap.sh            # python env + tools
#   ./scripts/bootstrap.sh --full     # also install optional extras
#
# Everything is installed into ./.venv so the repository stays self-contained.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VENV="${VENV:-.venv}"
PYTHON="${PYTHON:-python3}"
FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

log() { printf '\033[1;34m[bootstrap]\033[0m %s\n' "$*"; }

log "creating virtual environment in ${VENV}"
"$PYTHON" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip >/dev/null

log "installing package with test tooling"
pip install -e ".[dev]"
if [[ $FULL -eq 1 ]]; then
    log "installing optional extras (api, gui, ml, vision)"
    pip install -e ".[api,gui,ml,vision]" || log "optional extras partially unavailable (offline?)"
fi

log "installing open-source EDA backend (yowasp build of yosys, runs without OS packages)"
pip install yowasp-yosys yowasp-sby || log "yosys unavailable - HDL flow will be skipped"

log "environment ready"
python -c "import pnp, sys; print('  pnp import OK on', sys.version.split()[0])"
cat <<'TIP'

Next steps:
  make test          # python test suite
  make cpp-test      # C++ optimiser tests (needs g++)
  make hdl-lint      # RTL lint with yosys
  make formal        # SymbiYosys proofs
  make asic          # RTL -> GDSII mini-flow
  make verify-all    # everything above
TIP
