import os
import sys
import django
import requests
import logging
import re
import csv
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
from django.db.models import Max
from drilling.models import Trabajador, Contrato, ContratoServicio

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


def _parse_api_date(value):
    if not value:
        return None
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return value

    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        logger.warning("No se pudo parsear fecha de API: %s", raw)
        return None

def sync_trabajadores(dry_run=False, filter_centro=None, api_url=None):
    logger.info("Iniciando sincronización de trabajadores...")
    
    url = api_url if api_url else API_URL
    try:
        response = requests.get(url, timeout=120)
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
    
    # Cache: codigo_centro_costo -> Contrato object
    # Incluye tanto el codigo_centro_costo principal del Contrato
    # como los CCs adicionales definidos en ContratoServicio
    contratos_cache = {}

    # Pre-cargar desde campo principal
    for c in Contrato.objects.exclude(codigo_centro_costo__isnull=True).exclude(codigo_centro_costo__exact=''):
        contratos_cache[c.codigo_centro_costo] = c

    # Pre-cargar desde ContratoServicio (CCs adicionales)
    for srv in ContratoServicio.objects.filter(activo=True).select_related('contrato'):
        if srv.codigo_centro_costo and srv.codigo_centro_costo not in contratos_cache:
            contratos_cache[srv.codigo_centro_costo] = srv.contrato

    anomalies_file = os.path.join(project_root, 'logs', 'trabajadores_sync_anomalies.csv')
    os.makedirs(os.path.dirname(anomalies_file), exist_ok=True)

    for worker in workers_data:
        # Si se pidió filtrar por centro de costo, saltar los demás
        if filter_centro:
            cc = worker.get('centro_costo') or worker.get('centro') or ''
            if str(cc).strip() != str(filter_centro).strip():
                continue
        # Normalizar DNI: preservar ceros a la izquierda cuando posible.
        dni_raw = worker.get('dni')
        if dni_raw is None:
            logger.warning("Trabajador sin DNI encontrado en API. Saltando.")
            continue

        dni_orig = dni_raw
        dni = str(dni_raw).strip()
        # Eliminar caracteres no númericos para normalizar (pero conservar si no son todos dígitos)
        digits = re.sub(r"\D", "", dni)
        if digits:
            if len(digits) < 8:
                digits = digits.zfill(8)
            dni = digits

        if not dni:
            logger.warning(f"Trabajador con DNI vacío tras normalización (orig={dni_orig}). Saltando.")
            continue

        try:
            # Preparar datos base
            # Nombres y apellidos: aplicar fallbacks si la API viene inconsistente
            nombres_raw = worker.get('nombres', '') or ''
            apepat_raw = worker.get('apepat', '') or ''
            apemat_raw = worker.get('apemat', '') or ''

            nombres = nombres_raw.strip()
            apepat = apepat_raw.strip()
            apemat = apemat_raw.strip()

            # Caso: la API puede llegar con "APELLIDO, NOMBRES" en el campo `nombres`
            if (not apepat) and (',' in nombres):
                left, right = [p.strip() for p in nombres.split(',', 1)]
                # left suele ser apellidos, right los nombres
                name_parts = left.split()
                apepat = name_parts[0] if name_parts else ''
                apemat = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                nombres = right

            # Si aún no hay apellidos pero `nombres` tiene 3+ palabras, asumir ultimas 2 como apellidos
            if (not apepat and not apemat) and nombres:
                words = nombres.split()
                if len(words) >= 3:
                    apemat = words[-1]
                    apepat = words[-2]
                    nombres = ' '.join(words[:-2])
                elif len(words) == 2 and not apepat:
                    # asumir formato "Nombre Apellido"
                    apepat = words[-1]
                    nombres = words[0]

            cargo_api = worker.get('cargo', '').strip()
            grupo_calculado = Trabajador.calcular_grupo_desde_cargo(cargo_api)
            tipo_servicio_calculado = Trabajador.calcular_tipo_servicio_desde_cargo(cargo_api)
            
            estado_api = worker.get('estado', '')
            # Si la API marca al trabajador como standby, reflejarlo en el flag.
            # Cualquier otro estado (ACTIVO, INACTIVO, etc.) → es_standby=False.
            es_standby_api = estado_api.upper() in ('STAND_BY_CLIENTE', 'STAND_BY_ROCKDRILL', 'STAND_BY')

            defaults = {
                'nombres': nombres,
                'apepat': apepat,
                'apemat': apemat,
                'cargo': cargo_api, # Guardamos texto directo
                'grupo': grupo_calculado,
                'tipo_servicio': tipo_servicio_calculado,
                'centro_costo': worker.get('centro_costo', ''),
                'contrato_nombre': worker.get('contrato', ''),
                'fecha_contratacion': _parse_api_date(worker.get('fecha_contratacion')),
                'fecha_cese': _parse_api_date(
                    worker.get('fecha_cese')
                    or worker.get('fecha_baja')
                ),
                'estado': estado_api,
                'estado_api': estado_api,
                'es_standby': es_standby_api,  # sincronizar con API
                'synced': True
            }

            # Buscar Contrato (Mantenemos relación si existe)
            cc_code = worker.get('centro_costo')
            contrato_obj = None
            if cc_code:
                contrato_obj = contratos_cache.get(cc_code)
                if not contrato_obj:
                    contrato_obj = Contrato.objects.filter(codigo_centro_costo=cc_code).first()
                    if contrato_obj:
                        contratos_cache[cc_code] = contrato_obj
            
            if contrato_obj:
                defaults['contrato'] = contrato_obj

            # Registrar anomalías detectadas (DNI o nombres cambiados por la normalización)
            if str(dni_orig).strip() != dni:
                logger.warning(f"Normalizado DNI: orig={dni_orig} -> {dni} para nombre='{nombres} {apepat} {apemat}'")
                try:
                    with open(anomalies_file, 'a', newline='', encoding='utf-8') as af:
                        writer = csv.writer(af)
                        writer.writerow([datetime.utcnow().isoformat(), dni_orig, dni, nombres, apepat, apemat, worker.get('centro_costo')])
                except Exception:
                    logger.exception("No se pudo escribir archivo de anomalías de trabajadores.")

            # Update or Create (o simulación si dry_run)
            if dry_run:
                exists = Trabajador.objects.filter(dni=dni).exists()
                processed_count += 1
                if exists:
                    updated_count += 1
                else:
                    created_count += 1
            else:
                obj, created = Trabajador.objects.update_or_create(
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
