# División de Metas a Mitad de Período

## Descripción
Funcionalidad para ajustar metas durante el transcurso del mes operativo, dividiendo una meta existente en dos períodos con valores diferentes.

## Caso de Uso

### Ejemplo Real:
1. **Meta Inicial**: 1000m para todo el mes (26 Oct - 25 Nov)
2. **Situación**: Al 10 de noviembre llevan 800m (rendimiento excelente)
3. **Decisión**: Ajustar meta a 1500m para el resto del mes
4. **Resultado**: 
   - Período 1: 26 Oct - 9 Nov, Meta: 1000m, Real: 800m ✅ (80%)
   - Período 2: 10 Nov - 25 Nov, Meta: 1500m, Real: TBD

## ¿Cómo Funciona?

### Proceso de División:

```
Meta Original (Activa)
├─ 26 Oct - 25 Nov
├─ Meta: 1000m
└─ Estado: ACTIVA

              👇 DIVISIÓN (10 Nov)

Meta Período 1 (Desactivada)     Meta Período 2 (Nueva - Activa)
├─ 26 Oct - 9 Nov                ├─ 10 Nov - 25 Nov
├─ Meta: 1000m                   ├─ Meta: 1500m
├─ Real: 800m                    ├─ Real: TBD
├─ Estado: INACTIVA              └─ Estado: ACTIVA
└─ Observaciones: "Dividida el 10/11/2025. Real: 800m"
```

### Operaciones Realizadas:

1. **Meta Original**:
   - Se ajusta `fecha_fin` al día anterior de la división
   - Se marca como `activo = False`
   - Se agregan observaciones con metros reales del período

2. **Nueva Meta**:
   - Se crea con `fecha_inicio` = fecha de división
   - Se crea con `fecha_fin` = fecha fin del período operativo original
   - Hereda contrato, máquina, año y mes
   - Se marca como `activo = True`
   - Incluye observaciones indicando meta anterior

## Interfaz de Usuario

### Acceso:
1. Ir a **Turnos → Ver Todas las Metas**
2. Encontrar la meta activa que desea dividir
3. Hacer clic en el botón <i class="fas fa-cut"></i> **Dividir**

### Formulario:

**Campos Requeridos**:
- **Fecha de División**: Desde qué día comienza la nueva meta
- **Nueva Meta (metros)**: Valor ajustado para el período restante

**Información Mostrada**:
- Meta original y período completo
- Metros reales perforados hasta hoy
- Total de turnos completados
- Promedio diario de perforación
- Proyección a fin de mes

**Cálculo Automático**:
- Días del Período 1 (original hasta división)
- Días del Período 2 (división hasta fin)
- Meta diaria sugerida para Período 2

### Ejemplo de Pantalla:

```
┌─────────────────────────────────────────────────────┐
│ Meta Original                                       │
├─────────────────────────────────────────────────────┤
│ Máquina: PD-001    Contrato: AMERICANA             │
│ Período: 26/10/2025 - 25/11/2025                   │
│ Meta Original: 1000 metros                          │
└─────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┬─────────────┐
│ Metros Reales│   Turnos     │ Prom. Diario │ Proyección  │
├──────────────┼──────────────┼──────────────┼─────────────┤
│   800.00m    │      25      │   32.00m     │  1200.00m   │
└──────────────┴──────────────┴──────────────┴─────────────┘

┌─────────────────────────────────────────────────────┐
│ Fecha de División: [10/11/2025]                     │
│ Nueva Meta: [1500] metros                           │
└─────────────────────────────────────────────────────┘

        ━━━━━━━━━━━━━ División ━━━━━━━━━━━━━

┌──────────────────────────┬──────────────────────────┐
│ Período 1 (Finalizado)   │ Período 2 (Nueva Meta)  │
├──────────────────────────┼──────────────────────────┤
│ 26/10/2025 - 09/11/2025  │ 10/11/2025 - 25/11/2025 │
│ Meta: 1000 metros        │ Meta: 1500 metros       │
│ Estado: Se desactivará   │ Estado: Activa          │
└──────────────────────────┴──────────────────────────┘

📊 Información de días:
• Período 1: 15 días
• Período 2: 16 días  
• Meta diaria sugerida Período 2: 93.75 m/día
```

## Validaciones

### Frontend (JavaScript):
- ✅ Fecha debe estar dentro del rango del período
- ✅ Nueva meta debe ser > 0
- ✅ Confirmación antes de enviar

### Backend (Python):
```python
# Fecha dentro del período
if fecha_division <= fecha_inicio_original or fecha_division > fecha_fin_original:
    error("Fecha fuera de rango")

# Nueva meta válida
if not nueva_meta_metros or nueva_meta_metros <= 0:
    error("Meta inválida")
```

## Permisos

### Requeridos:
- `@login_required`: Usuario autenticado
- `can_manage_all_contracts()`: Admin puede dividir cualquier meta
- Usuario normal: Solo puede dividir metas de su contrato

### Restricciones:
- Solo se puede dividir metas **activas**
- El botón de dividir solo aparece en metas activas
- Metas inactivas no muestran opción de división

## Implementación Técnica

### Archivos Modificados/Creados:

**Nuevos**:
- `drilling/templates/drilling/metas/dividir.html` - Template del formulario
- `DIVISION_METAS.md` - Este documento

**Modificados**:
- `drilling/views.py` - Agregada función `metas_maquina_dividir()`
- `drilling/urls.py` - Agregada ruta `/metas/<id>/dividir/`
- `drilling/templates/drilling/metas/list.html` - Agregado botón "Dividir"

### Vista: `metas_maquina_dividir()`

**GET**: Muestra formulario con:
- Información de la meta original
- Estadísticas actuales (metros reales, turnos, promedios)
- Campos para fecha de división y nueva meta
- Preview visual de cómo quedará la división

**POST**: Procesa división:
1. Valida fecha y nueva meta
2. Calcula metros reales del Período 1
3. Actualiza meta original (ajusta fecha_fin, desactiva, agrega observaciones)
4. Crea nueva meta para Período 2
5. Muestra mensaje de éxito con detalles
6. Redirige a lista de metas

### Consulta de Metros Reales:
```python
turnos_periodo1 = TurnoAvance.objects.filter(
    turno__maquina=meta_original.maquina,
    turno__contrato=meta_original.contrato,
    turno__fecha__gte=fecha_inicio_original,
    turno__fecha__lt=fecha_division,  # Hasta el día anterior
    turno__estado__in=['COMPLETADO', 'APROBADO']
)
metros_periodo1 = turnos_periodo1.aggregate(total=Sum('metros_perforados'))['total']
```

## Casos de Uso Comunes

### 1. Ajuste por Rendimiento Superior
**Situación**: Máquina rinde mejor de lo esperado
- Meta inicial: 800m
- A mitad de mes: 600m perforados (75% con 50% del tiempo)
- **Acción**: Aumentar meta a 1200m para el resto del mes

### 2. Ajuste por Bajo Rendimiento
**Situación**: Problemas operativos reducen productividad
- Meta inicial: 1000m
- A mitad de mes: 300m perforados (30%)
- **Acción**: Reducir meta a 600m para ser realista

### 3. Cambio de Condiciones Geológicas
**Situación**: Cambio de zona de perforación
- Meta inicial: 900m (roca blanda)
- Nueva zona: roca dura (menor avance esperado)
- **Acción**: Ajustar meta a 650m desde el cambio

### 4. Mantenimiento No Programado
**Situación**: Máquina entra a mantenimiento 10 días
- Meta inicial: 1000m
- Días disponibles reducidos
- **Acción**: Ajustar meta proporcionalmente

## Ventajas del Sistema

### ✅ Historial Completo
- No se pierde información
- Ambas metas quedan registradas
- Análisis retroactivo posible

### ✅ Análisis Preciso
- Se puede calcular cumplimiento por período
- Identificar cuándo cambió el rendimiento
- Auditoría de ajustes de metas

### ✅ Reportes Correctos
- PowerBI puede diferenciar períodos
- KPIs se calculan correctamente por fecha
- No se "mezclan" períodos con diferentes expectativas

### ✅ Trazabilidad
- Observaciones automáticas explican el cambio
- Fecha de división registrada
- Usuario que hizo el cambio (created_by)

## Ejemplo de Datos Resultantes

### Base de Datos - Tabla `MetaMaquina`:

**Antes de División**:
| ID | Máquina | Año | Mes | Fecha Inicio | Fecha Fin | Meta | Activo |
|----|---------|-----|-----|--------------|-----------|------|--------|
| 1  | PD-001  | 2025| 11  | NULL         | NULL      | 1000 | ✅ Sí  |

**Después de División (fecha: 10/11/2025, nueva meta: 1500m)**:
| ID | Máquina | Año | Mes | Fecha Inicio | Fecha Fin  | Meta | Activo | Observaciones |
|----|---------|-----|-----|--------------|------------|------|--------|---------------|
| 1  | PD-001  | 2025| 11  | 2025-10-26   | 2025-11-09 | 1000 | ❌ No  | [Dividida el 10/11/2025. Real: 800m] |
| 2  | PD-001  | 2025| 11  | 2025-11-10   | 2025-11-25 | 1500 | ✅ Sí  | Meta dividida desde 2025-11-10. Meta anterior: 1000m |

### Cálculo de Cumplimiento:

**Período 1** (ID=1):
```python
fecha_inicio = 2025-10-26
fecha_fin = 2025-11-09
meta = 1000m
real = 800m (de observaciones o recalculando)
cumplimiento = (800 / 1000) * 100 = 80%
```

**Período 2** (ID=2):
```python
fecha_inicio = 2025-11-10
fecha_fin = 2025-11-25
meta = 1500m
real = [consulta a TurnoAvance con esas fechas]
cumplimiento = (real / 1500) * 100
```

## Mejores Prácticas

### ✅ Cuándo Dividir:
- Al llegar a mitad del período
- Cuando hay evidencia clara de cambio de rendimiento
- Después de 5-7 días de datos consistentes
- Ante cambios operativos significativos

### ❌ Cuándo NO Dividir:
- En los últimos 2-3 días del período
- Con variaciones temporales (1-2 días)
- Sin datos suficientes para proyectar
- Por fluctuaciones normales del día a día

### 📋 Recomendaciones:
1. **Documentar el motivo** en observaciones adicionales
2. **Comunicar el cambio** al equipo operativo
3. **Revisar historial** antes de dividir
4. **Considerar tendencias** no solo un día bueno/malo
5. **Usar la proyección** como guía para la nueva meta

## Testing

### Casos de Prueba:

**✅ Test 1: División exitosa**
- Meta activa del mes actual
- Fecha de división = hoy
- Nueva meta = 1500m
- Resultado: 2 metas, original inactiva, nueva activa

**✅ Test 2: Validación de fecha fuera de rango**
- Fecha de división antes del inicio del período
- Resultado: Error "Fecha fuera de rango"

**✅ Test 3: Meta inactiva no se puede dividir**
- Intentar dividir meta ya inactiva
- Resultado: Botón no visible en UI

**✅ Test 4: Permisos por contrato**
- Usuario del contrato A intenta dividir meta del contrato B
- Resultado: Error "No tienes permisos"

**✅ Test 5: Cálculo correcto de metros Período 1**
- División el día 10
- Verificar que metros calculados coinciden con turnos del 26/10 al 9/11
- Resultado: Metros en observaciones = suma real

## Conclusión

La división de metas permite una gestión flexible y realista de objetivos durante el transcurso del mes operativo, manteniendo la integridad del historial y permitiendo análisis precisos del desempeño por períodos específicos.

Esta funcionalidad es especialmente útil en operaciones mineras donde las condiciones cambian frecuentemente y las metas deben ajustarse a la realidad operativa sin perder trazabilidad.
