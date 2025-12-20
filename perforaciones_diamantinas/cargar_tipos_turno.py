import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import TipoTurno

# Verificar tipos de turno existentes
print("Tipos de turno actuales:")
for t in TipoTurno.objects.all():
    print(f"  - {t.id}: {t.nombre}")

# Crear DIA y NOCHE si no existen
tipos_requeridos = ['DIA', 'NOCHE']

for tipo in tipos_requeridos:
    turno, created = TipoTurno.objects.get_or_create(
        nombre=tipo,
        defaults={'descripcion': f'Turno de {tipo.lower()}'}
    )
    if created:
        print(f"\n✓ Creado: {tipo}")
    else:
        print(f"\n↻ Ya existe: {tipo}")

print("\n" + "="*60)
print("Tipos de turno finales:")
for t in TipoTurno.objects.all():
    print(f"  - {t.id}: {t.nombre}")
print("="*60)
