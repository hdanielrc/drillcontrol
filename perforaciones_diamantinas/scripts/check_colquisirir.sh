#!/bin/bash

# Script para verificar estados de turnos en Colquisirir
# Ejecutar desde el servidor con: bash scripts/check_colquisirir.sh

echo "====================================="
echo "VERIFICACIÓN DE TURNOS - COLQUISIRIR"
echo "====================================="
echo ""

# Ir al directorio del proyecto
cd /var/www/drillcontrol/app/perforaciones_diamantinas

# Hacer pull de los últimos cambios
echo "Actualizando repositorio..."
git pull

# Ejecutar el script de verificación
echo ""
echo "Ejecutando verificación..."
echo ""
python3 scripts/check_colquisirir.py

echo ""
echo "====================================="
echo "VERIFICACIÓN COMPLETADA"
echo "====================================="
