#!/bin/bash
# ====================================================================
# Instala el cron job para la sincronización diaria a las 5:00 AM
# Uso: sudo bash programar_sync_abastecimientos.sh
# ====================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SYNC_SCRIPT="$SCRIPT_DIR/sync_abastecimientos_diario.sh"
CRON_COMMENT="drillcontrol-sync-abastecimientos"

echo "====================================================================="
echo "  PROGRAMAR SINCRONIZACIÓN DIARIA DE ABASTECIMIENTOS - 5:00 AM"
echo "====================================================================="
echo ""

# Verificar que el script de sync existe
if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "ERROR: No se encontró $SYNC_SCRIPT"
    exit 1
fi

# Dar permisos de ejecución
chmod +x "$SYNC_SCRIPT"
echo "✓ Permisos de ejecución asignados a sync_abastecimientos_diario.sh"

# Crear directorio de logs si no existe
mkdir -p "$SCRIPT_DIR/logs"
echo "✓ Directorio de logs verificado: $SCRIPT_DIR/logs"

# Línea del cron: 5:00 AM todos los días
CRON_LINE="0 5 * * * $SYNC_SCRIPT >> $SCRIPT_DIR/logs/sync_cron.log 2>&1 # $CRON_COMMENT"

# Verificar si ya existe una entrada para este script
CURRENT_CRON=$(crontab -l 2>/dev/null)

if echo "$CURRENT_CRON" | grep -q "$CRON_COMMENT"; then
    echo ""
    echo "⚠  Ya existe una tarea programada para sincronización de abastecimientos:"
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
(echo "$CURRENT_CRON"; echo "$CRON_LINE") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "====================================================================="
    echo "✓ CRON JOB REGISTRADO EXITOSAMENTE"
    echo "====================================================================="
    echo ""
    echo "  Horario : Todos los días a las 5:00 AM"
    echo "  Script  : $SYNC_SCRIPT"
    echo "  Logs    : $SCRIPT_DIR/logs/"
    echo ""
    echo "Cron jobs activos:"
    crontab -l | grep "$CRON_COMMENT"
    echo ""
    echo "Para ejecutar manualmente ahora:"
    echo "  bash $SYNC_SCRIPT"
    echo ""
    echo "Para ver logs en tiempo real:"
    echo "  tail -f $SCRIPT_DIR/logs/sync_cron.log"
    echo ""
else
    echo "ERROR: No se pudo registrar el cron job"
    exit 1
fi
