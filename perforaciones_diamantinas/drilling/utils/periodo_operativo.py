"""
Utilidades globales para Mes Operativo (26-25).

Mes operativo N = desde el 26 del mes N-1 hasta el 25 del mes N.
Ejemplo: Abril 2026 → 26-Mar-2026 a 25-Abr-2026.

TODAS las vistas y servicios del proyecto deben usar estas funciones
para garantizar consistencia.
"""

from datetime import date


def get_rango_mes_operativo(anio, mes):
    """
    Retorna (fecha_inicio, fecha_fin) del mes operativo.

    Args:
        anio: Año del mes operativo (año del día 25/fin).
        mes:  Mes del mes operativo (1-12).

    Returns:
        (date(anio_anterior, mes_anterior, 26), date(anio, mes, 25))

    Ejemplo:
        get_rango_mes_operativo(2026, 4) → (2026-03-26, 2026-04-25)
        get_rango_mes_operativo(2026, 1) → (2025-12-26, 2026-01-25)
    """
    if mes == 1:
        fecha_inicio = date(anio - 1, 12, 26)
    else:
        fecha_inicio = date(anio, mes - 1, 26)
    fecha_fin = date(anio, mes, 25)
    return fecha_inicio, fecha_fin


def mes_operativo_de_fecha(fecha):
    """
    Dado una fecha, devuelve (anio, mes) del mes operativo al que pertenece.

    - Si fecha.day <= 25 → pertenece al mes actual.
    - Si fecha.day >= 26 → pertenece al mes siguiente.

    Ejemplo:
        mes_operativo_de_fecha(date(2026, 3, 26)) → (2026, 4)   # Abril
        mes_operativo_de_fecha(date(2026, 4, 25)) → (2026, 4)   # Abril
        mes_operativo_de_fecha(date(2026, 4, 16)) → (2026, 4)   # Abril
        mes_operativo_de_fecha(date(2025, 12, 26)) → (2026, 1)  # Enero
    """
    if fecha.day >= 26:
        if fecha.month == 12:
            return fecha.year + 1, 1
        return fecha.year, fecha.month + 1
    return fecha.year, fecha.month


def cantidad_dias_mes_operativo(anio, mes):
    """Cantidad de días del mes operativo (siempre entre 28 y 31)."""
    fi, ff = get_rango_mes_operativo(anio, mes)
    return (ff - fi).days + 1
