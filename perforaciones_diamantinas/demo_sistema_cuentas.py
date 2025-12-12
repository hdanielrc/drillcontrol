"""
Script de demostración del sistema de gestión de cuentas

Este script muestra cómo funciona el sistema de activación de cuentas.
En desarrollo, los emails se muestran en la consola del servidor.
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from drilling.auth_views import send_activation_email

User = get_user_model()

def demo_crear_usuario():
    """Demuestra cómo se crea un usuario y se envía el email de activación"""
    
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: Creación de Usuario y Envío de Email de Activación")
    print("="*70 + "\n")
    
    # Verificar si ya existe
    username = "usuario_demo"
    if User.objects.filter(username=username).exists():
        print(f"⚠️  El usuario '{username}' ya existe. Eliminándolo para la demo...")
        User.objects.filter(username=username).delete()
    
    # Crear usuario de demostración
    print("1️⃣  Creando usuario de demostración...")
    user = User.objects.create(
        username=username,
        email="demo@vilbragroup.com",
        first_name="Usuario",
        last_name="Demo",
        role="OPERADOR",
        is_active=False,  # Inactivo hasta activación
        is_account_active=False
    )
    user.set_unusable_password()  # Sin contraseña hasta activación
    user.save()
    
    print(f"   ✅ Usuario creado: {user.username}")
    print(f"   📧 Email: {user.email}")
    print(f"   👤 Nombre: {user.get_full_name()}")
    print(f"   🔒 Cuenta activa: {user.is_account_active}")
    print(f"   🚪 Puede iniciar sesión: {user.is_active}")
    
    # Simular envío de email
    print("\n2️⃣  Generando token y simulando envío de email...")
    factory = RequestFactory()
    request = factory.get('/admin/')
    request.META['HTTP_HOST'] = 'localhost:8000'
    
    try:
        send_activation_email(user, request)
        print("   ✅ Email de activación preparado")
        
        # Mostrar información del token
        user.refresh_from_db()
        print(f"\n3️⃣  Información del token generado:")
        print(f"   🔑 Token: {user.activation_token[:20]}...")
        print(f"   📅 Creado: {user.token_created_at}")
        print(f"   ⏰ Expira: en 24 horas")
        
        # Construir URL de activación
        activation_url = f"http://localhost:8000/activate/{user.activation_token}/"
        print(f"\n4️⃣  URL de activación:")
        print(f"   🔗 {activation_url}")
        
        print("\n" + "="*70)
        print("PRÓXIMOS PASOS:")
        print("="*70)
        print("\n1. Inicia el servidor: python manage.py runserver")
        print("2. El email se mostrará en la consola (modo desarrollo)")
        print("3. Copia la URL de activación desde el email")
        print("4. Ábrela en el navegador")
        print("5. Establece una contraseña")
        print("6. ¡Listo! Podrás iniciar sesión")
        
        print("\n💡 CONSEJO:")
        print("   En producción, configura EMAIL_BACKEND para envío real de emails")
        print("   Ver: .env.email.example para configuración SMTP\n")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

def demo_recuperar_contraseña():
    """Demuestra el flujo de recuperación de contraseña"""
    
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: Recuperación de Contraseña")
    print("="*70 + "\n")
    
    # Buscar un usuario existente
    users = User.objects.filter(is_active=True, email__isnull=False).exclude(email='')
    
    if not users.exists():
        print("⚠️  No hay usuarios activos con email. Crea uno primero.")
        return
    
    user = users.first()
    
    print(f"1️⃣  Usuario seleccionado: {user.username}")
    print(f"   📧 Email: {user.email}")
    
    print("\n2️⃣  Flujo de recuperación:")
    print("   a. Usuario va a: http://localhost:8000/password-reset/")
    print("   b. Ingresa su email")
    print("   c. Sistema genera token y envía email")
    print("   d. Usuario hace clic en el enlace")
    print("   e. Establece nueva contraseña")
    
    print("\n3️⃣  Ejemplo de URL de recuperación:")
    token = "ejemplo-token-abc123xyz789"
    reset_url = f"http://localhost:8000/password-reset/{token}/"
    print(f"   🔗 {reset_url}")
    
    print("\n💡 Este token expirará en 24 horas por seguridad\n")

def demo_cambiar_contraseña():
    """Demuestra el cambio de contraseña desde el perfil"""
    
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: Cambio de Contraseña desde Perfil")
    print("="*70 + "\n")
    
    print("1️⃣  Usuario logueado accede a su perfil")
    print("   📍 Menú Usuario → 'Cambiar Contraseña'")
    print("   🔗 URL: http://localhost:8000/change-password/")
    
    print("\n2️⃣  Formulario de cambio:")
    print("   🔒 Contraseña actual (requerida)")
    print("   🆕 Nueva contraseña (mínimo 8 caracteres)")
    print("   🔁 Confirmar nueva contraseña")
    
    print("\n3️⃣  Validaciones:")
    print("   ✓ Contraseña actual correcta")
    print("   ✓ Nueva contraseña diferente a la actual")
    print("   ✓ Ambas contraseñas nuevas coinciden")
    print("   ✓ Mínimo 8 caracteres")
    
    print("\n4️⃣  Después del cambio:")
    print("   ✅ Contraseña actualizada")
    print("   🔓 Sesión permanece activa (no requiere re-login)\n")

def menu():
    """Menú principal de demostración"""
    
    print("\n" + "="*70)
    print(" SISTEMA DE GESTIÓN DE CUENTAS - DEMOSTRACIÓN")
    print("="*70)
    print("\nSelecciona una opción:\n")
    print("1. Demostrar creación de usuario y activación")
    print("2. Demostrar recuperación de contraseña")
    print("3. Demostrar cambio de contraseña")
    print("4. Ejecutar todas las demos")
    print("5. Salir")
    
    opcion = input("\nOpción (1-5): ").strip()
    
    if opcion == "1":
        demo_crear_usuario()
    elif opcion == "2":
        demo_recuperar_contraseña()
    elif opcion == "3":
        demo_cambiar_contraseña()
    elif opcion == "4":
        demo_crear_usuario()
        input("\n[Presiona ENTER para continuar...]")
        demo_recuperar_contraseña()
        input("\n[Presiona ENTER para continuar...]")
        demo_cambiar_contraseña()
    elif opcion == "5":
        print("\n👋 ¡Hasta luego!\n")
        return
    else:
        print("\n❌ Opción no válida\n")
    
    input("\n[Presiona ENTER para volver al menú...]")
    menu()

if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!\n")
