#!/bin/bash
# Wrapper para ejecutar la sincronización completa de DrillControl
# Uso:
#   ./run_full_sync.sh [--no-dry-run] [--verbose]

set -euo pipefail

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
cd "$PROJECT_DIR"

# Intentar activar .venv local si existe
if [ -f ".venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source .venv/bin/activate
    echo "Entorno virtual .venv activado"
fi

DRY_RUN=1
VERBOSE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-dry-run)
      DRY_RUN=0; shift;;
    --verbose)
      VERBOSE=1; shift;;
    *)
      echo "Opción desconocida: $1"; exit 2;;
  esac
done

CMD="python manage.py sync_all_contracts"
if [ "$DRY_RUN" -eq 1 ]; then
  CMD="$CMD --dry-run"
fi
if [ "$VERBOSE" -eq 1 ]; then
  CMD="$CMD --verbose"
fi

echo "Ejecutando: $CMD"
eval "$CMD"

echo "Sincronización completa (dry_run=$DRY_RUN). Revisa logs para detalles."
