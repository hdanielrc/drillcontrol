# 🚀 GUÍA RÁPIDA: Usuarios con Acceso a Todos los Contratos

## ⚡ Resumen en 30 Segundos

Para que un usuario tenga acceso a **TODOS** los contratos:
- **Deja el campo "Contrato" VACÍO** al crear el usuario
- Eso es todo ✅

---

## 📝 Crear Usuario con Acceso Total

### Desde el Admin

1. **Ir a**: http://127.0.0.1:8000/admin/

2. **Usuarios** → **Agregar usuario**

3. **Completar**:
   - ✅ Username: `control_proyecto`
   - ✅ Email: `control@vilbragroup.com`
   - ✅ Nombre: `Control`
   - ✅ Apellido: `De Proyecto`
   - ⚠️ **Contrato: DEJAR VACÍO** ← ¡IMPORTANTE!
   - ✅ Role: `Manager de Contrato` (o el que necesites)
   - ⬜ Is system admin: NO (a menos que sea admin total)

4. **Guardar**

5. **Resultado**: 
   - Lista de usuarios mostrará: 🌐 **TODOS LOS CONTRATOS**
   - Usuario puede ver y trabajar con todos los contratos

---

## 🔍 Verificar Acceso

### En el Menú del Usuario

Cuando el usuario inicie sesión, verá:

```
┌──────────────────────────┐
│ 👤 Control De Proyecto   │
│    🌐 Todos los Contratos│  ← Indica acceso total
└──────────────────────────┘
```

### En la Lista del Admin

En `/admin/drilling/customuser/` verás:

| Username | Role | Acceso a Contratos |
|----------|------|-------------------|
| admin | Admin Sistema | 🌐 TODOS LOS CONTRATOS |
| control_proyecto | Manager Contrato | 🌐 TODOS LOS CONTRATOS |
| supervisor_americana | Supervisor | 🏢 AMERICANA |

---

## 👥 Casos de Uso

### Admin del Sistema
```
is_system_admin: ✅ Sí
contrato: (cualquiera o vacío)
Resultado: Acceso total siempre
```

### Control de Proyecto
```
role: Manager de Contrato
contrato: (VACÍO)
Resultado: Ve todos los contratos
```

### Supervisor General
```
role: Supervisor
contrato: (VACÍO)
Resultado: Ve todos los contratos
```

### Manager de Contrato Específico
```
role: Manager de Contrato
contrato: AMERICANA
Resultado: Solo ve AMERICANA
```

---

## ⚠️ IMPORTANTE

| Campo Contrato | Resultado |
|---------------|-----------|
| **VACÍO (NULL)** | ✅ Acceso a TODOS los contratos |
| **Con valor** | 🏢 Acceso SOLO a ese contrato |

---

## 🧪 Probar

1. **Crear usuario** sin contrato (dejarlo vacío)
2. **Iniciar sesión** con ese usuario
3. **Verificar menú**: Debe decir "🌐 Todos los Contratos"
4. **Ir a cualquier vista** de turnos/metas/etc.
5. **Verificar**: Debe ver datos de todos los contratos

---

## 📚 Documentación Completa

Ver `ACCESO_MULTI_CONTRATO.md` para detalles técnicos y ejemplos de código.

---

**TL;DR**: Contrato vacío = Acceso total ✨
