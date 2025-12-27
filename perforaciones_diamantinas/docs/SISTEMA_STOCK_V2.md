# Sistema de Gestión de Stock v2.0

## Resumen Ejecutivo

El Sistema de Stock v2.0 introduce una arquitectura híbrida que combina consultas en tiempo real a las APIs de PDD y ADITIVOS con almacenamiento local para análisis histórico, proyecciones y alertas automáticas.

### Mejoras Principales

| Característica | v1.0 (Anterior) | v2.0 (Nuevo) |
|---------------|-----------------|--------------|
| Datos | Solo tiempo real | Histórico + tiempo real |
| Alertas | Manuales | Automáticas por umbral |
| Proyecciones | No disponible | Por consumo histórico |
| Power BI | Consulta API | Vistas SQL optimizadas |
| Tendencias | No disponible | Gráficas Chart.js |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND                                 │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Dashboard      │  Detalle        │  Alertas                │
│  Stock          │  Artículo       │  List                   │
└────────┬────────┴────────┬────────┴──────────┬──────────────┘
         │                 │                   │
         ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   StockService                               │
│  - sincronizar_stock_completo()                              │
│  - obtener_resumen_stock()                                   │
│  - obtener_proyeccion_stock()                                │
│  - generar_alertas()                                         │
│  - obtener_tendencia_articulo()                              │
└────────┬────────────────────────────────────────┬───────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────────┐              ┌─────────────────────────┐
│   API Externa       │              │   Base de Datos Local   │
│   (PDD/ADITIVOS)    │              │   PostgreSQL            │
│                     │              │                         │
│   - GET stock       │              │   - StockSnapshot       │
│   - Tiempo real     │              │   - AlertaStock         │
│                     │              │   - ConfigAlertaStock   │
└─────────────────────┘              └─────────────────────────┘
         │                                        │
         └────────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │   Power BI          │
              │   (Vistas SQL)      │
              └─────────────────────┘
```

---

## Modelos de Datos

### StockSnapshot
Almacena fotografías diarias del stock para análisis histórico.

```python
class StockSnapshot(models.Model):
    contrato = ForeignKey(Contrato)
    familia = CharField()        # 'PDD' o 'ADIT'
    codigo_articulo = CharField()
    descripcion = CharField()
    stock_cantidad = DecimalField()
    unidad_medida = CharField()
    lote = CharField()
    ubicacion = CharField()
    precio_unitario = DecimalField()
    valor_total = DecimalField()
    fecha_sync = DateTimeField()
```

**Métodos clave:**
- `get_stock_actual(contrato_id)`: Obtiene el stock más reciente
- `get_historial_articulo(contrato_id, codigo, dias)`: Historial para tendencias

### AlertaStock
Sistema de alertas automáticas basadas en umbrales.

```python
class AlertaStock(models.Model):
    contrato = ForeignKey(Contrato)
    codigo_articulo = CharField()
    descripcion_articulo = CharField()
    familia = CharField()
    
    # Tipo y prioridad
    tipo_alerta = CharField(choices=TIPO_ALERTA_CHOICES)
    prioridad = IntegerField(1-4)  # 1=Crítica, 4=Baja
    mensaje = TextField()
    
    # Métricas contextuales
    stock_actual = DecimalField()
    consumo_diario_promedio = DecimalField()
    dias_stock_restante = IntegerField()
    
    # Estado
    leida = BooleanField()
    resuelta = BooleanField()
```

**Tipos de alerta:**
| Tipo | Descripción | Prioridad |
|------|-------------|-----------|
| AGOTADO | Stock = 0 | 1 (Crítica) |
| STOCK_CRITICO | Stock ≤ 5 unidades | 1 (Crítica) |
| STOCK_BAJO | Stock ≤ 20 unidades | 2 (Alta) |
| REPOSICION_URGENTE | ≤ 5 días de stock | 1 (Crítica) |
| SIN_ROTACION | Sin movimiento 30+ días | 4 (Baja) |
| CONSUMO_ANORMAL | Pico de consumo | 3 (Media) |

### ConfiguracionAlertaStock
Configuración de umbrales por contrato.

```python
class ConfiguracionAlertaStock(models.Model):
    contrato = OneToOneField(Contrato)
    
    # Umbrales de stock
    umbral_stock_critico = IntegerField(default=5)
    umbral_stock_bajo = IntegerField(default=20)
    umbral_dias_alerta = IntegerField(default=15)
    
    # Control de alertas
    alertas_activas = BooleanField(default=True)
    alerta_email = BooleanField(default=False)
    emails_notificacion = TextField()
```

---

## StockService

Servicio centralizado en `drilling/utils/stock_service.py`.

### Inicialización

```python
from drilling.utils.stock_service import StockService

# Para un contrato específico
service = StockService(contrato_id=123)

# Sincronizar todos los contratos
from drilling.utils.stock_service import sincronizar_todos_los_contratos
sincronizar_todos_los_contratos()
```

### Métodos Principales

#### sincronizar_stock_completo()
Sincroniza stock desde API externa y guarda snapshots.

```python
resultado = service.sincronizar_stock_completo()
# {
#     'pdd': {'exito': True, 'items': 150, 'error': None},
#     'aditivos': {'exito': True, 'items': 80, 'error': None}
# }
```

#### obtener_resumen_stock()
Resumen general con KPIs.

```python
resumen = service.obtener_resumen_stock()
# {
#     'total_items': 230,
#     'valor_total': Decimal('45678.90'),
#     'items_agotados': 3,
#     'items_stock_bajo': 12,
#     'ultima_sync': datetime(...)
# }
```

#### obtener_proyeccion_stock()
Proyecciones basadas en consumo histórico.

```python
proyecciones = service.obtener_proyeccion_stock()
# [
#     {
#         'codigo': 'ABC123',
#         'descripcion': 'Broca HQ',
#         'stock_actual': 10,
#         'consumo_diario': 0.5,
#         'dias_restantes': 20,
#         'fecha_agotamiento': date(2024, 1, 15),
#         'estado': 'ALERTA'
#     },
#     ...
# ]
```

#### generar_alertas()
Genera alertas automáticas según configuración.

```python
nuevas_alertas = service.generar_alertas()
# Retorna lista de AlertaStock creadas
```

#### obtener_tendencia_articulo(codigo, dias=30)
Datos históricos para gráficas.

```python
tendencia = service.obtener_tendencia_articulo('ABC123', dias=30)
# {
#     'labels': ['2024-01-01', '2024-01-02', ...],
#     'data': [100, 95, 90, 85, ...],
#     'consumo_promedio': 1.67
# }
```

---

## API Endpoints

### Base URL: `/api/stock/v2/`

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/resumen/<contrato_id>/` | GET | Resumen y KPIs |
| `/actual/<contrato_id>/` | GET | Stock actual |
| `/proyecciones/<contrato_id>/` | GET | Proyecciones |
| `/tendencia/<contrato>/<codigo>/` | GET | Datos para gráfica |
| `/alertas/<contrato_id>/` | GET | Alertas activas |
| `/sincronizar/<contrato_id>/` | POST | Forzar sincronización |

### Ejemplos de Respuesta

#### GET `/api/stock/v2/resumen/123/`
```json
{
    "success": true,
    "data": {
        "total_items": 230,
        "valor_total": 45678.90,
        "items_agotados": 3,
        "items_stock_bajo": 12,
        "ultima_sync": "2024-01-10T08:30:00Z",
        "alertas_activas": 5
    }
}
```

#### GET `/api/stock/v2/tendencia/123/ABC123/`
```json
{
    "success": true,
    "codigo": "ABC123",
    "descripcion": "Broca HQ",
    "labels": ["01/01", "02/01", "03/01"],
    "data": [100, 95, 90],
    "consumo_promedio": 3.33
}
```

---

## Vistas y Templates

### URLs

| URL | Vista | Template |
|-----|-------|----------|
| `/stock/dashboard/` | `dashboard_stock` | `stock/dashboard_stock.html` |
| `/stock/articulo/<contrato>/<codigo>/` | `detalle_articulo_stock` | `stock/detalle_articulo.html` |
| `/stock/alertas/` | `AlertaStockListView` | `stock/alertas_list.html` |

### Dashboard (`dashboard_stock.html`)
- KPIs: Total artículos, valor inventario, alertas activas
- Tabs: PDD / Aditivos
- Tabla con stock actual y estado
- Panel lateral de alertas recientes
- Botón de sincronización manual

### Detalle Artículo (`detalle_articulo.html`)
- Métricas del artículo
- Gráfica de tendencia (Chart.js)
- Proyección de agotamiento
- Histórico de consumos

### Lista de Alertas (`alertas_list.html`)
- Filtros: Contrato, tipo, prioridad, estado
- Acciones: Marcar leída, resolver
- Paginación

---

## Sincronización Automática

### Script: `scripts/sync/sync_stock_v2.py`

```bash
# Sincronizar todos los contratos
python manage.py shell < scripts/sync/sync_stock_v2.py

# Con opciones
python scripts/sync/sync_stock_v2.py --verbose
python scripts/sync/sync_stock_v2.py --contrato=123
python scripts/sync/sync_stock_v2.py --dry-run
```

### Programar con Task Scheduler (Windows)

1. Abrir Task Scheduler
2. Crear tarea básica
3. Trigger: Diario a las 06:00
4. Acción: Iniciar programa
   - Programa: `python`
   - Argumentos: `manage.py shell < scripts/sync/sync_stock_v2.py`
   - Directorio: `C:\...\perforaciones_diamantinas`

### Programar con Cron (Linux)

```cron
# Sincronizar stock diario a las 6:00 AM
0 6 * * * cd /path/to/perforaciones_diamantinas && python manage.py shell < scripts/sync/sync_stock_v2.py >> /var/log/stock_sync.log 2>&1
```

---

## Vistas SQL para Power BI

Archivo: `sql_views/vw_stock_historico.sql`

### Vistas Disponibles

| Vista | Descripción |
|-------|-------------|
| `vw_stock_actual` | Stock actual por contrato (última sync) |
| `vw_stock_historico` | Todos los snapshots para tendencias |
| `vw_alertas_stock` | Alertas con detalles para monitoreo |
| `vw_stock_resumen_contrato` | KPIs ejecutivos por contrato |
| `vw_consumo_stock_periodo` | Consumos agrupados por período |
| `vw_stock_proyeccion` | Proyección de agotamiento |

### Conexión Power BI

1. **Modo Directo**: Conectar a PostgreSQL con las vistas
2. **Import Mode**: Programar refresh diario
3. **Filtros recomendados**: `contrato_id`, `familia`, `periodo`

---

## Migración de Datos

### Aplicar Migración

```bash
cd perforaciones_diamantinas
python manage.py migrate drilling 0054_stock_snapshots_alertas
```

### Cargar Datos Históricos

Si hay datos de consumo previos, se pueden generar snapshots retroactivos:

```python
from drilling.utils.stock_service import sincronizar_todos_los_contratos
from drilling.models import Contrato

for contrato in Contrato.objects.filter(estado='ACTIVO'):
    service = StockService(contrato.id)
    service.sincronizar_stock_completo()
    service.generar_alertas()
```

---

## Configuración por Contrato

### Desde Django Admin

1. Ir a `/admin/drilling/configuracionalertastock/`
2. Crear o editar configuración para cada contrato
3. Ajustar umbrales según necesidad del proyecto

### Umbrales Recomendados

| Tipo Proyecto | Stock Crítico | Stock Bajo | Días Alerta |
|--------------|---------------|------------|-------------|
| Proyecto pequeño | 3 | 10 | 7 |
| Proyecto mediano | 5 | 20 | 15 |
| Proyecto grande | 10 | 50 | 30 |

---

## Troubleshooting

### La sincronización falla
1. Verificar conectividad a API externa
2. Revisar logs en `scripts/sync/sync_stock_v2.py --verbose`
3. Verificar credenciales API en configuración

### No se generan alertas
1. Verificar que `alertas_activas=True` en ConfiguracionAlertaStock
2. Revisar umbrales configurados
3. Ejecutar manualmente: `service.generar_alertas()`

### Gráficas no muestran datos
1. Verificar que haya snapshots históricos (mínimo 2 puntos)
2. Revisar consola del navegador para errores JS
3. Verificar endpoint API de tendencia

### Power BI no muestra datos
1. Verificar conexión a PostgreSQL
2. Ejecutar vistas SQL manualmente para probar
3. Verificar permisos de usuario de base de datos

---

## Changelog

### v2.0.0 (Diciembre 2024)
- ✅ Modelos StockSnapshot, AlertaStock, ConfiguracionAlertaStock
- ✅ StockService centralizado
- ✅ Dashboard con KPIs y tabs
- ✅ Sistema de alertas automáticas
- ✅ Gráficas de tendencia con Chart.js
- ✅ API endpoints v2
- ✅ Vistas SQL para Power BI
- ✅ Sincronización automática programable

### Roadmap v2.1
- [ ] Notificaciones por email
- [ ] Exportación a Excel
- [ ] Predicción con ML
- [ ] Dashboard móvil responsive
- [ ] Integración con WhatsApp Business API
