"""
Script para crear un usuario de prueba para el contrato AMERICANA
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser, Contrato

print("\n" + "="*70)
print("CREAR USUARIO DE PRUEBA - AMERICANA")
print("="*70 + "\n")

# Buscar contrato AMERICANA
try:
    contrato = Contrato.objects.get(nombre_contrato__icontains='AMERICANA')
    print(f"✓ Contrato encontrado: {contrato.nombre_contrato}")
    print(f"  Cliente: {contrato.cliente.nombre}")
    print(f"  ID: {contrato.id}")
except Contrato.DoesNotExist:
    print("✗ No se encontró el contrato AMERICANA")
    print("\nContratos disponibles:")
    for c in Contrato.objects.all():
        print(f"  - {c.nombre_contrato} (Cliente: {c.cliente.nombre})")
    exit(1)

# Crear usuario
username = 'operador_americana'
password = 'test123'

# Verificar si ya existe
if CustomUser.objects.filter(username=username).exists():
    print(f"\n⚠ El usuario '{username}' ya existe")
    usuario = CustomUser.objects.get(username=username)
    print(f"  Email: {usuario.email}")
    print(f"  Contrato: {usuario.contrato}")
    print(f"  Rol: {usuario.get_role_display()}")
else:
    usuario = CustomUser.objects.create_user(
        username=username,
        password=password,
        email='operador@americana.com',
        contrato=contrato,
        role='OPERADOR'
    )
    print(f"\n✓ Usuario creado exitosamente")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Email: {usuario.email}")
    print(f"  Contrato: {usuario.contrato.nombre_contrato}")
    print(f"  Rol: {usuario.get_role_display()}")

print("\n" + "="*70)
print("VERIFICACIÓN:")
print("="*70)
print(f"\n1. Inicia sesión con:")
print(f"   Usuario: {username}")
print(f"   Contraseña: {password}")
print(f"\n2. Ve a 'Nuevo Turno' y verifica que:")
print(f"   - NO veas productos de CONDESTABLE")
print(f"   - Los selectores estén vacíos (hasta que sincronices AMERICANA)")
print(f"\n3. Para sincronizar productos para AMERICANA:")
print(f"   python manage.py sync_productos_diamantados --contrato-id={contrato.id}")
print(f"   python manage.py sync_aditivos --contrato-id={contrato.id}")
print("\n" + "="*70 + "\n")
