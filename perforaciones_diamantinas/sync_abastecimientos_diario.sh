#!/bin/bash
# ====================================================================
# Script de Sincronización Diaria de Abastecimientos - TODOS LOS CONTRATOS
# Se ejecuta automáticamente a las 5:00 AM via cron
# Sincroniza los últimos 3 meses para TODOS los contratos activos
# Cubre todas las familias (PDD, ADIT, EPP, IN, etc.)
#
# Instalación del cron:
#   chmod +x sync_abastecimientos_diario.sh
#   ./programar_sync_abastecimientos.sh
# ====================================================================

# Directorio del proyecto Django (donde está manage.py)
PROJECT_DIR="/var/www/drillcontrol/app/perforaciones_diamantinas"
LOG_DIR="$PROJECT_DIR/logs"

cd "$PROJECT_DIR" || { echo "ERROR: No se encontró $PROJECT_DIR"; exit 1; }

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

LOG_GENERAL="$LOG_DIR/sync_diario_$(date +%Y%m%d).log"

echo "====================================================================" | tee -a "$LOG_GENERAL"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando sincronización diaria de abastecimientos" | tee -a "$LOG_GENERAL"
echo "====================================================================" | tee -a "$LOG_GENERAL"

# Activar entorno virtual
PYTHON_EXEC="python3"

if [ -f "../.venv/bin/activate" ]; then
    source "../.venv/bin/activate"
    PYTHON_EXEC="python"
    echo "[$(date '+%H:%M:%S')] Entorno virtual .venv activado" | tee -a "$LOG_GENERAL"
elif [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
    PYTHON_EXEC="python"
    echo "[$(date '+%H:%M:%S')] Entorno virtual .venv activado" | tee -a "$LOG_GENERAL"
elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
    PYTHON_EXEC="python"
    echo "[$(date '+%H:%M:%S')] Entorno virtual venv activado" | tee -a "$LOG_GENERAL"
else
    echo "[$(date '+%H:%M:%S')] AVISO: Entorno virtual no encontrado, usando $PYTHON_EXEC del sistema" | tee -a "$LOG_GENERAL"
fi

# Calcular los últimos 3 meses con Python puro
PERIODOS=$($PYTHON_EXEC -c "
from datetime import date
d = date.today()
m, y = d.month, d.year
result = []
for i in range(2, -1, -1):
    mes = m - i
    anio = y
    if mes <= 0:
        mes += 12
        anio -= 1
    result.append(f'{anio}{str(mes).zfill(2)}')
print(' '.join(result))
")

if [ -z "$PERIODOS" ]; then
    echo "[$(date '+%H:%M:%S')] ERROR: No se pudieron calcular los periodos" | tee -a "$LOG_GENERAL"
    exit 1
fi

echo "[$(date '+%H:%M:%S')] Periodos a sincronizar: $PERIODOS" | tee -a "$LOG_GENERAL"
echo "" | tee -a "$LOG_GENERAL"

# Sincronizar cada periodo
EXIT_CODE=0
for PERIODO in $PERIODOS; do
    LOG_PERIODO="$LOG_DIR/sync_abastecimientos_${PERIODO}.log"

    echo "--------------------------------------------------------------------" | tee -a "$LOG_GENERAL"
    echo "[$(date '+%H:%M:%S')] Sincronizando periodo: $PERIODO - TODOS los contratos activos" | tee -a "$LOG_GENERAL"
    echo "--------------------------------------------------------------------" | tee -a "$LOG_GENERAL"

    $PYTHON_EXEC manage.py sincronizar_abastecimientos "$PERIODO" --verbose >> "$LOG_PERIODO" 2>&1

    if [ $? -eq 0 ]; then
        echo "[$(date '+%H:%M:%S')] ✓ Periodo $PERIODO completado exitosamente" | tee -a "$LOG_GENERAL"
    else
        echo "[$(date '+%H:%M:%S')] ✗ ERROR en periodo $PERIODO - ver $LOG_PERIODO" | tee -a "$LOG_GENERAL"
        EXIT_CODE=1
    fi
done

echo "" | tee -a "$LOG_GENERAL"
echo "====================================================================" | tee -a "$LOG_GENERAL"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Proceso finalizado" | tee -a "$LOG_GENERAL"
echo "====================================================================" | tee -a "$LOG_GENERAL"

exit $EXIT_CODE
