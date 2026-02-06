"""
Servicio de sincronización de abastecimientos desde API externa
Gestiona la importación de artículos abastecidos y su integración con HistorialBroca
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
from decimal import Decimal
import logging

from django.db import transaction
from django.db import models
from django.utils import timezone

from drilling.api_client import VilbragroupAPIClient
from drilling.models import (
    AbastecimientoArticulo,
    Contrato,
    HistorialBroca,
    TipoComplemento
)

logger = logging.getLogger(__name__)


class AbastecimientoService:
    """
    Servicio para sincronizar abastecimientos desde API externa
    """
    
    def __init__(self):
        self.api_client = VilbragroupAPIClient()
    
    def sincronizar_periodo(
        self,
        periodo: str,
        centro_costo: Optional[str] = None,
        solo_familia: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Sincroniza todos los abastecimientos de un periodo desde la API
        
        Args:
            periodo: Periodo en formato YYYYMM (ej: '202601')
            centro_costo: Centro de costo específico (opcional)
            solo_familia: Filtrar solo por familia específica (ej: 'PDD', 'ADIT')
        
        Returns:
            Diccionario con resultados de la sincronización:
            {
                'total_api': 100,
                'importados': 95,
                'actualizados': 5,
                'errores': 0,
                'brocas_creadas': 10,
                'detalles_errores': []
            }
        """
        logger.info(f"Iniciando sincronización de abastecimientos - Periodo: {periodo}")
        
        resultado = {
            'total_api': 0,
            'importados': 0,
            'actualizados': 0,
            'errores': 0,
            'brocas_creadas': 0,
            'detalles_errores': []
        }
        
        try:
            # Obtener datos de la API
            abastecimientos = self.api_client.obtener_articulos_abastecidos(
                periodo=periodo,
                centro_costo=centro_costo
            )
            
            if not abastecimientos:
                logger.warning(f"No se obtuvieron abastecimientos de la API para el periodo {periodo}")
                return resultado
            
            resultado['total_api'] = len(abastecimientos)
            logger.info(f"Obtenidos {len(abastecimientos)} registros de la API")
            
            # Filtrar por familia si se especificó
            if solo_familia:
                abastecimientos = [
                    a for a in abastecimientos 
                    if a.get('familia') == solo_familia
                ]
                logger.info(f"Filtrados a {len(abastecimientos)} registros de familia {solo_familia}")
            
            # Procesar cada abastecimiento
            for item in abastecimientos:
                try:
                    created, broca_creada = self._procesar_abastecimiento(item)
                    
                    if created:
                        resultado['importados'] += 1
                    else:
                        resultado['actualizados'] += 1
                    
                    if broca_creada:
                        resultado['brocas_creadas'] += 1
                        
                except Exception as e:
                    resultado['errores'] += 1
                    error_msg = f"Error procesando {item.get('codigo', 'UNKNOWN')}: {str(e)}"
                    logger.error(error_msg)
                    resultado['detalles_errores'].append(error_msg)
            
            logger.info(
                f"Sincronización completada - "
                f"Importados: {resultado['importados']}, "
                f"Actualizados: {resultado['actualizados']}, "
                f"Errores: {resultado['errores']}, "
                f"Brocas creadas: {resultado['brocas_creadas']}"
            )
            
        except Exception as e:
            logger.error(f"Error crítico en sincronización: {e}")
            resultado['detalles_errores'].append(f"Error crítico: {str(e)}")
        
        return resultado
    
    @transaction.atomic
    def _procesar_abastecimiento(self, data: Dict) -> Tuple[bool, bool]:
        """
        Procesa un registro de abastecimiento individual
        
        Args:
            data: Diccionario con datos del abastecimiento desde API
        
        Returns:
            Tupla (created, broca_creada):
            - created: True si se creó nuevo registro, False si se actualizó
            - broca_creada: True si se creó nuevo registro en HistorialBroca
        """
        # Validar campos requeridos
        campos_requeridos = [
            'fecha', 'centro_costo', 'documento', 'codigo', 
            'descripcion', 'cantidad', 'unidad', 'familia',
            'precio_unitario', 'precio_total'
        ]
        
        for campo in campos_requeridos:
            if campo not in data:
                raise ValueError(f"Campo requerido faltante: {campo}")
        
        # Parsear fecha
        fecha = self._parsear_fecha(data['fecha'])
        
        # Obtener o buscar contrato por centro de costo
        contrato = self._obtener_contrato(data['centro_costo'])
        if not contrato:
            raise ValueError(f"Contrato no encontrado para centro de costo: {data['centro_costo']}")
        
        # Buscar si ya existe el registro
        serie = data.get('serie')
        
        abastecimiento, created = AbastecimientoArticulo.objects.update_or_create(
            documento=data['documento'],
            codigo=data['codigo'],
            serie=serie if serie else '',  # Para unique_together
            defaults={
                'fecha': fecha,
                'centro_costo': data['centro_costo'],
                'contrato': contrato,
                'documento_referencia': data.get('documento_referencia', ''),
                'descripcion': data['descripcion'],
                'codigo_movimiento': data.get('codigo_movimiento', ''),
                'cantidad': Decimal(str(data['cantidad'])),
                'unidad': data['unidad'],
                'familia': data['familia'],
                'precio_unitario': Decimal(str(data['precio_unitario'])),
                'precio_total': Decimal(str(data['precio_total'])),
            }
        )
        
        # Verificar si se creó una broca nueva
        broca_creada = False
        if created and data['familia'] == 'PDD' and serie:
            # El método save() del modelo ya sincroniza con HistorialBroca
            # Solo verificamos si se creó
            if abastecimiento.historial_broca:
                broca_creada = True
                logger.info(f"Nueva broca registrada: {serie}")
        
        return created, broca_creada
    
    def _parsear_fecha(self, fecha_str: str) -> date:
        """
        Parsea una fecha en formato string a objeto date
        Soporta múltiples formatos: YYYY-MM-DD, DD/MM/YYYY, etc.
        """
        formatos = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
        ]
        
        for formato in formatos:
            try:
                return datetime.strptime(fecha_str, formato).date()
            except ValueError:
                continue
        
        raise ValueError(f"Formato de fecha no reconocido: {fecha_str}")
    
    def _obtener_contrato(self, centro_costo: str) -> Optional[Contrato]:
        """
        Obtiene el contrato asociado a un centro de costo
        
        Estrategias:
        1. Buscar por centro_costo exacto
        2. Buscar por centro_costo en nombre_contrato
        3. Buscar contrato activo por defecto
        """
        try:
            # Buscar por centro_costo exacto (si existe el campo)
            if hasattr(Contrato, 'centro_costo'):
                contrato = Contrato.objects.filter(centro_costo=centro_costo).first()
                if contrato:
                    return contrato
            
            # Buscar en nombre o código
            contrato = Contrato.objects.filter(
                nombre_contrato__icontains=centro_costo
            ).first()
            
            if contrato:
                return contrato
            
            # Último recurso: obtener primer contrato activo
            logger.warning(f"No se encontró contrato para centro_costo {centro_costo}, usando primer contrato activo")
            return Contrato.objects.filter(activo=True).first()
            
        except Exception as e:
            logger.error(f"Error buscando contrato: {e}")
            return None
    
    def obtener_resumen_abastecimientos(
        self,
        contrato_id: int,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        familia: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Obtiene un resumen de abastecimientos para un contrato
        
        Args:
            contrato_id: ID del contrato
            fecha_inicio: Fecha inicio del rango (opcional)
            fecha_fin: Fecha fin del rango (opcional)
            familia: Filtrar por familia (opcional)
        
        Returns:
            Diccionario con resumen de abastecimientos
        """
        queryset = AbastecimientoArticulo.objects.filter(contrato_id=contrato_id)
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        if familia:
            queryset = queryset.filter(familia=familia)
        
        from django.db.models import Sum, Count
        
        resumen = queryset.aggregate(
            total_registros=Count('id'),
            total_cantidad=Sum('cantidad'),
            total_valor=Sum('precio_total'),
            brocas_con_serie=Count('id', filter=models.Q(familia='PDD', serie__isnull=False))
        )
        
        # Obtener últimas sincronizaciones
        ultimas = queryset.order_by('-fecha_sincronizacion')[:10]
        
        return {
            'resumen': resumen,
            'ultimas_sincronizaciones': list(ultimas.values(
                'fecha', 'codigo', 'descripcion', 'serie', 'cantidad', 
                'precio_total', 'fecha_sincronizacion'
            ))
        }
    
    def buscar_broca_por_serie(self, serie: str) -> Optional[HistorialBroca]:
        """
        Busca una broca en el historial por su serie
        
        Args:
            serie: Serie de la broca
        
        Returns:
            Objeto HistorialBroca o None
        """
        try:
            return HistorialBroca.objects.select_related(
                'tipo_complemento', 'contrato_actual'
            ).get(serie=serie)
        except HistorialBroca.DoesNotExist:
            return None
    
    def listar_brocas_disponibles(
        self,
        contrato_id: int,
        tipo_complemento_id: Optional[int] = None
    ) -> List[HistorialBroca]:
        """
        Lista brocas disponibles (estado NUEVA o EN_USO) para un contrato
        
        Args:
            contrato_id: ID del contrato
            tipo_complemento_id: Filtrar por tipo de complemento (opcional)
        
        Returns:
            Lista de HistorialBroca
        """
        queryset = HistorialBroca.objects.filter(
            contrato_actual_id=contrato_id,
            estado__in=['NUEVA', 'EN_USO']
        ).select_related('tipo_complemento')
        
        if tipo_complemento_id:
            queryset = queryset.filter(tipo_complemento_id=tipo_complemento_id)
        
        return list(queryset.order_by('serie'))
    
    def sincronizar_todos_ddh(
        self,
        periodo: str,
        solo_familia: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Sincroniza todos los centros de costo DDH para un periodo
        
        Args:
            periodo: Periodo en formato YYYYMM (ej: '202601')
            solo_familia: Filtrar solo por familia específica (ej: 'PDD')
        
        Returns:
            Diccionario con resultados consolidados:
            {
                'periodo': '202601',
                'total_centros': 19,
                'centros_procesados': 18,
                'centros_con_error': 1,
                'total_importados': 250,
                'total_actualizados': 50,
                'total_errores': 2,
                'total_brocas_creadas': 45,
                'resultados_por_centro': {...},
                'errores': [...]
            }
        """
        from django.conf import settings
        
        logger.info(f"Iniciando sincronización masiva DDH - Periodo: {periodo}")
        
        centros_ddh = getattr(settings, 'CENTROS_COSTO_DDH', [])
        
        resultado_consolidado = {
            'periodo': periodo,
            'total_centros': len(centros_ddh),
            'centros_procesados': 0,
            'centros_con_error': 0,
            'total_importados': 0,
            'total_actualizados': 0,
            'total_errores': 0,
            'total_brocas_creadas': 0,
            'resultados_por_centro': {},
            'errores': []
        }
        
        for centro_costo in centros_ddh:
            try:
                logger.info(f"Procesando centro de costo: {centro_costo}")
                
                resultado = self.sincronizar_periodo(
                    periodo=periodo,
                    centro_costo=centro_costo,
                    solo_familia=solo_familia
                )
                
                resultado_consolidado['centros_procesados'] += 1
                resultado_consolidado['total_importados'] += resultado['importados']
                resultado_consolidado['total_actualizados'] += resultado['actualizados']
                resultado_consolidado['total_errores'] += resultado['errores']
                resultado_consolidado['total_brocas_creadas'] += resultado['brocas_creadas']
                
                resultado_consolidado['resultados_por_centro'][centro_costo] = {
                    'total_api': resultado['total_api'],
                    'importados': resultado['importados'],
                    'actualizados': resultado['actualizados'],
                    'errores': resultado['errores'],
                    'brocas_creadas': resultado['brocas_creadas']
                }
                
                logger.info(
                    f"Centro {centro_costo} completado - "
                    f"Registros API: {resultado['total_api']}, "
                    f"Importados: {resultado['importados']}, "
                    f"Brocas creadas: {resultado['brocas_creadas']}"
                )
                
            except Exception as e:
                resultado_consolidado['centros_con_error'] += 1
                error_msg = f"Error en centro {centro_costo}: {str(e)}"
                logger.error(error_msg)
                resultado_consolidado['errores'].append(error_msg)
                
                resultado_consolidado['resultados_por_centro'][centro_costo] = {
                    'error': str(e)
                }
        
        logger.info(
            f"Sincronización masiva DDH completada - "
            f"Centros procesados: {resultado_consolidado['centros_procesados']}/{resultado_consolidado['total_centros']}, "
            f"Total importados: {resultado_consolidado['total_importados']}, "
            f"Total brocas creadas: {resultado_consolidado['total_brocas_creadas']}, "
            f"Centros con error: {resultado_consolidado['centros_con_error']}"
        )
        
        return resultado_consolidado


# Instancia global del servicio
abastecimiento_service = AbastecimientoService()
