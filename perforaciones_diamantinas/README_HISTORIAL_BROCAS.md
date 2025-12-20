# Sistema de Historial de Brocas Diamantadas

## Descripción

Sistema automático para hacer seguimiento del ciclo de vida completo de cada broca diamantada, acumulando métricas de uso y controlando estados.

## Arquitectura

### 1. TurnoComplemento (Detalle por turno)
- Registra cada uso individual de una broca en un turno
- Campos: `codigo_serie`, `metros_inicio`, `metros_fin`, `metros_turno_calc`
- **Actualización automática**: Al guardar, sincroniza con `HistorialBroca`

### 2. HistorialBroca (Vista consolidada)
- Un registro por serie única de broca
- Acumula automáticamente el metraje total
- Controla estado de vida útil
- Campos clave:
  - `metraje_acumulado`: Total de metros perforados
  - `numero_usos`: Cantidad de turnos donde se usó
  - `estado`: NUEVA → EN_USO → DESGASTADA → QUEMADA
  - `fecha_primer_uso`, `fecha_ultimo_uso`

## Instalación

### 1. Crear migración
```bash
python manage.py makemigrations drilling -n historial_broca
```

### 2. Aplicar migración
```bash
python manage.py migrate drilling
```

### 3. Cargar productos desde API (primera vez)
```bash
python cargar_productos_api.py
```

### 4. Sincronizar historial (si hay datos existentes)
```bash
python sincronizar_historial_brocas.py
```

## Uso

### Automático
El historial se actualiza **automáticamente** cada vez que se guarda un `TurnoComplemento`:
- Se suma el metraje al acumulado
- Se incrementa el contador de usos
- Se actualiza la fecha de último uso
- Se cambia el estado de NUEVA a EN_USO

### Consultas

#### Consultar broca específica
```bash
python consultar_historial_broca.py 409381
```

Muestra:
- Información general (producto, estado, contrato)
- Métricas (metraje acumulado, número de usos, promedio)
- Fechas (primer uso, último uso, días sin usar)
- Historial detallado de todos los usos

#### Listar brocas activas
```bash
python consultar_historial_broca.py
```

Muestra top 50 brocas activas ordenadas por metraje.

### Desde Django ORM

```python
from drilling.models import HistorialBroca

# Obtener broca por serie
broca = HistorialBroca.objects.get(serie='409381')

# Ver métricas
print(f"Metraje: {broca.metraje_acumulado} m")
print(f"Usos: {broca.numero_usos}")
print(f"Promedio: {broca.metraje_promedio_por_uso()} m/uso")

# Ver historial detallado
for uso in broca.obtener_historial_detallado():
    print(f"{uso.turno.fecha}: {uso.metros_turno_calc} m")

# Marcar como quemada
broca.marcar_como_quemada(observaciones="Desgaste excesivo")
```

### Consultas útiles

```python
# Brocas más usadas
brocas_top = HistorialBroca.objects.order_by('-metraje_acumulado')[:10]

# Brocas activas
activas = HistorialBroca.objects.filter(estado__in=['NUEVA', 'EN_USO'])

# Brocas sin usar últimos 30 días
from datetime import date, timedelta
fecha_limite = date.today() - timedelta(days=30)
sin_uso = HistorialBroca.objects.filter(
    fecha_ultimo_uso__lt=fecha_limite,
    estado='EN_USO'
)

# Brocas por contrato
del_contrato = HistorialBroca.objects.filter(
    contrato_actual__nombre_contrato='COLQUISIRI'
)

# Vida útil promedio por tipo de producto
from django.db.models import Avg
promedios = HistorialBroca.objects.values(
    'tipo_complemento__nombre'
).annotate(
    metraje_promedio=Avg('metraje_acumulado')
)
```

## Estados de Broca

| Estado | Descripción | Acción |
|--------|-------------|--------|
| **NUEVA** | Broca sin usar aún | Automático al crear |
| **EN_USO** | Broca en uso activo | Automático en primer uso |
| **DESGASTADA** | Broca con desgaste visible | Manual |
| **QUEMADA** | Broca fuera de servicio por desgaste | Manual con `marcar_como_quemada()` |
| **FUERA_SERVICIO** | Broca temporalmente fuera | Manual |
| **PERDIDA** | Broca extraviada | Manual |

## Reportes

### Dashboard de brocas
```python
from drilling.models import HistorialBroca
from django.db.models import Count, Sum, Avg

stats = HistorialBroca.objects.aggregate(
    total_brocas=Count('id'),
    metraje_total=Sum('metraje_acumulado'),
    metraje_promedio=Avg('metraje_acumulado')
)

por_estado = HistorialBroca.objects.values('estado').annotate(
    cantidad=Count('id'),
    metraje=Sum('metraje_acumulado')
)
```

## Integración con Formulario de Turnos

El formulario `crear_turno_completo.html` ya captura:
- `codigo_serie`: Código/serie de la broca
- `metros_inicio`: Metraje inicial
- `metros_fin`: Metraje final

Al guardar el turno, el historial se actualiza **automáticamente**.

### Autocompletado por serie

Para que el formulario autocomplete la descripción al ingresar la serie:

1. Asegurar que los productos estén cargados en `TipoComplemento`:
```bash
python cargar_productos_api.py
```

2. El JavaScript busca en `productosData` (generado desde `tipos_complemento`):
```javascript
const productoEncontrado = productosData.find(p => 
    p.serie.toLowerCase() === serieIngresada
);
```

## Mantenimiento

### Re-sincronizar historial
Si hay inconsistencias, re-ejecutar:
```bash
python sincronizar_historial_brocas.py
```

### Actualizar productos desde API
```bash
python cargar_productos_api.py
```

## Notas Técnicas

- **Actualización automática**: Usa señales de Django (`post_save` implícito en `TurnoComplemento.save()`)
- **F() expressions**: Usa `F()` para actualizaciones atómicas sin race conditions
- **Índices**: Optimizado con índices en `serie`, `estado`, `metraje_acumulado`
- **Unique constraint**: `serie` es única para evitar duplicados

## Solución de Problemas

### "Broca no aparece en historial"
```bash
python sincronizar_historial_brocas.py
```

### "No autocompleta descripción al ingresar serie"
1. Verificar que el producto esté en `TipoComplemento`:
```python
TipoComplemento.objects.filter(serie='409381').exists()
```

2. Si no existe, cargar desde API:
```bash
python cargar_productos_api.py
```

### "Metraje acumulado incorrecto"
Re-sincronizar desde datos fuente:
```bash
python sincronizar_historial_brocas.py
```

## Beneficios

✅ **Consultas instantáneas**: Metraje acumulado pre-calculado  
✅ **Trazabilidad completa**: Historial detallado por turno  
✅ **Alertas proactivas**: Identificar brocas próximas a fin de vida  
✅ **Reportes rápidos**: Estadísticas sin queries pesadas  
✅ **Auditoría**: Fechas de primer/último uso registradas  
✅ **Gestión de inventario**: Control de estado de cada broca
