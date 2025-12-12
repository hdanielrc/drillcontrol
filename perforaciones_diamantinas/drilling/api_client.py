"""
Cliente para APIs de Vilbragroup TIC
Maneja la conexión con las APIs de trabajadores y almacén
"""
import requests
from django.conf import settings
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class VilbragroupAPIClient:
    """Cliente para consumir APIs de Vilbragroup TIC"""
    
    BASE_URL = "https://tic.vilbragroup.net/API/DrillControl"
    
    def __init__(self, token: Optional[str] = None, centro_costo: Optional[str] = None):
        """
        Inicializa el cliente de API
        
        Args:
            token: Token de autenticación (si no se provee, se obtiene de settings)
            centro_costo: Centro de costo por defecto (si no se provee, se obtiene de settings)
        """
        self.token = token or getattr(settings, 'VILBRAGROUP_API_TOKEN', '')
        self.centro_costo = centro_costo or getattr(settings, 'CENTRO_COSTO_DEFAULT', '')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DrillControl/1.0',
            'Accept': 'application/json'
        })
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Realiza una petición GET a la API
        
        Args:
            endpoint: Endpoint de la API (ej: 'perforistas')
            params: Parámetros GET
            
        Returns:
            Respuesta JSON o None si hay error
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al conectar con {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a {url}: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"Error al parsear JSON de {url}: {str(e)}")
            return None
    

    def obtener_articulos_almacen(
        self, 
        familia: str, 
        centro_costo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene stock de artículos del almacén según familia
        
        Args:
            familia: Código de familia ('PDD' para productos diamantados, 'ADIT' para aditivos)
            centro_costo: Centro de costo específico (opcional)
            
        Returns:
            Lista de artículos con su stock
            Ejemplo de estructura esperada:
            [
                {
                    'codigo': 'ART001',
                    'descripcion': 'Broca Diamantada 3"',
                    'familia': 'PDD',
                    'stock': 50,
                    'unidad': 'UND',
                    'centro_costo': 'CC001',
                    # ... otros campos según API
                }
            ]
        """
        cc = centro_costo or self.centro_costo
        
        if not self.token:
            logger.error("Token de API no configurado")
            return []
        
        if not cc:
            logger.error("Centro de costo no especificado")
            return []
        
        if familia not in ['PDD', 'ADIT']:
            logger.error(f"Familia inválida: {familia}. Debe ser 'PDD' o 'ADIT'")
            return []
        
        params = {
            'token': self.token,
            'cc': cc,
            'fam': familia
        }
        
        logger.info(f"Obteniendo artículos familia {familia} para centro de costo: {cc}")
        data = self._make_request('articulos', params)
        
        if data is None:
            return []
        
        # La API retorna un diccionario con clave 'articulos'
        if isinstance(data, dict) and 'articulos' in data:
            return data['articulos']
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        elif isinstance(data, list):
            return data
        else:
            logger.warning(f"Formato de respuesta inesperado: {type(data)}. Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
            return []
    
    def obtener_productos_diamantados(self, centro_costo: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Shortcut para obtener productos diamantados (familia PDD)
        
        Args:
            centro_costo: Centro de costo específico (opcional)
            
        Returns:
            Lista de productos diamantados con stock
        """
        return self.obtener_articulos_almacen('PDD', centro_costo)
    
    def obtener_aditivos(self, centro_costo: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Shortcut para obtener aditivos (familia ADIT)
        
        Args:
            centro_costo: Centro de costo específico (opcional)
            
        Returns:
            Lista de aditivos con stock
        """
        return self.obtener_articulos_almacen('ADIT', centro_costo)


# Instancia global del cliente (opcional, para uso simple)
def get_api_client() -> VilbragroupAPIClient:
    """
    Retorna una instancia del cliente API con configuración por defecto
    """
    return VilbragroupAPIClient()
