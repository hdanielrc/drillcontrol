# =============================================================================
# CHECKLIST DE IMPLEMENTACIÓN: TAREO V2
# =============================================================================
# Sistema de Asistencia Normalizado para DrillControl
# Fecha: Enero 2026
# =============================================================================

## 📋 FASE 1: PRE-IMPLEMENTACIÓN (PREPARACIÓN)

### 1.1 Backup de Base de Datos
- [ ] Realizar backup completo de la BD de producción
- [ ] Verificar que el backup sea restaurable
- [ ] Documentar versión actual del sistema

**Comando sugerido**:
```bash
# MySQL/MariaDB
mysqldump -u usuario -p nombre_bd > backup_pre_tareo_v2_$(date +%Y%m%d).sql

# PostgreSQL
pg_dump -U usuario nombre_bd > backup_pre_tareo_v2_$(date +%Y%m%d).sql
```

### 1.2 Revisión de Código
- [x] Modelo `AsistenciaDiaria` creado en `drilling/models.py`
- [x] Servicio `TareoService` en `drilling/utils/tareo_service.py`
- [x] Vista `tareo_v2_mensual_view` en `drilling/views_tareo_v2.py`
- [x] Template `tareo_v2_mensual.html` creado
- [x] Custom filters en `drilling/templatetags/custom_filters.py`
- [x] Comando Django `generar_proyeccion_tareo.py` creado
- [x] Tests en `drilling/tests_tareo_v2.py`
- [x] Documentación completa en `docs/`

### 1.3 Revisión de Dependencias
- [ ] Verificar versión de Django (>= 3.2 recomendado)
- [ ] Verificar paquetes instalados:
  - openpyxl (para exports Excel)
  - django (framework base)

**Comando**:
```bash
python manage.py --version
pip list | grep -E "django|openpyxl"
```

---

## 📦 FASE 2: MIGRACIÓN DE BASE DE DATOS

### 2.1 Generar Migraciones
- [ ] Ejecutar `makemigrations` para crear archivo de migración

**Comando**:
```bash
python manage.py makemigrations drilling
```

**Salida esperada**:
```
Migrations for 'drilling':
  drilling/migrations/0XXX_asistenciadiaria.py
    - Create model AsistenciaDiaria
    - Add constraint unique_empleado_fecha
    - Add indexes...
```

### 2.2 Revisar Archivo de Migración
- [ ] Abrir archivo generado en `drilling/migrations/0XXX_*.py`
- [ ] Verificar que incluya:
  - Creación de tabla `asistencia_diaria`
  - Constraint `unique_empleado_fecha`
  - Índices: `idx_empleado_fecha`, `idx_fecha_estado`, etc.

### 2.3 Ejecutar Migración en Desarrollo
- [ ] Ejecutar migración en entorno de desarrollo primero

**Comando**:
```bash
python manage.py migrate drilling
```

**Salida esperada**:
```
Operations to perform:
  Apply all migrations: drilling
Running migrations:
  Applying drilling.0XXX_asistenciadiaria... OK
```

### 2.4 Verificar Tabla Creada
- [ ] Conectar a BD y verificar tabla

**SQL**:
```sql
-- Verificar tabla
SHOW TABLES LIKE 'asistencia_diaria';

-- Verificar estructura
DESCRIBE asistencia_diaria;

-- Verificar índices
SHOW INDEX FROM asistencia_diaria;

-- Verificar constraint
SHOW CREATE TABLE asistencia_diaria;
```

### 2.5 Ejecutar Migración en Producción
- [ ] **IMPORTANTE**: Realizar en horario de bajo tráfico
- [ ] Poner aplicación en modo mantenimiento (opcional)
- [ ] Ejecutar migración

**Comando**:
```bash
python manage.py migrate drilling --database=default
```

- [ ] Verificar que no haya errores
- [ ] Reactivar aplicación

---

## ⚙️ FASE 3: CONFIGURACIÓN DEL SISTEMA

### 3.1 Configurar URLs
- [ ] Editar `drilling/urls.py`
- [ ] Agregar importaciones:

```python
from .views_tareo_v2 import (
    tareo_v2_mensual_view,
    api_generar_proyeccion,
    api_corregir_asistencia,
    tareo_v2_estadisticas
)
```

- [ ] Agregar rutas a `urlpatterns`:

```python
# Tareo V2
path('tareo/v2/', tareo_v2_mensual_view, name='tareo_v2_mensual'),
path('tareo/v2/api/generar-proyeccion/', api_generar_proyeccion, name='api_generar_proyeccion'),
path('tareo/v2/api/corregir/', api_corregir_asistencia, name='api_corregir_asistencia'),
path('tareo/v2/estadisticas/', tareo_v2_estadisticas, name='tareo_v2_estadisticas'),
```

- [ ] Guardar archivo
- [ ] Verificar sintaxis: `python manage.py check`

### 3.2 Configurar Trabajadores
- [ ] Verificar que todos los trabajadores tengan:

**Régimen laboral**:
```python
from drilling.models import Trabajador

# Ver trabajadores sin régimen
sin_regimen = Trabajador.objects.filter(
    estado='ACTIVO',
    regimen_laboral__isnull=True
)
print(f"Sin régimen: {sin_regimen.count()}")

# Asignar régimen por defecto (ajustar según caso)
sin_regimen.update(regimen_laboral='14x7')
```

**Fecha inicio de ciclo**:
```python
from datetime import date

# Ver trabajadores sin fecha
sin_fecha = Trabajador.objects.filter(
    estado='ACTIVO',
    fecha_inicio_ciclo__isnull=True
)
print(f"Sin fecha: {sin_fecha.count()}")

# Asignar fecha base (primer día del mes actual)
sin_fecha.update(fecha_inicio_ciclo=date(2026, 1, 1))
```

**Guardia asignada**:
```python
# Ver trabajadores sin guardia
sin_guardia = Trabajador.objects.filter(
    estado='ACTIVO',
    guardia_asignada__isnull=True
)
print(f"Sin guardia: {sin_guardia.count()}")

# Asignar guardia A por defecto
sin_guardia.update(guardia_asignada='A')
```

### 3.3 Ejecutar Script de Validación
- [ ] Ejecutar script de validación:

```bash
python manage.py shell < scripts/validar_tareo_v2.py
```

- [ ] Revisar resultados
- [ ] Corregir cualquier problema detectado
- [ ] Re-ejecutar hasta que todas las validaciones pasen

---

## 🧪 FASE 4: PRUEBAS

### 4.1 Tests Unitarios
- [ ] Ejecutar suite de tests:

```bash
python manage.py test drilling.tests_tareo_v2 -v 2
```

- [ ] Verificar que todos pasen
- [ ] Corregir tests fallidos si los hay

### 4.2 Prueba Manual - Generar Proyección
- [ ] Ejecutar comando de proyección:

```bash
python manage.py generar_proyeccion_tareo --mes 1 --anio 2026
```

- [ ] Verificar output:
  - `✅ Trabajadores procesados: X`
  - `✅ Registros creados: Y`
  - `✅ Sin errores`

- [ ] Verificar en BD:

```sql
SELECT COUNT(*) FROM asistencia_diaria WHERE es_proyeccion = 1;
SELECT estado, COUNT(*) FROM asistencia_diaria GROUP BY estado;
```

### 4.3 Prueba Manual - Interfaz Web
- [ ] Iniciar servidor: `python manage.py runserver`
- [ ] Acceder a: `http://localhost:8000/tareo/v2/`
- [ ] Verificar que cargue sin errores
- [ ] Verificar elementos visuales:
  - Header con navegación de meses
  - Tabla con scroll horizontal
  - Columnas fijas (Trabajador + Guardia)
  - Dropdowns de estado funcionando
  - Indicadores P (proyección) / ✓ (corrección)
  - Botón "Generar Proyección" funciona (AJAX)
  - Botón "Guardar" funciona

### 4.4 Prueba de Rendimiento
- [ ] Medir tiempo de carga de matriz con 70+ trabajadores
- [ ] Objetivo: < 1 segundo
- [ ] Usar herramientas: Django Debug Toolbar, Chrome DevTools

```python
import time
start = time.time()
# Cargar vista...
end = time.time()
print(f"Tiempo: {end - start:.2f}s")
```

### 4.5 Prueba de Guardado Masivo
- [ ] Cambiar múltiples estados (10-20)
- [ ] Hacer clic en "Guardar"
- [ ] Verificar mensaje de éxito
- [ ] Verificar cambios en BD

```sql
SELECT * FROM asistencia_diaria 
WHERE es_proyeccion = 0 
ORDER BY updated_at DESC 
LIMIT 10;
```

---

## 🚀 FASE 5: DESPLIEGUE A PRODUCCIÓN

### 5.1 Despliegue Gradual (Recomendado)

**Paso 1: Piloto con 1 contrato pequeño**
- [ ] Seleccionar contrato piloto (< 30 trabajadores)
- [ ] Comunicar a usuarios clave del contrato
- [ ] Activar acceso a Tareo V2 para ese contrato
- [ ] Monitorear uso durante 1 semana

**Paso 2: Validación con usuarios**
- [ ] Recopilar feedback de usuarios piloto
- [ ] Realizar ajustes si es necesario
- [ ] Confirmar que todo funciona correctamente

**Paso 3: Expansión gradual**
- [ ] Habilitar para 2-3 contratos más
- [ ] Monitorear por 3-5 días
- [ ] Continuar expansión progresiva

**Paso 4: Despliegue completo**
- [ ] Habilitar para todos los contratos
- [ ] Enviar comunicado general a usuarios
- [ ] Mantener Tareo V1 como fallback por 1 mes

### 5.2 Despliegue Directo (Alternativa)
- [ ] Realizar en horario de bajo tráfico
- [ ] Ejecutar migración: `python manage.py migrate`
- [ ] Generar proyección inicial para mes actual:

```bash
python manage.py generar_proyeccion_tareo
```

- [ ] Verificar que cargue correctamente
- [ ] Enviar comunicado a usuarios

### 5.3 Comunicación a Usuarios
- [ ] Preparar documento de capacitación
- [ ] Enviar correo con:
  - Nueva URL: `/tareo/v2/`
  - Cambios principales
  - Video tutorial (opcional)
  - Contacto de soporte

### 5.4 Monitoreo Post-Despliegue
- [ ] Configurar alertas de errores
- [ ] Monitorear logs de aplicación
- [ ] Revisar métricas de rendimiento
- [ ] Atender consultas de usuarios

---

## 📊 FASE 6: OPTIMIZACIÓN Y MEJORA CONTINUA

### 6.1 Métricas de Éxito (Semana 1)
- [ ] Tiempo de carga promedio < 1s
- [ ] Tiempo de guardado < 2s
- [ ] Tasa de error < 1%
- [ ] Satisfacción de usuarios > 4/5

### 6.2 Recopilar Feedback
- [ ] Encuesta a usuarios clave
- [ ] Reunión con managers de contrato
- [ ] Identificar puntos de mejora

### 6.3 Mejoras Iterativas
- [ ] Implementar sugerencias prioritarias
- [ ] Agregar features adicionales si es necesario:
  - Export a Excel desde V2
  - Reportes adicionales
  - Gráficos de tendencias

### 6.4 Deprecación de Tareo V1 (Opcional)
- [ ] Después de 1 mes de uso exitoso de V2
- [ ] Confirmar que no hay dependencias críticas en V1
- [ ] Mantener código de V1 por 3 meses adicionales
- [ ] Documentar diferencias para histórico

---

## 🔧 FASE 7: MANTENIMIENTO

### 7.1 Tareas Recurrentes

**Mensuales**:
- [ ] Verificar índices de BD (optimización)
- [ ] Revisar logs de errores
- [ ] Actualizar documentación si hay cambios

**Trimestrales**:
- [ ] Revisar rendimiento (query optimization)
- [ ] Actualizar tests con nuevos casos
- [ ] Backup de código y BD

### 7.2 Actualizaciones Futuras
- [ ] Mantener Django actualizado
- [ ] Actualizar dependencias de seguridad
- [ ] Revisar nuevas features de Django para optimizaciones

---

## 🆘 TROUBLESHOOTING

### Problema: Migración falla

**Solución**:
1. Verificar que no haya conflictos con migraciones previas
2. Revisar logs de error
3. Rollback: `python manage.py migrate drilling XXXX` (número anterior)
4. Corregir migración y re-intentar

### Problema: Proyección no genera registros

**Solución**:
1. Verificar trabajadores activos: `Trabajador.objects.filter(estado='ACTIVO').count()`
2. Verificar configuración: `regimen_laboral`, `fecha_inicio_ciclo`
3. Revisar logs: `python manage.py shell` y ejecutar función manualmente

### Problema: Vista carga lenta

**Solución**:
1. Activar Django Debug Toolbar
2. Revisar queries duplicadas
3. Agregar `select_related` / `prefetch_related` donde corresponda
4. Verificar índices en BD

### Problema: Error al guardar

**Solución**:
1. Verificar permisos de usuario
2. Revisar formato de datos enviados (F12 → Network)
3. Verificar transacciones en BD
4. Revisar logs de error de Django

---

## ✅ RESUMEN FINAL

**Estado Actual de Archivos**:
- [x] Modelo creado y documentado
- [x] Servicio implementado y testeado
- [x] Vista con transformación pivot
- [x] Template optimizado con CSS/JS
- [x] Custom filters
- [x] Comando Django CLI
- [x] Tests unitarios (15+ casos)
- [x] Documentación completa (4 archivos)
- [x] Script de validación
- [ ] URLs configuradas (PENDIENTE - manual)
- [ ] Migración ejecutada (PENDIENTE - manual)
- [ ] Proyección inicial generada (PENDIENTE - manual)

**Próximos Pasos Inmediatos**:
1. ✅ Revisar este checklist completo
2. ⬜ Configurar URLs en `drilling/urls.py`
3. ⬜ Ejecutar migraciones: `python manage.py makemigrations && python manage.py migrate`
4. ⬜ Configurar trabajadores (régimen, fecha, guardia)
5. ⬜ Ejecutar validación: `python scripts/validar_tareo_v2.py`
6. ⬜ Generar proyección: `python manage.py generar_proyeccion_tareo`
7. ⬜ Acceder a `/tareo/v2/` y probar
8. ⬜ Capacitar usuarios clave
9. ⬜ Desplegar a producción (gradual o directo)
10. ⬜ Monitorear y optimizar

---

**Fecha de creación del checklist**: Enero 2026  
**Versión**: 1.0  
**Autor**: Sistema DrillControl  
**Estado**: ✅ LISTO PARA IMPLEMENTACIÓN

---

**NOTAS IMPORTANTES**:
- ⚠️  **SIEMPRE** hacer backup antes de migrar en producción
- ⚠️  Probar en desarrollo/staging primero
- ⚠️  Desplegar en horarios de bajo tráfico
- ⚠️  Mantener V1 como fallback durante transición
- ⚠️  Documentar cualquier problema encontrado

**CONTACTO SOPORTE**:
- Documentación: `docs/MIGRACION_TAREO_V2.md`
- Ejemplos: `docs/EJEMPLOS_USO_TAREO_V2.py`
- Tests: `drilling/tests_tareo_v2.py`
- Validación: `scripts/validar_tareo_v2.py`

---

¡Buena suerte con la implementación! 🚀
