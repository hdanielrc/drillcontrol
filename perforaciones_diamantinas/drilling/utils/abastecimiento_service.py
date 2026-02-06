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
        Sincroniza todos los abastecimientos de un periodo desde la API.
        Si no se especifica centro_costo, itera sobre todos los contratos activos.
        
        Args:
            periodo: Periodo en formato YYYYMM (ej: '202601')
            centro_costo: Centro de costo específico (opcional)
            solo_familia: Filtrar solo por familia específica (ej: 'PDD', 'ADIT')
        
        Returns:
            Diccionario con resultados consolidados
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
        
        # 1. Determinar lista de Centros de Costo a procesar
        centros_costo_list = []
        if centro_costo:
            centros_costo_list.append(centro_costo)
        else:
            # Obtener todos los CC de contratos activos
            contratos = Contrato.objects.filter(
                estado='ACTIVO'
            ).exclude(codigo_centro_costo__isnull=True).exclude(codigo_centro_costo='')
            
            # Usar set para evitar duplicados
            centros_costo_list = list(set(c.codigo_centro_costo for c in contratos))
            logger.info(f"Modo multi-contrato: Se procesarán {len(centros_costo_list)} centros de costo: {centros_costo_list}")
            
            if not centros_costo_list:
                logger.warning("No se encontraron contratos activos con código de centro de costo.")
                resultado['detalles_errores'].append("No hay contratos activos con centro de costo configurado.")
                return resultado

        # 2. Iterar sobre cada Centro de Costo
        for cc_actual in centros_costo_list:
            try:
                logger.info(f"Procesando centro de costo: {cc_actual}")
                
                # Obtener datos de la API para este CC
                abastecimientos = self.api_client.obtener_articulos_abastecidos(
                    periodo=periodo,
                    centro_costo=cc_actual
                )
                
                if not abastecimientos:
                    logger.warning(f"No se obtuvieron datos para CC {cc_actual}")
                    continue
                
                logger.info(f"Obtenidos {len(abastecimientos)} registros para CC {cc_actual}")
                
                # Filtrar por familia si se especificó
                if solo_familia:
                    abastecimientos = [
                        a for a in abastecimientos 
                        if a.get('familia') == solo_familia
                    ]
                
                # Acumular total encontrado
                resultado['total_api'] += len(abastecimientos)
                
                # Procesar registros
                for item in abastecimientos:
                    try:
                        # Asegurar que el CC del item coincida con el solicitado (por seguridad)
                        if 'centro_costo' not in item or not item['centro_costo']:
                            item['centro_costo'] = cc_actual
                            
                        created, broca_creada = self._procesar_abastecimiento(item)
                        
                        if created:
                            resultado['importados'] += 1
                        else:
                            resultado['actualizados'] += 1
                        
                        if broca_creada:
                            resultado['brocas_creadas'] += 1
                            
                    except Exception as e:
                        resultado['errores'] += 1
                        error_msg = f"Error en CC {cc_actual} item {item.get('codigo', '?')}: {str(e)}"
                        # Solo guardar los primeros 50 errores para no saturar
                        if len(resultado['detalles_errores']) < 50:
                            resultado['detalles_errores'].append(error_msg)
                            
            except Exception as e_cc:
                # Error a nivel de centro de costo (ej: error 500 en API para ese CC)
                msg = f"Error procesando lote de CC {cc_actual}: {str(e_cc)}"
                logger.error(msg)
                resultado['detalles_errores'].append(msg)
                resultado['errores'] += 1

        logger.info(
            f"Sincronización FINALIZADA - "
            f"Total API: {resultado['total_api']}, "
            f"Importados: {resultado['importados']}, "
            f"Errores: {resultado['errores']}"
        )
        
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
            'descripcion', 'cantidad', 'unidad', 'familia'
        ]
        
        for campo in campos_requeridos:
            if campo not in data:
                # Intento de recuperación si falta familia pero hay descripción
                if campo == 'familia':
                    data['familia'] = 'OTROS' # Valor por defecto
                    logger.warning(f"Campo familia faltante en {data.get('codigo')}, asignado OTROS")
                else:
                    raise ValueError(f"Campo requerido faltante: {campo}")
        
        # Limpiar datos
        data['familia'] = str(data['familia']).strip() if data.get('familia') else 'OTROS'
        
        # Parsear fecha
        fecha = self._parsear_fecha(data['fecha'])
        
        # Obtener o buscar contrato por centro de costo
        contrato = self._obtener_contrato(data['centro_costo'])
        if not contrato:
            raise ValueError(f"Contrato no encontrado para centro de costo: {data['centro_costo']}")
        
        # Buscar si ya existe el registro
        serie = data.get('serie')
        if serie:
            serie = str(serie).strip()
        
        # Manejo seguro acumuladores numéricos
        def clean_decimal(val):
            try:
                if val is None or val == '':
                    return Decimal('0')
                return Decimal(str(val))
            except:
                return Decimal('0')

        abastecimiento, created = AbastecimientoArticulo.objects.update_or_create(
            documento=str(data['documento']).strip(),
            codigo=str(data['codigo']).strip(),
            serie=serie if serie else '',  # Para unique_together
            defaults={
                'fecha': fecha,
                'centro_costo': data['centro_costo'],
                'contrato': contrato,
                'documento_referencia': data.get('documento_referencia', ''),
                'descripcion': data.get('descripcion', 'Sin descripción'),
                'codigo_movimiento': data.get('codigo_movimiento', ''),
                'cantidad': clean_decimal(data.get('cantidad')),
                'unidad': data.get('unidad', 'UND'),
                'familia': data['familia'],
                'precio_unitario': clean_decimal(data.get('precio_unitario')),
                'precio_total': clean_decimal(data.get('precio_total')),
            }
        )
        
        # Verificar si se creó una broca nueva (o si existe pero no tiene broca asociada)
        broca_creada = False
        
        # LOGICA CRÍTICA: Asegurar creación de HistorialBroca para PDD
        if data['familia'] == 'PDD' and serie:
            # Forzar sincronización si no tiene historial
            if not abastecimiento.historial_broca:
                abastecimiento._sincronizar_historial_broca()
                if abastecimiento.historial_broca:
                    broca_creada = True
                    # abast.save() no es necesario porque _sincronizar guarda
            elif created:
                # Si se acaba de crear, contamos como creada
                broca_creada = True
                
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
        1. Buscar por codigo_centro_costo exacto
        2. Buscar por centro_costo en nombre_contrato
        3. Buscar contrato activo por defecto
        """
        try:
            # 1. Buscar por codigo_centro_costo exacto
            contrato = Contrato.objects.filter(codigo_centro_costo=centro_costo).first()
            if contrato:
                return contrato
            
            # 2. Buscar en nombre o código
            contrato = Contrato.objects.filter(
                nombre_contrato__icontains=centro_costo
            ).first()
            
            if contrato:
                return contrato
            
            # 3. Último recurso: obtener primer contrato activo
            logger.warning(f"No se encontró contrato para centro_costo {centro_costo}, usando primer contrato activo")
            # El modelo Contrato usa estado='ACTIVO' no un booleano
            return Contrato.objects.filter(estado='ACTIVO').first()
            
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
