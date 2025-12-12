"""
Script para asignar un usuario al contrato de CONDESTABLE
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser, Contrato

# Listar usuarios
print("=" * 60)
print("USUARIOS DISPONIBLES")
print("=" * 60)

usuarios = CustomUser.objects.all()
for user in usuarios:
    contrato_nombre = user.contrato.nombre_contrato if user.contrato else "(sin contrato)"
    print(f"\nUsername: {user.username}")
    print(f"Email: {user.email}")
    print(f"Contrato actual: {contrato_nombre}")
    print(f"Rol: {user.role}")

# Asignar el primer usuario al contrato CONDESTABLE
print("\n" + "=" * 60)
print("ASIGNANDO USUARIO A CONDESTABLE")
print("=" * 60)

contrato_condestable = Contrato.objects.get(nombre_contrato='CONDESTABLE')
usuario = usuarios.first()

if usuario:
    usuario.contrato = contrato_condestable
    usuario.save()
    print(f"\n✓ Usuario '{usuario.username}' asignado al contrato CONDESTABLE")
    print(f"  Centro de costo: {contrato_condestable.codigo_centro_costo}")
else:
    print("\n✗ No hay usuarios disponibles")
