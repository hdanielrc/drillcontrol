#!/bin/bash
# Script de despliegue para servidor Ubuntu/Debian

echo "======================================================================"
echo "DESPLIEGUE DE DRILLCONTROL - SERVIDOR PRODUCCIÓN"
echo "======================================================================"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}1. Actualizando código desde repositorio...${NC}"
git pull origin main

echo -e "${YELLOW}2. Configurando archivo .env para producción...${NC}"
if [ ! -f .env ]; then
    echo "Copiando .env.production como .env"
    cp .env.production .env
    echo -e "${GREEN}✓ Archivo .env creado${NC}"
else
    echo "⚠️  .env ya existe. Asegúrate de que tenga DB_HOST=localhost"
fi

echo -e "${YELLOW}3. Activando entorno virtual...${NC}"
source venv/bin/activate

echo -e "${YELLOW}4. Instalando/actualizando dependencias...${NC}"
pip install -r requirements.txt

echo -e "${YELLOW}5. Aplicando migraciones de base de datos...${NC}"
python manage.py migrate --noinput

echo -e "${YELLOW}6. Recolectando archivos estáticos...${NC}"
python manage.py collectstatic --noinput

echo -e "${YELLOW}7. Precargando cache para optimizar rendimiento...${NC}"
python preload_cache.py

echo -e "${YELLOW}8. Verificando configuración...${NC}"
python manage.py check

echo ""
echo "======================================================================"
echo -e "${GREEN}✓ DESPLIEGUE COMPLETADO${NC}"
echo "======================================================================"
echo ""
echo "Siguiente paso: Reiniciar servicios"
echo ""
echo "  sudo systemctl restart gunicorn"
echo "  sudo systemctl restart nginx"
echo ""
echo "O si usas supervisor:"
echo "  sudo supervisorctl restart drillcontrol"
echo ""
echo "Para verificar que el servidor está corriendo:"
echo "  curl http://localhost:8000"
echo ""
