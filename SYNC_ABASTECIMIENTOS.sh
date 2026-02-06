#!/bin/bash
# Script de Sincronización de Abastecimientos para Linux/Unix
# Uso: ./SYNC_ABASTECIMIENTOS.sh [YEAR] [CENTRO_COSTO]

# Configuración
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CD "$PROJECT_DIR"
VENV_ACTIVATE=".venv/bin/activate"

echo "========================================================"
echo "  Sincronizador Automático de Abastecimientos (Linux)"
echo "========================================================"
echo ""

# Activar entorno virtual
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
else
    echo "Advertencia: Entorno virtual no encontrado en $VENV_ACTIVATE"
    echo "Usando python del sistema..."
fi

# Parámetros
ANIO="${1:-2025}"
CC="$2"

echo "Año: $ANIO"
if [ -z "$CC" ]; then
    echo "Centro de Costo: TODOS"
    CMD="python perforaciones_diamantinas/scripts/sync/sync_abastecimientos.py --year=$ANIO"
else
    echo "Centro de Costo: $CC"
    CMD="python perforaciones_diamantinas/scripts/sync/sync_abastecimientos.py --year=$ANIO --cc=$CC"
fi

echo ""
echo "Ejecutando: $CMD"
echo ""

$CMD

echo ""
echo "========================================================"
echo "  Proceso Finalizado."
echo "========================================================"
