#!/bin/bash
# Script de Sincronización de Abastecimientos para Linux/Unix
# Uso: ./SYNC_ABASTECIMIENTOS.sh [YEAR] [CENTRO_COSTO]

# Configuración
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR" || exit

echo "========================================================"
echo "  Sincronizador Automático de Abastecimientos (Linux)"
echo "========================================================"
echo ""

# Auto-detectar Python y Entorno Virtual
PYTHON_EXEC="python3"

echo "DEBUG: Buscando entorno virtual desde $(pwd)..."

if [ -f ".venv/bin/activate" ]; then
    echo "Activando .venv/bin/activate"
    source ".venv/bin/activate"
    PYTHON_EXEC="python" 
elif [ -f "venv/bin/activate" ]; then
     echo "Activando venv/bin/activate"
     source "venv/bin/activate"
     PYTHON_EXEC="python"
elif [ -f "perforaciones_diamantinas/venv/bin/activate" ]; then
     echo "Activando perforaciones_diamantinas/venv/bin/activate"
     source "perforaciones_diamantinas/venv/bin/activate"
     PYTHON_EXEC="python"
elif [ -f "../venv/bin/activate" ]; then
     echo "Activando ../venv/bin/activate"
     source "../venv/bin/activate"
     PYTHON_EXEC="python"
elif [ -f "../.venv/bin/activate" ]; then
     echo "Activando ../.venv/bin/activate"
     source "../.venv/bin/activate"
     PYTHON_EXEC="python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
    echo "VirtualEnv no encontrado. Usando python3 del sistema."
elif command -v python &>/dev/null; then
    PYTHON_EXEC="python"
    echo "VirtualEnv no encontrado. Usando python del sistema."
else
    echo "ERROR: Python no encontrado."
    exit 1
fi

# Parámetros
ANIO="${1:-2025}"
CC="$2"

echo "Año: $ANIO"
if [ -z "$CC" ]; then
    echo "Centro de Costo: TODOS"
    CMD="$PYTHON_EXEC perforaciones_diamantinas/scripts/sync/sync_abastecimientos.py --year=$ANIO"
else
    echo "Centro de Costo: $CC"
    CMD="$PYTHON_EXEC perforaciones_diamantinas/scripts/sync/sync_abastecimientos.py --year=$ANIO --cc=$CC"
fi

echo ""
echo "Ejecutando: $CMD"
echo ""

$CMD

echo ""
echo "========================================================"
echo "  Proceso Finalizado."
echo "========================================================"
