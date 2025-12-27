"""
Script para marcar servicios existentes como cobrables.

Uso:
    python manage.py shell < marcar_servicios_cobrables.py
"""

from drilling.models import TipoActividad

print("=" * 60)
print("MARCAR SERVICIOS COMO COBRABLES")
print("=" * 60)

# Listar todos los servicios
servicios = TipoActividad.objects.all()
print(f"\n📋 Total de servicios encontrados: {servicios.count()}")

# Mostrar servicios actuales
print("\n" + "=" * 60)
print("SERVICIOS ACTUALES")
print("=" * 60)

for servicio in servicios:
    estado = "✓ Cobrable" if servicio.es_cobrable else "✗ No cobrable"
    print(f"{servicio.id:3d}. {servicio.nombre:40s} [{estado}]")

# Servicios que típicamente son cobrables (ajusta según tus necesidades)
servicios_cobrables = [
    'perforación',
    'perforacion',
    'diamantina',
    'sondaje',
    'drilling',
    'ddh',
    'rc',
    'operativo',
    'producción',
    'produccion',
]

print("\n" + "=" * 60)
print("MARCANDO SERVICIOS COMO COBRABLES")
print("=" * 60)

actualizados = 0

for servicio in servicios:
    # Buscar si el nombre del servicio contiene alguna palabra clave
    nombre_lower = servicio.nombre.lower()
    es_operativo = servicio.tipo_actividad == 'OPERATIVO'
    
    debe_ser_cobrable = any(
        palabra in nombre_lower for palabra in servicios_cobrables
    ) or es_operativo
    
    if debe_ser_cobrable and not servicio.es_cobrable:
        servicio.es_cobrable = True
        servicio.save()
        print(f"✓ Marcado como cobrable: {servicio.nombre}")
        actualizados += 1
    elif not debe_ser_cobrable and servicio.es_cobrable:
        # Opcional: desmarcar si no debería ser cobrable
        # servicio.es_cobrable = False
        # servicio.save()
        pass

print(f"\n✓ Servicios actualizados: {actualizados}")

# Mostrar servicios cobrables finales
print("\n" + "=" * 60)
print("SERVICIOS COBRABLES (PARA PRECIO UNITARIO)")
print("=" * 60)

servicios_cobrables_final = TipoActividad.objects.filter(es_cobrable=True)
print(f"\n📋 Total: {servicios_cobrables_final.count()}")

for servicio in servicios_cobrables_final:
    print(f"  • {servicio.nombre}")

if servicios_cobrables_final.count() == 0:
    print("\n⚠️  No hay servicios cobrables marcados.")
    print("   Puedes marcar servicios desde el admin de Django:")
    print("   http://127.0.0.1:8000/admin/drilling/tipoactividad/")

print("\n" + "=" * 60)
print("FINALIZADO")
print("=" * 60)
