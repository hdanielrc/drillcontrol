import os
import sys
import django
import requests
import logging
from datetime import datetime

# ==========================================
# Configuración del Entorno Django
# ==========================================
# Obtener ruta base del proyecto (2 niveles arriba: scripts/sync/ -> scripts/ -> root)
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(scripts_dir)

# Agregar el directorio raíz al path de Python
sys.path.append(project_root)

# Configurar la variable de entorno para los settings de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')

# Inicializar Django
try:
    django.setup()
    print("Django setup completado exitosamente.")
except Exception as e:
    print(f"Error configurando Django: {e}")
    sys.exit(1)

# Importar modelos después de setup
from drilling.models import TrabajadorAPI, Contrato, Cargo

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

API_URL = "https://tic.vilbragroup.net/API/DrillControl/trabajadores?token=cff25a36-682a-4570-ad84-aaaabffc89bf"

def sync_trabajadores():
    logger.info("Iniciando sincronización de trabajadores...")
    
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Handle dict response with 'trabajadores' key or direct list
        if isinstance(data, dict) and 'trabajadores' in data:
            workers_data = data['trabajadores']
        elif isinstance(data, list):
            workers_data = data
        else:
            logger.error(f"Formato de respuesta inesperado: {type(data)}")
            return
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con la API: {e}")
        return
    except ValueError as e: # JSONDecodeError
        logger.error(f"Error decodificando respuesta JSON: {e}")
        return

    logger.info(f"Se obtuvieron {len(workers_data)} trabajadores de la API.")

    processed_count = 0
    created_count = 0
    updated_count = 0
    
    # Cache para optimizar búsquedas
    # Mapeo: codigo_centro_costo -> Contrato object
    contratos_cache = {}
    # Mapeo: nombre_cargo -> Cargo object 
    cargos_cache = {}

    # Pre-cargar contratos que tienen codigo_centro_costo
    for c in Contrato.objects.exclude(codigo_centro_costo__isnull=True).exclude(codigo_centro_costo__exact=''):
        contratos_cache[c.codigo_centro_costo] = c

    # Pre-cargar cargos por nombre
    for c in Cargo.objects.all():
        cargos_cache[c.nombre] = c

    for worker in workers_data:
        dni = worker.get('dni')
        if not dni:
            logger.warning("Trabajador sin DNI encontrado en API. Saltando.")
            continue

        try:
            # Preparar datos base
            defaults = {
                'nombres': worker.get('nombres', ''),
                'apepat': worker.get('apepat', ''),
                'apemat': worker.get('apemat', ''),
                'cargo_nombre': worker.get('cargo', ''),
                'centro_costo': worker.get('centro_costo', ''),
                'contrato_nombre': worker.get('contrato', ''),
                'fecha_contratacion': worker.get('fecha_contratacion'), # Asumimos formato compatible YYYY-MM-DD o None
                'estado_api': worker.get('estado', ''),
                'synced': True
            }

            # Buscar Contrato
            cc_code = worker.get('centro_costo')
            contrato_obj = None
            if cc_code:
                contrato_obj = contratos_cache.get(cc_code)
                # Si no está en cache, intentar buscar en DB de nuevo por si acaso (aunque pre-cargamos)
                if not contrato_obj:
                    contrato_obj = Contrato.objects.filter(codigo_centro_costo=cc_code).first()
                    if contrato_obj:
                        contratos_cache[cc_code] = contrato_obj
            
            if contrato_obj:
                defaults['contrato'] = contrato_obj

            # Buscar Cargo
            cargo_name = worker.get('cargo')
            cargo_obj = None
            if cargo_name:
                cargo_obj = cargos_cache.get(cargo_name)
                if not cargo_obj:
                    # Intentar búsqueda flexible o directa
                    cargo_obj = Cargo.objects.filter(nombre__iexact=cargo_name).first()
                    if cargo_obj:
                        cargos_cache[cargo_name] = cargo_obj
                    else:
                        logger.warning(f"Cargo no encontrado para DNI {dni}: '{cargo_name}'")
            
            if cargo_obj:
                defaults['cargo'] = cargo_obj

            # Update or Create
            obj, created = TrabajadorAPI.objects.update_or_create(
                dni=dni,
                defaults=defaults
            )

            processed_count += 1
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            if processed_count % 100 == 0:
                logger.info(f"Procesados {processed_count} trabajadores...")

        except Exception as e:
            logger.error(f"Error procesando trabajador DNI {dni}: {e}")

    logger.info("="*40)
    logger.info("RESUMEN DE SINCRONIZACIÓN DE TRABAJADORES")
    logger.info("="*40)
    logger.info(f"Total procesados: {processed_count}")
    logger.info(f"Creados: {created_count}")
    logger.info(f"Actualizados: {updated_count}")
    logger.info("="*40)

if __name__ == "__main__":
    sync_trabajadores()
