"""
Script de sincronización diaria de stock desde APIs de Vilbragroup
Sincroniza PDD (Productos Diamantados) y ADIT (Aditivos) para todos los contratos

Ejecutar manualmente: python sync_stock_diario.py
"""
import os
import sys
import django
from datetime import datetime
import logging

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser, Contrato
from drilling.api_client import get_api_client

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

def sync_pdd(centro_costo, nombre_contrato):
    """Sincroniza Productos Diamantados (PDD)"""
    logger.info(f"{'='*80}")
    logger.info(f"Sincronizando PDD para {nombre_contrato} (CC: {centro_costo})")
    logger.info(f"{'='*80}")
    
    try:
        client = get_api_client()
        productos = client.obtener_productos_diamantados(centro_costo=centro_costo)
        
        if not productos:
            logger.warning(f"⚠️ No se obtuvieron productos PDD para {nombre_contrato}")
            return False
        
        logger.info(f"✅ {nombre_contrato}: {len(productos)} artículos PDD obtenidos")
        
        # Aquí se puede agregar lógica para guardar en BD si es necesario
        # Por ahora solo registramos la consulta exitosa
        
        return True
    except KeyboardInterrupt:
        logger.warning(f"⚠️ Sincronización interrumpida manualmente en PDD {nombre_contrato}")
        raise  # Re-lanzar para detener el script completamente
    except Exception as e:
        logger.error(f"❌ Error sincronizando PDD para {nombre_contrato}: {str(e)}", exc_info=True)
        return False

def sync_adit(centro_costo, nombre_contrato):
    """Sincroniza Aditivos (ADIT)"""
    logger.info(f"{'='*80}")
    logger.info(f"Sincronizando ADIT para {nombre_contrato} (CC: {centro_costo})")
    logger.info(f"{'='*80}")
    
    try:
        client = get_api_client()
        aditivos = client.obtener_aditivos(centro_costo=centro_costo)
        
        if not aditivos:
            logger.warning(f"⚠️ No se obtuvieron aditivos para {nombre_contrato}")
            return False
        
        logger.info(f"✅ {nombre_contrato}: {len(aditivos)} artículos ADIT obtenidos")
        
        # Aquí se puede agregar lógica para guardar en BD si es necesario
        # Por ahora solo registramos la consulta exitosa
        
        return True
    except KeyboardInterrupt:
        logger.warning(f"⚠️ Sincronización interrumpida manualmente en ADIT {nombre_contrato}")
        raise  # Re-lanzar para detener el script completamente
    except Exception as e:
        logger.error(f"❌ Error sincronizando ADIT para {nombre_contrato}: {str(e)}", exc_info=True)
        return False

def main():
    """Función principal de sincronización"""
    logger.info("="*80)
    logger.info("INICIO DE SINCRONIZACIÓN DIARIA DE STOCK")
    logger.info(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    # Obtener solo los contratos activos
    contratos = Contrato.objects.filter(estado='ACTIVO')
    
    if not contratos.exists():
        logger.error("❌ No se encontraron contratos activos en la base de datos")
        return
    
    logger.info(f"Contratos activos encontrados: {contratos.count()}")
    
    resultados = {
        'pdd_exitosos': 0,
        'pdd_fallidos': 0,
        'adit_exitosos': 0,
        'adit_fallidos': 0
    }
    
    # Sincronizar para cada contrato
    for contrato in contratos:
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Procesando contrato: {contrato.nombre_contrato}")
            logger.info(f"Centro de Costo: {contrato.codigo_centro_costo}")
            logger.info(f"{'='*80}")
            
            # Sincronizar PDD
            try:
                if sync_pdd(contrato.codigo_centro_costo, contrato.nombre_contrato):
                    resultados['pdd_exitosos'] += 1
                else:
                    resultados['pdd_fallidos'] += 1
            except KeyboardInterrupt:
                logger.warning("⚠️ Sincronización interrumpida por el usuario")
                raise
            except Exception as e:
                logger.error(f"❌ Error inesperado en PDD para {contrato.nombre_contrato}: {str(e)}", exc_info=True)
                resultados['pdd_fallidos'] += 1
            
            # Sincronizar ADIT
            try:
                if sync_adit(contrato.codigo_centro_costo, contrato.nombre_contrato):
                    resultados['adit_exitosos'] += 1
                else:
                    resultados['adit_fallidos'] += 1
            except KeyboardInterrupt:
                logger.warning("⚠️ Sincronización interrumpida por el usuario")
                raise
            except Exception as e:
                logger.error(f"❌ Error inesperado en ADIT para {contrato.nombre_contrato}: {str(e)}", exc_info=True)
                resultados['adit_fallidos'] += 1
                
        except KeyboardInterrupt:
            logger.warning(f"⚠️ Sincronización detenida en contrato {contrato.nombre_contrato}")
            break  # Salir del loop de contratos
        except Exception as e:
            logger.error(f"❌ Error crítico procesando contrato {contrato.nombre_contrato}: {str(e)}", exc_info=True)
            # Continuar con el siguiente contrato
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("RESUMEN DE SINCRONIZACIÓN")
    logger.info("="*80)
    logger.info(f"PDD exitosos: {resultados['pdd_exitosos']}")
    logger.info(f"PDD fallidos: {resultados['pdd_fallidos']}")
    logger.info(f"ADIT exitosos: {resultados['adit_exitosos']}")
    logger.info(f"ADIT fallidos: {resultados['adit_fallidos']}")
    logger.info("="*80)
    logger.info("FIN DE SINCRONIZACIÓN")
    logger.info("="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Sincronización interrumpida manualmente por el usuario")
        sys.exit(130)  # Código de salida estándar para KeyboardInterrupt
    except Exception as e:
        logger.error(f"❌ Error crítico en la sincronización: {str(e)}", exc_info=True)
        sys.exit(1)
