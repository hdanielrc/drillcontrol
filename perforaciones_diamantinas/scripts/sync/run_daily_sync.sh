#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
LOCK_FILE="/tmp/drillcontrol_sync_all_contracts.lock"
PYTHON_BIN="${PYTHON_BIN:-${PROJECT_ROOT}/venv/bin/python}"
MANAGE_PY="${PROJECT_ROOT}/manage.py"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

mkdir -p "${LOG_DIR}"

if [[ ! -f "${MANAGE_PY}" ]]; then
  echo "[${TIMESTAMP}] ERROR: no se encontro manage.py en ${PROJECT_ROOT}" | tee -a "${LOG_DIR}/sync_all_contracts.log"
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

if [[ -f "${LOCK_FILE}" ]] && kill -0 "$(cat "${LOCK_FILE}")" 2>/dev/null; then
  echo "[${TIMESTAMP}] SKIP: ya hay una sincronizacion en ejecucion (PID $(cat "${LOCK_FILE}"))" >> "${LOG_DIR}/sync_all_contracts.log"
  exit 0
fi

echo $$ > "${LOCK_FILE}"
trap 'rm -f "${LOCK_FILE}"' EXIT

{
  echo "======================================================================"
  echo "[${TIMESTAMP}] Inicio sync_all_contracts"
  echo "Proyecto: ${PROJECT_ROOT}"
  echo "Python: ${PYTHON_BIN}"
  cd "${PROJECT_ROOT}"
  "${PYTHON_BIN}" "${MANAGE_PY}" sync_all_contracts
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Fin sync_all_contracts"
} >> "${LOG_DIR}/sync_all_contracts.log" 2>&1
