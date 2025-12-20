"""Actualizar usuarios con roles legacy"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser

print("=" * 80)
print("ACTUALIZANDO USUARIOS CON ROLES LEGACY")
print("=" * 80)

# Actualizar admin (OPERADOR -> CONTROL_PROYECTOS)
try:
    admin = CustomUser.objects.get(username='admin')
    print(f"\nUsuario: admin")
    print(f"  Rol actual: {admin.role}")
    print(f"  Actualizando a: CONTROL_PROYECTOS")
    admin.role = 'CONTROL_PROYECTOS'
    admin.is_system_admin = True
    admin.contrato = None  # Los roles globales no necesitan contrato
    admin.save()
    print("  OK - Actualizado")
except CustomUser.DoesNotExist:
    print("\nUsuario 'admin' no existe")
except Exception as e:
    print(f"\nError al actualizar admin: {e}")

# Actualizar rdadmin (ADMIN_SISTEMA -> GERENCIA)
try:
    rdadmin = CustomUser.objects.get(username='rdadmin')
    print(f"\nUsuario: rdadmin")
    print(f"  Rol actual: {rdadmin.role}")
    print(f"  is_system_admin: {rdadmin.is_system_admin}")
    print(f"  Actualizando a: GERENCIA")
    rdadmin.role = 'GERENCIA'
    rdadmin.is_system_admin = True
    rdadmin.save()
    print("  OK - Actualizado")
except CustomUser.DoesNotExist:
    print("\nUsuario 'rdadmin' no existe")
except Exception as e:
    print(f"\nError al actualizar rdadmin: {e}")

print("\n" + "=" * 80)
print("VERIFICACION FINAL")
print("=" * 80)

roles_validos = [r[0] for r in CustomUser.USER_ROLES]
usuarios_invalidos = CustomUser.objects.exclude(role__in=roles_validos)
print(f"\nUsuarios con roles invalidos: {usuarios_invalidos.count()}")

if usuarios_invalidos.count() == 0:
    print("OK - Todos los usuarios tienen roles validos")
else:
    for u in usuarios_invalidos:
        print(f"  - {u.username}: {u.role}")

print("\n" + "=" * 80)
