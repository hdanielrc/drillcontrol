"""
Script para verificar el estado actual de los datos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador, TipoComplemento, TipoAditivo, Contrato, CustomUser

print("\n" + "="*70)
print("VERIFICACIÓN DE DATOS")
print("="*70 + "\n")

# Verificar usuario actual
print("USUARIOS:")
usuarios = CustomUser.objects.all()
for u in usuarios:
    print(f"  - {u.username}: Contrato={u.contrato}, Role={u.role}")

# Verificar contratos
print("\nCONTRATOS:")
contratos = Contrato.objects.all()
for c in contratos:
    print(f"  - {c.nombre_contrato} (ID: {c.id})")
    print(f"    Centro de Costo: {c.codigo_centro_costo or 'NO CONFIGURADO'}")

# Verificar trabajadores
print("\nTRABAJADORES:")
trabajadores = Trabajador.objects.all()
if trabajadores:
    for t in trabajadores[:5]:  # Mostrar primeros 5
        print(f"  - {t.nombres} {t.apellidos} ({t.cargo}) - Contrato: {t.contrato.nombre_contrato}")
    if trabajadores.count() > 5:
        print(f"  ... y {trabajadores.count() - 5} más")
else:
    print("  No hay trabajadores registrados")

# Verificar productos diamantados
print("\nPRODUCTOS DIAMANTADOS (PDD):")
pdd = TipoComplemento.objects.all()
if pdd:
    print(f"  Total: {pdd.count()}")
    pdd_con_serie = pdd.exclude(serie__isnull=True).exclude(serie='')
    print(f"  Con serie: {pdd_con_serie.count()}")
    pdd_nuevo = pdd.filter(estado='NUEVO')
    print(f"  Estado NUEVO: {pdd_nuevo.count()}")
    
    # Mostrar algunos ejemplos
    print("\n  Ejemplos:")
    for p in pdd[:3]:
        print(f"    - {p.nombre}")
        print(f"      Serie: {p.serie or 'N/A'}")
        print(f"      Código: {p.codigo or 'N/A'}")
        print(f"      Estado: {p.estado}")
        print(f"      Contrato: {p.contrato or 'N/A'}")
else:
    print("  No hay productos diamantados registrados")
    print("  ⚠ Necesitas ejecutar: python sync_condestable.py")

# Verificar aditivos
print("\nADITIVOS (ADIT):")
adit = TipoAditivo.objects.all()
if adit:
    print(f"  Total: {adit.count()}")
    
    # Mostrar algunos ejemplos
    print("\n  Ejemplos:")
    for a in adit[:3]:
        print(f"    - {a.nombre}")
        print(f"      Código: {a.codigo or 'N/A'}")
        print(f"      Contrato: {a.contrato or 'N/A'}")
else:
    print("  No hay aditivos registrados")
    print("  ⚠ Necesitas ejecutar: python sync_condestable.py")

print("\n" + "="*70)
print("RESUMEN:")
print(f"  Usuarios: {usuarios.count()}")
print(f"  Contratos: {contratos.count()}")
print(f"  Trabajadores: {trabajadores.count()}")
print(f"  Productos Diamantados: {pdd.count()}")
print(f"  Aditivos: {adit.count()}")
print("="*70 + "\n")

# Instrucciones
if pdd.count() == 0 or adit.count() == 0:
    print("⚠ ACCIÓN REQUERIDA:")
    print("\n1. Aplicar migraciones:")
    print("   python manage.py makemigrations")
    print("   python manage.py migrate")
    print("\n2. Ejecutar sincronización:")
    print("   python sync_condestable.py")
    print()
