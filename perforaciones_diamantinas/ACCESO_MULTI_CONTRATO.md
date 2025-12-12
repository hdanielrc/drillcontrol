# 🌐 Sistema de Acceso Multi-Contrato

## 📋 Resumen

Sistema que permite que usuarios específicos (Admin, Control de Proyecto) tengan acceso a **TODOS** los contratos sin necesidad de asignarles uno en particular.

---

## 🎯 Lógica de Acceso

### Regla Principal

El acceso a contratos se determina por el campo `contrato` del usuario:

| Condición | Acceso | Caso de Uso |
|-----------|--------|-------------|
| **`contrato = NULL`** | ✅ **TODOS los contratos** | Admin Sistema, Control de Proyecto, Supervisión General |
| **`contrato = [ID]`** | 🏢 **Solo ese contrato** | Manager, Supervisor, Operador de un contrato específico |
| **`is_system_admin = True`** | ✅ **TODOS los contratos** | Administrador del sistema (siempre acceso total) |

---

## 👥 Tipos de Usuarios

### 1. Admin del Sistema
```
is_system_admin: True
contrato: NULL (recomendado) o cualquier valor
Acceso: TODOS LOS CONTRATOS (siempre)
```

### 2. Control de Proyecto / Supervisión General
```
role: MANAGER_CONTRATO o SUPERVISOR
contrato: NULL (sin asignar)
Acceso: TODOS LOS CONTRATOS
```

### 3. Manager de Contrato
```
role: MANAGER_CONTRATO
contrato: [Contrato específico]
Acceso: SOLO ese contrato
```

### 4. Supervisor de Contrato
```
role: SUPERVISOR
contrato: [Contrato específico]
Acceso: SOLO ese contrato
```

### 5. Operador
```
role: OPERADOR
contrato: [Contrato específico]
Acceso: SOLO ese contrato
```

---

## 🔧 Cómo Crear Usuarios con Acceso Total

### Opción A: Desde el Admin de Django

1. **Accede al admin**: http://127.0.0.1:8000/admin/

2. **Ve a**: Usuarios → Agregar usuario

3. **Completa el formulario**:
   - ✅ Username
   - ✅ Email
   - ✅ First name / Last name
   - ⚠️ **Contrato**: **DÉJALO VACÍO** (no selecciones ninguno)
   - ✅ Role: Selecciona el rol apropiado
   - ✅ Is system admin: Marca si es admin total

4. **Guardar**

5. **Resultado**: 
   - Usuario con acceso a todos los contratos
   - En la lista verás: 🌐 TODOS LOS CONTRATOS

### Opción B: Programáticamente

```python
from drilling.models import CustomUser

# Usuario de Control de Proyecto
user = CustomUser.objects.create(
    username='control_proyecto',
    email='control@vilbragroup.com',
    first_name='Control',
    last_name='De Proyecto',
    role='MANAGER_CONTRATO',
    contrato=None,  # SIN CONTRATO = ACCESO A TODOS
    is_active=True
)
user.set_password('password123')
user.save()
```

---

## 🔍 Métodos del Modelo

### `has_access_to_all_contracts()`

Verifica si un usuario tiene acceso a todos los contratos:

```python
if request.user.has_access_to_all_contracts():
    # Usuario puede ver todos los contratos
    contratos = Contrato.objects.all()
else:
    # Usuario solo ve su contrato
    contratos = Contrato.objects.filter(id=request.user.contrato_id)
```

**Retorna `True` si:**
- `is_system_admin = True`, o
- `contrato = None` (sin asignar)

### `get_accessible_contracts()`

Obtiene el queryset de contratos accesibles:

```python
# En una vista
accessible_contracts = request.user.get_accessible_contracts()

# Ejemplo: Filtrar turnos
turnos = Turno.objects.filter(
    contrato__in=request.user.get_accessible_contracts()
)
```

**Retorna:**
- `Contrato.objects.all()` si tiene acceso total
- `Contrato.objects.filter(id=contrato_id)` si tiene contrato asignado
- `Contrato.objects.none()` si no tiene acceso

---

## 🎨 Interfaz de Usuario

### Menú del Usuario

Cuando un usuario tiene acceso a todos los contratos, el menú muestra:

```
┌─────────────────────────────┐
│ 👤 Juan Pérez               │
│    🌐 Todos los Contratos   │  ← Indica acceso total
├─────────────────────────────┤
│ 🔑 Cambiar Contraseña       │
├─────────────────────────────┤
│ 🚪 Cerrar Sesión            │
└─────────────────────────────┘
```

Cuando tiene un contrato específico:

```
┌─────────────────────────────┐
│ 👤 María López              │
│    🏢 AMERICANA             │  ← Contrato específico
├─────────────────────────────┤
│ 🔑 Cambiar Contraseña       │
├─────────────────────────────┤
│ 🚪 Cerrar Sesión            │
└─────────────────────────────┘
```

### Lista de Usuarios (Admin)

En el admin, la columna "Acceso a Contratos" muestra:

- 🌐 **TODOS LOS CONTRATOS** - Acceso total
- 🏢 **Nombre del Contrato** - Acceso específico
- ⚠️ **Sin acceso** - Sin contrato y sin permisos

---

## 📊 Ejemplos de Uso en Vistas

### Filtrar Datos por Contrato

```python
from django.views.generic import ListView

class TurnoListView(ListView):
    model = Turno
    template_name = 'drilling/turnos/list.html'
    
    def get_queryset(self):
        # Filtrar por contratos accesibles
        return Turno.objects.filter(
            contrato__in=self.request.user.get_accessible_contracts()
        ).order_by('-fecha')
```

### Vista de Detalle con Validación

```python
from django.shortcuts import get_object_or_404

def turno_detail(request, pk):
    # Obtener turno
    turno = get_object_or_404(Turno, pk=pk)
    
    # Verificar acceso
    if not request.user.has_access_to_all_contracts():
        if turno.contrato != request.user.contrato:
            return HttpResponseForbidden("No tienes acceso a este contrato")
    
    return render(request, 'turno_detail.html', {'turno': turno})
```

### Formulario con Contratos Disponibles

```python
class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ['contrato', 'fecha', ...]
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user:
            # Limitar contratos según acceso del usuario
            self.fields['contrato'].queryset = user.get_accessible_contracts()
```

---

## 🔐 Mejores Prácticas

### 1. Verificar Acceso en Vistas
```python
def my_view(request):
    # SIEMPRE filtrar por contratos accesibles
    data = Model.objects.filter(
        contrato__in=request.user.get_accessible_contracts()
    )
```

### 2. Mostrar Opciones Según Acceso
```python
{% if user.has_access_to_all_contracts %}
    <!-- Mostrar selector de contratos -->
    <select name="contrato">
        {% for contrato in all_contratos %}
            <option value="{{ contrato.id }}">{{ contrato.nombre_contrato }}</option>
        {% endfor %}
    </select>
{% else %}
    <!-- Mostrar solo su contrato -->
    <p>Contrato: {{ user.contrato.nombre_contrato }}</p>
{% endif %}
```

### 3. Mensajes Claros
```python
if user.has_access_to_all_contracts():
    messages.info(request, "Estás viendo datos de todos los contratos")
else:
    messages.info(request, f"Estás viendo datos de: {user.contrato.nombre_contrato}")
```

---

## 🎯 Casos de Uso Comunes

### Caso 1: Control de Proyecto
**Necesidad**: Supervisar todos los contratos sin asignación fija

**Solución**:
```python
usuario = CustomUser.objects.create(
    username='control_proyecto',
    role='MANAGER_CONTRATO',
    contrato=None,  # Sin asignar
    ...
)
```

**Resultado**: Ve todos los turnos, metas, abastecimientos de todos los contratos.

### Caso 2: Supervisor de un Solo Proyecto
**Necesidad**: Supervisar solo el contrato AMERICANA

**Solución**:
```python
contrato_americana = Contrato.objects.get(nombre_contrato='AMERICANA')
usuario = CustomUser.objects.create(
    username='supervisor_americana',
    role='SUPERVISOR',
    contrato=contrato_americana,  # Asignado
    ...
)
```

**Resultado**: Ve solo turnos, metas, abastecimientos de AMERICANA.

### Caso 3: Admin del Sistema
**Necesidad**: Acceso total y configuración del sistema

**Solución**:
```python
usuario = CustomUser.objects.create(
    username='admin',
    role='ADMIN_SISTEMA',
    is_system_admin=True,
    contrato=None,  # Opcional
    ...
)
```

**Resultado**: Acceso total, puede gestionar configuración, usuarios, etc.

---

## ⚠️ Consideraciones Importantes

### 1. Seguridad
- **SIEMPRE** usar `get_accessible_contracts()` para filtrar datos
- **NUNCA** asumir que un usuario puede ver todos los contratos
- Validar permisos en cada vista

### 2. Performance
- El método `get_accessible_contracts()` retorna un queryset
- Se puede cachear si es necesario
- Usar `.select_related('contrato')` para optimizar queries

### 3. Migraciones
- No requiere migración (solo cambios en lógica)
- El campo `contrato` ya es nullable
- Compatible con datos existentes

---

## 🧪 Testing

### Prueba Manual

1. **Crear usuario sin contrato**:
   ```bash
   python manage.py createsuperuser
   # O desde admin: dejar contrato vacío
   ```

2. **Iniciar sesión**

3. **Verificar menú**: Debe mostrar "🌐 Todos los Contratos"

4. **Verificar acceso**: Debe ver datos de todos los contratos

### Prueba Programática

```python
from drilling.models import CustomUser, Contrato

# Test 1: Usuario sin contrato
user = CustomUser.objects.create(username='test1', contrato=None)
assert user.has_access_to_all_contracts() == True
assert user.get_accessible_contracts().count() == Contrato.objects.count()

# Test 2: Usuario con contrato
contrato = Contrato.objects.first()
user = CustomUser.objects.create(username='test2', contrato=contrato)
assert user.has_access_to_all_contracts() == False
assert user.get_accessible_contracts().count() == 1

# Test 3: Admin del sistema
user = CustomUser.objects.create(username='test3', is_system_admin=True)
assert user.has_access_to_all_contracts() == True
```

---

## 📈 Resumen de Cambios

### Archivos Modificados

1. **`drilling/models.py`**
   - ✅ Método `has_access_to_all_contracts()`
   - ✅ Método `get_accessible_contracts()` actualizado
   - ✅ Método `get_permissions_summary()` actualizado

2. **`drilling/admin.py`**
   - ✅ Campo `get_contract_access_display()` 
   - ✅ Descripciones en fieldsets
   - ✅ Indicador visual 🌐

3. **`drilling/templates/drilling/base.html`**
   - ✅ Mostrar "Todos los Contratos" si `contrato=None`

### Sin Migración Necesaria

Los cambios son solo de lógica, no requieren migración de base de datos.

---

## 🎓 Conclusión

Con este sistema:
- ✅ Admin tiene acceso total (siempre)
- ✅ Control de Proyecto tiene acceso total (contrato=NULL)
- ✅ Supervisores/Operadores tienen acceso específico (contrato=ID)
- ✅ Sistema flexible y seguro
- ✅ Sin complejidad de Many-to-Many
- ✅ Simple de entender y mantener

---

**Implementado**: Noviembre 25, 2025  
**Estado**: ✅ Funcional y documentado  
**Método**: Contrato NULL = Acceso Total
