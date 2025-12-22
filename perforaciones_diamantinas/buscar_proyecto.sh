#!/bin/bash
# Script para encontrar la ubicación del proyecto en el servidor

echo "======================================================================"
echo "BUSCANDO PROYECTO DRILLCONTROL EN EL SERVIDOR"
echo "======================================================================"

echo ""
echo "🔍 Buscando por archivos característicos..."

# Buscar manage.py (archivo característico de Django)
echo ""
echo "1️⃣ Buscando manage.py de Django:"
find / -name "manage.py" -path "*/perforaciones_diamantinas/*" 2>/dev/null | head -5

# Buscar por nombre de directorio
echo ""
echo "2️⃣ Buscando directorio perforaciones_diamantinas:"
find / -type d -name "perforaciones_diamantinas" 2>/dev/null | head -5

# Buscar en ubicaciones comunes
echo ""
echo "3️⃣ Verificando ubicaciones comunes:"
for dir in /var/www /home /opt /srv /root; do
    if [ -d "$dir" ]; then
        echo "Buscando en $dir..."
        find "$dir" -name "manage.py" -path "*/perforaciones_diamantinas/*" 2>/dev/null
    fi
done

# Buscar procesos de gunicorn que puedan indicar la ruta
echo ""
echo "4️⃣ Verificando procesos activos (gunicorn/django):"
ps aux | grep -i "gunicorn\|django\|drillcontrol" | grep -v grep

# Verificar configuración de systemd
echo ""
echo "5️⃣ Verificando servicios systemd:"
if [ -f /etc/systemd/system/gunicorn.service ]; then
    echo "Encontrado: /etc/systemd/system/gunicorn.service"
    grep -i "workingdirectory\|execstart" /etc/systemd/system/gunicorn.service
fi

# Verificar nginx
echo ""
echo "6️⃣ Verificando configuración de Nginx:"
if [ -d /etc/nginx/sites-enabled ]; then
    grep -r "drillcontrol\|perforaciones" /etc/nginx/sites-enabled/ 2>/dev/null | head -3
fi

echo ""
echo "======================================================================"
