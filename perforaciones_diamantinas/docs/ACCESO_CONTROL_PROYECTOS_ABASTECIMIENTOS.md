# Sistema de Abastecimientos - Acceso Control de Proyectos

## Resumen

Sistema completo de sincronización, gestión y visualización de abastecimientos con API externa. Incluye acceso multi-contrato especialmente diseñado para el rol **Control de Proyectos**.

---

## 🎯 Vistas Disponibles

### 1. **Dashboard Multi-Contrato** (Control de Proyectos)
**URL:** `/abastecimientos/control-proyectos/`  
**Acceso:** Control de Proyectos, Gerencia, Superuser

**Funcionalidades:**
- ✅ Vista consolidada de **todos los contratos**
- ✅ Métricas por contrato: abastecimientos, brocas, valores
- ✅ Resumen general de toda la operación
- ✅ Acceso rápido a cada contrato individual
- ✅ Sincronización manual desde la interfaz

**Métricas Mostradas:**
- Total de abastecimientos por contrato
- Brocas disponibles (Nuevas + En Uso)
- Brocas nuevas sin usar
- Brocas en uso actualmente
- Valor total abastecido (en Soles)

---

### 2. **Lista de Abastecimientos**
**URL:** `/abastecimientos/`  
**Acceso:** Todos los roles (filtrado por contrato según permisos)

**Funcionalidades:**
- ✅ Tabla completa de abastecimientos sincronizados
- ✅ Filtros por: contrato, familia, fechas, búsqueda
- ✅ Visualización de series de brocas
- ✅ Link directo al historial de cada broca
- ✅ Paginación (50 registros por página)
- ✅ Sincronización manual por periodo

**Campos Mostrados:**
- Fecha de abastecimiento
- Código y serie del artículo
- Descripción
- Familia (PDD/ADIT)
- Cantidad y unidad
- Precios unitario y total
- Documento de origen

---

### 3. **Detalle de Abastecimiento**
**URL:** `/abastecimientos/<id>/`  
**Acceso:** Todos los roles (según contrato)

**Funcionalidades:**
- ✅ Información completa del artículo
- ✅ Datos documentales (documento, referencia, movimiento)
- ✅ Si tiene serie: link al historial de la broca
- ✅ Información del historial de la broca (si aplica)
- ✅ Usos recientes de la broca (si aplica)
- ✅ Estado actual y metraje acumulado

---

### 4. **Dashboard de Brocas Disponibles**
**URL:** `/abastecimientos/brocas-disponibles/`  
**Acceso:** Todos los roles (filtrado por contrato)

**Funcionalidades:**
- ✅ Vista organizada: Brocas Nuevas vs En Uso
- ✅ Estadísticas consolidadas
- ✅ Selector de contrato
- ✅ Información de cada broca:
  - Serie
  - Tipo de complemento
  - Metraje acumulado
  - Número de usos
  - Promedio por uso
  - Última fecha de uso

---

## 🔐 Control de Acceso

### Rol: **CONTROL_PROYECTOS**
- ✅ Acceso a **todos los contratos**
- ✅ Dashboard multi-contrato exclusivo
- ✅ Vista consolidada de métricas
- ✅ Puede sincronizar manualmente
- ✅ Acceso completo a todas las vistas

### Rol: **GERENCIA**
- ✅ Mismos permisos que Control de Proyectos
- ✅ Acceso a todos los contratos

### Rol: **ADMINISTRADOR**
- ✅ Acceso solo a su contrato asignado
- ✅ No ve dashboard multi-contrato
- ✅ Puede sincronizar su contrato

### Rol: **SUPERVISOR/OPERADOR**
- ✅ Acceso solo a su contrato asignado
- ✅ Solo visualización (no sincronización)

---

## 🎨 Navegación

### Menú Principal → **Inventario**

Para usuarios de **Control de Proyectos**:
```
📊 Dashboard Multi-Contrato  ← Destacado en azul (exclusivo)
─────────────────────────────
🚚 Abastecimiento
➖ Consumo
📦 Stock Disponible
─────────────────────────────
☁️ Stock Almacén (API)
─────────────────────────────
📦 Abastecimientos API v2
🔧 Brocas Disponibles
─────────────────────────────
📜 Historial de Brocas
```

---

## 📊 Datos Mostrados por Centro de Costo

Cada contrato muestra:

### Información del Contrato
- Nombre del contrato
- Centro de costo
- Estado (Activo/Inactivo)

### Métricas de Abastecimientos
- **Total de registros:** Cantidad de abastecimientos sincronizados
- **Valor total:** Suma de precio_total de todos los abastecimientos

### Métricas de Brocas
- **Brocas Disponibles:** Total (Nuevas + En Uso)
- **Brocas Nuevas:** Estado = 'NUEVA' (sin usar)
- **Brocas En Uso:** Estado = 'EN_USO' (actualmente en operación)

---

## 🔄 Sincronización

### Desde la Interfaz Web

**Dashboard Multi-Contrato:**
1. Botón "Sincronizar Ahora"
2. Modal con opciones:
   - Periodo (YYYYMM)
   - Centro de costo (opcional)
   - Familia (PDD/ADIT o todas)
3. Ejecuta sincronización para todos los contratos

**Lista de Abastecimientos:**
1. Botón "Sincronizar Ahora"
2. Similar al dashboard
3. Se filtra por el contrato seleccionado

### Desde Línea de Comandos

```bash
# Sincronizar periodo específico
python manage.py sincronizar_abastecimientos 202602 --familia PDD

# Ver detalles
python manage.py sincronizar_abastecimientos 202602 --verbose
```

### Automática (4:00 AM)

Script programado que ejecuta diariamente:
- Mes actual
- Mes anterior (datos rezagados)
- Solo familia PDD (brocas)

---

## 🔍 Filtros Disponibles

### Lista de Abastecimientos

**Contrato:**
- Selector dropdown
- Control de Proyectos: ve todos
- Otros roles: solo su contrato

**Familia:**
- Todas
- PDD (Productos Diamantados - Brocas)
- ADIT (Aditivos)

**Fechas:**
- Fecha inicio
- Fecha fin
- Rango flexible

**Búsqueda:**
- Por código de artículo
- Por serie
- Por descripción
- Por número de documento

---

## 🏷️ Identificación Visual

### Familia de Artículos
- **PDD:** Badge verde (Productos Diamantados)
- **ADIT:** Badge amarillo (Aditivos)

### Estado de Brocas
- **NUEVA:** Badge verde claro
- **EN_USO:** Badge azul claro
- **DESGASTADA:** Badge amarillo
- **QUEMADA:** Badge rojo
- **FUERA_SERVICIO:** Badge gris

### Series
- Fondo azul claro
- Fuente monoespaciada (Courier New)
- Link al historial si existe

---

## 📈 Integración con Historial de Brocas

### Flujo de Datos

```
API Externa (articulos_v2)
         ↓
AbastecimientoArticulo
         ↓ (si familia = PDD y tiene serie)
HistorialBroca
         ↓ (al registrar uso en turno)
TurnoComplemento
```

### Sincronización Automática

Cuando se sincroniza un abastecimiento con serie:
1. Se crea registro en `AbastecimientoArticulo`
2. **Automáticamente** se crea/actualiza `HistorialBroca`
3. Se vinculan ambos registros
4. La broca queda disponible para uso en turnos

---

## 🛠️ Acciones Rápidas

### Desde Dashboard Multi-Contrato
- **Ver Abastecimientos:** Lista filtrada por contrato
- **Ver Brocas:** Dashboard de brocas del contrato
- **Sincronizar Periodo:** Modal de sincronización
- **Historial Completo:** Todas las brocas de todos los contratos
- **Admin Django:** Acceso al panel administrativo

### Desde Lista de Abastecimientos
- **Ver Detalle:** Click en ojo 👁️
- **Ver Historial Broca:** Click en ⏱️ (si tiene serie)
- **Filtrar:** Formulario de filtros
- **Sincronizar:** Botón en header

### Desde Dashboard de Brocas
- **Ver Historial:** Click en ojo 👁️ por cada broca
- **Cambiar Contrato:** Selector en header

---

## 📱 Responsive Design

Todas las vistas están optimizadas para:
- ✅ Desktop (full width)
- ✅ Tablets (grid adaptativo)
- ✅ Móviles (cards apiladas)

---

## 💡 Tips para Control de Proyectos

1. **Página de Inicio Recomendada:**  
   Configurar `/abastecimientos/control-proyectos/` como bookmark

2. **Monitoreo Diario:**
   - Revisar métricas generales
   - Verificar sincronización automática
   - Controlar valor total abastecido

3. **Reportes:**
   - Exportar desde Admin Django
   - Filtrar por fechas en lista de abastecimientos
   - Usar API endpoints para Power BI

4. **Sincronización:**
   - Automática diaria a las 4 AM
   - Manual cuando se necesite datos inmediatos
   - Revisar logs en `logs/sync_abastecimientos_*.log`

5. **Alertas:**
   - Vigilar brocas sin serie (no se crea historial)
   - Verificar contratos sin centro de costo
   - Revisar errores en logs de sincronización

---

## 🔗 URLs Completas

```
# Dashboard Multi-Contrato (Control de Proyectos)
/abastecimientos/control-proyectos/

# Lista de Abastecimientos
/abastecimientos/

# Detalle de Abastecimiento
/abastecimientos/<id>/

# Dashboard Brocas Disponibles
/abastecimientos/brocas-disponibles/

# Historial de Brocas (general)
/historial-brocas/

# Historial de Broca Individual
/historial-brocas/<serie>/

# Admin Django
/admin/drilling/abastecimientoarticulo/
```

---

## 🎓 Capacitación para Control de Proyectos

### Flujo de Trabajo Típico

1. **Inicio del Día:**
   - Abrir Dashboard Multi-Contrato
   - Revisar totales generales
   - Verificar sincronización automática

2. **Revisión por Contrato:**
   - Click en "Ver Abastecimientos" de cada contrato
   - Filtrar por fechas recientes
   - Verificar brocas con serie

3. **Seguimiento de Brocas:**
   - Acceder a "Brocas Disponibles"
   - Revisar estados (Nuevas vs En Uso)
   - Verificar metraje acumulado

4. **Sincronización Manual (si necesario):**
   - Click en "Sincronizar Ahora"
   - Ingresar periodo (YYYYMM)
   - Seleccionar familia
   - Esperar confirmación

5. **Reportes y Análisis:**
   - Usar filtros de fecha
   - Exportar desde Admin Django
   - Revisar logs si hay problemas

---

**Última actualización:** Febrero 2026  
**Versión:** 1.0
