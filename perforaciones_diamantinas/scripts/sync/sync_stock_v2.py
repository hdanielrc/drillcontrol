"""
Script de sincronización diaria de stock desde APIs de Vilbragroup
VERSIÓN 2.0 - Con Snapshots Históricos y Alertas Automáticas

Sincroniza PDD (Productos Diamantados) y ADIT (Aditivos) para todos los contratos.
Ahora guarda snapshots históricos y genera alertas automáticas.

Ejecutar manualmente: python sync_stock_diario.py
Opciones:
    --verbose       Muestra progreso detallado
    --contrato=ID   Sincronizar solo un contrato específico
    --dry-run       Simular sin guardar datos

Autor: DrillControl
Actualizado: Diciembre 2024
"""
import os
import sys
import django
from datetime import datetime
import logging
import argparse

# Configurar Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import Contrato
from drilling.utils.stock_service import StockService, sincronizar_todos_los_contratos

# Configurar logging
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'sync_stock_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Sincronización de stock desde API Vilbragroup con histórico y alertas'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar progreso detallado'
    )
    parser.add_argument(
        '--contrato',
        type=int,
        help='ID del contrato específico a sincronizar'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sincronización sin guardar datos'
    )
    return parser.parse_args()


def sincronizar_contrato_especifico(contrato_id: int, verbose: bool = False) -> dict:
    """
    Sincroniza un contrato específico.
    
    Args:
        contrato_id: ID del contrato
        verbose: Mostrar detalles
        
    Returns:
        Resultado de la sincronización
    """
    try:
        contrato = Contrato.objects.get(id=contrato_id)
    except Contrato.DoesNotExist:
        logger.error(f"❌ Contrato con ID {contrato_id} no encontrado")
        return {'success': False, 'error': 'Contrato no encontrado'}
    
    if not contrato.codigo_centro_costo:
        logger.error(f"❌ Contrato {contrato.nombre_contrato} no tiene código de centro de costo")
        return {'success': False, 'error': 'Sin código de centro de costo'}
    
    if verbose:
        print(f"\n📡 Sincronizando contrato: {contrato.nombre_contrato}")
        print(f"   Centro de costo: {contrato.codigo_centro_costo}")
    
    service = StockService(contrato)
    resultado = service.sincronizar_stock_completo()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"📊 RESULTADOS:")
        print(f"   PDD sincronizados: {resultado['pdd']['count']}")
        print(f"   ADIT sincronizados: {resultado['adit']['count']}")
        print(f"   Alertas generadas: {resultado['alertas_generadas']}")
        
        if resultado['pdd']['error']:
            print(f"   ⚠️ Error PDD: {resultado['pdd']['error']}")
        if resultado['adit']['error']:
            print(f"   ⚠️ Error ADIT: {resultado['adit']['error']}")
        
        # Mostrar resumen de stock
        resumen = service.obtener_resumen_stock()
        print(f"\n📦 RESUMEN DE STOCK:")
        print(f"   Total artículos: {resumen['total_articulos']}")
        print(f"   PDD: {resumen['pdd_count']} | ADIT: {resumen['adit_count']}")
        print(f"   Artículos críticos: {resumen['articulos_criticos']}")
        print(f"   Artículos agotados: {resumen['articulos_agotados']}")
        print(f"   Alertas activas: {resumen['alertas_activas']}")
    
    return resultado


def main():
    """Función principal de sincronización"""
    args = parse_args()
    
    logger.info("="*80)
    logger.info("INICIO DE SINCRONIZACIÓN DE STOCK v2.0")
    logger.info(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Con snapshots históricos y alertas automáticas")
    logger.info("="*80)
    
    if args.dry_run:
        logger.info("🔍 MODO DRY-RUN: No se guardarán datos")
        print("⚠️ Modo dry-run no implementado aún. Use sin --dry-run")
        return
    
    try:
        if args.contrato:
            # Sincronizar contrato específico
            resultado = sincronizar_contrato_especifico(args.contrato, args.verbose)
            success = resultado.get('success', False)
        else:
            # Sincronizar todos los contratos
            resultados = sincronizar_todos_los_contratos(verbose=args.verbose)
            success = resultados['contratos_exitosos'] > 0
            
            # Log resumen
            logger.info("\n" + "="*80)
            logger.info("RESUMEN FINAL DE SINCRONIZACIÓN")
            logger.info("="*80)
            logger.info(f"Contratos procesados: {resultados['contratos_procesados']}")
            logger.info(f"Contratos exitosos: {resultados['contratos_exitosos']}")
            logger.info(f"Contratos fallidos: {resultados['contratos_fallidos']}")
            logger.info(f"Total PDD sincronizados: {resultados['total_pdd']}")
            logger.info(f"Total ADIT sincronizados: {resultados['total_adit']}")
            logger.info(f"Total alertas generadas: {resultados['total_alertas']}")
            logger.info(f"Duración: {resultados['duracion_segundos']:.1f} segundos")
            logger.info("="*80)
        
        if success:
            logger.info("✅ Sincronización completada exitosamente")
        else:
            logger.warning("⚠️ Sincronización completada con errores")
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Sincronización interrumpida por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Error crítico: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
