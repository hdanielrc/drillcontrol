"""
Servicio de Stock - Gestión de Snapshots y Alertas

Este módulo centraliza toda la lógica de negocio relacionada con:
- Sincronización de stock desde API Vilbragroup
- Creación de snapshots históricos
- Generación automática de alertas
- Cálculo de proyecciones y tendencias

Autor: DrillControl
Fecha: Diciembre 2024
"""

import logging
from decimal import Decimal
from datetime import timedelta
from typing import List, Dict, Any, Optional, Tuple

from django.db import transaction
from django.db.models import Sum, Avg, F, Count
from django.utils import timezone

from drilling.models import (
    Contrato, StockSnapshot, AlertaStock, ConfiguracionAlertaStock,
    ConsumoStock, TurnoAditivo
)
from drilling.api_client import get_api_client

logger = logging.getLogger(__name__)


class StockService:
    """
    Servicio principal para gestión de stock.
    Maneja sincronización, snapshots y alertas.
    """
    
    def __init__(self, contrato: Contrato):
        """
        Inicializa el servicio para un contrato específico.
        
        Args:
            contrato: Instancia del modelo Contrato
        """
        self.contrato = contrato
        self.api_client = get_api_client()
        self.config = ConfiguracionAlertaStock.get_o_crear(contrato)
        self.fecha_sync = timezone.now()
    
    # =========================================================================
    # SINCRONIZACIÓN Y SNAPSHOTS
    # =========================================================================
    
    def sincronizar_stock_completo(self) -> Dict[str, Any]:
        """
        Sincroniza todo el stock (PDD y ADIT) y genera alertas.
        
        Returns:
            Dict con resultados de la sincronización
        """
        resultado = {
            'contrato': self.contrato.nombre_contrato,
            'fecha_sync': self.fecha_sync,
            'pdd': {'count': 0, 'success': False, 'error': None},
            'adit': {'count': 0, 'success': False, 'error': None},
            'alertas_generadas': 0,
            'success': False
        }
        
        # Sincronizar PDD
        try:
            pdd_data = self.api_client.obtener_productos_diamantados(
                centro_costo=self.contrato.codigo_centro_costo
            )
            if pdd_data:
                snapshots_pdd = self._crear_snapshots(pdd_data, 'PDD')
                resultado['pdd']['count'] = len(snapshots_pdd)
                resultado['pdd']['success'] = True
                logger.info(f"✅ {self.contrato.nombre_contrato}: {len(snapshots_pdd)} PDD sincronizados")
        except Exception as e:
            resultado['pdd']['error'] = str(e)
            logger.error(f"❌ Error sincronizando PDD para {self.contrato.nombre_contrato}: {e}")
        
        # Sincronizar ADIT
        try:
            adit_data = self.api_client.obtener_aditivos(
                centro_costo=self.contrato.codigo_centro_costo
            )
            if adit_data:
                snapshots_adit = self._crear_snapshots(adit_data, 'ADIT')
                resultado['adit']['count'] = len(snapshots_adit)
                resultado['adit']['success'] = True
                logger.info(f"✅ {self.contrato.nombre_contrato}: {len(snapshots_adit)} ADIT sincronizados")
        except Exception as e:
            resultado['adit']['error'] = str(e)
            logger.error(f"❌ Error sincronizando ADIT para {self.contrato.nombre_contrato}: {e}")
        
        # Generar alertas
        try:
            alertas = self.generar_alertas()
            resultado['alertas_generadas'] = len(alertas)
        except Exception as e:
            logger.error(f"❌ Error generando alertas para {self.contrato.nombre_contrato}: {e}")
        
        resultado['success'] = resultado['pdd']['success'] or resultado['adit']['success']
        return resultado
    
    @transaction.atomic
    def _crear_snapshots(self, datos_api: List[Dict], familia: str) -> List[StockSnapshot]:
        """
        Crea snapshots a partir de datos de la API.
        
        Args:
            datos_api: Lista de artículos desde la API
            familia: 'PDD' o 'ADIT'
            
        Returns:
            Lista de StockSnapshot creados
        """
        snapshots = []
        
        for item in datos_api:
            try:
                snapshot = StockSnapshot(
                    contrato=self.contrato,
                    fecha_sync=self.fecha_sync,
                    familia=familia,
                    codigo_articulo=item.get('codigo', item.get('Codigo', '')),
                    descripcion=item.get('descripcion', item.get('Descripcion', 'Sin descripción')),
                    stock_cantidad=Decimal(str(item.get('stock', item.get('Stock', 0)))),
                    unidad_medida=item.get('unidad', item.get('Unidad', 'UND')),
                    lote=item.get('lote', item.get('Lote')),
                    ubicacion=item.get('ubicacion', item.get('Ubicacion')),
                    precio_unitario=self._parse_decimal(item.get('precio', item.get('Precio')))
                )
                snapshots.append(snapshot)
            except Exception as e:
                logger.warning(f"Error procesando artículo {item}: {e}")
                continue
        
        # Bulk create para mejor performance
        if snapshots:
            StockSnapshot.objects.bulk_create(snapshots)
        
        return snapshots
    
    def _parse_decimal(self, valor) -> Optional[Decimal]:
        """Convierte un valor a Decimal de forma segura"""
        if valor is None:
            return None
        try:
            return Decimal(str(valor))
        except:
            return None
    
    # =========================================================================
    # CÁLCULO DE CONSUMOS Y PROYECCIONES
    # =========================================================================
    
    def calcular_consumo_diario(self, codigo_articulo: str, dias: int = 30) -> Decimal:
        """
        Calcula el consumo diario promedio de un artículo.
        Analiza los consumos registrados en turnos.
        
        Args:
            codigo_articulo: Código del artículo
            dias: Días hacia atrás para calcular promedio
            
        Returns:
            Consumo diario promedio
        """
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
        # Buscar consumos en ConsumoStock (para PDD)
        consumo_stock = ConsumoStock.objects.filter(
            turno__contrato=self.contrato,
            turno__fecha__gte=fecha_inicio,
            abastecimiento__codigo_producto=codigo_articulo
        ).aggregate(total=Sum('cantidad_consumida'))
        
        total_consumo = consumo_stock.get('total') or Decimal('0')
        
        # Si no hay consumos en ConsumoStock, buscar en TurnoAditivo (para ADIT)
        if total_consumo == 0:
            consumo_aditivo = TurnoAditivo.objects.filter(
                turno__contrato=self.contrato,
                turno__fecha__gte=fecha_inicio,
                tipo_aditivo__codigo=codigo_articulo
            ).aggregate(total=Sum('cantidad_usada'))
            total_consumo = consumo_aditivo.get('total') or Decimal('0')
        
        # Calcular promedio diario
        if total_consumo > 0:
            return total_consumo / Decimal(str(dias))
        
        return Decimal('0')
    
    def calcular_dias_restantes(self, stock_actual: Decimal, consumo_diario: Decimal) -> Optional[Decimal]:
        """
        Calcula cuántos días durará el stock actual.
        
        Args:
            stock_actual: Cantidad actual en stock
            consumo_diario: Consumo diario promedio
            
        Returns:
            Días restantes o None si no hay consumo
        """
        if consumo_diario <= 0:
            return None  # Sin consumo histórico, no se puede calcular
        
        return stock_actual / consumo_diario
    
    def obtener_proyeccion_stock(self, dias_proyeccion: int = 30) -> List[Dict]:
        """
        Genera proyección de stock para todos los artículos del contrato.
        
        Args:
            dias_proyeccion: Días a futuro para proyectar
            
        Returns:
            Lista de artículos con su proyección
        """
        stock_actual = StockSnapshot.get_stock_actual(self.contrato)
        proyecciones = []
        
        for item in stock_actual:
            consumo_diario = self.calcular_consumo_diario(item.codigo_articulo)
            dias_restantes = self.calcular_dias_restantes(item.stock_cantidad, consumo_diario)
            
            proyeccion = {
                'codigo': item.codigo_articulo,
                'descripcion': item.descripcion,
                'familia': item.familia,
                'stock_actual': item.stock_cantidad,
                'unidad': item.unidad_medida,
                'consumo_diario': consumo_diario,
                'dias_restantes': dias_restantes,
                'fecha_agotamiento': None,
                'estado': 'OK'
            }
            
            # Calcular fecha de agotamiento
            if dias_restantes is not None:
                proyeccion['fecha_agotamiento'] = timezone.now() + timedelta(days=float(dias_restantes))
                
                # Determinar estado
                if dias_restantes <= self.config.dias_stock_critico:
                    proyeccion['estado'] = 'CRITICO'
                elif dias_restantes <= self.config.dias_stock_bajo:
                    proyeccion['estado'] = 'BAJO'
                elif dias_restantes <= self.config.dias_stock_alerta:
                    proyeccion['estado'] = 'ALERTA'
            
            # Si stock es 0
            if item.stock_cantidad <= 0:
                proyeccion['estado'] = 'AGOTADO'
            
            proyecciones.append(proyeccion)
        
        # Ordenar por días restantes (más urgentes primero)
        proyecciones.sort(key=lambda x: x['dias_restantes'] if x['dias_restantes'] is not None else float('inf'))
        
        return proyecciones
    
    # =========================================================================
    # GENERACIÓN DE ALERTAS
    # =========================================================================
    
    def generar_alertas(self) -> List[AlertaStock]:
        """
        Genera alertas automáticas basadas en el stock actual.
        
        Returns:
            Lista de alertas generadas
        """
        alertas_creadas = []
        stock_actual = StockSnapshot.get_stock_actual(self.contrato)
        
        for item in stock_actual:
            # 1. Verificar si está agotado
            if self.config.alertar_agotado and item.stock_cantidad <= 0:
                alerta = self._crear_alerta_agotado(item)
                if alerta:
                    alertas_creadas.append(alerta)
                continue
            
            # 2. Calcular consumo y días restantes
            consumo_diario = self.calcular_consumo_diario(item.codigo_articulo)
            dias_restantes = self.calcular_dias_restantes(item.stock_cantidad, consumo_diario)
            
            # 3. Verificar stock crítico/bajo
            if self.config.alertar_stock_bajo and dias_restantes is not None:
                if dias_restantes <= self.config.dias_stock_critico:
                    alerta = self._crear_alerta_stock_critico(item, consumo_diario, dias_restantes)
                    if alerta:
                        alertas_creadas.append(alerta)
                elif dias_restantes <= self.config.dias_stock_bajo:
                    alerta = self._crear_alerta_stock_bajo(item, consumo_diario, dias_restantes)
                    if alerta:
                        alertas_creadas.append(alerta)
            
            # 4. Verificar sin rotación
            if self.config.alertar_sin_rotacion and consumo_diario == 0:
                alerta = self._crear_alerta_sin_rotacion(item)
                if alerta:
                    alertas_creadas.append(alerta)
        
        logger.info(f"📢 {self.contrato.nombre_contrato}: {len(alertas_creadas)} alertas generadas")
        return alertas_creadas
    
    def _crear_alerta_agotado(self, item: StockSnapshot) -> Optional[AlertaStock]:
        """Crea alerta de artículo agotado"""
        return AlertaStock.crear_alerta(
            contrato=self.contrato,
            codigo_articulo=item.codigo_articulo,
            descripcion=item.descripcion,
            familia=item.familia,
            tipo_alerta='AGOTADO',
            prioridad=1,  # Crítica
            mensaje=f"⚠️ AGOTADO: {item.descripcion} ({item.codigo_articulo}) no tiene stock disponible.",
            stock_actual=item.stock_cantidad,
            umbral=Decimal('0')
        )
    
    def _crear_alerta_stock_critico(
        self, 
        item: StockSnapshot, 
        consumo_diario: Decimal, 
        dias_restantes: Decimal
    ) -> Optional[AlertaStock]:
        """Crea alerta de stock crítico"""
        return AlertaStock.crear_alerta(
            contrato=self.contrato,
            codigo_articulo=item.codigo_articulo,
            descripcion=item.descripcion,
            familia=item.familia,
            tipo_alerta='STOCK_CRITICO',
            prioridad=1,  # Crítica
            mensaje=(
                f"🚨 STOCK CRÍTICO: {item.descripcion} tiene solo {dias_restantes:.0f} días de stock. "
                f"Stock actual: {item.stock_cantidad} {item.unidad_medida}. "
                f"Consumo diario: {consumo_diario:.2f}. "
                f"Se requiere reposición URGENTE."
            ),
            stock_actual=item.stock_cantidad,
            consumo_diario=consumo_diario,
            dias_restante=dias_restantes,
            umbral=Decimal(str(self.config.dias_stock_critico))
        )
    
    def _crear_alerta_stock_bajo(
        self, 
        item: StockSnapshot, 
        consumo_diario: Decimal, 
        dias_restantes: Decimal
    ) -> Optional[AlertaStock]:
        """Crea alerta de stock bajo"""
        return AlertaStock.crear_alerta(
            contrato=self.contrato,
            codigo_articulo=item.codigo_articulo,
            descripcion=item.descripcion,
            familia=item.familia,
            tipo_alerta='STOCK_BAJO',
            prioridad=2,  # Alta
            mensaje=(
                f"⚡ STOCK BAJO: {item.descripcion} tiene {dias_restantes:.0f} días de stock restante. "
                f"Stock actual: {item.stock_cantidad} {item.unidad_medida}. "
                f"Planificar reposición."
            ),
            stock_actual=item.stock_cantidad,
            consumo_diario=consumo_diario,
            dias_restante=dias_restantes,
            umbral=Decimal(str(self.config.dias_stock_bajo))
        )
    
    def _crear_alerta_sin_rotacion(self, item: StockSnapshot) -> Optional[AlertaStock]:
        """Crea alerta de artículo sin rotación"""
        return AlertaStock.crear_alerta(
            contrato=self.contrato,
            codigo_articulo=item.codigo_articulo,
            descripcion=item.descripcion,
            familia=item.familia,
            tipo_alerta='SIN_ROTACION',
            prioridad=4,  # Baja
            mensaje=(
                f"📦 SIN ROTACIÓN: {item.descripcion} no ha tenido movimiento en los últimos "
                f"{self.config.dias_sin_rotacion} días. Stock: {item.stock_cantidad} {item.unidad_medida}. "
                f"Verificar si es necesario."
            ),
            stock_actual=item.stock_cantidad,
            umbral=Decimal(str(self.config.dias_sin_rotacion))
        )
    
    # =========================================================================
    # MÉTODOS DE ANÁLISIS
    # =========================================================================
    
    def obtener_resumen_stock(self) -> Dict[str, Any]:
        """
        Obtiene un resumen ejecutivo del estado del stock.
        
        Returns:
            Dict con métricas clave
        """
        stock_actual = StockSnapshot.get_stock_actual(self.contrato)
        alertas_activas = AlertaStock.get_alertas_activas(contrato=self.contrato)
        
        # Contar por familia
        pdd_count = stock_actual.filter(familia='PDD').count()
        adit_count = stock_actual.filter(familia='ADIT').count()
        
        # Contar por estado de alerta
        proyecciones = self.obtener_proyeccion_stock()
        estados = {'AGOTADO': 0, 'CRITICO': 0, 'BAJO': 0, 'ALERTA': 0, 'OK': 0}
        for p in proyecciones:
            estados[p['estado']] = estados.get(p['estado'], 0) + 1
        
        # Valor total del inventario
        valor_total = stock_actual.aggregate(
            total=Sum(F('stock_cantidad') * F('precio_unitario'))
        )['total'] or Decimal('0')
        
        return {
            'contrato': self.contrato.nombre_contrato,
            'fecha_ultimo_sync': stock_actual.first().fecha_sync if stock_actual.exists() else None,
            'total_articulos': stock_actual.count(),
            'pdd_count': pdd_count,
            'adit_count': adit_count,
            'valor_inventario': valor_total,
            'alertas_activas': alertas_activas.count(),
            'alertas_criticas': alertas_activas.filter(prioridad=1).count(),
            'articulos_agotados': estados['AGOTADO'],
            'articulos_criticos': estados['CRITICO'],
            'articulos_stock_bajo': estados['BAJO'],
            'articulos_ok': estados['OK'],
        }
    
    def obtener_tendencia_articulo(self, codigo_articulo: str, dias: int = 30) -> List[Dict]:
        """
        Obtiene la tendencia histórica de un artículo específico.
        Útil para gráficas.
        
        Args:
            codigo_articulo: Código del artículo
            dias: Días de histórico
            
        Returns:
            Lista de puntos de datos para la gráfica
        """
        historial = StockSnapshot.get_historial_articulo(
            self.contrato, codigo_articulo, dias
        )
        
        return [
            {
                'fecha': item.fecha_sync.isoformat(),
                'stock': float(item.stock_cantidad),
                'valor': float(item.valor_total) if item.valor_total else None
            }
            for item in historial
        ]


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def sincronizar_todos_los_contratos(verbose: bool = False) -> Dict[str, Any]:
    """
    Sincroniza stock de todos los contratos activos.
    
    Args:
        verbose: Si True, imprime progreso
        
    Returns:
        Resumen de la sincronización
    """
    from drilling.models import Contrato
    
    contratos = Contrato.objects.filter(
        estado='ACTIVO',
        codigo_centro_costo__isnull=False
    ).exclude(codigo_centro_costo='')
    
    resultados = {
        'fecha_inicio': timezone.now(),
        'contratos_procesados': 0,
        'contratos_exitosos': 0,
        'contratos_fallidos': 0,
        'total_pdd': 0,
        'total_adit': 0,
        'total_alertas': 0,
        'detalles': []
    }
    
    for contrato in contratos:
        if verbose:
            print(f"\n📡 Sincronizando: {contrato.nombre_contrato}")
        
        try:
            service = StockService(contrato)
            resultado = service.sincronizar_stock_completo()
            
            resultados['contratos_procesados'] += 1
            if resultado['success']:
                resultados['contratos_exitosos'] += 1
            else:
                resultados['contratos_fallidos'] += 1
            
            resultados['total_pdd'] += resultado['pdd']['count']
            resultados['total_adit'] += resultado['adit']['count']
            resultados['total_alertas'] += resultado['alertas_generadas']
            resultados['detalles'].append(resultado)
            
            if verbose:
                print(f"   ✅ PDD: {resultado['pdd']['count']}, ADIT: {resultado['adit']['count']}")
                print(f"   📢 Alertas: {resultado['alertas_generadas']}")
                
        except Exception as e:
            resultados['contratos_procesados'] += 1
            resultados['contratos_fallidos'] += 1
            logger.error(f"Error sincronizando {contrato.nombre_contrato}: {e}")
            if verbose:
                print(f"   ❌ Error: {e}")
    
    resultados['fecha_fin'] = timezone.now()
    resultados['duracion_segundos'] = (
        resultados['fecha_fin'] - resultados['fecha_inicio']
    ).total_seconds()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ Sincronización completada en {resultados['duracion_segundos']:.1f}s")
        print(f"   Contratos: {resultados['contratos_exitosos']}/{resultados['contratos_procesados']} exitosos")
        print(f"   Artículos: {resultados['total_pdd']} PDD + {resultados['total_adit']} ADIT")
        print(f"   Alertas generadas: {resultados['total_alertas']}")
    
    return resultados
