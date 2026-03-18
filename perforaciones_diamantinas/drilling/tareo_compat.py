"""
Compatibilidad entre modelos legacy y nuevos modelos de Tareo.

Este módulo exporta los nombres esperados por el código existente
(`AsistenciaDiaria`, `CierreMensualTareo`, `HistorialCambioAsistencia`) y
los enlaza a las nuevas clases definidas en `models_tareo.py` cuando
estén disponibles. Si no, hace fallback a las definiciones en `models.py`.
"""
try:
    from .models_tareo import TareoEntry as AsistenciaDiaria
    from .models_tareo import TareoClosure as CierreMensualTareo
    from .models_tareo import TareoEntryAudit as HistorialCambioAsistencia
    NEW_TAREO = True
except Exception:
    # Si no existen los nuevos modelos, usar los modelos legados
    from .models import AsistenciaDiaria, CierreMensualTareo, HistorialCambioAsistencia  # type: ignore
    NEW_TAREO = False

__all__ = [
    'AsistenciaDiaria',
    'CierreMensualTareo',
    'HistorialCambioAsistencia',
    'NEW_TAREO',
]
