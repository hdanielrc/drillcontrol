# 📊 Guía de Reporte de Horas Extras por Trabajador

## 📝 Descripción

Este módulo permite visualizar y exportar reportes detallados de las horas extras otorgadas a los trabajadores basándose en el metraje de avance de los turnos.

## 🎯 Características Principales

### 1. **Filtros Avanzados**
- **Rango de Fechas**: Filtra por fecha de inicio y fin
- **Contrato**: Selecciona contratos específicos (solo para administradores)
- **DNI Trabajador**: Busca por DNI específico de trabajador

### 2. **Estadísticas en Tiempo Real**
- ✅ Total de horas extras acumuladas
- 📅 Total de turnos con horas extras
- 👥 Total de trabajadores beneficiados

### 3. **Dos Vistas de Datos**

#### A) Resumen por Trabajador
Tabla consolidada con:
- DNI y nombre completo del trabajador
- Cargo
- Cantidad de turnos realizados
- Total de horas extras acumuladas
- Promedio de horas por turno

#### B) Detalle por Turno
Tabla detallada con:
- Fecha del turno
- Link al turno completo
- Trabajador beneficiado
- Metros del turno que generaron las horas extras
- Configuración aplicada
- Observaciones

### 4. **Exportación a Excel**
- Exporta el resumen por trabajador
- Exporta el detalle completo por turno
- Formato profesional con ajuste automático de columnas
- Atajos de teclado: `Ctrl+E` (resumen) y `Ctrl+D` (detalle)

## 🔐 Permisos de Acceso

### Usuarios con Acceso
✅ **Administradores del Sistema**: Acceso completo a todos los contratos
✅ **Supervisores**: Acceso a los datos de su contrato
❌ **Operadores**: Sin acceso al reporte

## 🚀 Cómo Usar

### Acceso al Reporte

**Opción 1: Desde el Menú de Turnos**
1. Ir a `Turnos` en el menú superior
2. Seleccionar `Horas Extras`

**Opción 2: Desde Configuración (Admin)**
1. Ir a `Configuración` en el menú superior
2. Seleccionar `Reporte Horas Extras`

### Filtrar Datos

1. **Por Rango de Fechas**:
   - Selecciona fecha inicio y fin
   - Click en "Buscar"

2. **Por Trabajador Específico**:
   - Ingresa el DNI en el campo correspondiente
   - Click en "Buscar"

3. **Limpiar Filtros**:
   - Click en "Limpiar Filtros"

### Exportar Reportes

**Método 1: Botones en Pantalla**
- Click en "Exportar Excel" en cada sección

**Método 2: Atajos de Teclado**
- `Ctrl + E`: Exporta resumen por trabajador
- `Ctrl + D`: Exporta detalle por turno

## 📊 Ejemplo de Uso

### Caso: Revisar horas extras del mes de noviembre

1. Ingresa al reporte desde `Turnos > Horas Extras`
2. Configura los filtros:
   - Fecha inicio: `01/11/2024`
   - Fecha fin: `30/11/2024`
3. Click en "Buscar"
4. Revisa las estadísticas en las tarjetas superiores
5. Analiza el resumen por trabajador
6. Si necesitas detalles, revisa la tabla inferior
7. Exporta a Excel con `Ctrl + E`

### Caso: Verificar horas extras de un trabajador específico

1. Ingresa al reporte
2. Ingresa el DNI del trabajador (ej: `12345678`)
3. Click en "Buscar"
4. Revisa el resumen y detalle del trabajador
5. Exporta si es necesario

## 🔧 Configuración de Horas Extras

Para configurar las reglas de cálculo de horas extras:

1. Ir a `Configuración > Gestionar Horas Extras`
2. Seleccionar el contrato
3. Configurar:
   - Metraje mínimo requerido
   - Cantidad de horas extras a otorgar
   - Activar/desactivar la regla
4. Guardar configuración

## 📈 Interpretación de Datos

### Tarjetas de Estadísticas
- **Total Horas Extras**: Suma de todas las horas extras en el período filtrado
- **Total Turnos**: Cantidad de turnos que generaron horas extras
- **Total Trabajadores**: Cantidad de trabajadores únicos beneficiados

### Tabla Resumen
- **Cantidad Turnos**: Número de turnos en los que el trabajador obtuvo horas extras
- **Total Horas Extras**: Suma de todas las horas extras del trabajador
- **Promedio x Turno**: Promedio de horas extras por turno

### Tabla Detalle
- **Metros Turno**: Metraje de avance que generó las horas extras
- **Configuración**: Indica si se aplicó una regla automática o fue manual
- Click en el número de turno para ver detalles completos

## 🎨 Características de Interfaz

- ✨ Diseño responsivo (funciona en móviles y tablets)
- 🎯 Tooltips informativos al pasar el mouse
- 🔍 Tablas con hover para mejor lectura
- 📱 Compatible con todos los navegadores modernos
- ⚡ Carga rápida de datos (primeros 100 registros)

## 🐛 Solución de Problemas

### No aparecen datos
- ✅ Verifica que existan turnos con horas extras en el período
- ✅ Revisa que la configuración de horas extras esté activa
- ✅ Confirma que los turnos tienen metraje de avance registrado

### No se puede exportar a Excel
- ✅ Verifica que tu navegador permita descargas
- ✅ Comprueba que haya datos en la tabla
- ✅ Intenta con otro navegador si persiste el problema

### No veo el enlace en el menú
- ✅ Confirma que tu usuario tiene rol de Supervisor o superior
- ✅ Refresca la página (F5)
- ✅ Verifica que estés autenticado correctamente

## 📞 Soporte

Para problemas o consultas adicionales:
- Contacta al administrador del sistema
- Revisa la documentación de configuración de horas extras
- Verifica los logs del sistema para errores

## 🔄 Actualizaciones Futuras

Próximas mejoras planificadas:
- [ ] Gráficos de tendencias
- [ ] Exportación a PDF
- [ ] Filtros adicionales por cargo o área
- [ ] Comparativas entre períodos
- [ ] Dashboard ejecutivo

---

**Última actualización**: Noviembre 2024
**Versión**: 1.0
