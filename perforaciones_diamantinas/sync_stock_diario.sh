#!/bin/bash
# ====================================================================
# Script de Sincronización Diaria de Stock y Brocas
# Se ejecuta automáticamente a las 2:00 AM via cron
# Sincroniza PDD (Productos Diamantados), ADIT (Aditivos) y Brocas
# para TODOS los contratos activos
#
# Instalación del cron:
#   chmod +x sync_stock_diario.sh
#   sudo bash programar_sync_stock.sh
# ====================================================================

# Directorio del proyecto Django (donde está manage.py)
PROJECT_DIR="/var/www/drillcontrol/app/perforaciones_diamantinas"
LOG_DIR="$PROJECT_DIR/logs"

cd "$PROJECT_DIR" || { echo "ERROR: No se encontró $PROJECT_DIR"; exit 1; }

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/sync_stock_$(date +%Y%m%d).log"

echo "====================================================================" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando sincronización de stock y brocas" | tee -a "$LOG_FILE"
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
    echo "[$(date '+%H:%M:%S')] Entorno virtual .venv activado" | tee -a "$LOG_FILE"
elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
    PYTHON_EXEC="python"
    echo "[$(date '+%H:%M:%S')] Entorno virtual venv activado" | tee -a "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] AVISO: Entorno virtual no encontrado, usando $PYTHON_EXEC del sistema" | tee -a "$LOG_FILE"
fi

# Ejecutar sincronización de stock v2 (con snapshots históricos y alertas)
echo "[$(date '+%H:%M:%S')] Ejecutando sync_stock_v2.py..." | tee -a "$LOG_FILE"
$PYTHON_EXEC scripts/sync/sync_stock_v2.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] ✓ Sincronización de stock completada exitosamente." | tee -a "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] ✗ ERROR en sincronización de stock (código $EXIT_CODE). Revisa $LOG_FILE" | tee -a "$LOG_FILE"
fi

echo "====================================================================" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Proceso finalizado." | tee -a "$LOG_FILE"
echo "====================================================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE
