# Implementación: Control de Proyectos - Stock y Turnos

## Resumen de Cambios

Se ha agregado funcionalidad completa para el rol de **Control de Proyectos** (CONTROL_PROYECTOS) permitiendo:

1. ✅ **Ver stock de PDD (Productos Diamantados)** de los contratos
2. ✅ **Ver stock de ADIT (Aditivos)** de los contratos  
3. ✅ **Ver turnos creados** con filtros avanzados
4. ✅ **Editar turnos** con los mismos permisos que los managers de contratos

## Archivos Creados/Modificados

### 1. Nuevo Template
**Archivo:** `drilling/templates/drilling/gestion_proyectos/stock_turnos.html`
- Template completo con tabs para Stock y Turnos
- Integración con API de Vilbragroup para consultar stock en tiempo real
- Tabla de turnos con opciones de ver, editar y eliminar
- Filtros por sondaje y fechas
- Estadísticas de metros perforados
- Búsqueda en tiempo real en tablas de stock

### 2. Nueva Vista
**Archivo:** `drilling/views_gestion_proyectos.py`
- Vista `gestion_proyectos_stock_turnos` con permisos para CONTROL_PROYECTOS y GERENCIA
- Gestión de múltiples contratos según permisos del usuario
- Filtros de turnos (sondaje, fecha desde, fecha hasta)
- Estadísticas de turnos y metros perforados
- Queries optimizados con select_related y prefetch_related

### 3. URLs Actualizadas
**Archivo:** `drilling/urls.py`
- Importación de `views_gestion_proyectos`
- Nueva ruta: `/gestion-proyectos/stock-turnos/` 
- Nombre de URL: `gestion-proyectos-stock-turnos`

### 4. Menú de Navegación
**Archivo:** `drilling/templates/drilling/base_admin.html`
- Agregado enlace "Control de Proyectos" en menú de Gestión
- Visible solo para usuarios con rol CONTROL_PROYECTOS y GERENCIA
- Icono: `fa-project-diagram`

## Cómo Usar

### Acceso
1. Iniciar sesión con un usuario que tenga rol **CONTROL_PROYECTOS** o **GERENCIA**
2. En el menú principal, ir a **Gestión → Control de Proyectos**
3. O acceder directamente a: `http://localhost:8000/gestion-proyectos/stock-turnos/`

### Funcionalidades

#### Tab "Stock de Almacén"
- **Productos Diamantados (PDD)**: Muestra serie, código, descripción y estado
- **Aditivos (ADIT)**: Muestra código, descripción, stock disponible y unidad
- Botón "Recargar" para actualizar datos de la API
- Búsqueda en tiempo real por cualquier campo
- Resumen con total de productos y estadísticas

#### Tab "Gestión de Turnos"
- **Filtros**: Por sondaje, fecha desde, fecha hasta
- **Tabla de Turnos** con:
  - ID del turno
  - Fecha
  - Sondaje(s) asignados
  - Máquina utilizada
  - Tipo de turno
  - Cantidad de trabajadores
  - Metros perforados
  - Acciones: Ver detalle, Editar, Eliminar
- **Estadísticas**: Total de turnos, metros totales, promedio por turno
- Limitado a 100 registros para mejor performance

#### Selector de Contrato
- Si el usuario tiene acceso a múltiples contratos (GERENCIA), puede cambiar entre ellos
- Si solo tiene un contrato asignado (CONTROL_PROYECTOS), se muestra automáticamente

## Permisos

### Rol CONTROL_PROYECTOS
- ✅ Ver stock de **todos los contratos activos**
- ✅ Ver turnos de **todos los contratos**
- ✅ Editar turnos de **todos los contratos**
- ✅ Crear nuevos turnos en cualquier contrato
- ✅ Cambiar entre contratos con selector
- ✅ Acceso completo a gestión de proyectos multi-contrato

### Rol GERENCIA  
- ✅ Ver stock de todos los contratos
- ✅ Ver turnos de todos los contratos
- ✅ Editar turnos de cualquier contrato
- ✅ Cambiar entre contratos con selector
- ✅ Crear nuevos turnos en cualquier contrato
- ✅ Acceso administrativo completo

## Características Técnicas

### Optimizaciones
- Uso de `select_related` y `prefetch_related` para reducir queries a la BD
- Anotación con `Subquery` para metros perforados
- Límite de 100 registros en listado de turnos
- Cache de consultas a API de stock

### Integraciones
- API de Vilbragroup para stock de PDD: `/api/stock/productos-diamantados/`
- API de Vilbragroup para stock de Aditivos: `/api/stock/aditivos/`
- Reutilización de vistas existentes para crear/editar turnos

### Responsive Design
- Diseño adaptable a móviles y tablets
- Tabs Bootstrap 5 para navegación fluida
- Iconos Font Awesome para mejor UX
- Alertas y feedback visual para el usuario

## Pruebas Recomendadas

1. ✅ Acceso con usuario CONTROL_PROYECTOS
2. ✅ Ver stock de PDD y ADIT
3. ✅ Búsqueda en tablas de stock
4. ✅ Filtrar turnos por sondaje y fechas
5. ✅ Editar un turno existente
6. ✅ Crear un nuevo turno
7. ✅ Ver detalles de un turno
8. ✅ Cambiar de contrato (si aplica)
9. ✅ Verificar que otros roles NO tengan acceso

## Notas Adicionales

- El template hereda el base correcto según el rol del usuario (base_admin.html para CONTROL_PROYECTOS y GERENCIA)
- Los colores y estilos siguen la paleta DrillControl definida en el sistema
- La funcionalidad de stock consulta en tiempo real la API de Vilbragroup
- Se mantiene consistencia con el resto del sistema en términos de diseño y UX

## Próximos Pasos (Opcional)

- Agregar exportación a Excel de la lista de turnos
- Implementar gráficos de evolución de stock
- Agregar alertas de stock bajo/crítico
- Implementar notificaciones para turnos próximos a vencer
- Dashboard específico para Control de Proyectos con KPIs

---
**Fecha de Implementación:** Diciembre 2025  
**Desarrollado para:** Sistema de Control de Perforaciones Diamantinas
