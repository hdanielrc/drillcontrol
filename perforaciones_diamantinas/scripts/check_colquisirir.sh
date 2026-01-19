#!/bin/bash

# Script para verificar estados de turnos en Colquisirir
# Ejecutar desde el servidor con: bash scripts/check_colquisirir.sh

echo "====================================="
echo "VERIFICACIÓN DE TURNOS - COLQUISIRIR"
echo "====================================="
echo ""

# Ir al directorio del proyecto
cd /root/perforaciones_diamantinas

# Hacer pull de los últimos cambios
echo "Actualizando repositorio..."
git pull

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Ejecutar el script de verificación
echo ""
echo "Ejecutando verificación..."
echo ""
python scripts/check_colquisirir.py

echo ""
echo "====================================="
echo "VERIFICACIÓN COMPLETADA"
echo "====================================="
