# Centros de Costo DDH - Diamond Drill Holes

## Descripción

Este documento lista todos los centros de costo configurados para el servicio DDH (Diamond Drill Holes - Perforaciones Diamantinas) que se sincronizan automáticamente desde la API de Vilbragroup TIC.

## Centros de Costo DDH

Los siguientes 19 centros de costo están configurados en `settings.CENTROS_COSTO_DDH`:

| Código | Nombre del Contrato |
|--------|---------------------|
| 000002 | CTR AMERICANA - DDH |
| 000003 | CTR CONDESTABLE - DDH |
| 000004 | CTR CHUNGAR - DDH |
| 000023 | CTR MOROCOCHA - DDH |
| 000029 | CTR TICLIO - DDH |
| 000032 | CTR CERRO - DDH |
| 000033 | CTR ANDAYCHAGUA - DDH |
| 000035 | CTR SAN CRISTÓBAL - DDH |
| 000036 | CTR CATALINA H. - DDH |
| 000037 | CTR COLQUISIRI - DDH |
| 000038 | CTR COBRIZA - DDH |
| 000044 | CTR LA ESTRELLA - DDH |
| 000049 | CTR BATEAS - DDH |
| 000051 | CTR RAURA - DDH |
| 000053 | CTR YAULIYACU - DDH |
| 000055 | CTR YUMPAG - DDH |
| 000056 | CTR INMACULADA - DDH |
| 000057 | CTR ROMINA - DDH |
| 000058 | CTR CUCULI - DDH |

## Otros Servicios

La empresa también presta otros servicios identificados con diferentes sufijos:

- **GEOT**: Servicios Geotécnicos
  - Ejemplo: 000101 - CTR CATALINA H. - GEOT
  - Ejemplo: 000103 - CTR COBRIZA - GEOT

- **WDTH**: Water Detection Through Holes (Detección de agua)
  - Ejemplo: 000201 - CTR COLQUIJIRCA - WDTH

- **VCR**: Vacuum Core Recovery (Recuperación de núcleo al vacío)
  - Ejemplo: 000202 - CTR CONDESTABLE - VCR

- **SGEOL**: Servicios Geológicos
  - Ejemplo: 000401 - CTR RAURA - SGEOL
  - Ejemplo: 000402 - CTR SAN CRISTÓBAL - SGEOL
  - Ejemplo: 000403 - CTR ANDAYCHAGUA - SGEOL
  - Ejemplo: 000404 - CTR TICLIO - SGEOL
  - Ejemplo: 000405 - CTR ANIMON - SGEOL
  - Ejemplo: 000406 - CTR COBRIZA - SGEOL
  - Ejemplo: 000407 - CTR CERRO - SGEOL
  - Ejemplo: 000408 - CTR YAULIYACU - SGEOL
  - Ejemplo: 000409 - CTR ROMINA - SGEOL
  - Ejemplo: 000410 - CTR CUCULI - SGEOL

> **Nota**: Por ahora, el sistema de sincronización automática solo procesa contratos DDH. 
> Los demás servicios pueden agregarse en el futuro según necesidad.

## Sincronización Automática

### Sincronización Manual de un Centro Específico

```bash
# Sincronizar solo un centro de costo
python manage.py sincronizar_abastecimientos 202602 --centro-costo 000003 --familia PDD

# Con información detallada
python manage.py sincronizar_abastecimientos 202602 --centro-costo 000003 --familia PDD --verbose
```

### Sincronización Masiva de Todos los Centros DDH

```bash
# Sincronizar automáticamente los 19 centros DDH
python manage.py sincronizar_abastecimientos 202602 --todos-ddh --familia PDD

# Con información detallada por centro
python manage.py sincronizar_abastecimientos 202602 --todos-ddh --familia PDD --verbose
```

### Sincronización Automática Diaria

El script `sync_abastecimientos_diario.bat` se ejecuta automáticamente a las 4:00 AM y sincroniza:

1. **Mes actual**: Todos los centros DDH del periodo actual
2. **Mes anterior**: Todos los centros DDH del mes anterior (para datos rezagados)

Para programar la tarea automática:

```batch
# Ejecutar con permisos de administrador
.\programar_sync_abastecimientos.bat
```

## Configuración en Código

### settings.py

```python
# Centros de costo DDH para sincronización automática
CENTROS_COSTO_DDH = [
    '000002',  # CTR AMERICANA - DDH
    '000003',  # CTR CONDESTABLE - DDH
    '000004',  # CTR CHUNGAR - DDH
    '000023',  # CTR MOROCOCHA - DDH
    '000029',  # CTR TICLIO - DDH
    '000032',  # CTR CERRO - DDH
    '000033',  # CTR ANDAYCHAGUA - DDH
    '000035',  # CTR SAN CRISTÓBAL - DDH
    '000036',  # CTR CATALINA H. - DDH
    '000037',  # CTR COLQUISIRI - DDH
    '000038',  # CTR COBRIZA - DDH
    '000044',  # CTR LA ESTRELLA - DDH
    '000049',  # CTR BATEAS - DDH
    '000051',  # CTR RAURA - DDH
    '000053',  # CTR YAULIYACU - DDH
    '000055',  # CTR YUMPAG - DDH
    '000056',  # CTR INMACULADA - DDH
    '000057',  # CTR ROMINA - DDH
    '000058',  # CTR CUCULI - DDH
]
```

### Modelo Contrato

Cada contrato en la base de datos tiene un campo `codigo_centro_costo` que debe coincidir con los códigos listados arriba:

```python
class Contrato(models.Model):
    codigo_centro_costo = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name='Código Centro de Costo',
        help_text='Código del centro de costo para APIs de Vilbragroup (ej: 000003)'
    )
```

## Agregar Nuevos Centros DDH

Para agregar un nuevo centro de costo DDH:

1. **Actualizar settings.py**: Agregar el código a `CENTROS_COSTO_DDH`
2. **Verificar en BD**: Asegurarse que el contrato existe con el código correcto
3. **Probar sincronización**: Ejecutar sincronización manual para el nuevo centro

```bash
# Probar nuevo centro
python manage.py sincronizar_abastecimientos 202602 --centro-costo 000XXX --familia PDD --verbose
```

## Agregar Otros Servicios (GEOT, WDTH, VCR, SGEOL)

Para habilitar sincronización de otros servicios en el futuro:

1. Crear nueva lista en settings.py (ej: `CENTROS_COSTO_GEOT`)
2. Crear nuevo método en `AbastecimientoService` (ej: `sincronizar_todos_geot()`)
3. Agregar opción al management command (ej: `--todos-geot`)
4. Actualizar scripts de sincronización automática

## Logs y Monitoreo

Los logs de sincronización se guardan en:

```
logs/sync_abastecimientos_YYYYMM.log
```

Para revisar el último resultado:

```bash
# Ver últimas líneas del log del mes actual
type logs\sync_abastecimientos_202602.log | more

# Buscar errores
findstr /i "error" logs\sync_abastecimientos_202602.log
```

## Preguntas Frecuentes

### ¿Por qué algunos contratos aparecen duplicados?

Algunos clientes contratan múltiples servicios. Por ejemplo:
- **SAN CRISTÓBAL - DDH** (000035): Perforación diamantina
- **SAN CRISTÓBAL - SGEOL** (000402): Servicios geológicos

Cada servicio se trata independientemente con su propio centro de costo.

### ¿Qué pasa si un centro no tiene datos?

La sincronización continúa sin problemas. El centro aparecerá con 0 registros en el reporte.

### ¿Cómo verifico que todos los centros se sincronizaron?

Usar el flag `--verbose` para ver el detalle:

```bash
python manage.py sincronizar_abastecimientos 202602 --todos-ddh --familia PDD --verbose
```

Esto mostrará estadísticas por cada centro de costo procesado.
