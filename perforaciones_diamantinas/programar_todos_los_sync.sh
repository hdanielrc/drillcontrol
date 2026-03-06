#!/bin/bash
# ====================================================================
# INSTALADOR MAESTRO DE CRON JOBS - DrillControl
# Programa TODOS los scripts de sincronización automática en Linux
#
# Uso: sudo bash programar_todos_los_sync.sh
#
# Horario resultante:
#   2:00 AM  → sync_stock_diario.sh    (Stock PDD/ADIT + Brocas)
#   4:00 AM  → sync_trabajadores_diario.sh  (Trabajadores)
#   5:00 AM  → sync_abastecimientos_diario.sh (Abastecimientos - todos los contratos)
# ====================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║       DRILLCONTROL - PROGRAMADOR MAESTRO DE SINCRONIZACIÓN        ║"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo "║  2:00 AM  Stock PDD/ADIT + Brocas    (sync_stock_diario.sh)       ║"
echo "║  4:00 AM  Trabajadores               (sync_trabajadores_diario.sh) ║"
echo "║  5:00 AM  Abastecimientos            (sync_abastecimientos_diario.sh)║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar scripts de ejecución
SCRIPTS=(
    "sync_stock_diario.sh"
    "sync_trabajadores_diario.sh"
    "sync_abastecimientos_diario.sh"
)

echo "Verificando scripts..."
MISSING=0
for SCRIPT in "${SCRIPTS[@]}"; do
    if [ -f "$SCRIPT_DIR/$SCRIPT" ]; then
        chmod +x "$SCRIPT_DIR/$SCRIPT"
        echo "  ✓ $SCRIPT"
    else
        echo "  ✗ $SCRIPT  ← NO ENCONTRADO"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "ERROR: Faltan $MISSING script(s). Asegúrate de estar en el directorio correcto."
    exit 1
fi

echo ""
mkdir -p "$SCRIPT_DIR/logs"
echo "✓ Directorio de logs: $SCRIPT_DIR/logs"
echo ""

# Definir cron jobs
declare -A CRON_JOBS
CRON_JOBS["drillcontrol-sync-stock"]="0 2 * * * $SCRIPT_DIR/sync_stock_diario.sh >> $SCRIPT_DIR/logs/sync_stock_cron.log 2>&1"
CRON_JOBS["drillcontrol-sync-trabajadores"]="0 4 * * * $SCRIPT_DIR/sync_trabajadores_diario.sh >> $SCRIPT_DIR/logs/sync_trabajadores_cron.log 2>&1"
CRON_JOBS["drillcontrol-sync-abastecimientos"]="0 5 * * * $SCRIPT_DIR/sync_abastecimientos_diario.sh >> $SCRIPT_DIR/logs/sync_cron.log 2>&1"

# Leer cron actual
CURRENT_CRON=$(crontab -l 2>/dev/null)

# Detectar si ya hay algún job registrado
EXISTING_COUNT=0
for COMMENT in "${!CRON_JOBS[@]}"; do
    if echo "$CURRENT_CRON" | grep -q "$COMMENT"; then
        EXISTING_COUNT=$((EXISTING_COUNT + 1))
    fi
done

if [ $EXISTING_COUNT -gt 0 ]; then
    echo "⚠  Se encontraron $EXISTING_COUNT cron job(s) de DrillControl ya registrados:"
    echo ""
    for COMMENT in "${!CRON_JOBS[@]}"; do
        if echo "$CURRENT_CRON" | grep -q "$COMMENT"; then
            echo "  $(echo "$CURRENT_CRON" | grep "$COMMENT")"
        fi
    done
    echo ""
    read -p "¿Reemplazar todos con la nueva configuración? (s/N): " CONFIRM
    if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]]; then
        echo "Cancelado."
        exit 0
    fi
    # Eliminar todas las entradas anteriores de DrillControl
    for COMMENT in "${!CRON_JOBS[@]}"; do
        CURRENT_CRON=$(echo "$CURRENT_CRON" | grep -v "$COMMENT")
    done
    echo "✓ Entradas anteriores eliminadas"
    echo ""
fi

# Construir nuevo crontab
NEW_CRON="$CURRENT_CRON"
for COMMENT in "${!CRON_JOBS[@]}"; do
    NEW_CRON="${NEW_CRON}
${CRON_JOBS[$COMMENT]} # $COMMENT"
done

# Instalar
echo "$NEW_CRON" | crontab -

if [ $? -ne 0 ]; then
    echo "ERROR: No se pudo actualizar el crontab."
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║              ✓ TODOS LOS CRON JOBS REGISTRADOS                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Cron jobs activos de DrillControl:"
echo ""
crontab -l | grep "drillcontrol-sync" | while read -r LINE; do
    echo "  $LINE"
done
echo ""
echo "Archivos de log:"
echo "  $SCRIPT_DIR/logs/sync_stock_cron.log"
echo "  $SCRIPT_DIR/logs/sync_trabajadores_cron.log"
echo "  $SCRIPT_DIR/logs/sync_cron.log"
echo ""
echo "Para ver todos los cron jobs activos:"
echo "  crontab -l"
echo ""
echo "Para monitorear logs en tiempo real:"
echo "  tail -f $SCRIPT_DIR/logs/sync_stock_cron.log"
echo "  tail -f $SCRIPT_DIR/logs/sync_trabajadores_cron.log"
echo "  tail -f $SCRIPT_DIR/logs/sync_cron.log"
echo ""

read -p "¿Deseas ejecutar una prueba completa ahora? (s/N): " TEST
if [[ "$TEST" == "s" || "$TEST" == "S" ]]; then
    echo ""
    echo "======================================================================"
    echo "Ejecutando stock sync..."
    bash "$SCRIPT_DIR/sync_stock_diario.sh"
    echo ""
    echo "Ejecutando trabajadores sync..."
    bash "$SCRIPT_DIR/sync_trabajadores_diario.sh"
    echo ""
    echo "Ejecutando abastecimientos sync..."
    bash "$SCRIPT_DIR/sync_abastecimientos_diario.sh"
    echo ""
    echo "======================================================================"
    echo "✓ Prueba completa finalizada. Revisa los logs para detalles."
fi
