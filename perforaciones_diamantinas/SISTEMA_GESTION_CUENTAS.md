# Sistema de Gestión de Cuentas - Administración Interna

## Descripción General

Este sistema permite que **solo los administradores** creen cuentas de usuario. Los usuarios reciben un email de activación para establecer su contraseña y activar su cuenta.

## Características Implementadas

### 1. Creación de Usuarios por Admin
- Solo el administrador puede crear usuarios desde el panel de admin
- Al crear un usuario, **no es necesario** establecer contraseña
- Se envía automáticamente un email de activación al usuario
- El usuario inicia inactivo hasta que active su cuenta

### 2. Activación de Cuenta
- El usuario recibe un email con un enlace de activación
- El enlace expira en **24 horas**
- El usuario establece su propia contraseña segura
- Después de activar, puede iniciar sesión

### 3. Recuperación de Contraseña
- Enlace "¿Olvidaste tu contraseña?" en la página de login
- Usuario ingresa su email
- Recibe un enlace para restablecer contraseña
- El enlace expira en 24 horas

### 4. Cambio de Contraseña
- Usuario logueado puede cambiar su contraseña
- Acceso desde el menú de usuario → "Cambiar Contraseña"
- Requiere contraseña actual
- La nueva contraseña debe tener mínimo 8 caracteres

## URLs Implementadas

```
/login/                          → Inicio de sesión
/password-reset/                 → Solicitar recuperación de contraseña
/password-reset/<token>/         → Restablecer contraseña
/activate/<token>/               → Activar cuenta nueva
/change-password/                → Cambiar contraseña (requiere login)
```

## Configuración de Email

### Variables de Entorno (.env)

Agrega estas variables en tu archivo `.env`:

```env
# Configuración de Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_app
DEFAULT_FROM_EMAIL=noreply@vilbragroup.com
```

### Configuración para Gmail

1. **Habilitar autenticación de dos factores** en tu cuenta de Gmail
2. **Generar contraseña de aplicación**:
   - Ve a: https://myaccount.google.com/apppasswords
   - Selecciona "Correo" y "Otro dispositivo"
   - Copia la contraseña generada
   - Úsala en `EMAIL_HOST_PASSWORD`

### Modo de Desarrollo (Console Backend)

Para pruebas locales sin servidor de correo:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Los emails se mostrarán en la consola del servidor en lugar de enviarse.

## Uso desde Django Admin

### Crear un Usuario

1. **Accede al admin**: http://127.0.0.1:8000/admin/
2. **Ve a "Usuarios"** → "Agregar usuario"
3. **Completa el formulario**:
   - **Username**: nombre de usuario único
   - **Email**: correo electrónico (OBLIGATORIO)
   - **First name / Last name**: nombre completo
   - **Contrato**: asigna el contrato
   - **Role**: selecciona el rol del usuario
   - **Contraseñas**: DÉJALAS VACÍAS (el usuario las creará)
4. **Guardar**

El sistema:
- Creará el usuario inactivo
- Generará un token de activación
- Enviará el email automáticamente
- Mostrará mensaje de confirmación

### Reenviar Email de Activación

Si un usuario no recibió el email:

1. En la lista de usuarios del admin
2. Selecciona el/los usuario(s)
3. En "Acciones" selecciona **"Reenviar email de activación"**
4. Haz clic en "Ir"

Esto generará un nuevo token y reenviará el email.

### Verificar Estado de Activación

En la lista de usuarios, verás:
- **is_account_active**: ✓ si el usuario activó su cuenta
- **is_active**: ✓ si el usuario puede iniciar sesión

## Flujos de Usuario

### Flujo de Activación

```
1. Admin crea usuario
2. Sistema envía email con enlace de activación
3. Usuario hace clic en el enlace
4. Usuario establece su contraseña
5. Usuario es activado automáticamente
6. Usuario puede iniciar sesión
```

### Flujo de Recuperación de Contraseña

```
1. Usuario hace clic en "¿Olvidaste tu contraseña?"
2. Ingresa su email
3. Sistema envía enlace de recuperación
4. Usuario hace clic en el enlace
5. Usuario establece nueva contraseña
6. Usuario puede iniciar sesión con la nueva contraseña
```

### Flujo de Cambio de Contraseña

```
1. Usuario logueado va a su perfil
2. Selecciona "Cambiar Contraseña"
3. Ingresa contraseña actual
4. Ingresa nueva contraseña (2 veces)
5. Sistema valida y cambia la contraseña
6. Sesión se mantiene activa
```

## Modelo de Datos

### Campos Agregados a CustomUser

```python
is_account_active = BooleanField(default=False)
    # Indica si el usuario ha activado su cuenta mediante email

activation_token = CharField(max_length=100, blank=True, null=True)
    # Token único de 32 caracteres para activación/recuperación

token_created_at = DateTimeField(null=True, blank=True)
    # Fecha de creación del token (para validar expiración)
```

## Seguridad

### Tokens
- Generados con `secrets.token_urlsafe(32)` (256 bits de entropía)
- Expiración: 24 horas
- Un solo uso (se eliminan después de usar)

### Contraseñas
- Mínimo 8 caracteres
- Validación de coincidencia
- Hasheadas con algoritmo de Django (PBKDF2-SHA256)
- No se pueden reutilizar la contraseña actual

### Prevención de Enumeración
- No revelar si un email existe en el sistema
- Mensajes genéricos en recuperación de contraseña

## Mensajes de Email

### Email de Activación

```
Asunto: Activa tu cuenta - Sistema de Perforaciones

Hola [Nombre],

Se ha creado una cuenta para ti en el Sistema de Perforaciones Diamantinas.

Para activar tu cuenta y establecer tu contraseña, haz clic en:
[ENLACE]

Este enlace expirará en 24 horas.

Tus datos:
- Usuario: [username]
- Email: [email]
```

### Email de Recuperación

```
Asunto: Recuperación de Contraseña - Sistema de Perforaciones

Hola [Nombre],

Has solicitado recuperar tu contraseña.

Para establecer una nueva contraseña, haz clic en:
[ENLACE]

Este enlace expirará en 24 horas.

Si no solicitaste este cambio, puedes ignorar este correo.
```

## Troubleshooting

### Usuario no recibe emails

1. **Verificar configuración SMTP** en `.env`
2. **Revisar logs** de Django para errores de email
3. **Verificar spam** en la bandeja del usuario
4. **Probar email manualmente**:
   ```python
   from django.core.mail import send_mail
   send_mail('Test', 'Mensaje', 'from@email.com', ['to@email.com'])
   ```

### Token expirado

- El usuario debe solicitar un nuevo token
- Admin puede reenviar el email desde el admin panel
- Los tokens expiran después de 24 horas

### Usuario no puede iniciar sesión

Verificar:
- `is_active = True`
- `is_account_active = True`
- Contraseña correcta

## Próximas Mejoras Sugeridas

- [ ] Historial de cambios de contraseña
- [ ] Políticas de contraseña más estrictas
- [ ] Autenticación de dos factores (2FA)
- [ ] Logs de actividad de usuario
- [ ] Notificaciones de cambios de seguridad
- [ ] Expiración automática de contraseñas
- [ ] Restricción de IPs permitidas

## Archivos Creados/Modificados

### Nuevos Archivos
- `drilling/auth_views.py` - Vistas de autenticación
- `drilling/templates/drilling/auth/activate_account.html`
- `drilling/templates/drilling/auth/request_password_reset.html`
- `drilling/templates/drilling/auth/reset_password.html`
- `drilling/templates/drilling/auth/change_password.html`
- `drilling/migrations/0039_customuser_activation_token_and_more.py`

### Archivos Modificados
- `drilling/models.py` - Campos de activación en CustomUser
- `drilling/admin.py` - Auto-envío de emails y acción de reenvío
- `drilling/urls.py` - Rutas de autenticación
- `drilling/templates/drilling/login.html` - Enlace de recuperación
- `drilling/templates/drilling/base.html` - Enlace de cambio de contraseña
- `perforaciones_diamantinas/settings.py` - Configuración de email

## Soporte

Para problemas o consultas:
- Revisa los logs de Django
- Verifica la configuración de email
- Contacta al administrador del sistema
