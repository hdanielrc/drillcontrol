# Guía de Sincronización - Mejores Prácticas

## ⚠️ Cambio Importante: Sincronización Manual/Programada

### ❌ Lo que NO hace el sistema:
- **NO sincroniza automáticamente al iniciar el servidor**
- **NO sincroniza en cada reinicio durante desarrollo**

### ✅ Lo que SÍ hace el sistema:
- **Sincronización manual bajo demanda**
- **Sincronización programada diaria** (2:00 AM)

## 🎯 Estrategia de Sincronización Recomendada

### Configuración Inicial (Una sola vez)

#### 1. Configurar credenciales API
En `settings.py`:
```python
VILBRAGROUP_API_TOKEN = 'cff25a36-682a-4570-ad84-aaaabffc89bf'
CENTRO_COSTO_DEFAULT = '000003'
```

#### 2. Asignar código de centro de costo a cada contrato
- Via admin: `/admin/drilling/contrato/`
- Editar cada contrato y agregar `codigo_centro_costo`

#### 3. Primera sincronización manual
```bash
python manage.py sync_all_contracts --verbose
```

#### 4. Configurar sincronización diaria automática
```bash
python setup_sync_schedule.py
```

### Uso Diario

#### Sincronización Automática Diaria
- **Hora**: 2:00 AM (configurable)
- **Frecuencia**: Una vez al día
- **Contratos**: Todos los activos con `codigo_centro_costo`
- **Log**: Ver `sync_log.txt`

#### Sincronización Manual (cuando necesites)
```bash
# Todos los contratos
python manage.py sync_all_contracts

# Solo un contrato específico
python manage.py sync_productos_diamantados --contrato-id=1
python manage.py sync_aditivos --contrato-id=1

# Ver qué cambiaría sin aplicar
python manage.py sync_all_contracts --dry-run --verbose
```

### Nuevo Contrato

Cuando agregas un nuevo contrato:

```bash
# 1. Crear contrato en admin con codigo_centro_costo

# 2. Sincronizar inmediatamente
python manage.py sync_productos_diamantados --contrato-id=5
python manage.py sync_aditivos --contrato-id=5

# 3. La próxima sincronización diaria lo incluirá automáticamente
```

## 📊 Rendimiento y Optimización

### Tiempos Esperados
- **CONDESTABLE** (~258 PDD + 10 ADIT): ~10-15 segundos
- **Contrato promedio** (~100 productos): ~5 segundos
- **Todos los contratos** (3-5 contratos): ~30-45 segundos

### Optimizaciones Implementadas
- ✅ Pre-carga de series/códigos existentes (evita N consultas)
- ✅ Transacciones por producto (integridad)
- ✅ Progreso cada 50 productos (feedback)
- ✅ Sincronización silenciosa en segundo plano

### Por qué NO sincronizar al iniciar servidor

❌ **Problemas de sincronización automática al inicio:**
1. Retrasa inicio del servidor (10-30 segundos)
2. Se ejecuta cada vez que reinicias en desarrollo
3. Carga innecesaria en la API de Vilbragroup
4. No es necesario (datos no cambian tanto)

✅ **Ventajas de sincronización programada:**
1. Servidor inicia instantáneamente
2. API se consulta solo 1 vez al día
3. Datos siempre actualizados (sincronización nocturna)
4. Control total sobre cuándo sincronizar

## 🔧 Configuración de Sincronización Diaria

### Windows - Programador de Tareas

```bash
python setup_sync_schedule.py
```

El script crea:
- **Archivo BAT**: `sync_daily.bat`
- **Instrucciones**: Para agregar al Programador de Tareas

**Manualmente:**
1. Win+R → `taskschd.msc`
2. Crear tarea básica
3. Nombre: "Sincronización Drilling Control"
4. Desencadenador: Diariamente a las 2:00 AM
5. Acción: Ejecutar `sync_daily.bat`

### Linux/Mac - Cron

```bash
python setup_sync_schedule.py
```

El script crea:
- **Archivo SH**: `sync_daily.sh`
- **Línea cron**: Para agregar a crontab

**Manualmente:**
```bash
# Editar crontab
crontab -e

# Agregar línea (ejecutar a las 2:00 AM diariamente)
0 2 * * * cd /ruta/proyecto && python manage.py sync_all_contracts >> sync_log.txt 2>&1
```

## 📝 Monitoreo y Logs

### Ver historial de sincronizaciones
```bash
# Windows
type sync_log.txt

# Linux/Mac
cat sync_log.txt
```

### Formato del log
```
Sincronización completada: 2025-11-17 02:00:15
Contratos sincronizados: 3
Productos: 425 total
Aditivos: 28 total
```

### Verificar última sincronización
```python
from drilling.models import TipoComplemento
from django.db.models import Max

ultima = TipoComplemento.objects.aggregate(Max('created_at'))
print(f"Última sincronización: {ultima}")
```

## 🐛 Troubleshooting

### Sincronización muy lenta
```bash
# Ver qué está pasando
python manage.py sync_all_contracts --verbose

# Probar sin aplicar cambios
python manage.py sync_all_contracts --dry-run
```

### API no responde
```bash
# Probar conexión
python test_api_debug.py

# Verificar token en settings.py
```

### Productos no aparecen en formularios
1. Verificar usuario tiene `contrato` asignado
2. Verificar productos tienen `contrato` correcto
3. Para PDD: solo estado `NUEVO` aparecen en selectores

```python
# Verificar en shell
from drilling.models import TipoComplemento, CustomUser

usuario = CustomUser.objects.get(username='operador_condestable')
productos = TipoComplemento.objects.filter(
    contrato=usuario.contrato,
    estado='NUEVO'
)
print(f"Productos disponibles: {productos.count()}")
```

## 📚 Resumen de Comandos

```bash
# Sincronización completa (todos los contratos)
python manage.py sync_all_contracts

# Sincronización con detalles
python manage.py sync_all_contracts --verbose

# Simulación (sin cambios)
python manage.py sync_all_contracts --dry-run

# Solo productos diamantados de un contrato
python manage.py sync_productos_diamantados --contrato-id=1

# Solo aditivos de un contrato
python manage.py sync_aditivos --contrato-id=1

# Configurar programación diaria
python setup_sync_schedule.py

# Verificar conexión API
python test_api_debug.py

# Verificar datos sincronizados
python verificar_datos.py
```

## ✅ Checklist de Implementación

- [ ] Token API configurado en `settings.py`
- [ ] Código centro de costo asignado a cada contrato
- [ ] Primera sincronización manual ejecutada
- [ ] Sincronización diaria configurada (cron/task scheduler)
- [ ] `sync_log.txt` está siendo generado
- [ ] Usuarios pueden ver productos en formularios
- [ ] Productos filtran correctamente por contrato

## 💡 Consejos

1. **Desarrollo**: Sincroniza manualmente solo cuando necesites datos frescos
2. **Producción**: Deja que la sincronización diaria haga su trabajo
3. **Nuevos datos**: Si necesitas datos inmediatamente, ejecuta manualmente
4. **Monitoreo**: Revisa `sync_log.txt` semanalmente
5. **Backup**: La sincronización no elimina datos, solo actualiza/crea
