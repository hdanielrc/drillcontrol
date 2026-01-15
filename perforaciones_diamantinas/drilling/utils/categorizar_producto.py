"""
Utilidad para categorizar productos automáticamente basándose en su nombre
"""


def categorizar_producto_por_nombre(nombre: str) -> str:
    """
    Determina la categoría de un producto basándose en palabras clave en su nombre.
    
    Args:
        nombre: Nombre del producto
        
    Returns:
        Categoría del producto: 'BROCA', 'REAMING_SHELL', 'ZAPATA', 'CORE_LIFTER'
    """
    nombre_upper = nombre.upper()
    
    # Reglas de categorización (orden importa)
    
    # 1. Reaming Shells y Escariadores
    if any(kw in nombre_upper for kw in ['REAMER', 'REAMING', 'ESCARIADOR']):
        return 'REAMING_SHELL'
    
    # 2. Zapatas
    if any(kw in nombre_upper for kw in ['ZAPATA', 'SHOE']):
        return 'ZAPATA'
    
    # 3. Core Lifters
    if any(kw in nombre_upper for kw in ['CORE LIFTER', 'LIFTER']):
        return 'CORE_LIFTER'
    
    # 4. Brocas (por defecto si tiene palabras relacionadas)
    if any(kw in nombre_upper for kw in ['DRILL BIT', 'BIT', 'BROCA', 'IMPREGNATED', 'SURFACE SET']):
        return 'BROCA'
    
    # Por defecto, asumimos que es una broca
    return 'BROCA'
