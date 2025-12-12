"""
Script para cargar precios unitarios de servicios de ejemplo.

Uso:
    python manage.py shell < cargar_precios_unitarios.py

O desde shell interactivo:
    python manage.py shell
    >>> exec(open('cargar_precios_unitarios.py').read())
"""

from drilling.models import Contrato, TipoActividad, PrecioUnitarioServicio, CustomUser
from decimal import Decimal
from datetime import date

print("=" * 60)
print("CARGA DE PRECIOS UNITARIOS DE SERVICIOS")
print("=" * 60)

# Obtener usuario admin para asignar como creador
try:
    admin_user = CustomUser.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("❌ No se encontró usuario administrador")
        exit()
    print(f"✓ Usuario creador: {admin_user.username}")
except Exception as e:
    print(f"❌ Error al obtener usuario: {e}")
    exit()

# Obtener contratos activos
contratos = Contrato.objects.filter(estado='ACTIVO')
print(f"\n✓ Contratos activos encontrados: {contratos.count()}")

# Obtener servicios cobrables
servicios = TipoActividad.objects.filter(es_cobrable=True)
print(f"✓ Servicios cobrables encontrados: {servicios.count()}")

if not servicios.exists():
    print("\n⚠️  No hay servicios cobrables. Creando servicios de ejemplo...")
    
    # Crear algunos servicios cobrables de ejemplo
    servicios_ejemplo = [
        {'nombre': 'Perforación Diamantina', 'descripcion': 'Perforación con equipo diamantino'},
        {'nombre': 'Perforación RC', 'descripcion': 'Perforación con equipo RC (Reverse Circulation)'},
        {'nombre': 'Perforación DDH', 'descripcion': 'Perforación DDH (Diamond Drill Hole)'},
    ]
    
    for serv_data in servicios_ejemplo:
        servicio, created = TipoActividad.objects.get_or_create(
            nombre=serv_data['nombre'],
            defaults={
                'descripcion': serv_data['descripcion'],
                'es_cobrable': True,
                'tipo_actividad': 'OPERATIVO'
            }
        )
        if created:
            print(f"   ✓ Creado: {servicio.nombre}")
    
    servicios = TipoActividad.objects.filter(es_cobrable=True)

# Precios unitarios de ejemplo por contrato (en USD)
precios_ejemplo = {
    'AMERICANA': {
        'Perforación Diamantina': 85.50,
        'Perforación RC': 75.00,
        'Perforación DDH': 90.00,
    },
    'COLQUISIRI': {
        'Perforación Diamantina': 80.00,
        'Perforación RC': 70.00,
        'Perforación DDH': 85.00,
    },
    'CONDESTABLE': {
        'Perforación Diamantina': 95.00,
        'Perforación RC': 82.00,
        'Perforación DDH': 100.00,
    }
}

print("\n" + "=" * 60)
print("CREANDO PRECIOS UNITARIOS")
print("=" * 60)

precios_creados = 0
precios_actualizados = 0

for contrato in contratos:
    print(f"\n📋 Contrato: {contrato.nombre_contrato}")
    
    # Buscar precios de ejemplo para este contrato
    precios_contrato = None
    for nombre_clave in precios_ejemplo.keys():
        if nombre_clave.upper() in contrato.nombre_contrato.upper():
            precios_contrato = precios_ejemplo[nombre_clave]
            break
    
    if not precios_contrato:
        # Usar precios por defecto
        precios_contrato = {
            'Perforación Diamantina': 82.00,
            'Perforación RC': 72.00,
            'Perforación DDH': 88.00,
        }
        print(f"   ⚠️  Usando precios por defecto")
    
    for servicio in servicios:
        # Buscar precio para este servicio
        precio_valor = None
        for nombre_serv, precio in precios_contrato.items():
            if nombre_serv in servicio.nombre:
                precio_valor = precio
                break
        
        if not precio_valor:
            # Precio genérico
            precio_valor = 80.00
        
        # Verificar si ya existe
        precio_existente = PrecioUnitarioServicio.objects.filter(
            contrato=contrato,
            servicio=servicio,
            fecha_inicio_vigencia=date(2024, 1, 1)
        ).first()
        
        if precio_existente:
            # Actualizar
            precio_existente.precio_unitario = Decimal(str(precio_valor))
            precio_existente.activo = True
            precio_existente.save()
            print(f"   ↻ Actualizado: {servicio.nombre} = USD {precio_valor}/m")
            precios_actualizados += 1
        else:
            # Crear nuevo
            PrecioUnitarioServicio.objects.create(
                contrato=contrato,
                servicio=servicio,
                precio_unitario=Decimal(str(precio_valor)),
                moneda='USD',
                fecha_inicio_vigencia=date(2024, 1, 1),
                fecha_fin_vigencia=None,  # Vigencia indefinida
                activo=True,
                observaciones=f'Precio unitario cargado automáticamente el {date.today()}',
                created_by=admin_user
            )
            print(f"   ✓ Creado: {servicio.nombre} = USD {precio_valor}/m")
            precios_creados += 1

print("\n" + "=" * 60)
print("RESUMEN")
print("=" * 60)
print(f"✓ Precios creados: {precios_creados}")
print(f"✓ Precios actualizados: {precios_actualizados}")
print(f"✓ Total de precios: {PrecioUnitarioServicio.objects.count()}")

# Mostrar precios vigentes
print("\n" + "=" * 60)
print("PRECIOS VIGENTES HOY")
print("=" * 60)

for contrato in contratos:
    print(f"\n📋 {contrato.nombre_contrato}:")
    precios_vigentes = PrecioUnitarioServicio.objects.filter(
        contrato=contrato,
        activo=True
    ).select_related('servicio')
    
    if precios_vigentes.exists():
        for precio in precios_vigentes:
            vigencia_str = "Indefinida"
            if precio.fecha_fin_vigencia:
                vigencia_str = f"hasta {precio.fecha_fin_vigencia}"
            
            print(f"   • {precio.servicio.nombre}: {precio.moneda} {precio.precio_unitario}/m ({vigencia_str})")
    else:
        print("   ⚠️  Sin precios vigentes")

print("\n" + "=" * 60)
print("FINALIZADO")
print("=" * 60)
