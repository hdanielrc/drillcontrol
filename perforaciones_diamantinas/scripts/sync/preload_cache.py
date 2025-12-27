"""
Optimizaciones de caching para reducir queries en carga de template
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.core.cache import cache
from drilling.models import TipoTurno, UnidadMedida, TipoActividad

def preload_static_data():
    """Pre-carga datos estáticos al cache para evitar queries repetidas"""
    
    print("Cargando datos estáticos al cache...")
    
    # 1. TipoTurno (casi nunca cambia, 2 registros)
    tipos_turno = list(TipoTurno.objects.values('id', 'nombre'))
    cache.set('tipos_turno_all', tipos_turno, timeout=86400)  # 24 horas
    print(f"✓ Cached {len(tipos_turno)} TipoTurno")
    
    # 2. UnidadMedida (nunca cambia, 1 registro)
    unidades = list(UnidadMedida.objects.values('id', 'nombre', 'simbolo'))
    cache.set('unidades_medida_all', unidades, timeout=86400)  # 24 horas
    print(f"✓ Cached {len(unidades)} UnidadMedida")
    
    # 3. TipoActividad (cambia poco, 82 registros)
    actividades = list(TipoActividad.objects.values('id', 'nombre', 'descripcion_corta'))
    cache.set('tipos_actividad_all', actividades, timeout=3600)  # 1 hora
    print(f"✓ Cached {len(actividades)} TipoActividad")
    
    print("\n✅ Datos estáticos cargados al cache exitosamente")
    print("Esto reducirá 3 queries de la carga del formulario")

if __name__ == '__main__':
    preload_static_data()
