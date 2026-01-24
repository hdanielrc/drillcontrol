# SISTEMA DE CIERRE MENSUAL Y AUDITORÍA DE TAREO
## Control Contable para Pagos y Nómina

---

## 🎯 OBJETIVO

Implementar un sistema de **cierre mensual auditable** que separe:

1. **Proyección Inicial** → Logística (refrigerios, campamento, transporte)
2. **Registro Real** → Pagos, nómina, contabilidad
3. **Cierre Contable** → Congelación de datos, auditoría completa

---

## 📋 FLUJO OPERATIVO

### **Inicio de Mes**
```
1. Sistema genera PROYECCIÓN automática
   ├─ Basado en régimen laboral (14x7, 20x10, etc.)
   ├─ Propósito: Logística (comprar refrigerios, reservar camas)
   └─ Estado: es_proyeccion=True

2. Mes queda en estado ABIERTO
   └─ Editable por supervisores/managers
```

### **Durante el Mes**
```
3. Supervisores registran asistencia REAL día a día
   ├─ Confirman proyecciones o las corrigen
   ├─ Cada cambio queda registrado en auditoría
   └─ Estado: es_proyeccion=False (registro real)

4. Sistema registra TODOS los cambios
   ├─ Quién modificó
   ├─ Cuándo
   ├─ Qué cambió (estado anterior → estado nuevo)
   └─ Motivo (opcional)
```

### **Fin de Mes**
```
5. Manager revisa resumen del mes
   ├─ Verifica que no queden proyecciones sin confirmar
   ├─ Revisa totales por trabajador
   └─ Valida datos antes de cerrar

6. Manager CIERRA el mes
   ├─ Sistema calcula estadísticas finales
   ├─ Estado cambia a CERRADO
   ├─ Datos quedan INMUTABLES
   └─ Se genera snapshot para nómina

7. Contabilidad/RRHH accede al reporte
   ├─ Solo meses cerrados
   ├─ Exporta a Excel para nómina
   └─ Datos garantizados (sin cambios posteriores)
```

### **Post-Cierre (Excepcional)**
```
8. Si hay error crítico:
   ├─ Solo ADMIN puede reabrir
   ├─ Requiere motivo detallado (>10 caracteres)
   ├─ Se registra en auditoría
   └─ Quedan marcados los cambios post-cierre
```

---

## 🗃️ MODELOS IMPLEMENTADOS

### 1. **CierreMensualTareo**
Registra el estado contable de cada mes.

```python
{
    'contrato': ForeignKey(Contrato),
    'anio': 2026,
    'mes': 1,
    'estado': 'CERRADO',  # ABIERTO | EN_REVISION | CERRADO | REABIERTO
    
    # Estadísticas (snapshot)
    'total_trabajadores': 85,
    'total_dias_trabajo': 1190,
    'total_dias_descanso': 595,
    'total_faltas': 12,
    'total_vacaciones': 45,
    'total_permisos': 8,
    
    # Auditoría
    'fecha_cierre': datetime(2026, 2, 1, 10, 30),
    'cerrado_por': User(nombre='Juan Manager'),
    'observaciones': 'Mes cerrado para nómina febrero',
    
    # Reapertura (excepcional)
    'fecha_reapertura': None,
    'reabierto_por': None,
    'motivo_reapertura': ''
}
```

### 2. **HistorialCambioAsistencia**
Auditoría completa de cada cambio.

```python
{
    'asistencia': ForeignKey(AsistenciaDiaria),
    
    # Estado antes del cambio
    'estado_anterior': 'TRABAJO',
    'es_proyeccion_anterior': True,
    
    # Estado después del cambio
    'estado_nuevo': 'FALTA',
    'es_proyeccion_nuevo': False,
    
    # Auditoría
    'fecha_cambio': datetime(2026, 1, 15, 14, 25),
    'usuario': User(nombre='Supervisor Pedro'),
    'motivo': 'Trabajador no se presentó',
    'ip_address': '192.168.1.100',
    
    # Contexto
    'mes_cerrado': False  # Cambio en mes abierto (normal)
}
```

---

## 🔧 SERVICIOS IMPLEMENTADOS

### **CierreMensualService**

#### `cerrar_mes(contrato, anio, mes, usuario, observaciones)`
```python
# Cierra contablemente un mes
resultado = CierreMensualService.cerrar_mes(
    contrato=mi_contrato,
    anio=2026,
    mes=1,
    usuario=request.user,
    observaciones='Mes validado, listo para nómina'
)

# Respuesta:
{
    'success': True,
    'cierre': <CierreMensualTareo>,
    'mensaje': 'Mes 1/2026 cerrado exitosamente'
}

# O si hay error:
{
    'success': False,
    'error': 'Hay 45 proyecciones sin confirmar',
    'proyecciones_pendientes': 45
}
```

#### `reabrir_mes(contrato, anio, mes, usuario, motivo)`
```python
# Reabre un mes cerrado (excepcional)
resultado = CierreMensualService.reabrir_mes(
    contrato=mi_contrato,
    anio=2026,
    mes=1,
    usuario=request.user,
    motivo='Error en cálculo de vacaciones detectado por auditoría'
)
```

#### `obtener_resumen_mes(contrato, anio, mes)`
```python
# Obtiene resumen completo del mes antes de cerrar
resumen = CierreMensualService.obtener_resumen_mes(
    contrato=mi_contrato,
    anio=2026,
    mes=1
)

# Retorna:
{
    'resumen_trabajadores': [
        {
            'trabajador': <Trabajador>,
            'total_dias': 31,
            'proyecciones': 0,  # Debe ser 0 para cerrar
            'reales': 31,
            'trabajo': 21,
            'descanso': 10,
            'faltas': 0,
            'completo': True
        },
        ...
    ],
    'totales': {
        'trabajadores': 85,
        'dias_esperados': 2635,  # 85 trabajadores * 31 días
        'proyecciones_pendientes': 0,
        'registros_reales': 2635,
        'total_trabajo': 1785,
        'total_descanso': 850
    },
    'listo_para_cerrar': True  # True si proyecciones_pendientes == 0
}
```

### **AuditoriaAsistenciaService**

#### `registrar_cambio(...)`
```python
# Se llama automáticamente al modificar una asistencia
historial = AuditoriaAsistenciaService.registrar_cambio(
    asistencia=asistencia_obj,
    estado_anterior='TRABAJO',
    es_proyeccion_anterior=True,
    usuario=request.user,
    motivo='Corrección por falta justificada',
    ip_address=request.META.get('REMOTE_ADDR')
)
```

#### `obtener_historial_trabajador(trabajador, fecha_inicio, fecha_fin)`
```python
# Obtiene historial completo de cambios
historial = AuditoriaAsistenciaService.obtener_historial_trabajador(
    trabajador=trabajador_obj,
    fecha_inicio=date(2026, 1, 1),
    fecha_fin=date(2026, 1, 31)
)
# Retorna QuerySet de HistorialCambioAsistencia ordenado por fecha
```

#### `obtener_cambios_post_cierre(contrato, anio, mes)`
```python
# Encuentra cambios realizados DESPUÉS del cierre (para auditoría)
resultado = AuditoriaAsistenciaService.obtener_cambios_post_cierre(
    contrato=mi_contrato,
    anio=2026,
    mes=1
)

# Retorna:
{
    'cierre': <CierreMensualTareo>,
    'cambios': <QuerySet[HistorialCambioAsistencia]>,
    'total_cambios': 3  # Número de cambios post-cierre
}
```

---

## 🌐 VISTAS Y URLS

### Vistas Implementadas:

1. **`tareo_cierre_mensual`** → `/tareo/v2/cierre-mensual/`
   - Muestra resumen del mes
   - Permite cerrar o reabrir
   - Solo managers/admins

2. **`tareo_historial_trabajador`** → `/tareo/v2/historial/<trabajador_id>/`
   - Historial completo de cambios por trabajador
   - Filtrable por fechas
   - Paginado (50 registros por página)

3. **`tareo_reporte_nomina`** → `/tareo/v2/reporte-nomina/`
   - Reporte para pagos y nómina
   - Solo muestra meses CERRADOS
   - Exportable a Excel

### APIs Implementadas:

1. **`api_cerrar_mes`** → POST `/tareo/v2/api/cerrar-mes/`
   ```javascript
   fetch('/tareo/v2/api/cerrar-mes/', {
       method: 'POST',
       headers: {
           'X-CSRFToken': csrf_token,
           'Content-Type': 'application/x-www-form-urlencoded'
       },
       body: `contrato_id=${contratoId}&mes=${mes}&anio=${anio}&observaciones=${obs}`
   })
   ```

2. **`api_reabrir_mes`** → POST `/tareo/v2/api/reabrir-mes/`
   ```javascript
   fetch('/tareo/v2/api/reabrir-mes/', {
       method: 'POST',
       body: `contrato_id=${contratoId}&mes=${mes}&anio=${anio}&motivo=${motivo}`
   })
   ```

3. **`api_exportar_nomina_excel`** → GET `/tareo/v2/exportar-nomina/<cierre_id>/`
   - Descarga Excel con datos del mes cerrado
   - Formato listo para sistema de nómina

---

## 📝 CONFIGURACIÓN DE URLs

Agregar a `drilling/urls.py`:

```python
from .views_tareo_v2 import (
    # ... vistas existentes ...
    tareo_cierre_mensual,
    tareo_historial_trabajador,
    tareo_reporte_nomina,
    api_cerrar_mes,
    api_reabrir_mes,
    api_exportar_nomina_excel,
)

urlpatterns = [
    # ... URLs existentes ...
    
    # Cierre mensual y auditoría
    path('tareo/v2/cierre-mensual/', tareo_cierre_mensual, name='tareo_cierre_mensual'),
    path('tareo/v2/historial/<int:trabajador_id>/', tareo_historial_trabajador, name='tareo_historial_trabajador'),
    path('tareo/v2/reporte-nomina/', tareo_reporte_nomina, name='tareo_reporte_nomina'),
    
    # APIs
    path('tareo/v2/api/cerrar-mes/', api_cerrar_mes, name='api_cerrar_mes'),
    path('tareo/v2/api/reabrir-mes/', api_reabrir_mes, name='api_reabrir_mes'),
    path('tareo/v2/exportar-nomina/<int:cierre_id>/', api_exportar_nomina_excel, name='api_exportar_nomina_excel'),
]
```

---

## 🚀 PASOS DE IMPLEMENTACIÓN

### **PASO 1: Migración de Base de Datos**

```bash
# Crear migraciones
python manage.py makemigrations drilling

# Revisar migración generada
# Debe crear las tablas:
# - cierre_mensual_tareo
# - historial_cambio_asistencia

# Aplicar migración
python manage.py migrate drilling
```

### **PASO 2: Configurar URLs**

Agregar las nuevas rutas en `drilling/urls.py` (código arriba).

### **PASO 3: Crear Templates**

Necesitas crear 3 templates nuevos:

1. **`drilling/templates/drilling/tareo/cierre_mensual.html`**
   - Formulario de revisión y cierre
   - Tabla con resumen por trabajador
   - Botón "Cerrar Mes" (solo si listo)

2. **`drilling/templates/drilling/tareo/historial_trabajador.html`**
   - Timeline de cambios del trabajador
   - Filtros por fecha
   - Paginación

3. **`drilling/templates/drilling/tareo/reporte_nomina.html`**
   - Tabla con días por tipo de asistencia
   - Selector de mes cerrado
   - Botón "Exportar a Excel"

### **PASO 4: Modificar Template Existente**

En `drilling/templates/drilling/tareo/tareo_v2_mensual.html`, agregar:

```html
<!-- Al inicio, después del título -->
{% if cierre_mes %}
    {% if cierre_mes.estado == 'CERRADO' %}
    <div class="alert alert-warning">
        <i class="fas fa-lock me-2"></i>
        <strong>Mes Cerrado</strong> - Este mes fue cerrado el {{ cierre_mes.fecha_cierre|date:"d/m/Y H:i" }} 
        por {{ cierre_mes.cerrado_por }}. Los cambios no están permitidos.
        {% if user.is_staff %}
        <a href="#" class="btn btn-sm btn-danger ms-3" onclick="reabrirMes()">
            <i class="fas fa-unlock me-1"></i> Reabrir Mes
        </a>
        {% endif %}
    </div>
    {% elif cierre_mes.estado == 'ABIERTO' %}
    <div class="alert alert-info">
        <i class="fas fa-edit me-2"></i>
        <strong>Mes Abierto</strong> - Puede editar libremente las asistencias.
        <a href="{% url 'tareo_cierre_mensual' %}?contrato={{ contrato.id }}&mes={{ mes }}&anio={{ anio }}" 
           class="btn btn-sm btn-primary ms-3">
            <i class="fas fa-check-circle me-1"></i> Revisar y Cerrar Mes
        </a>
    </div>
    {% endif %}
{% endif %}
```

### **PASO 5: Actualizar Vista Principal**

En `views_tareo_v2.py`, modificar `tareo_v2_mensual_view`:

```python
def tareo_v2_mensual_view(request):
    # ... código existente ...
    
    # AGREGAR: Obtener estado del cierre
    from ..utils.tareo_service import CierreMensualService
    cierre_mes = CierreMensualService.obtener_o_crear_cierre(
        contrato=contrato,
        anio=anio,
        mes=mes
    )
    
    # Verificar si puede editar
    puede_editar = cierre_mes.puede_editarse()
    
    # Agregar al context
    context = {
        # ... variables existentes ...
        'cierre_mes': cierre_mes,
        'puede_editar': puede_editar,
    }
```

### **PASO 6: Validar Ediciones**

En la vista POST de `tareo_v2_mensual_view`, agregar validación:

```python
if request.method == 'POST':
    # AGREGAR al inicio:
    if not cierre_mes.puede_editarse():
        messages.error(request, 'No puede editar un mes cerrado. Contacte al administrador.')
        return redirect('tareo_v2_mensual')
    
    # ... resto del código de procesamiento ...
```

---

## 📊 CASOS DE USO

### **Caso 1: Cierre Normal de Mes**

```python
# 1. Manager revisa el mes
resumen = CierreMensualService.obtener_resumen_mes(contrato, 2026, 1)

if resumen['listo_para_cerrar']:
    # 2. Cierra el mes
    resultado = CierreMensualService.cerrar_mes(
        contrato=contrato,
        anio=2026,
        mes=1,
        usuario=request.user,
        observaciones='Mes validado, listo para nómina'
    )
    
    # 3. RRHH genera reporte
    # Accede a tareo_reporte_nomina
    # Exporta Excel
```

### **Caso 2: Auditoría de Trabajador**

```python
# Obtener historial completo
historial = AuditoriaAsistenciaService.obtener_historial_trabajador(
    trabajador=trabajador,
    fecha_inicio=date(2026, 1, 1),
    fecha_fin=date(2026, 1, 31)
)

# Mostrar en vista
for cambio in historial:
    print(f"{cambio.fecha_cambio}: {cambio.estado_anterior} → {cambio.estado_nuevo}")
    print(f"   Por: {cambio.usuario}")
    print(f"   Motivo: {cambio.motivo}")
```

### **Caso 3: Corrección Post-Cierre (Excepcional)**

```python
# 1. Admin detecta error en mes cerrado
# 2. Reabre el mes
resultado = CierreMensualService.reabrir_mes(
    contrato=contrato,
    anio=2026,
    mes=1,
    usuario=request.user,
    motivo='Error en cálculo de vacaciones detectado en auditoría externa'
)

# 3. Realiza correcciones
# (Se registran en auditoría con mes_cerrado=True)

# 4. Vuelve a cerrar
resultado = CierreMensualService.cerrar_mes(...)
```

---

## 🔒 SEGURIDAD Y PERMISOS

### **Niveles de Acceso:**

| Rol | Ver Tareo | Editar Tareo | Cerrar Mes | Reabrir Mes | Ver Auditoría |
|-----|-----------|--------------|------------|-------------|---------------|
| Operador | ❌ | ❌ | ❌ | ❌ | ❌ |
| Supervisor | ✅ | ✅ (mes abierto) | ❌ | ❌ | ✅ |
| Manager | ✅ | ✅ (mes abierto) | ✅ | ❌ | ✅ |
| Admin | ✅ | ✅ (siempre) | ✅ | ✅ | ✅ |

### **Validaciones Implementadas:**

1. ✅ No se puede cerrar con proyecciones pendientes
2. ✅ No se puede editar un mes cerrado (excepto admin con reapertura)
3. ✅ Reapertura requiere motivo detallado (>10 caracteres)
4. ✅ Todos los cambios quedan registrados en auditoría
5. ✅ Cambios post-cierre quedan marcados especialmente

---

## 📈 REPORTES GENERADOS

### **1. Resumen de Cierre**
- Total trabajadores
- Días trabajo / descanso / faltas / vacaciones
- Proyecciones pendientes
- Estado de completitud por trabajador

### **2. Reporte de Nómina (Excel)**
Columnas:
- DNI
- Apellidos, Nombres
- Cargo
- Régimen laboral
- Días Trabajo
- Días Descanso
- Faltas
- Vacaciones
- Permisos
- Descanso Médico
- Total Días

### **3. Historial de Auditoría**
- Fecha/hora del cambio
- Usuario
- Estado anterior → Estado nuevo
- Proyección → Real
- Motivo
- IP del usuario

---

## ✅ CHECKLIST DE VALIDACIÓN

Antes de cerrar un mes, verificar:

- [ ] Todos los días tienen registro (31/31 días)
- [ ] No hay proyecciones pendientes de confirmar
- [ ] Faltas están justificadas o documentadas
- [ ] Vacaciones tienen aprobación
- [ ] Permisos tienen documento de respaldo
- [ ] Datos revisados por supervisor
- [ ] Datos validados por manager
- [ ] Observaciones relevantes agregadas

---

## 🎓 CAPACITACIÓN

### **Para Supervisores:**
1. Registrar asistencia real diariamente
2. Confirmar o corregir proyecciones
3. Agregar observaciones cuando sea necesario
4. Notificar a manager cuando mes esté completo

### **Para Managers:**
1. Revisar resumen mensual
2. Validar datos antes de cerrar
3. Cerrar mes al final del periodo
4. Coordinar con RRHH para nómina

### **Para RRHH/Contabilidad:**
1. Acceder solo a meses cerrados
2. Descargar reporte de nómina
3. Validar totales con sistema de pagos
4. Reportar inconsistencias a manager

---

## 📞 SOPORTE

Para más información o problemas:
- Revisar logs: `logs/tareo_service.log`
- Revisar historial de auditoría en base de datos
- Contactar a administrador del sistema

---

**Documento creado**: Enero 2026  
**Sistema**: DrillControl - Tareo V2  
**Versión**: 1.0
