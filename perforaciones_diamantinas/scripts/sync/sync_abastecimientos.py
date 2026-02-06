"""
Script de sincronización de Abastecimientos desde APIs de Vilbragroup
Sincroniza todos los abastecimientos (PDD, ADIT, EPP, IN, etc.) 
y genera el historial de brocas automáticamente.

Uso:
    python scripts/sync/sync_abastecimientos.py [--year=2025] [--cc=000002] [--family=PDD]

Opciones:
    --year      Año a sincronizar (Defecto: año actual)
    --cc        Código de Centro de Costo (Opcional, si no se envía sincroniza TODOS)
    --family    Familia específica (Opcional, si no se envía sincroniza TODAS)

Autor: DrillControl
Fecha: Febrero 2026
"""
import os
import sys
import django
import argparse
import logging
from datetime import datetime

# ==========================================
# Configuración del Entorno Django
# ==========================================
# Obtener ruta base del proyecto (2 niveles arriba: scripts/sync/ -> scripts/ -> root)
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(scripts_dir)

# Agregar raíz al path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')

try:
    django.setup()
    print("Django environment configured successfully.")
except Exception as e:
    print(f"Error configuring Django: {e}")
    sys.exit(1)

# Importar modelos y servicios DESPUÉS de setup()
from drilling.utils.abastecimiento_service import AbastecimientoService
from drilling.models import Contrato

# ==========================================
# Configuración de Logging
# ==========================================
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'sync_abastecim_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='Sincronización de Abastecimientos')
    parser.add_argument('--year', type=str, default=str(datetime.now().year), help='Año a sincronizar (YYYY)')
    parser.add_argument('--cc', type=str, default=None, help='Código Centro de Costo específico')
    parser.add_argument('--family', type=str, default=None, help='Familia específica (ej: PDD)')
    return parser.parse_args()

def main():
    args = parse_args()
    
    logger.info("=======================================")
    logger.info(f"Iniciando Sincronización de Abastecimientos")
    logger.info(f"Año: {args.year}")
    logger.info(f"Centro Costo: {args.cc if args.cc else 'TODOS'}")
    logger.info(f"Familia: {args.family if args.family else 'TODAS'}")
    logger.info("=======================================")

    service = AbastecimientoService()
    
    try:
        # Ejecutar sincronización
        resultado = service.sincronizar_periodo(
            periodo=args.year,
            centro_costo=args.cc,
            solo_familia=args.family
        )
        
        # Reporte Final
        logger.info("\n=== RESULTADOS ===")
        logger.info(f"Total API Scan: {resultado.get('total_api', 0)}")
        logger.info(f"Nuevos Importados: {resultado.get('importados', 0)}")
        logger.info(f"Actualizados: {resultado.get('actualizados', 0)}")
        logger.info(f"Errores: {resultado.get('errores', 0)}")
        logger.info(f"Brocas Nuevas Detectadas: {resultado.get('brocas_creadas', 0)}")
        
        if resultado.get('detalles_errores'):
            logger.warning("\n--- Errores Registrados ---")
            for err in resultado['detalles_errores'][:10]: # Mostrar solo primeros 10
                logger.warning(f"- {err}")
            if len(resultado['detalles_errores']) > 10:
                logger.warning(f"... y {len(resultado['detalles_errores']) - 10} errores más.")

    except Exception as e:
        logger.error(f"Error fatal durante la ejecución del script: {str(e)}", exc_info=True)

if __name__ == '__main__':
    main()
