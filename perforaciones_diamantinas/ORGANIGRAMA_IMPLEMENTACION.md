# Implementación del Organigrama Jerárquico - 4 Niveles

## ⚠️ IMPORTANTE - ALCANCE Y LIMITACIONES

### Este organigrama es SOLO para visualización esquemática

El campo `maquina_asignada` en el modelo `Trabajador` es **ÚNICAMENTE para representación visual** en el organigrama. 

**NO afecta ni reemplaza:**
- ✅ Asignación de trabajadores a turnos (`TurnoTrabajador`)
- ✅ Registro de actividades por turno (`TurnoActividad`)
- ✅ Reportes de sondajes y avances
- ✅ Cualquier otra lógica operativa existente

**Características del campo:**
- Completamente **OPCIONAL** (`null=True, blank=True`)
- No requiere validación obligatoria
- Puede dejarse vacío sin afectar el sistema
- Solo sirve para mostrar estructura organizacional visual

### Las asignaciones operativas reales se manejan mediante:
1. **TurnoTrabajador**: Asigna trabajadores específicos a turnos
2. **TurnoActividad**: Registra actividades realizadas en cada turno
3. **Sondaje**: Define trabajos y ubicaciones específicas

**El organigrama NO interfiere con ninguno de estos procesos.**

---

## 📋 Resumen

Se ha implementado un **organigrama visual y descargable** de 4 niveles jerárquicos para mostrar la estructura organizacional de los trabajadores por contrato. El nivel 4 agrupa a los trabajadores operativos por máquina asignada (perforistas + ayudantes por equipo).

## ✅ Cambios Realizados

### 1. Modelo de Datos (`drilling/models.py`)

**Modelo `Cargo`:**
- ✅ `nivel_jerarquico` (IntegerField): Nivel jerárquico del cargo (1-4)
- ✅ `cargo_superior` (ForeignKey): Relación de reporte jerárquico

**Modelo `Trabajador`:**
- ✅ `maquina_asignada` (ForeignKey): Máquina asignada al trabajador (Nivel 4)

### 2. Migraciones

- ✅ **Migration 0040**: Añadió `nivel_jerarquico` y `cargo_superior` a `Cargo`
- ✅ **Migration 0041**: Añadió `maquina_asignada` a `Trabajador`

### 3. Scripts de Configuración

**`actualizar_jerarquia_cargos.py`:**
- Asigna niveles jerárquicos a todos los cargos existentes
- **Nivel 1**: RESIDENTE
- **Nivel 2**: Administrativos (21 cargos)
  - ADMINISTRADOR, JEFE LOGÍSTICA, ING. SEGURIDAD SENIOR, etc.
- **Nivel 3**: Supervisores (5 cargos)
  - SUPERVISOR, SUPERVISOR OPERATIVO-I, ASISTENTE DE OPERACIONES
- **Nivel 4**: Operaciones (13 cargos)
  - PERFORISTA DDH-I/II, AYUDANTE PERFORISTA, TÉCNICO MECÁNICO, CONDUCTOR, etc.

**`fix_cargos_faltantes.py`:**
- Corrige cargos con espacios extras (RESIDENTE, ADMINISTRADOR, ING SEGURIDAD)

### 4. Vistas

**`drilling/views_organigrama.py`:**
- `organigrama_view()`: Vista principal del organigrama
- Filtra trabajadores activos del contrato seleccionado
- Agrupa trabajadores por nivel jerárquico (1-4)
- Para **Nivel 4**: Agrupa por máquina asignada clasificando:
  - **Perforistas**: Cargos con "perforista" en el nombre
  - **Ayudantes**: Cargos con "ayudante" en el nombre
  - **Otros**: Resto de cargos operativos
- Lista trabajadores sin máquina asignada

**`drilling/api_organigrama.py`:**
- `asignar_maquina_trabajador()`: API AJAX para asignación dinámica
- Método: POST
- Parámetros: `trabajador_id`, `maquina_id`
- Valida permisos del usuario según contrato
- Retorna JSON con resultado de la asignación

### 5. URLs (`drilling/urls.py`)

```python
path('organigrama/', organigrama_view, name='organigrama'),
path('api/organigrama/asignar-maquina/', asignar_maquina_trabajador, name='api-asignar-maquina'),
```

### 6. Templates

**`drilling/templates/drilling/organigrama/view.html`:**
- 📊 **Diseño visual en cascada** con 4 niveles diferenciados
- 🎨 **Colores distintos por nivel**:
  - Nivel 1: Rosa/Rojo (RESIDENTE)
  - Nivel 2: Azul/Cian (Administrativos)
  - Nivel 3: Verde (Supervisores)
  - Nivel 4: Amarillo/Rosa (Operaciones)
- 🏗️ **Tarjetas de máquina** que agrupan:
  - Perforistas (icono ⭐)
  - Ayudantes (icono 🤝)
  - Otros trabajadores
- ⚠️ **Sección "Sin Máquina Asignada"** con botón "Asignar"
- 📥 **Descarga como PNG** con `html2canvas.js`
- 🔄 **Modal de asignación dinámica** con dropdown de máquinas

**Navegación añadida en:**
- `drilling/templates/drilling/base_manager.html`: Menú TRABAJADORES → Organigrama
- `drilling/templates/drilling/base_admin.html`: Menú Gestión → Organigrama

### 7. Formularios (`drilling/forms.py`)

**`TrabajadorForm`:**
- ✅ Campo `maquina_asignada` añadido
- ✅ Widget: `forms.Select` con clase Bootstrap
- ✅ Filtrado automático de máquinas por contrato del usuario
- ✅ Solo muestra máquinas activas

## 🎯 Jerarquía de 4 Niveles

### Nivel 1: Dirección
- **RESIDENTE** (único cargo)
- Aparece centrado en la parte superior

### Nivel 2: Gerencias
- Administrativos, Logística, Seguridad
- Distribuidos horizontalmente: Admin → Logística → Seguridad
- 21 cargos: ADMINISTRADOR, ASISTENTE DE RESIDENTE, JEFE ZONAL, SUPERVISOR OPERATIVO-I, ING. SEGURIDAD SENIOR, etc.

### Nivel 3: Supervisión
- Supervisores operativos
- 5 cargos: SUPERVISOR, SUPERVISOR OPERATIVO-I, ASISTENTE DE OPERACIONES

### Nivel 4: Operaciones (Agrupado por Máquina)
- **Perforistas** (cargo contiene "perforista")
- **Ayudantes** (cargo contiene "ayudante")
- **Otros** (técnicos, conductores, etc.)
- 13 cargos: PERFORISTA DDH-I/II, AYUDANTE PERFORISTA, AYUDANTE DDH-I/II, TECNICO MECANICO-I/II, CONDUCTOR, etc.

## 🔧 Funcionalidades

### 1. Visualización
- ✅ Organigrama en cascada con 4 niveles
- ✅ Tarjetas de trabajador con avatar, nombre, cargo
- ✅ Tarjetas de máquina agrupando equipo de trabajo
- ✅ Colores diferenciados por nivel
- ✅ Responsive (adaptable a móviles)

### 2. Asignación de Máquinas
- ✅ **Formulario de trabajador**: Campo `maquina_asignada` en creación/edición
- ✅ **Modal dinámica**: Click en "Asignar" abre modal con selector de máquina
- ✅ **API AJAX**: Asignación sin recargar página
- ✅ **Validación de permisos**: Solo usuarios autorizados pueden asignar

### 3. Descarga
- ✅ **Botón "Descargar PNG"**: Captura el organigrama completo
- ✅ Usa `html2canvas.js` versión 1.4.1
- ✅ Nombre del archivo: `organigrama_[nombre-contrato]_[fecha].png`
- ✅ Alta calidad (escala 2x)

### 4. Selector de Contrato
- ✅ Usuario ADMIN puede ver todos los contratos
- ✅ Dropdown para seleccionar contrato
- ✅ Usuario MANAGER ve solo su contrato

## 📂 Archivos Creados/Modificados

### Creados
```
drilling/views_organigrama.py
drilling/api_organigrama.py
drilling/templates/drilling/organigrama/view.html
actualizar_jerarquia_cargos.py
fix_cargos_faltantes.py
ORGANIGRAMA_IMPLEMENTACION.md (este archivo)
```

### Modificados
```
drilling/models.py
drilling/forms.py
drilling/urls.py
drilling/templates/drilling/base_manager.html
drilling/templates/drilling/base_admin.html
drilling/migrations/0040_*.py (auto-generado)
drilling/migrations/0041_*.py (auto-generado)
```

## 🚀 Uso

### 1. Asignar Niveles a Cargos (Primera vez)
```bash
python actualizar_jerarquia_cargos.py
```

### 2. Corregir Cargos con Espacios
```bash
python fix_cargos_faltantes.py
```

### 3. Acceder al Organigrama
1. Iniciar sesión en el sistema
2. **Manager**: Menú TRABAJADORES → Organigrama
3. **Admin**: Menú Gestión → Organigrama
4. Seleccionar contrato (si tienes acceso a múltiples)

### 4. Asignar Máquina a Trabajador

**Opción 1: Formulario (creación/edición)**
1. Ir a Trabajadores → Nuevo Trabajador
2. Llenar datos y seleccionar máquina en campo "Máquina Asignada"
3. Guardar

**Opción 2: Modal Dinámica (organigrama)**
1. Abrir organigrama
2. En sección "Sin Máquina Asignada", click en botón "Asignar"
3. Seleccionar máquina del dropdown
4. Click "Asignar"
5. La página se recarga automáticamente

### 5. Descargar Organigrama
1. Abrir organigrama
2. Click en botón "Descargar PNG"
3. Archivo se descarga automáticamente

## 🧪 Testing

```bash
# Verificar configuración
python manage.py check

# Crear superusuario de prueba (si no existe)
python manage.py createsuperuser

# Iniciar servidor
python manage.py runserver

# Acceder a:
# http://localhost:8000/organigrama/
```

## 📊 Estructura de Datos

### Context en `organigrama_view`
```python
{
    'contrato': Contrato,
    'niveles': {
        1: [Trabajador, ...],  # RESIDENTE
        2: [Trabajador, ...],  # Administrativos
        3: [Trabajador, ...],  # Supervisores
        4: [Trabajador, ...]   # Operaciones (todos)
    },
    'trabajadores_por_maquina': {
        Maquina: {
            'perforistas': [Trabajador, ...],
            'ayudantes': [Trabajador, ...],
            'otros': [Trabajador, ...]
        },
        ...
    },
    'trabajadores_sin_maquina': [Trabajador, ...],
    'maquinas_disponibles': [Maquina, ...],
    'contratos_disponibles': [Contrato, ...],
    'total_trabajadores': int
}
```

## 🔒 Permisos

- **ADMIN**: Ve todos los contratos, puede cambiar entre ellos
- **MANAGER**: Ve solo su contrato asignado
- **API**: Valida que el trabajador pertenezca al contrato del usuario

## 🎨 UI/UX

- **Diseño moderno**: Gradientes, sombras, animaciones hover
- **Iconos Font Awesome**: Representan roles (👑 Residente, ⚙️ Admin, ✅ Supervisor, 🏗️ Operaciones)
- **Cards responsivas**: Se adaptan a tamaño de pantalla
- **Loading states**: Spinners al asignar máquina o generar PNG
- **Mensajes de éxito/error**: Feedback inmediato al usuario

## 📝 Notas Técnicas

1. **html2canvas**: Captura el DOM como imagen, no requiere backend
2. **CSRF Token**: Incluido en template para API AJAX
3. **Bootstrap 5.3**: Modales y estilos
4. **PostgreSQL**: Soporte completo para ForeignKey y relaciones
5. **Nivel 99**: Valor por defecto para cargos sin nivel asignado

## 🐛 Debugging

Si un cargo no aparece en ningún nivel:
```python
# Verificar nivel_jerarquico
from drilling.models import Cargo
cargos_sin_nivel = Cargo.objects.filter(nivel_jerarquico=99)
print(cargos_sin_nivel)

# Asignar manualmente
cargo = Cargo.objects.get(nombre='NOMBRE_CARGO')
cargo.nivel_jerarquico = 4  # Por ejemplo
cargo.save()
```

Si un trabajador no aparece en máquina:
```python
# Verificar maquina_asignada
from drilling.models import Trabajador
trabajador = Trabajador.objects.get(id=123)
print(trabajador.maquina_asignada)  # None si no está asignado
```

## ✨ Mejoras Futuras (Opcional)

- [ ] Drag & drop para reasignar máquinas
- [ ] Filtros por área/cargo
- [ ] Exportar a PDF además de PNG
- [ ] Gráfico de líneas de reporte (cargo_superior)
- [ ] Historial de asignaciones de máquinas
- [ ] Notificaciones al asignar trabajador a máquina

## 📞 Soporte

Para cualquier duda o problema, revisar:
1. Logs de Django: `python manage.py runserver` en consola
2. Consola del navegador (F12) para errores JavaScript
3. Network tab para ver respuestas de API AJAX
