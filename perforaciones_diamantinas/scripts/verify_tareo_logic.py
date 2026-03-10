import os
import sys
import django
from datetime import date

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Trabajador, Contrato

def verificar_logica_tareo():
    print("=== VERIFICACIÓN DE LÓGICA DE TAREO (SIMULACIÓN) ===\n")
    
    # 1. Usar COLQUISIRI como prueba porque sabemos que tiene Línea de Mando
    try:
        contrato = Contrato.objects.get(nombre_contrato__icontains='COLQUISIRI')
        print(f"Usando datos de contrato: {contrato.nombre_contrato}")
    except Contrato.DoesNotExist:
        print("No se encontró contrato COLQUISIRI para la prueba")
        return

    # 2. Obtener trabajadores
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).select_related('cargo')
    
    print(f"Total trabajadores activos: {trabajadores.count()}")
    
    # 3. Simular la lógica de agrupación de views_tareo.py
    trabajadores_por_grupo = {}
    
    for trabajador in trabajadores:
        # Lógica exacta de la vista
        grupo_key = trabajador.grupo
        if not grupo_key:
            grupo_key = trabajador.asignar_grupo_automatico()
            if not grupo_key:
                grupo_key = 'SIN_GRUPO'
        
        # Aquí está la clave: Si no tiene guardia, se asigna 'SIN_GUARDIA'
        guardia_key = trabajador.guardia_asignada if trabajador.guardia_asignada else 'SIN_GUARDIA'
        
        if grupo_key not in trabajadores_por_grupo:
            trabajadores_por_grupo[grupo_key] = {
                'nombre': grupo_key, # Simplificado para el test
                'guardias': {}
            }
        
        if guardia_key not in trabajadores_por_grupo[grupo_key]['guardias']:
            trabajadores_por_grupo[grupo_key]['guardias'][guardia_key] = []
            
        trabajadores_por_grupo[grupo_key]['guardias'][guardia_key].append(trabajador)

    # 4. Imprimir resultados simulando la renderización
    orden_grupos = ['LINEA_MANDO', 'OPERADORES', 'SERVICIOS_GEOLOGICOS', 'CONDUCTORES', 'SIN_GRUPO']
    
    print("\n=== RESULTADO DE LA AGRUPACIÓN ===")
    for grupo in orden_grupos:
        if grupo in trabajadores_por_grupo:
            print(f"\n📂 GRUPO: {grupo}")
            guardias = trabajadores_por_grupo[grupo]['guardias']
            
            # Ordenar guardias como en la vista
            keys_guardias = ['A', 'B', 'C', 'SIN_GUARDIA']
            
            for g_key in keys_guardias:
                if g_key in guardias:
                    lista = guardias[g_key]
                    print(f"   └── 🛡️ GUARDIA: {g_key} ({len(lista)} trabajadores)")
                    for t in lista:
                        # Verificar si es uno de los casos clave
                        es_clave = any(x in t.apellidos for x in ['FONSECA', 'IPARRAGUIRRE', 'CHOQUE'])
                        marcador = "✅" if es_clave else "-"
                        print(f"       {marcador} {t.nombres} {t.apellidos} | Cargo: {t.cargo.nombre}")

if __name__ == '__main__':
    verificar_logica_tareo()
