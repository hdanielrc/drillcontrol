# Sincronización Retroactiva de Brocas

## Problema

Cuando se registra un turno con una broca que **no está sincronizada desde el API**, el sistema:
- ✅ Permite guardar el turno (asume categoría BROCA por defecto)
- ✅ Calcula correctamente el metraje
- ❌ Pero el `tipo_complemento` queda vacío (NULL)

Días después, cuando esa broca **sí aparece en el API**, necesitamos actualizar esos registros históricos con la información correcta.

## Solución Automática (Recomendado)

### 🔄 Sincronización Programada a las 2 AM

El sistema ejecuta **automáticamente** cada madrugada:

1. **Sincronización de Stock** (PDD y Aditivos desde API)
2. **Sincronización de Brocas Pendientes** (actualiza registros sin datos)

#### Configurar Tarea Programada

Ejecutar como **Administrador**:

```batch
# Windows (Opción 1 - Batch)
programar_sync_stock.bat

# Windows (Opción 2 - PowerShell)
.\programar_sync_stock.ps1
```

Esto creará una tarea en el **Task Scheduler** llamada:
- `DrillControl_Sync_Stock_Brocas_API`
- Se ejecuta diariamente a las **2:00 AM**
- Logs en: `scripts/sync/logs/sync_stock_YYYYMMDD.log`

#### Verificar Tarea Programada

```batch
# Ver estado de la tarea
schtasks /Query /TN "DrillControl_Sync_Stock_Brocas_API"

# Ejecutar manualmente (para probar)
schtasks /Run /TN "DrillControl_Sync_Stock_Brocas_API"

# Desactivar temporalmente
schtasks /Change /TN "DrillControl_Sync_Stock_Brocas_API" /DISABLE

# Reactivar
schtasks /Change /TN "DrillControl_Sync_Stock_Brocas_API" /ENABLE
```

#### Ver Logs de Sincronización

```batch
# Abrir carpeta de logs
cd perforaciones_diamantinas\scripts\sync\logs

# Ver log de hoy
type sync_stock_20260131.log

# Ver últimas líneas del log
powershell -Command "Get-Content sync_stock_20260131.log -Tail 50"
```

## Solución Manual

### Comando de Sincronización

```bash
# Ver qué se actualizaría (sin hacer cambios)
python manage.py sincronizar_brocas_pendientes --dry-run

# Ejecutar sincronización real
python manage.py sincronizar_brocas_pendientes

# Sincronizar solo una serie específica
python manage.py sincronizar_brocas_pendientes --serie=409381
```

### ¿Qué hace el comando?

1. **Busca** todos los `TurnoComplemento` sin `tipo_complemento` (guardados sin API)
2. **Verifica** si ahora existe el producto en `TipoComplemento` (ya sincronizado)
3. **Actualiza** los registros con el `tipo_complemento` correcto
4. **Actualiza** el `HistorialBroca` con el tipo de producto
5. **Reporta** qué series se sincronizaron y cuáles aún están pendientes

### Ejemplo de Salida

```
======================================================================
SINCRONIZACIÓN DE BROCAS PENDIENTES
======================================================================

📊 Total de registros pendientes: 15
📦 Series únicas pendientes: 3

──────────────────────────────────────────────────────────────────────
Serie: 409381 (8 usos)
  ✓ Producto encontrado: DRILL BIT NMLC 2.370" (60.2 mm)
    Categoría: BROCA
    Código: DD-NQ-409381
    ✓ 8 registros actualizados
    ✓ HistorialBroca actualizado

──────────────────────────────────────────────────────────────────────
Serie: 412555 (5 usos)
  ⚠️  Producto no encontrado en API (aún pendiente)
    - Turno 234 (2025-12-15): 25.50m
    - Turno 238 (2025-12-16): 30.20m
    - Turno 242 (2025-12-17): 28.75m
    ... y 2 usos más

──────────────────────────────────────────────────────────────────────
Serie: 415890 (2 usos)
  ✓ Producto encontrado: DRILL BIT HQ 3.780" (96 mm)
    Categoría: BROCA
    Código: DD-HQ-415890
    ✓ 2 registros actualizados
    ✓ HistorialBroca creado

======================================================================
RESUMEN
======================================================================
✓ Series sincronizadas:     2
⚠️  Series no encontradas:    1

✓ Sincronización completada
```

## Estrategias de Uso

### 1. Sincronización Automática (Ya Configurada) ✅

La tarea programada se ejecuta **automáticamente cada madrugada** a las 2 AM:

```
02:00 AM - Inicio de Sincronización
├── Fase 1: Sincronizar Stock desde API
│   ├── Productos Diamantados (PDD)
│   └── Aditivos (ADIT)
├── Fase 2: Sincronizar Brocas Pendientes
│   ├── Buscar brocas sin tipo_complemento
│   ├── Verificar si ahora existen en TipoComplemento
│   └── Actualizar registros históricos
└── Generar log con resultados
```

**Ventajas:**
- ✅ No requiere intervención manual
- ✅ Se ejecuta en horario sin operaciones
- ✅ Mantiene todo sincronizado automáticamente
- ✅ Genera logs para auditoría

## Ventajas de este Enfoque

✅ **No pierde datos**: Los turnos se guardan inmediatamente sin esperar API
✅ **Automático**: Se sincroniza cada madrugada sin intervención manual
✅ **Actualización retroactiva**: Corrige todo el historial automáticamente
✅ **Verificación segura**: Logs detallados de cada sincronización
✅ **Granular**: Puede ejecutarse manualmente para casos específicos
✅ **Auditable**: Reportes claros de qué se sincronizó y qué falta

## Flujo de Trabajo Completo

```
Día 1: Operador registra turno
  └─> Broca 409381 no está en API
  └─> Se guarda como "Producto no sincronizado"
  └─> tipo_complemento = NULL
  └─> Metraje se calcula correctamente
  └─> Campo de serie muestra borde naranja (advertencia)

Día 2-10: Operaciones normales
  └─> Cada noche a las 2 AM se ejecuta sincronización automática
  └─> Broca 409381 aún no aparece en API
  └─> Log reporta: "Serie 409381 no encontrada"

Día 10: Proveedor actualiza inventario
  └─> Broca 409381 aparece en sistema del proveedor
  
Día 11: Sincronización Automática (2 AM)
  └─> Ejecuta: sync_stock_diario.py
  └─> Fase 1: Sincroniza productos desde API
      └─> Broca 409381 ahora está en TipoComplemento
  └─> Fase 2: Sincroniza brocas pendientes
      └─> Detecta que 409381 tiene registros sin tipo
      └─> Actualiza todos los usos históricos
      └─> Actualiza HistorialBroca
  └─> Log reporta: "Serie 409381: 8 registros actualizados"

Resultado:
  ✓ Datos históricos completos y correctos
  ✓ Reportes precisos de productos usados
  ✓ Sin pérdida de información operacional
  ✓ Todo automático, sin intervención manual
```

## Ejemplo de Log de Sincronización

```
2026-01-31 02:00:15 - INFO - ================================================================================
2026-01-31 02:00:15 - INFO - INICIO DE SINCRONIZACIÓN DIARIA DE STOCK Y BROCAS
2026-01-31 02:00:15 - INFO - Fecha y hora: 2026-01-31 02:00:15
2026-01-31 02:00:15 - INFO - ================================================================================

2026-01-31 02:00:16 - INFO - Contratos activos encontrados: 3

2026-01-31 02:01:45 - INFO - ✅ COLQUISIRI: 245 artículos PDD obtenidos
2026-01-31 02:02:12 - INFO - ✅ COLQUISIRI: 89 artículos ADIT obtenidos

2026-01-31 02:04:30 - INFO - ================================================================================
2026-01-31 02:04:30 - INFO - FASE 2: SINCRONIZACIÓN DE BROCAS PENDIENTES
2026-01-31 02:04:30 - INFO - ================================================================================

2026-01-31 02:04:31 - INFO - 📊 Total de registros pendientes: 15
2026-01-31 02:04:31 - INFO - 📦 Series únicas pendientes: 3

2026-01-31 02:04:32 - INFO - ✅ Serie 409381: 8 registros actualizados - DRILL BIT NMLC 2.370" (60.2 mm)
2026-01-31 02:04:32 - WARNING - ⚠️ Serie 412555 (5 usos): Producto no encontrado en API
2026-01-31 02:04:33 - INFO - ✅ Serie 415890: 2 registros actualizados - DRILL BIT HQ 3.780" (96 mm)

2026-01-31 02:04:33 - INFO - ================================================================================
2026-01-31 02:04:33 - INFO - RESUMEN DE SINCRONIZACIÓN
2026-01-31 02:04:33 - INFO - ================================================================================
2026-01-31 02:04:33 - INFO - 
2026-01-31 02:04:33 - INFO - 📦 STOCK:
2026-01-31 02:04:33 - INFO -   PDD exitosos: 3
2026-01-31 02:04:33 - INFO -   PDD fallidos: 0
2026-01-31 02:04:33 - INFO -   ADIT exitosos: 3
2026-01-31 02:04:33 - INFO -   ADIT fallidos: 0
2026-01-31 02:04:33 - INFO - 
2026-01-31 02:04:33 - INFO - 🔧 BROCAS PENDIENTES:
2026-01-31 02:04:33 - INFO -   Sincronizadas: 2
2026-01-31 02:04:33 - INFO -   No encontradas: 1
2026-01-31 02:04:33 - INFO -   Errores: 0
2026-01-31 02:04:33 - INFO - 
2026-01-31 02:04:33 - INFO - ================================================================================
2026-01-31 02:04:33 - INFO - FIN DE SINCRONIZACIÓN
2026-01-31 02:04:33 - INFO - ================================================================================
```

## Consultas Útiles

### Ver brocas pendientes de sincronizar
```python
from drilling.models import TurnoComplemento

pendientes = TurnoComplemento.objects.filter(
    tipo_complemento__isnull=True
).values('codigo_serie').distinct()

print(f"Series pendientes: {pendientes.count()}")
for p in pendientes:
    print(f"  - {p['codigo_serie']}")
```

### Ver usos de una serie sin sincronizar
```python
serie = "409381"
usos = TurnoComplemento.objects.filter(
    codigo_serie=serie,
    tipo_complemento__isnull=True
).select_related('turno')

print(f"Usos de {serie} sin sincronizar: {usos.count()}")
for uso in usos:
    print(f"  Turno {uso.turno_id} - {uso.turno.fecha}: {uso.metros_turno_calc}m")
```

## Notas Importantes

⚠️ **El comando es seguro**: Solo actualiza registros que tienen `tipo_complemento = NULL`

⚠️ **No afecta metrajes**: Los metrajes ya calculados se mantienen intactos

⚠️ **Usa transacciones**: Si algo falla, se revierte todo para esa serie

⚠️ **Actualiza HistorialBroca**: Asegura que el historial tenga el tipo correcto

## Alternativa: Validación al Guardar (Opcional)

Si prefieres **prevenir** que se guarden brocas sin API en lugar de sincronizar después, puedes modificar `crear_turno_completo` en `views.py` para validar que todas las series existan en TipoComplemento antes de guardar.

Pero esto tiene la desventaja de **bloquear** la operación si el API no está actualizado.

## Recomendación Final

✅ **Usar el enfoque actual** (permitir guardar + sincronizar después):
- Más flexible y operativo
- No bloquea el trabajo de campo
- Fácil de mantener sincronizado
- Un comando resuelve todo el historial

La sincronización retroactiva es la mejor práctica para sistemas que dependen de APIs externas que pueden tener retrasos.
