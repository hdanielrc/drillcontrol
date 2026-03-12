#!/bin/bash
# ====================================================================
# Script de Sincronización Diaria de Trabajadores
# Se ejecuta automáticamente a las 4:00 AM via cron
# Sincroniza trabajadores desde la API de Vilbra Group
#
# Instalación del cron:
#   chmod +x sync_trabajadores_diario.sh
#   sudo bash programar_sync_trabajadores.sh
# ====================================================================

# Directorio del proyecto Django (donde está manage.py)
PROJECT_DIR="/var/www/drillcontrol/app/perforaciones_diamantinas"
LOG_DIR="$PROJECT_DIR/logs"

cd "$PROJECT_DIR" || { echo "ERROR: No se encontró $PROJECT_DIR"; exit 1; }

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/sync_trabajadores_$(date +%Y%m%d).log"

echo "====================================================================" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando sincronización de trabajadores" | tee -a "$LOG_FILE"
echo "====================================================================" | tee -a "$LOG_FILE"

# Activar entorno virtual
PYTHON_EXEC="python3"

if [ -f "../.venv/bin/activate" ]; then
    source "../.venv/bin/activate"
    PYTHON_EXEC="python"
    echo "[$(date '+%H:%M:%S')] Entorno virtual .venv activado" | tee -a "$LOG_FILE"
elif [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
    PYTHON_EXEC="python"
    echo "[$(date '+%H:%M:%S')] Entorno virtual activado" | tee -a "$LOG_FILE"
elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
    PYTHON_EXEC="python"
    echo "[$(date '+%H:%M:%S')] Entorno virtual venv activado" | tee -a "$LOG_FILE"
fi

# Ejecutar sincronización de trabajadores
echo "[$(date '+%H:%M:%S')] Ejecutando sync_trabajadores.py (dry-run)..." | tee -a "$LOG_FILE"
$PYTHON_EXEC scripts/sync/sync_trabajadores.py --dry-run >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] ✓ Sincronización de trabajadores completada exitosamente." | tee -a "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] ✗ ERROR en sincronización (código $EXIT_CODE). Revisa $LOG_FILE" | tee -a "$LOG_FILE"
fi

echo "====================================================================" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Proceso finalizado." | tee -a "$LOG_FILE"
echo "====================================================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE
