"""
Script para crear usuario Gerente General con acceso a todos los contratos.

Ejecutar con:
python manage.py shell < scripts/usuarios/crear_gerente_general.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser, Contrato

def crear_gerente_general():
    """Crear usuario gerente con rol GERENTE_GENERAL"""
    
    username = 'gerente'
    password = 'Gerente2026!'
    email = 'gerencia@rockdrill.com'
    
    # Verificar si el usuario ya existe
    if CustomUser.objects.filter(username=username).exists():
        print(f"Usuario '{username}' ya existe.")
        user = CustomUser.objects.get(username=username)
        print(f"   - ID: {user.id}")
        print(f"   - Email: {user.email}")
        print(f"   - Rol: {user.role}")
        print(f"   - Activo: {user.is_active}")
        return user
    
    # Obtener el primer contrato disponible (por defecto)
    contrato = Contrato.objects.first()
    if not contrato:
        print("Error: No hay contratos registrados en el sistema.")
        print("   Por favor, cree al menos un contrato antes de crear el usuario gerente.")
        return None
    
    # Crear usuario
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        role='GERENTE_GENERAL',
        contrato=contrato,  # Contrato por defecto
        is_active=True,
        is_staff=False,
        is_system_admin=False
    )
    
    print("Usuario Gerente General creado exitosamente!")
    print(f"   - Usuario: {username}")
    print(f"   - Contrasena: {password}")
    print(f"   - Email: {email}")
    print(f"   - Rol: GERENTE_GENERAL")
    print(f"   - Contrato por defecto: {contrato.nombre_contrato}")
    print(f"   - ID: {user.id}")
    print("")
    print("El gerente puede ver informacion de TODOS los contratos en el dashboard.")
    print("Por favor, cambie la contrasena despues del primer ingreso.")
    
    return user


if __name__ == '__main__':
    crear_gerente_general()
