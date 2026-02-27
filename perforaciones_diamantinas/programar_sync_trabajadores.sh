#!/bin/bash
# ====================================================================
# Instala el cron job para la sincronización diaria de trabajadores
# a las 4:00 AM.
# Uso: sudo bash programar_sync_trabajadores.sh
# ====================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SYNC_SCRIPT="$SCRIPT_DIR/sync_trabajadores_diario.sh"
CRON_COMMENT="drillcontrol-sync-trabajadores"

echo "====================================================================="
echo "  PROGRAMAR SINCRONIZACIÓN DIARIA DE TRABAJADORES - 4:00 AM"
echo "====================================================================="
echo ""

# Verificar que el script de sync existe
if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "ERROR: No se encontró $SYNC_SCRIPT"
    exit 1
fi

# Dar permisos de ejecución
chmod +x "$SYNC_SCRIPT"
echo "✓ Permisos de ejecución asignados a sync_trabajadores_diario.sh"

# Crear directorio de logs si no existe
mkdir -p "$SCRIPT_DIR/logs"
echo "✓ Directorio de logs verificado: $SCRIPT_DIR/logs"

# Línea del cron: 4:00 AM todos los días
CRON_LINE="0 4 * * * $SYNC_SCRIPT >> $SCRIPT_DIR/logs/sync_trabajadores_cron.log 2>&1 # $CRON_COMMENT"

# Verificar si ya existe una entrada para este script
CURRENT_CRON=$(crontab -l 2>/dev/null)

if echo "$CURRENT_CRON" | grep -q "$CRON_COMMENT"; then
    echo ""
    echo "⚠  Ya existe una tarea programada para sincronización de trabajadores:"
    echo "$CURRENT_CRON" | grep "$CRON_COMMENT"
    echo ""
    read -p "¿Reemplazar con la nueva configuración? (s/N): " CONFIRM
    if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]]; then
        echo "Cancelado."
        exit 0
    fi
    # Eliminar entrada anterior
    CURRENT_CRON=$(echo "$CURRENT_CRON" | grep -v "$CRON_COMMENT")
    echo "✓ Entrada anterior eliminada"
fi

# Agregar nueva entrada al cron
NEW_CRON="${CURRENT_CRON}
${CRON_LINE}"

echo "$NEW_CRON" | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "====================================================================="
    echo "✓ CRON JOB CREADO EXITOSAMENTE"
    echo "====================================================================="
    echo ""
    echo "Horario  : Todos los días a las 4:00 AM"
    echo "Script   : $SYNC_SCRIPT"
    echo "Log cron : $SCRIPT_DIR/logs/sync_trabajadores_cron.log"
    echo ""
    echo "Cron actual:"
    crontab -l | grep "$CRON_COMMENT"
    echo ""
    echo "Para verificar todos los crons activos:"
    echo "  crontab -l"
    echo ""
    read -p "¿Deseas ejecutar una prueba ahora mismo? (s/N): " TEST
    if [[ "$TEST" == "s" || "$TEST" == "S" ]]; then
        echo ""
        echo "Ejecutando sincronización de prueba..."
        bash "$SYNC_SCRIPT"
    fi
else
    echo "✗ ERROR al instalar el cron job."
    exit 1
fi
