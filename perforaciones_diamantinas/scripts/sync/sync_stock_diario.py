"""
Script de sincronización diaria de stock desde APIs de Vilbragroup
Sincroniza PDD (Productos Diamantados) y ADIT (Aditivos) para todos los contratos
También sincroniza brocas pendientes (guardadas sin datos del API)

Ejecutar manualmente: python sync_stock_diario.py
"""
import os
import sys
import django
from datetime import datetime
import logging

# Configurar Django (2 niveles arriba: scripts/sync/ -> scripts/ -> perforaciones_diamantinas/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser, Contrato, TurnoComplemento, TipoComplemento, HistorialBroca
from drilling.api_client import get_api_client
from django.db import transaction

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

def sync_brocas_pendientes():
    """Sincroniza brocas que fueron guardadas sin datos del API"""
    logger.info(f"\n{'='*80}")
    logger.info("SINCRONIZACIÓN DE BROCAS PENDIENTES")
    logger.info(f"{'='*80}")
    
    try:
        # Buscar TurnoComplemento sin tipo_complemento (guardadas sin API)
        pendientes = TurnoComplemento.objects.filter(
            tipo_complemento__isnull=True
        ).select_related('turno')
        
        if not pendientes.exists():
            logger.info("✅ No hay brocas pendientes de sincronizar")
            return {'sincronizadas': 0, 'no_encontradas': 0, 'errores': 0}
        
        logger.info(f"📊 Total de registros pendientes: {pendientes.count()}")
        
        # Agrupar por serie
        series_pendientes = {}
        for tc in pendientes:
            serie = tc.codigo_serie
            if serie not in series_pendientes:
                series_pendientes[serie] = []
            series_pendientes[serie].append(tc)
        
        logger.info(f"📦 Series únicas pendientes: {len(series_pendientes)}")
        
        resultados = {
            'sincronizadas': 0,
            'no_encontradas': 0,
            'errores': 0
        }
        
        # Procesar cada serie
        for serie, turnos_complementos in series_pendientes.items():
            try:
                # Buscar el producto en TipoComplemento por serie
                producto = TipoComplemento.objects.filter(serie=serie).first()
                
                if not producto:
                    logger.warning(f"⚠️ Serie {serie} ({len(turnos_complementos)} usos): Producto no encontrado en API")
                    resultados['no_encontradas'] += 1
                    continue
                
                # Producto encontrado - actualizar
                with transaction.atomic():
                    actualizados = TurnoComplemento.objects.filter(
                        id__in=[tc.id for tc in turnos_complementos]
                    ).update(tipo_complemento=producto)
                    
                    # Actualizar o crear HistorialBroca
                    historial, created = HistorialBroca.objects.get_or_create(
                        serie=serie,
                        defaults={
                            'tipo_complemento': producto,
                            'contrato_actual': turnos_complementos[0].turno.contrato,
                            'fecha_primer_uso': min(tc.turno.fecha for tc in turnos_complementos),
                            'estado': 'EN_USO'
                        }
                    )
                    
                    if not created:
                        historial.tipo_complemento = producto
                        historial.save(update_fields=['tipo_complemento'])
                    
                    logger.info(f"✅ Serie {serie}: {actualizados} registros actualizados - {producto.nombre}")
                    resultados['sincronizadas'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Error sincronizando serie {serie}: {str(e)}", exc_info=True)
                resultados['errores'] += 1
        
        return resultados
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización de brocas pendientes: {str(e)}", exc_info=True)
        return {'sincronizadas': 0, 'no_encontradas': 0, 'errores': 1}

def main():
    """Función principal de sincronización"""
    logger.info("="*80)
    logger.info("INICIO DE SINCRONIZACIÓN DIARIA DE STOCK Y BROCAS")
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
    
    # Sincronizar brocas pendientes después del stock
    logger.info("\n" + "="*80)
    logger.info("FASE 2: SINCRONIZACIÓN DE BROCAS PENDIENTES")
    logger.info("="*80)
    
    resultados_brocas = sync_brocas_pendientes()
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("RESUMEN DE SINCRONIZACIÓN")
    logger.info("="*80)
    logger.info("\n📦 STOCK:")
    logger.info(f"  PDD exitosos: {resultados['pdd_exitosos']}")
    logger.info(f"  PDD fallidos: {resultados['pdd_fallidos']}")
    logger.info(f"  ADIT exitosos: {resultados['adit_exitosos']}")
    logger.info(f"  ADIT fallidos: {resultados['adit_fallidos']}")
    logger.info("\n🔧 BROCAS PENDIENTES:")
    logger.info(f"  Sincronizadas: {resultados_brocas['sincronizadas']}")
    logger.info(f"  No encontradas: {resultados_brocas['no_encontradas']}")
    logger.info(f"  Errores: {resultados_brocas['errores']}")
    logger.info("\n" + "="*80)
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
