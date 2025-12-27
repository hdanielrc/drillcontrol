"""
Script para actualizar automáticamente el campo 'grupo' de todos los trabajadores existentes
basándose en su cargo actual.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador

def actualizar_grupos_trabajadores():
    """Actualiza el grupo de todos los trabajadores basándose en su cargo"""
    
    trabajadores = Trabajador.objects.all().select_related('cargo')
    total = trabajadores.count()
    actualizados = 0
    
    print(f"Iniciando actualización de grupos para {total} trabajadores...\n")
    
    grupos_conteo = {
        'OPERADORES': 0,
        'SERVICIOS_GEOLOGICOS': 0,
        'LINEA_MANDO': 0,
        'PERSONAL_AUXILIAR': 0,
    }
    
    for trabajador in trabajadores:
        grupo_anterior = trabajador.grupo
        grupo_nuevo = trabajador.asignar_grupo_automatico()
        
        if grupo_nuevo and grupo_nuevo != grupo_anterior:
            trabajador.grupo = grupo_nuevo
            trabajador.save(update_fields=['grupo'])
            actualizados += 1
            grupos_conteo[grupo_nuevo] += 1
            print(f"✓ {trabajador.nombres} {trabajador.apellidos} ({trabajador.cargo.nombre}): {grupo_anterior or 'Sin grupo'} → {grupo_nuevo}")
        elif grupo_nuevo:
            grupos_conteo[grupo_nuevo] += 1
    
    print(f"\n{'='*80}")
    print(f"Actualización completada:")
    print(f"  - Total de trabajadores: {total}")
    print(f"  - Actualizados: {actualizados}")
    print(f"\nDistribución por grupos:")
    print(f"  - Operadores: {grupos_conteo['OPERADORES']}")
    print(f"  - Servicios Geológicos: {grupos_conteo['SERVICIOS_GEOLOGICOS']}")
    print(f"  - Línea de Mando: {grupos_conteo['LINEA_MANDO']}")
    print(f"  - Personal Auxiliar: {grupos_conteo['PERSONAL_AUXILIAR']}")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    actualizar_grupos_trabajadores()
