# 🚀 INICIO RÁPIDO - Sistema de Gestión de Cuentas

## ⚡ Resumen en 30 segundos

✅ Sistema implementado y funcionando  
✅ Solo admin puede crear cuentas  
✅ Usuarios reciben email para activar y crear contraseña  
✅ Recuperación y cambio de contraseña incluidos  

---

## 📝 Crear un Usuario (Admin)

1. **Accede al admin**: http://127.0.0.1:8000/admin/

2. **Ve a**: Usuarios → Agregar usuario

3. **Completa**:
   - ✅ Username (único)
   - ✅ Email (obligatorio)
   - ✅ Nombre y apellido
   - ✅ Contrato
   - ✅ Rol
   - ⚠️ **NO pongas contraseñas** (déjalas vacías)

4. **Guardar** → Email se envía automáticamente

5. **Resultado**: En la consola del servidor verás el email con el enlace de activación

---

## 🔐 Activar Cuenta (Usuario)

1. **Revisa** la consola del servidor (donde ejecutas `runserver`)

2. **Copia** el enlace que aparece en el email simulado

3. **Ábrelo** en el navegador

4. **Establece** tu contraseña (mínimo 8 caracteres)

5. **Listo** → Ya puedes iniciar sesión en `/login/`

---

## 🔑 Recuperar Contraseña

1. En **login** → "¿Olvidaste tu contraseña?"

2. Ingresa tu **email**

3. Revisa la **consola del servidor** para el enlace

4. Establece **nueva contraseña**

5. Inicia sesión

---

## 🛠️ Cambiar Contraseña (Logueado)

1. Menú usuario → **"Cambiar Contraseña"**

2. Ingresa contraseña **actual** + **nueva**

3. Confirmar

---

## 📧 Configuración Email

### Desarrollo (Actual)
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```
Los emails aparecen en la **consola**.

### Producción (Cuando necesites)
En tu archivo `.env`:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_de_app
DEFAULT_FROM_EMAIL=noreply@vilbragroup.com
```

Ver archivo `.env.email.example` para más detalles.

---

## 🎯 URLs Importantes

```
/login/                    → Iniciar sesión
/admin/                    → Panel de administración
/password-reset/           → Recuperar contraseña
/change-password/          → Cambiar contraseña (requiere login)
/activate/<token>/         → Activar cuenta (enlace del email)
```

---

## 🐛 Troubleshooting

### Usuario no recibe email
- ✅ Verifica que el email esté configurado en el usuario
- ✅ Revisa la consola del servidor (modo desarrollo)
- ✅ Usa la acción "Reenviar email de activación" en el admin

### Token expirado
- ⏰ Los tokens duran 24 horas
- 🔄 Usa "Reenviar email de activación" para generar uno nuevo

### Usuario no puede iniciar sesión
Verifica en el admin:
- ✅ `is_active` = Sí
- ✅ `is_account_active` = Sí
- ✅ Contraseña establecida

---

## 📚 Documentación Completa

- **Guía detallada**: `SISTEMA_GESTION_CUENTAS.md`
- **Resumen técnico**: `RESUMEN_SISTEMA_CUENTAS.md`
- **Demo interactiva**: `python demo_sistema_cuentas.py`

---

## ✨ Características

✅ Activación por email  
✅ Recuperación de contraseña  
✅ Cambio de contraseña  
✅ Tokens seguros (256 bits)  
✅ Expiración automática (24h)  
✅ Admin integrado  
✅ Templates con Bootstrap 5  
✅ Validación de contraseñas  

---

## 🎓 Ejemplo Completo

```bash
# 1. Inicia el servidor
python manage.py runserver

# 2. En otro terminal, abre el admin
http://127.0.0.1:8000/admin/

# 3. Crea un usuario (sin contraseña)
# 4. Revisa la consola del servidor
# 5. Copia el enlace de activación
# 6. Ábrelo en el navegador
# 7. Establece contraseña
# 8. ¡Listo! Inicia sesión
```

---

**¿Necesitas más ayuda?**  
Lee `SISTEMA_GESTION_CUENTAS.md` para detalles completos.
