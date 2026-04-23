#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
LOCK_FILE="/tmp/drillcontrol_sync_all_contracts.lock"
PYTHON_BIN="${PYTHON_BIN:-${PROJECT_ROOT}/venv/bin/python}"
MANAGE_PY="${PROJECT_ROOT}/manage.py"
TRABAJADORES_SYNC_SCRIPT="${PROJECT_ROOT}/scripts/sync/sync_trabajadores.py"
PERIODO_ACTUAL="$(date '+%Y%m')"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
MAIN_LOG="${LOG_DIR}/sync_diario.log"
TRABAJADORES_LOG="${LOG_DIR}/sync_trabajadores.log"
INVENTARIO_LOG="${LOG_DIR}/sync_inventario.log"
CONSUMOS_LOG="${LOG_DIR}/sync_consumos.log"

mkdir -p "${LOG_DIR}"



if [[ ! -f "${MANAGE_PY}" ]]; then
  echo "[${TIMESTAMP}] ERROR: no se encontro manage.py en ${PROJECT_ROOT}" | tee -a "${MAIN_LOG}"
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

if [[ -f "${LOCK_FILE}" ]] && kill -0 "$(cat "${LOCK_FILE}")" 2>/dev/null; then
  echo "[${TIMESTAMP}] SKIP: ya hay una sincronizacion en ejecucion (PID $(cat "${LOCK_FILE}"))" >> "${MAIN_LOG}"
  exit 0
fi

echo $$ > "${LOCK_FILE}"
trap 'rm -f "${LOCK_FILE}"' EXIT

log_main() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${MAIN_LOG}"
}

run_step() {
  local step_name="$1"
  local step_log="$2"
  shift 2

  log_main "Inicio ${step_name}"
  set +e
  {
    echo "======================================================================"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Inicio ${step_name}"
    echo "Proyecto: ${PROJECT_ROOT}"
    echo "Python: ${PYTHON_BIN}"
    "$@"
  } >> "${step_log}" 2>&1
  local status=$?
  set -e
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Fin ${step_name} status=${status}" >> "${step_log}"
  if [[ ${status} -ne 0 ]]; then
    log_main "Error en ${step_name}. Revisar ${step_log}"
    exit ${status}
  fi
  log_main "Fin ${step_name}"
}

log_main "======================================================================"
log_main "Inicio sincronizacion diaria"
log_main "Proyecto: ${PROJECT_ROOT}"
log_main "Python: ${PYTHON_BIN}"

cd "${PROJECT_ROOT}"

run_step "sync_trabajadores" "${TRABAJADORES_LOG}" "${PYTHON_BIN}" "${TRABAJADORES_SYNC_SCRIPT}"
run_step "sync_inventario" "${INVENTARIO_LOG}" "${PYTHON_BIN}" "${MANAGE_PY}" sync_all_contracts
run_step "sync_consumos_${PERIODO_ACTUAL}" "${CONSUMOS_LOG}" "${PYTHON_BIN}" "${MANAGE_PY}" sincronizar_consumos "${PERIODO_ACTUAL}"

log_main "Fin sincronizacion diaria"
