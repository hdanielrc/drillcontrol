"""
Vistas para gestión de autenticación de usuarios:
- Activación de cuenta
- Recuperación de contraseña
- Cambio de contraseña
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import secrets

from .models import CustomUser


def generate_activation_token():
    """Genera un token seguro de 32 caracteres"""
    return secrets.token_urlsafe(32)


def send_activation_email(user, request):
    """Envía email de activación a un usuario recién creado"""
    # Generar token
    user.activation_token = generate_activation_token()
    user.token_created_at = timezone.now()
    user.save(update_fields=['activation_token', 'token_created_at'])
    
    # Construir URL de activación
    activation_url = request.build_absolute_uri(
        reverse('activate_account', kwargs={'token': user.activation_token})
    )
    
    # Enviar email
    subject = 'Activa tu cuenta - Sistema de Perforaciones'
    message = f"""
Hola {user.get_full_name() or user.username},

Se ha creado una cuenta para ti en el Sistema de Perforaciones Diamantinas.

Para activar tu cuenta y establecer tu contraseña, haz clic en el siguiente enlace:

{activation_url}

Este enlace expirará en {settings.ACTIVATION_TOKEN_EXPIRY_HOURS} horas.

Tus datos de acceso:
- Usuario: {user.username}
- Email: {user.email}

Una vez activada tu cuenta, podrás iniciar sesión en el sistema.

Si no solicitaste esta cuenta, puedes ignorar este correo.

---
Sistema de Perforaciones Diamantinas
Vilbragroup
"""
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def activate_account(request, token):
    """Vista para activar cuenta mediante token"""
    user = get_object_or_404(CustomUser, activation_token=token)
    
    # Verificar si el token ha expirado
    if user.token_created_at:
        expiry_time = user.token_created_at + timedelta(hours=settings.ACTIVATION_TOKEN_EXPIRY_HOURS)
        if timezone.now() > expiry_time:
            messages.error(request, 'El enlace de activación ha expirado. Contacta al administrador.')
            return redirect('login')
    
    # Verificar si ya está activada
    if user.is_account_active:
        messages.info(request, 'Tu cuenta ya está activada. Puedes iniciar sesión.')
        return redirect('login')
    
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validar contraseñas
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            # Establecer contraseña y activar cuenta
            user.set_password(password1)
            user.is_account_active = True
            user.is_active = True
            user.activation_token = None
            user.token_created_at = None
            user.save()
            
            messages.success(request, '¡Cuenta activada exitosamente! Ya puedes iniciar sesión.')
            return redirect('login')
    
    context = {
        'user': user,
        'token': token,
    }
    return render(request, 'drilling/auth/activate_account.html', context)


def request_password_reset(request):
    """Vista para solicitar recuperación de contraseña"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
            
            # Generar token
            user.activation_token = generate_activation_token()
            user.token_created_at = timezone.now()
            user.save(update_fields=['activation_token', 'token_created_at'])
            
            # Construir URL de recuperación
            reset_url = request.build_absolute_uri(
                reverse('reset_password', kwargs={'token': user.activation_token})
            )
            
            # Enviar email
            subject = 'Recuperación de Contraseña - Sistema de Perforaciones'
            message = f"""
Hola {user.get_full_name() or user.username},

Has solicitado recuperar tu contraseña en el Sistema de Perforaciones Diamantinas.

Para establecer una nueva contraseña, haz clic en el siguiente enlace:

{reset_url}

Este enlace expirará en {settings.ACTIVATION_TOKEN_EXPIRY_HOURS} horas.

Si no solicitaste este cambio, puedes ignorar este correo y tu contraseña actual permanecerá sin cambios.

---
Sistema de Perforaciones Diamantinas
Vilbragroup
"""
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            messages.success(request, 'Se ha enviado un enlace de recuperación a tu correo electrónico.')
            return redirect('login')
            
        except CustomUser.DoesNotExist:
            # Por seguridad, no revelar si el email existe o no
            messages.success(request, 'Si el correo está registrado, recibirás un enlace de recuperación.')
            return redirect('login')
    
    return render(request, 'drilling/auth/request_password_reset.html')


def reset_password(request, token):
    """Vista para restablecer contraseña mediante token"""
    user = get_object_or_404(CustomUser, activation_token=token)
    
    # Verificar si el token ha expirado
    if user.token_created_at:
        expiry_time = user.token_created_at + timedelta(hours=settings.ACTIVATION_TOKEN_EXPIRY_HOURS)
        if timezone.now() > expiry_time:
            messages.error(request, 'El enlace de recuperación ha expirado. Solicita uno nuevo.')
            return redirect('request_password_reset')
    
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validar contraseñas
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            # Establecer nueva contraseña
            user.set_password(password1)
            user.activation_token = None
            user.token_created_at = None
            user.save()
            
            messages.success(request, '¡Contraseña cambiada exitosamente! Ya puedes iniciar sesión.')
            return redirect('login')
    
    context = {
        'user': user,
        'token': token,
    }
    return render(request, 'drilling/auth/reset_password.html', context)


@login_required
def change_password(request):
    """Vista para cambiar contraseña estando logueado"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Verificar contraseña actual
        if not request.user.check_password(current_password):
            messages.error(request, 'La contraseña actual es incorrecta.')
        # Validar nuevas contraseñas
        elif new_password1 != new_password2:
            messages.error(request, 'Las contraseñas nuevas no coinciden.')
        elif len(new_password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        elif current_password == new_password1:
            messages.error(request, 'La nueva contraseña debe ser diferente a la actual.')
        else:
            # Cambiar contraseña
            request.user.set_password(new_password1)
            request.user.save()
            
            # Mantener sesión activa después del cambio
            update_session_auth_hash(request, request.user)
            
            messages.success(request, '¡Contraseña cambiada exitosamente!')
            return redirect('home')
    
    return render(request, 'drilling/auth/change_password.html')
