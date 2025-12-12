import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Cargo

# Actualizar RESIDENTE
residentes = Cargo.objects.filter(nombre__icontains='RESIDENTE')
for cargo in residentes:
    cargo.nivel_jerarquico = 1
    cargo.save()
    print(f"✅ {cargo.nombre} → Nivel 1")

# Actualizar ADMINISTRADOR
admins = Cargo.objects.filter(nombre__icontains='ADMINISTRADOR')
for cargo in admins:
    cargo.nivel_jerarquico = 2
    cargo.save()
    print(f"✅ {cargo.nombre} → Nivel 2")

# Actualizar ING SEGURIDAD
ings = Cargo.objects.filter(nombre__icontains='ING SEGURIDAD')
for cargo in ings:
    cargo.nivel_jerarquico = 2
    cargo.save()
    print(f"✅ {cargo.nombre} → Nivel 2")

print("\n✅ Todos los cargos actualizados correctamente")
