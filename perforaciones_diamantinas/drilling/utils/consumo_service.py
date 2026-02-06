"""
Servicio de sincronización de consumos (salidas) desde API externa
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging

from django.db import transaction
from django.db import models
from django.utils import timezone
from django.db.models import Q

from drilling.api_client import VilbragroupAPIClient
from drilling.models import (
    ConsumoArticulo,
    Contrato,
    HistorialBroca,
    InventarioAlmacen
)

logger = logging.getLogger(__name__)


class ConsumoService:
    """
    Servicio para sincronizar consumos desde API externa
    """
    
    def __init__(self):
        self.api_client = VilbragroupAPIClient()
    

    def _formatear_codigo_almacen(self, codigo: str) -> str:
        """
        Formatea el código de almacén al formato requerido por la API (2 dígitos).
        Ej: '000003' -> '03', '6' -> '06', '000023' -> '23'
        """
        if not codigo:
            return ""
        try:
            # Convertir a entero y formatear a 2 dígitos con ceros a la izquierda
            numero = int(codigo)
            return f"{numero:02d}"
        except ValueError:
            # Si no es numérico, devolver tal cual (fallback)
            logger.warning(f"Código de almacén no numérico encontrado: {codigo}")
            return codigo

    def sincronizar_periodo(
        self,
        fecha_inicio: str,
        fecha_fin: str,
        centro_costo: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Sincroniza consumos de un rango de fechas.
        Args:
            fecha_inicio: String 'DDMMYYYY' (formato requerido por API)
            fecha_fin: String 'DDMMYYYY'
            centro_costo: Código de centro de costo (opcional)
        """
        logger.info(f"Iniciando sincronización consmumos: {fecha_inicio} - {fecha_fin}")
        
        resultado = {
            'total_api': 0,
            'importados': 0,
            'actualizados': 0,
            'errores': 0,
            'detalles_errores': []
        }

        # 1. Determinar lista de Centros de Costo (Usando codigo_almacen si existe, o fallback a lógica antigua)
        # centros_map: codigo_almacen_para_api -> Objeto Contrato
        centros_map = {} 
        
        if centro_costo:
            # Buscar contrato por codigo_centro_costo (entrada del usuario)
            contratos = Contrato.objects.filter(codigo_centro_costo=centro_costo)
            
            if contratos.exists():
                contrato = contratos.first()
                # Usar el nuevo campo codigo_almacen para la API
                codigo_api = contrato.codigo_almacen
                if codigo_api:
                    centros_map[codigo_api] = contrato
                else:
                    logger.warning(f"Contrato {contrato.nombre_contrato} no tiene codigo_almacen configurado.")
            else:
                logger.warning(f"No se encontró contrato para CC {centro_costo}")

        else:
            # Todos los activos con codigo_almacen configurado
            contratos = Contrato.objects.filter(
                estado='ACTIVO'
            ).exclude(codigo_almacen__isnull=True).exclude(codigo_almacen='')
            
            for c in contratos:
                centros_map[c.codigo_almacen] = c

        if not centros_map:
            logger.warning("No hay contratos con codigo_almacen configurado para sincronizar")
            return resultado

        # 2. Iterar
        for codigo_api, contrato_obj in centros_map.items():
            try:
                # Formatear el código (API requiere 2 dígitos: '01', '03', '24'...)
                codigo_formatted = self._formatear_codigo_almacen(codigo_api)
                
                logger.info(f"Sincronizando {contrato_obj.nombre_contrato} (CC:{contrato_obj.codigo_centro_costo}) -> API Almacen:{codigo_formatted}")
                
                consumos = self.api_client.obtener_consumos(
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    codigo_almacen=codigo_formatted
                )
                
                if not consumos:
                    logger.info(f"Sin consumos para Almacen {codigo_formatted}")
                    continue
                    
                resultado['total_api'] += len(consumos)
                
                with transaction.atomic():
                    for item in consumos:
                        try:
                            # Pasamos codigo_api (almacen) pero el contrato ya está resuelto
                            self._procesar_item_consumo(item, codigo_api, contrato_obj, resultado)
                        except Exception as e:
                            msg = f"Error pesistiendo item {item.get('codigo')} en Almacen {codigo_api}: {str(e)}"
                            logger.error(msg)
                            resultado['errores'] += 1
                            resultado['detalles_errores'].append(msg)
                            
            except Exception as e:
                logger.error(f"Error procesando lote de CC {cc_codigo}: {str(e)}")
                resultado['errores'] += 1

        return resultado

    def _procesar_item_consumo(self, item: dict, cc_codigo: str, contrato: Contrato, resultado: dict):
        """
        Procesa un item individual de la API y lo guarda en BD
        """
        # Parsear fecha: API devuelve YYYY-MM-DD (aunque documentación decía DD/MM/YYYY)
        fecha_str = item.get('fecha')
        fecha_date = None
        
        # Intentar varios formatos por robustez
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                if fecha_str:
                    fecha_date = datetime.strptime(fecha_str, fmt).date()
                    break
            except ValueError:
                continue
        
        if not fecha_date:
            logger.warning(f"Fecha inválida o vacía: {fecha_str}")
            return

        # Mapeo de campos
        # Clave única lógica: Contrato + Vale + Codigo + Serie (si existe)
        # Ojo: Un vale puede tener el mismo item 2 veces? Sí, pero raro.
        # Mejora: Usar todos los campos determinantes para update_or_create
        
        defaults = {
            'fecha': fecha_date,
            'contrato': contrato, # Usamos el contrato LOCAL mapeado por codigo_centro_costo
            'centro_costo': cc_codigo,
            'documento_referencia': item.get('guia', ''),
            'descripcion': item.get('articulo', ''),
            'serie': item.get('serie') or '',
            'codigo_movimiento': item.get('tipo', 'SALIDA'), # Usamos 'tipo' como cod movimiento
            'cantidad': Decimal(str(item.get('cantidad', 0))),
            'unidad': item.get('unidad', 'UND'),
            'familia': item.get('familia', 'GENERAL'),
            # Precio/Costo no están en el modelo ConsumoArticulo actual según recuerdo, 
            # pero si estuvieran se añadirían aquí.
        }
        
        # Identificadores para búsqueda
        criterios = {
            'documento': item.get('vale'),
            'codigo': item.get('codigo'),
            'centro_costo': cc_codigo,
            'fecha': fecha_date
        }
        
        # Si tiene serie, la incluimos en criterios para diferenciar
        serie_val = item.get('serie')
        if serie_val:
            criterios['serie'] = serie_val
        
        obj, created = ConsumoArticulo.objects.update_or_create(
            **criterios,
            defaults=defaults
        )
        
        if created:
            resultado['importados'] += 1
            # Si es una broca (tiene serie), intentar vincular con HistorialBroca
            # Esto dispara la señal o lógica de actualización de stock
        else:
            resultado['actualizados'] += 1
            
        # IMPORTANTE: 
        # El modelo ConsumoArticulo debe actualizar InventarioAlmacen al gardarse.
        # Si no lo hace automáticamente en save(), hay que llamarlo aquí.
        # Según el análisis previo, agregué lógica en `save()` o `_actualizar_stock`.
        # Si se usa update_or_create, save() es llamado.

consumo_service = ConsumoService()
