# Gestión de Metas por Contrato - Implementación Masiva

## Descripción
Sistema de gestión masiva de metas de máquinas por contrato, que permite configurar las metas de todas las máquinas de un contrato en una sola interfaz.

## Características Implementadas

### 1. Vista de Gestión Masiva (`metas_maquina_gestionar`)
- **Ubicación**: `drilling/views.py`
- **Ruta**: `/metas/gestionar/`

#### Funcionalidad GET:
- Selección de contrato (filtrado por permisos de usuario)
- Selección de año y mes
- Calcula automáticamente el período operativo (26 del mes anterior al 25 del mes seleccionado)
- Muestra tabla con todas las máquinas operativas del contrato
- Para cada máquina muestra:
  - Meta actual (si existe)
  - Estado activo/inactivo
  - Metros reales perforados en el período
  - Total de turnos completados
  - Porcentaje de cumplimiento con barra de progreso

#### Funcionalidad POST:
- Guarda/actualiza metas para múltiples máquinas en una sola transacción
- Verifica si existe meta previa para el período
- Si existe: actualiza
- Si no existe: crea nueva
- Solo procesa máquinas con valores > 0
- Muestra mensajes de éxito con cantidad de metas creadas/actualizadas

### 2. Template `gestionar.html`
- **Ubicación**: `drilling/templates/drilling/metas/gestionar.html`

#### Componentes:
1. **Filtros superiores**:
   - Selector de contrato (dinámico según permisos)
   - Selector de año (2024 hasta año actual +1)
   - Selector de mes
   - Auto-submit al cambiar filtros

2. **Información del período**:
   - Muestra fechas exactas del período operativo
   - Resalta con formato especial

3. **Tabla de metas**:
   - Columnas: #, Máquina, Meta (metros), Activo, Metros Reales, Turnos, Cumplimiento
   - Input numérico para cada máquina
   - Checkbox de activo por máquina
   - Campos ocultos para meta_id (actualización)
   - Barras de progreso con código de colores:
     - Rojo: 0-49%
     - Amarillo: 50-79%
     - Azul: 80-99%
     - Verde: ≥100%

4. **Footer del formulario**:
   - Botón "Cancelar" (vuelve a lista)
   - Botón "Guardar Todas las Metas"
   - Información del período

5. **Leyenda**:
   - Explicación de colores
   - Instrucciones de uso

#### Validaciones JavaScript:
- Previene envío sin al menos una meta con valor > 0
- Resaltado visual de filas al hacer hover

### 3. Actualización de Menú
- **Ubicación**: `drilling/templates/drilling/base.html`

#### Cambios:
- Menú "Turnos" → Sección "Gestionar Metas" (principal)
- Menú "Turnos" → Sección "Ver Todas las Metas" (lista tradicional)
- Solo visible para usuarios con `can_supervise_operations()`

### 4. URL Routing
- **Ubicación**: `drilling/urls.py`

Nueva ruta:
```python
path('metas/gestionar/', views.metas_maquina_gestionar, name='metas-maquina-gestionar'),
```

## Flujo de Trabajo

### Uso Típico:
1. Usuario accede a "Gestionar Metas" desde menú Turnos
2. Selecciona contrato (si tiene permisos múltiples)
3. Selecciona año y mes
4. Sistema muestra tabla con todas las máquinas del contrato
5. Usuario ingresa metas en metros para cada máquina
6. Marca/desmarca checkbox "Activo" según necesidad
7. Hace clic en "Guardar Todas las Metas"
8. Sistema procesa:
   - Verifica metas existentes para el período
   - Actualiza o crea según corresponda
   - Muestra mensaje de éxito con totales
9. Redirige a la misma vista con datos actualizados

### Cálculo de Cumplimiento:
```python
# Filtros aplicados:
turnos_con_avance = TurnoAvance.objects.filter(
    turno__maquina=maquina,
    turno__contrato=contrato,
    turno__fecha__gte=fecha_inicio,  # 26 del mes anterior
    turno__fecha__lte=fecha_fin,     # 25 del mes seleccionado
    turno__estado__in=['COMPLETADO', 'APROBADO']
)

metros_reales = turnos_con_avance.aggregate(total=Sum('metros_perforados'))['total']
porcentaje = (metros_reales / meta_metros) * 100
```

## Permisos y Seguridad

### Decoradores:
- `@login_required`: Requiere autenticación
- `@require_http_methods(["GET", "POST"])`: Solo GET y POST permitidos

### Validaciones:
1. **Contratos**: 
   - Admin ve todos los contratos activos
   - Usuario normal solo ve su contrato asignado
   
2. **Edición**:
   - Solo admin puede gestionar cualquier contrato
   - Usuario normal solo su propio contrato

3. **Datos**:
   - Solo máquinas con `estado='OPERATIVO'`
   - Solo turnos con `estado__in=['COMPLETADO', 'APROBADO']`

## Ventajas vs. Implementación Anterior

### Antes:
- ❌ Una página por máquina
- ❌ Navegación tedious entre formularios
- ❌ No visualización de cumplimiento al crear
- ❌ Sin contexto de otras máquinas

### Ahora:
- ✅ Todas las máquinas en una sola vista
- ✅ Contexto completo del contrato
- ✅ Visualización en tiempo real de cumplimiento
- ✅ Guardado masivo en una transacción
- ✅ Comparación visual entre máquinas
- ✅ Filtros dinámicos por contrato/período

## Consideraciones Técnicas

### Performance:
- Queries optimizadas con `select_related` implícito
- Agregaciones eficientes con `Sum()`
- Un query por máquina para cumplimiento (puede optimizarse con prefetch_related)

### Transacciones:
- Todas las metas se guardan en el mismo request
- Django maneja transaccionalidad automáticamente
- Rollback automático en caso de error

### Validación de Datos:
- Metas deben ser > 0 (validación JS y Python)
- Decimal con 2 decimales
- Período debe ser válido (año/mes existente)

## Próximos Pasos Sugeridos

### Optimizaciones:
1. Agregar `transaction.atomic()` explícito para garantizar atomicidad
2. Optimizar queries con `prefetch_related` para cumplimiento
3. Cache de cálculos de cumplimiento

### Mejoras UX:
1. Botón "Copiar metas del mes anterior"
2. Exportar/importar metas desde Excel
3. Gráficas de tendencia de cumplimiento
4. Alertas automáticas por bajo cumplimiento

### Reportes:
1. Vista consolidada de cumplimiento por contrato
2. Ranking de máquinas por cumplimiento
3. Histórico de metas vs. reales

## Archivos Modificados/Creados

### Creados:
- `drilling/templates/drilling/metas/gestionar.html`
- `GESTION_METAS_BULK.md` (este archivo)

### Modificados:
- `drilling/views.py` - Agregada función `metas_maquina_gestionar()`
- `drilling/urls.py` - Agregada ruta `metas/gestionar/`
- `drilling/templates/drilling/base.html` - Actualizado menú con dos opciones

## Testing

### Para probar la funcionalidad:
1. Servidor corriendo en `http://127.0.0.1:8000/`
2. Acceder como usuario con permisos de supervisión
3. Navegar a Turnos → Gestionar Metas
4. Seleccionar contrato, año y mes
5. Ingresar metas para las máquinas
6. Guardar y verificar mensajes de éxito
7. Verificar en "Ver Todas las Metas" que se crearon correctamente

### Casos de prueba:
- ✅ Creación de múltiples metas nuevas
- ✅ Actualización de metas existentes
- ✅ Mezcla de creación y actualización
- ✅ Permisos por contrato
- ✅ Validación de campos vacíos
- ✅ Cálculo correcto de cumplimiento

## Conclusión

La implementación de gestión masiva de metas mejora significativamente la eficiencia operativa al permitir configurar todas las metas de un contrato en una sola interfaz, con visualización en tiempo real del cumplimiento y contexto completo del desempeño de todas las máquinas.
