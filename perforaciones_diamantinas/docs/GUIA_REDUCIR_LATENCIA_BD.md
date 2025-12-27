# Guía para Reducir Latencia de Red PostgreSQL (Neon.tech)

## 🔴 Problema Actual

**Base de datos:** Neon.tech PostgreSQL  
**Ubicación:** AWS sa-east-1 (São Paulo, Brasil)  
**Host:** `ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech`  
**Latencia actual:** ~160ms por query  
**Latencia esperada:** <50ms

---

## 🎯 Soluciones Ordenadas por Impacto

### 1. **Connection Pooling Local con PgBouncer** ⭐⭐⭐⭐⭐
**Impacto:** Alto - Reduce latencia en 30-50ms  
**Complejidad:** Media  
**Costo:** Gratis

PgBouncer actúa como proxy local que mantiene conexiones persistentes abiertas.

#### Instalación Windows

**Opción A: Instalador oficial**
```bash
# Descargar de: https://www.pgbouncer.org/downloads.html
# O usar chocolatey:
choco install pgbouncer
```

**Opción B: Docker (Recomendado)**
```bash
docker run -d --name pgbouncer \
  -p 6432:6432 \
  -e DATABASE_URL="postgres://neondb_owner:npg_Athe0VmqL6cI@ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech:5432/neondb?sslmode=require" \
  -e POOL_MODE=transaction \
  -e MAX_CLIENT_CONN=100 \
  -e DEFAULT_POOL_SIZE=20 \
  edoburu/pgbouncer
```

#### Configurar Django para usar PgBouncer

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'neondb',
        'USER': 'neondb_owner',
        'PASSWORD': 'npg_Athe0VmqL6cI',
        'HOST': 'localhost',  # ← Cambiar a localhost
        'PORT': '6432',       # ← Puerto de PgBouncer
        'CONN_MAX_AGE': 0,    # ← Dejar que PgBouncer maneje el pooling
        'OPTIONS': {
            'sslmode': 'disable',  # ← No SSL con PgBouncer local
        },
    }
}
```

**Mejora esperada:** 30-50ms menos por query

---

### 2. **Optimizar Configuración de Neon Pooler** ⭐⭐⭐⭐
**Impacto:** Medio - Reduce latencia en 20-30ms  
**Complejidad:** Baja  
**Costo:** Gratis

Neon ya está usando su pooler interno, pero podemos optimizarlo.

#### En `settings.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'neondb',
        'USER': 'neondb_owner',
        'PASSWORD': 'npg_Athe0VmqL6cI',
        'HOST': 'ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
        'DISABLE_SERVER_SIDE_CURSORS': True,  # ← Agregar esto
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 5,  # ← Reducir de 10 a 5
            'keepalives': 1,       # ← Mantener conexión viva
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        },
    }
}
```

---

### 3. **Usar django-db-connection-pool** ⭐⭐⭐⭐
**Impacto:** Medio-Alto  
**Complejidad:** Baja  
**Costo:** Gratis

Esta librería implementa connection pooling nativo en Python.

#### Instalación

```bash
pip install django-db-connection-pool
```

#### Configurar en `settings.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'dj_db_conn_pool.backends.postgresql',  # ← Cambiar engine
        'NAME': 'neondb',
        'USER': 'neondb_owner',
        'PASSWORD': 'npg_Athe0VmqL6cI',
        'HOST': 'ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,           # Conexiones en el pool
            'MAX_OVERFLOW': 10,        # Conexiones extra en picos
            'RECYCLE': 3600,           # Reciclar conexión cada hora
            'POOL_PRE_PING': True,     # Verificar conexión antes de usar
        }
    }
}
```

#### Agregar a `requirements.txt`
```
django-db-connection-pool==1.2.4
```

**Mejora esperada:** 40-60ms menos por query

---

### 4. **Migrar a Región más Cercana** ⭐⭐⭐⭐⭐
**Impacto:** CRÍTICO - Reduce latencia en 100-120ms  
**Complejidad:** Alta  
**Costo:** Variable

Si tu servidor está en Perú, São Paulo (sa-east-1) está a ~3000km de distancia.

#### Opciones de Neon.tech por región:

| Región | Latencia desde Perú | Recomendación |
|--------|---------------------|---------------|
| **us-east-1** (Virginia) | ~120ms | ⚠️ Lejos |
| **us-west-2** (Oregon) | ~100ms | 🟡 Mejor |
| **sa-east-1** (São Paulo) | **~160ms** | 🔴 **Actual** |
| **eu-central-1** (Frankfurt) | ~200ms | ❌ Muy lejos |

#### Pasos para migrar:

1. **Crear nuevo proyecto Neon en región más cercana**
   - Login en https://console.neon.tech
   - Create Project → Seleccionar región us-west-2
   
2. **Exportar datos actuales**
```bash
pg_dump -h ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech \
        -U neondb_owner \
        -d neondb \
        -F c \
        -f backup_neondb.dump
```

3. **Importar a nueva base de datos**
```bash
pg_restore -h <nuevo-host>.us-west-2.aws.neon.tech \
           -U <nuevo-user> \
           -d <nueva-db> \
           -v backup_neondb.dump
```

4. **Actualizar settings.py** con nuevos credenciales

**Mejora esperada:** 100-120ms menos (latencia final: ~40-60ms)

---

### 5. **Postgres Local + Replicación** ⭐⭐⭐⭐⭐
**Impacto:** MÁXIMO - Latencia <5ms  
**Complejidad:** Muy Alta  
**Costo:** Medio (requiere servidor)

#### Opción A: PostgreSQL Local Read Replica

**Ventajas:**
- Latencia <5ms para lecturas
- 95% de queries son SELECT

**Desventajas:**
- Escrituras siguen con latencia alta
- Requiere sincronización

#### Configuración:

1. **Instalar PostgreSQL localmente**
```bash
# Windows
choco install postgresql14

# Iniciar servicio
net start postgresql-x64-14
```

2. **Configurar replicación lógica desde Neon**
```sql
-- En Neon (maestro)
CREATE PUBLICATION drillcontrol_pub FOR ALL TABLES;

-- En PostgreSQL local (réplica)
CREATE SUBSCRIPTION drillcontrol_sub 
CONNECTION 'host=ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech 
            port=5432 dbname=neondb user=neondb_owner password=npg_Athe0VmqL6cI' 
PUBLICATION drillcontrol_pub;
```

3. **Configurar Django con DB router**
```python
# settings.py
DATABASES = {
    'default': {  # Escrituras -> Neon
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech',
        # ... resto de config
    },
    'replica': {  # Lecturas -> Local
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'localhost',
        'PORT': '5432',
        'NAME': 'neondb_replica',
        # ... resto de config
    }
}

DATABASE_ROUTERS = ['drilling.routers.ReplicaRouter']
```

**Mejora esperada:** Lecturas <5ms, escrituras siguen con 160ms

---

### 6. **Migrar a PostgreSQL Completamente Local** ⭐⭐⭐⭐⭐
**Impacto:** MÁXIMO  
**Complejidad:** Media  
**Costo:** Bajo-Medio

#### Si tienes servidor Windows/Linux disponible:

1. **Instalar PostgreSQL localmente**
```bash
# Windows
choco install postgresql14

# Linux
sudo apt install postgresql-14
```

2. **Restaurar backup**
```bash
pg_restore -h localhost -U postgres -d drillcontrol backup_neondb.dump
```

3. **Actualizar settings.py**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'drillcontrol',
        'USER': 'postgres',
        'PASSWORD': 'tu_password_local',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
    }
}
```

4. **Configurar backup automático a Neon** (disaster recovery)
```bash
# Cron job para backup diario
0 2 * * * pg_dump -h localhost -U postgres drillcontrol | \
          psql -h ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech \
               -U neondb_owner -d neondb
```

**Mejora esperada:** Latencia <5ms (97% más rápido)

---

## 📊 Comparación de Soluciones

| Solución | Latencia Final | Reducción | Complejidad | Costo | Recomendación |
|----------|---------------|-----------|-------------|-------|---------------|
| **Actual** | 160ms | - | - | - | 🔴 |
| PgBouncer | 110-130ms | 30-50ms | Media | Gratis | 🟡 |
| django-db-conn-pool | 100-120ms | 40-60ms | Baja | Gratis | 🟢 |
| Neon us-west-2 | 40-60ms | 100-120ms | Alta | Variable | 🟢 |
| PG Local + Réplica | <5ms (reads) | 155ms | Muy Alta | Medio | 🟡 |
| **PG Completamente Local** | **<5ms** | **155ms** | **Media** | **Bajo** | **🟢🟢🟢** |

---

## 🚀 Plan de Acción Recomendado

### Fase 1: Rápido (Hoy mismo) ⚡
1. Instalar `django-db-connection-pool`
2. Optimizar configuración de Neon
3. **Mejora esperada: 40-60ms (latencia final: ~100ms)**

### Fase 2: Corto Plazo (Esta semana) 📅
1. Evaluar PgBouncer con Docker
2. Combinar con django-db-connection-pool
3. **Mejora esperada: 70-90ms (latencia final: ~70ms)**

### Fase 3: Mediano Plazo (Próximo mes) 🎯
1. Migrar a PostgreSQL local
2. Configurar backup automático a Neon (disaster recovery)
3. **Mejora esperada: 155ms (latencia final: <5ms)** ✨

---

## 📝 Implementación Inmediata (Fase 1)

### 1. Instalar django-db-connection-pool

```bash
cd c:\Users\PERDLAP140.VILBRAGROUP\Documents\drillcontrol\drillcontrol\perforaciones_diamantinas
.\venv\Scripts\pip.exe install django-db-connection-pool
```

### 2. Modificar settings.py

```python
DATABASES = {
    'default': {
        'ENGINE': 'dj_db_conn_pool.backends.postgresql',
        'NAME': env('DB_NAME', default='neondb'),
        'USER': env('DB_USER', default='neondb_owner'),
        'PASSWORD': env('DB_PASSWORD', default='npg_Athe0VmqL6cI'),
        'HOST': env('DB_HOST', default='ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech'),
        'PORT': env('DB_PORT', default='5432'),
        'DISABLE_SERVER_SIDE_CURSORS': True,
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 5,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        },
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 10,
            'RECYCLE': 3600,
            'POOL_PRE_PING': True,
        }
    }
}
```

### 3. Probar

```bash
python test_performance_carga.py
```

**Latencia esperada después de Fase 1:** ~100ms (38% más rápido)

---

## ⚠️ Notas Importantes

1. **Neon Free Tier** tiene límites:
   - Compute: 0.25 vCPU
   - Storage: 512 MB
   - Branches: 10
   - Si estás cerca del límite, considera upgrade o migración local

2. **Connection Limits:**
   - Neon Pooler: 100 conexiones simultáneas en Free tier
   - Con PgBouncer local puedes optimizar esto

3. **Backup antes de cambios:**
```bash
python manage.py dumpdata > backup_$(date +%Y%m%d).json
```

---

## 📞 Soporte

Si tienes dudas sobre alguna implementación, pregúntame y te ayudo paso a paso.

**Recomendación final:** Empezar con Fase 1 (django-db-connection-pool) hoy mismo, y planificar migración a PostgreSQL local para máximo rendimiento.
