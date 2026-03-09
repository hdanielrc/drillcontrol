"""
views_tareo_v2.py  — Stub de compatibilidad hacia atrás

Todas las funciones han sido consolidadas en views_tareo.py.
Este módulo re-exporta todo para no romper importaciones existentes.
"""
from .views_tareo import (  # noqa: F401
    AsistenciaDiariaForm,
    tareo_v2_mensual_view,
    api_generar_proyeccion,
    api_corregir_asistencia,
    api_guardar_dia_tareo,
    api_obtener_maquinas,
    tareo_v2_estadisticas,
    tareo_cierre_mensual,
    api_cerrar_mes,
    api_reabrir_mes,
    api_importar_desde_v1,
    tareo_historial_trabajador,
    tareo_reporte_nomina,
    api_exportar_nomina_excel,
)
