"""
Cliente para APIs de Vilbragroup TIC
Maneja la conexión con las APIs de trabajadores y almacén
"""
import cloudscraper
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
        # Usar cloudscraper en lugar de requests.Session para bypass Cloudflare
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Referer': 'https://tic.vilbragroup.net/',
            'Origin': 'https://tic.vilbragroup.net',
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
        # Log detallado para depuración
        print("[API DEBUG] URL:", url)
        print("[API DEBUG] Headers:", dict(self.session.headers))
        print("[API DEBUG] Params:", params)
        try:
            response = self.session.get(url, params=params, timeout=30)
            print("[API DEBUG] Status Code:", response.status_code)
            print("[API DEBUG] Response Text (primeros 1000 chars):", response.text[:1000])
            
            # Si es 403, mostrar más info antes de fallar
            if response.status_code == 403:
                print("[API DEBUG] ❌ Error 403 Forbidden - Verificar token y centro de costo")
                print("[API DEBUG] Token presente:", 'token' in params and bool(params.get('token')))
                print("[API DEBUG] Centro costo:", params.get('cc', 'NO ENVIADO'))
                print("[API DEBUG] Familia:", params.get('fam', 'NO ENVIADO'))
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Manejar todos los errores (timeout, HTTP errors, etc)
            error_type = type(e).__name__
            logger.error(f"Error {error_type} en petición a {url}: {str(e)}")
            print(f"[API DEBUG] Exception type: {error_type}")
            print(f"[API DEBUG] Exception details: {str(e)}")
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
        
        print(f"[API DEBUG obtener_articulos_almacen] Familia: {familia}")
        print(f"[API DEBUG obtener_articulos_almacen] Centro costo recibido: {centro_costo}")
        print(f"[API DEBUG obtener_articulos_almacen] Centro costo por defecto: {self.centro_costo}")
        print(f"[API DEBUG obtener_articulos_almacen] Centro costo final (cc): {cc}")
        print(f"[API DEBUG obtener_articulos_almacen] Token configurado: {bool(self.token)}")
        
        if not self.token:
            logger.error("Token de API no configurado")
            print("[API DEBUG obtener_articulos_almacen] ❌ ERROR: Token no configurado")
            return []
        
        if not cc:
            logger.error("Centro de costo no especificado")
            print("[API DEBUG obtener_articulos_almacen] ❌ ERROR: Centro de costo no especificado")
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
