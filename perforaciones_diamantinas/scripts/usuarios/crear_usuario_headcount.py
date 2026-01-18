"""
Script para crear usuario con rol HEADCOUNT
Ejecutar: python manage.py shell < scripts/usuarios/crear_usuario_headcount.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser

# Datos del usuario HEADCOUNT
username = 'headcount'
email = 'headcount@drillcontrol.com'
password = 'Headcount2026!'
first_name = 'Gestión'
last_name = 'Personal'

# Verificar si ya existe
if CustomUser.objects.filter(username=username).exists():
    print(f'❌ El usuario {username} ya existe')
    user = CustomUser.objects.get(username=username)
    print(f'Usuario actual: {user.username} - {user.get_role_display()}')
else:
    # Crear usuario
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role='HEADCOUNT',
        is_staff=True,
        is_active=True,
        is_account_active=True,
        contrato=None  # Acceso a todos los contratos
    )
    
    print('=' * 60)
    print('✅ USUARIO HEADCOUNT CREADO EXITOSAMENTE')
    print('=' * 60)
    print(f'Username:  {username}')
    print(f'Password:  {password}')
    print(f'Email:     {email}')
    print(f'Rol:       {user.get_role_display()}')
    print(f'Acceso:    Todos los contratos')
    print('=' * 60)
    print('⚠️  IMPORTANTE: Guarda estas credenciales en un lugar seguro')
    print('=' * 60)
