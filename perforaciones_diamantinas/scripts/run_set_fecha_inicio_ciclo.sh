#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 --date YYYY-MM-DD [--force] [--venv /path/to/venv]

This script runs the Django management command set_fecha_inicio_ciclo
inside the project's Python virtualenv. It's intended to be run on the
Linux server where the app is deployed.

Options:
  --date   Required. Date to set (YYYY-MM-DD), e.g. 2026-02-26
  --force  Optional. Overwrite existing fecha_inicio_ciclo values
  --venv   Optional. Path to virtualenv root (contains bin/activate)

Example:
  ./run_set_fecha_inicio_ciclo.sh --date 2026-02-26 --force --venv /opt/rdapp/.venv
EOF
}

DATE=""
FORCE=""
VENV=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)
      DATE="$2"; shift 2;;
    --force)
      FORCE="--force"; shift 1;;
    --venv)
      VENV="$2"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown arg: $1"; usage; exit 2;;
  esac
done

if [[ -z "$DATE" ]]; then
  echo "--date is required"
  usage
  exit 2
fi

# Determine project manage.py location (this script is under perforaciones_diamantinas/scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANAGE_PY="$PROJECT_DIR/manage.py"

if [[ ! -f "$MANAGE_PY" ]]; then
  echo "Could not find manage.py at $MANAGE_PY" >&2
  exit 1
fi

PYTHON_CMD="python3"
if [[ -n "$VENV" ]]; then
  if [[ -f "$VENV/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$VENV/bin/activate"
    PYTHON_CMD="$VENV/bin/python"
  else
    echo "Provided venv path does not look valid: $VENV" >&2
    exit 1
  fi
else
  # try to find a local .venv in project parent directories
  if [[ -f "$PROJECT_DIR/../.venv/bin/activate" ]]; then
    source "$PROJECT_DIR/../.venv/bin/activate"
    PYTHON_CMD="$PROJECT_DIR/../.venv/bin/python"
  elif [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    PYTHON_CMD="$PROJECT_DIR/.venv/bin/python"
  fi
fi

echo "Using python: $(command -v "$PYTHON_CMD" || echo $PYTHON_CMD)"
echo "Running manage.py set_fecha_inicio_ciclo --date $DATE $FORCE"

cd "$PROJECT_DIR"
"$PYTHON_CMD" "$MANAGE_PY" set_fecha_inicio_ciclo --date "$DATE" $FORCE

echo "Done."
