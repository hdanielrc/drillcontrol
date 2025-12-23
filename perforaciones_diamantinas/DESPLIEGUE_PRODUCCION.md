# 🚀 GUÍA DE DESPLIEGUE A PRODUCCIÓN
## Dominio: http://drillcontrol.rockdrill.site/

---

## ✅ CONFIGURACIONES COMPLETADAS EN DJANGO

### 1. **Configuración de Dominio**
- ✅ `ALLOWED_HOSTS` incluye: `drillcontrol.rockdrill.site`
- ✅ `CSRF_TRUSTED_ORIGINS` incluye:
  - `http://drillcontrol.rockdrill.site`
  - `https://drillcontrol.rockdrill.site`

### 2. **Seguridad para Producción**
- ✅ Configuraciones de seguridad automáticas cuando `DEBUG=False`:
  - Cookies solo por HTTPS
  - HSTS habilitado (fuerza HTTPS por 1 año)
  - Protección XSS
  - Protección contra clickjacking
  - SSL redirect automático

### 3. **Archivos Estáticos**
- ✅ `STATIC_ROOT` configurado: `/staticfiles`
- ✅ `STATIC_URL` configurado: `/static/`
- ✅ Hash de archivos habilitado en producción

---

## ⚠️ TAREAS PENDIENTES (LADO SERVIDOR/HOSTING)

### 🔴 **CRÍTICO - Antes de Desplegar**

#### 1. **Configurar DNS**
El dominio `drillcontrol.rockdrill.site` debe apuntar a tu servidor:
```
Tipo A Record:
- Host: drillcontrol.rockdrill.site
- IP: [IP_DE_TU_SERVIDOR]
```

#### 2. **Instalar Certificado SSL (HTTPS)**
**Recomendado: Let's Encrypt (Gratis)**
```bash
# En el servidor con Ubuntu/Debian:
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d drillcontrol.rockdrill.site
```

#### 3. **Configurar Servidor Web (Nginx)**
Crear archivo: `/etc/nginx/sites-available/drillcontrol`

```nginx
upstream django_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name drillcontrol.rockdrill.site;
    
    # Redirigir HTTP a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name drillcontrol.rockdrill.site;
    
    # Certificados SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/drillcontrol.rockdrill.site/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/drillcontrol.rockdrill.site/privkey.pem;
    
    # Configuraciones SSL recomendadas
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Archivos estáticos
    location /static/ {
        alias /ruta/a/tu/proyecto/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Archivos media
    location /media/ {
        alias /ruta/a/tu/proyecto/media/;
        expires 7d;
    }
    
    # Proxy a Django
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts para operaciones largas
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Límites de tamaño de upload
    client_max_body_size 10M;
}
```

**Activar configuración:**
```bash
sudo ln -s /etc/nginx/sites-available/drillcontrol /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar configuración
sudo systemctl reload nginx
```

#### 4. **Configurar Gunicorn (Servidor WSGI)**
Instalar y configurar:
```bash
pip install gunicorn

# Crear servicio systemd: /etc/systemd/system/drillcontrol.service
```

**Archivo de servicio:**
```ini
[Unit]
Description=DrillControl Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/ruta/a/tu/proyecto/perforaciones_diamantinas
Environment="PATH=/ruta/a/tu/venv/bin"
ExecStart=/ruta/a/tu/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 60 \
    --access-logfile /var/log/drillcontrol/access.log \
    --error-logfile /var/log/drillcontrol/error.log \
    perforaciones_diamantinas.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Iniciar servicio:**
```bash
sudo systemctl daemon-reload
sudo systemctl start drillcontrol
sudo systemctl enable drillcontrol
sudo systemctl status drillcontrol
```

#### 5. **Colectar Archivos Estáticos**
```bash
cd /ruta/a/tu/proyecto/perforaciones_diamantinas
source ../venv/bin/activate
python manage.py collectstatic --noinput
```

#### 6. **Cambiar a Modo Producción**
Editar `settings.py` en el servidor:
```python
DEBUG = False  # CAMBIAR DE True A False
```

O mejor, usar variables de entorno en `.env`:
```env
DEBUG=False
SECRET_KEY=tu-secret-key-super-segura-generada-aleatoriamente
```

#### 7. **Generar SECRET_KEY Segura**
```python
# En Python:
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

Copiar el resultado al `.env` del servidor.

---

### 🟡 **OPCIONAL - Mejoras de Performance**

#### 8. **Configurar PostgreSQL en Servidor Local**
En vez de conectar a IP remota `138.197.203.247`, instalar PostgreSQL localmente:
```bash
sudo apt install postgresql postgresql-contrib
```

Cambiar en `.env`:
```env
DB_HOST=localhost  # En vez de 138.197.203.247
```

#### 9. **Instalar Redis para Caché**
```bash
sudo apt install redis-server
```

Cambiar en `settings.py`:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

#### 10. **Configurar Backup Automático**
Crear script de backup de PostgreSQL:
```bash
#!/bin/bash
# /usr/local/bin/backup_drillcontrol.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/drillcontrol"
pg_dump -U drilldb drilldb | gzip > $BACKUP_DIR/drilldb_$DATE.sql.gz

# Mantener solo últimos 7 días
find $BACKUP_DIR -name "drilldb_*.sql.gz" -mtime +7 -delete
```

Agregar a crontab:
```bash
0 2 * * * /usr/local/bin/backup_drillcontrol.sh
```

---

## 📋 CHECKLIST DE DESPLIEGUE

### Pre-Despliegue
- [ ] DNS configurado y propagado
- [ ] Servidor con Ubuntu/Debian preparado
- [ ] Python 3.11+ instalado
- [ ] PostgreSQL instalado (local o acceso remoto)
- [ ] Nginx instalado

### Despliegue
- [ ] Código del proyecto copiado al servidor
- [ ] Entorno virtual creado e instalado `requirements.txt`
- [ ] Archivo `.env` creado con configuraciones de producción
- [ ] `DEBUG=False` en `.env`
- [ ] `SECRET_KEY` generada y configurada
- [ ] Migraciones aplicadas: `python manage.py migrate`
- [ ] Usuario admin creado: `python manage.py createsuperuser`
- [ ] Archivos estáticos colectados: `python manage.py collectstatic`
- [ ] Gunicorn configurado y corriendo
- [ ] Nginx configurado y corriendo
- [ ] Certificado SSL instalado (Let's Encrypt)
- [ ] Firewall configurado (puertos 80, 443, 5432)

### Post-Despliegue
- [ ] Probar acceso a https://drillcontrol.rockdrill.site
- [ ] Verificar login de usuarios
- [ ] Probar carga de archivos
- [ ] Verificar conexión a API externa
- [ ] Configurar monitoreo de logs
- [ ] Configurar backups automáticos
- [ ] Documentar credenciales y accesos

---

## 🔒 SEGURIDAD - VARIABLES DE ENTORNO

Crear archivo `.env` en el servidor con:

```env
# Django
DEBUG=False
SECRET_KEY=tu-secret-key-generada-aleatoriamente-de-50-caracteres

# Database
DB_NAME=drilldb
DB_USER=drilldb
DB_PASSWORD=password-segura-de-produccion
DB_HOST=localhost
DB_PORT=5432

# Hosts
ALLOWED_HOSTS=drillcontrol.rockdrill.site
CSRF_TRUSTED_ORIGINS=https://drillcontrol.rockdrill.site

# API Externa
VILBRAGROUP_API_TOKEN=cff25a36-682a-4570-ad84-aaaabffc89bf
CENTRO_COSTO_DEFAULT=000003

# Email (Opcional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@vilbragroup.com
EMAIL_HOST_PASSWORD=tu-password-de-app
DEFAULT_FROM_EMAIL=noreply@vilbragroup.com
```

---

## 🚨 COMANDOS ÚTILES EN SERVIDOR

### Ver logs en tiempo real:
```bash
# Logs de Gunicorn
sudo journalctl -u drillcontrol -f

# Logs de Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Reiniciar servicios:
```bash
sudo systemctl restart drillcontrol  # Django
sudo systemctl reload nginx          # Nginx
```

### Verificar estado:
```bash
sudo systemctl status drillcontrol
sudo systemctl status nginx
sudo systemctl status postgresql
```

---

## 📞 SOPORTE

Si encuentras problemas:
1. Revisar logs de Gunicorn y Nginx
2. Verificar que DEBUG=False en producción
3. Verificar permisos de archivos (www-data)
4. Verificar que PostgreSQL acepta conexiones
5. Verificar firewall no bloquea puertos 80/443

---

**Última actualización:** 23 de diciembre, 2025
