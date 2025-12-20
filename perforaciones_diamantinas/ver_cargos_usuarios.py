"""
Script para mostrar los cargos y niveles jerárquicos del sistema
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Cargo, CustomUser

print("="*80)
print("ESTRUCTURA DE CARGOS Y NIVELES JERARQUICOS")
print("="*80)

cargos = Cargo.objects.all().order_by('nivel_jerarquico', 'nombre')

print(f"\nTotal de cargos: {cargos.count()}\n")

nivel_actual = None
for cargo in cargos:
    if cargo.nivel_jerarquico != nivel_actual:
        nivel_actual = cargo.nivel_jerarquico
        print(f"\n--- NIVEL {nivel_actual} ---")
    print(f"  • {cargo.nombre}")

print("\n" + "="*80)
print("USUARIOS EXISTENTES EN EL SISTEMA")
print("="*80)

usuarios = CustomUser.objects.all().select_related('contrato')
print(f"\nTotal de usuarios: {usuarios.count()}\n")

if usuarios.exists():
    for user in usuarios:
        contrato_info = f" - Contrato: {user.contrato.nombre_contrato}" if user.contrato else " - Sin contrato"
        superuser = " [SUPERUSUARIO]" if user.is_superuser else ""
        print(f"  • {user.username}{superuser}{contrato_info}")
else:
    print("  No hay usuarios creados aún")

print("\n" + "="*80)
