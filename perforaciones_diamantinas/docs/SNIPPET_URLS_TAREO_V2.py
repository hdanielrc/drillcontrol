"""
=============================================================================
SNIPPET DE CONFIGURACIÓN: URLs para Tareo V2
=============================================================================

Agregar estas rutas al archivo drilling/urls.py
"""

from django.urls import path
from .views_tareo_v2 import (
    tareo_v2_mensual_view,
    api_generar_proyeccion,
    api_corregir_asistencia,
    tareo_v2_estadisticas
)

# URLs del Tareo V2 (agregar a urlpatterns)
urlpatterns = [
    # ... URLs existentes ...
    
    # =========================================================================
    # TAREO V2 - Sistema Normalizado con Proyección Automática
    # =========================================================================
    
    # Vista principal - Matriz tipo Excel
    path('tareo/v2/', tareo_v2_mensual_view, name='tareo_v2_mensual'),
    
    # API para proyección mensual automática (AJAX)
    path(
        'tareo/v2/api/generar-proyeccion/', 
        api_generar_proyeccion, 
        name='api_generar_proyeccion'
    ),
    
    # API para corrección individual de asistencia (AJAX)
    path(
        'tareo/v2/api/corregir/', 
        api_corregir_asistencia, 
        name='api_corregir_asistencia'
    ),
    
    # Dashboard de estadísticas
    path(
        'tareo/v2/estadisticas/', 
        tareo_v2_estadisticas, 
        name='tareo_v2_estadisticas'
    ),
]
