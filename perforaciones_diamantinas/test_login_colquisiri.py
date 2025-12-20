"""Test de login con usuario ADMINISTRADORCOLQUISIRI"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.contrib.auth import authenticate
from drilling.models import CustomUser

username = 'ADMINISTRADORCOLQUISIRI'
password = 'VilbraDD2024'

print("=" * 80)
print(f"TEST DE LOGIN: {username}")
print("=" * 80)

# Verificar que el usuario existe
try:
    user = CustomUser.objects.get(username=username)
    print(f"\nUsuario encontrado:")
    print(f"  Username: {user.username}")
    print(f"  Rol: {user.role} ({user.get_role_display()})")
    print(f"  Contrato: {user.contrato.nombre_contrato if user.contrato else 'Sin contrato'}")
    print(f"  is_active: {user.is_active}")
    print(f"  is_staff: {user.is_staff}")
    print(f"  is_system_admin: {user.is_system_admin}")
    
    # Intentar autenticar
    print(f"\nIntentando autenticar con password: {password}")
    auth_user = authenticate(username=username, password=password)
    
    if auth_user is not None:
        print("\n[OK] AUTENTICACION EXITOSA")
        print(f"  Usuario autenticado: {auth_user.username}")
        print(f"  Puede acceder al sistema")
    else:
        print("\n[ERROR] AUTENTICACION FALLIDA")
        print("  Credenciales incorrectas o usuario inactivo")
        
except CustomUser.DoesNotExist:
    print(f"\n[ERROR] Usuario '{username}' no existe en la base de datos")
except Exception as e:
    print(f"\n[ERROR] Excepcion: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
