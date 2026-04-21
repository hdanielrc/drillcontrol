"""
=============================================================================
ATTENDANCE PROJECTOR — Motor de Proyección de Asistencia Individual
=============================================================================

Genera la proyección de asistencia para un trabajador hasta una fecha
objetivo, respetando:

  1. Ancla del ciclo a partir del último registro real (no proyección).
  2. Variables de turno por contrato (turno_inicio: 'TD' | 'TN').
  3. Continuidad del contrato: trunca en fecha_cese.
  4. Novedades/correcciones manuales: prioridad sobre la proyección.
  5. Fechas cerradas (FechaCerrada por contrato).
  6. Cierre mensual: meses CERRADO no se sobreescriben.
  7. Gestión de fatiga: marca observación en cambios de bloque sin gap
     de al menos 1 día libre entre TD→TN o TN→TD.

Compatibilidad:
  - Regímenes 14x7 con guardias A/B/C → usa TareoEngine (determinista).
  - Otros regímenes → usa TareoService.calcular_estado_dia().

PEP 8 — comentarios en español — sin consultas N+1.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Set

from django.db import transaction

from ..models import AsistenciaDiaria, CierreMensualTareo, FechaCerrada, Trabajador
from .tareo_service import TareoEngine, TareoService

logger = logging.getLogger(__name__)

# Estado sentinel de cese (herencia del epoch Unix en BD)
_SENTINEL_CESE = date(1969, 12, 31)

# Estados que representan correcciones manuales que NO deben sobreescribirse
_ESTADOS_MANUALES_PROTEGIDOS: Set[str] = {
    'V', 'DM', 'LSG', 'LCG', 'LFC', 'LOG', 'SUB',
    'PT', 'PT1', 'S', 'C', 'F',
}


# ---------------------------------------------------------------------------
# DTO de resultado
# ---------------------------------------------------------------------------

@dataclass
class DiaProyectado:
    """Resultado de la proyección para un día específico."""
    fecha: date
    estado: str                            # TD, TN, DL, V, DM, C, …
    es_proyeccion: bool                    # True = automático, False = manual/protegido
    fuente: str                            # 'PROYECCION' | 'MANUAL' | 'CERRADO' | 'FIN_CONTRATO'
    observaciones: str = ''
    trabajador_id: Optional[int] = None


# ---------------------------------------------------------------------------
# AttendanceProjector
# ---------------------------------------------------------------------------

class AttendanceProjector:
    """
    Proyecta la asistencia de un trabajador desde su último registro real
    hasta ``fecha_objetivo``.

    Uso::

        proyector = AttendanceProjector(trabajador_id=42, fecha_objetivo=date(2026, 4, 25))
        dias = proyector.project()   # list[DiaProyectado]
        proyector.save()             # persiste como AsistenciaDiaria(es_proyeccion=True)

    Si no hay historial previo, la proyección parte de
    ``Trabajador.fecha_inicio_labores`` o ``TareoService.HISTORICO_START``.
    """

    def __init__(
        self,
        trabajador_id: int,
        fecha_objetivo: date,
        usuario=None,
    ):
        self.trabajador_id = trabajador_id
        self.fecha_objetivo = fecha_objetivo
        self.usuario = usuario

        # Carga trabajador con contrato para evitar N+1
        self.trabajador: Trabajador = (
            Trabajador.objects
            .select_related('contrato', 'maquina_asignada')
            .get(pk=trabajador_id)
        )
        self.contrato = self.trabajador.contrato

        # Pre-cachés cargados en _prefetch()
        self._asistencias_existentes: Dict[date, AsistenciaDiaria] = {}
        self._fechas_cerradas: Set[date] = set()
        self._meses_cerrados: Set[tuple] = set()   # (anio, mes)

        self._resultado: Optional[List[DiaProyectado]] = None

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def project(self) -> List[DiaProyectado]:
        """Ejecuta la proyección y retorna la lista de días calculados."""
        fecha_inicio = self._determinar_fecha_inicio()
        self._prefetch(fecha_inicio, self.fecha_objetivo)
        self._resultado = self._iterar_rango(fecha_inicio, self.fecha_objetivo)
        return self._resultado

    @transaction.atomic
    def save(self) -> dict:
        """
        Persiste la proyección en ``AsistenciaDiaria``.
        Solo sobreescribe registros con ``es_proyeccion=True``; los manuales
        se respetan completamente.

        Returns:
            dict con claves: creados, actualizados, respetados.
        """
        if self._resultado is None:
            self.project()

        creados = actualizados = respetados = 0

        for dia in self._resultado:
            if dia.fuente in ('MANUAL', 'CERRADO', 'FIN_CONTRATO'):
                respetados += 1
                continue

            defaults = {
                'estado': dia.estado,
                'es_proyeccion': True,
                'guardia_snapshot': getattr(self.trabajador, 'guardia_asignada', None) or '',
                'maquina_snapshot': self.trabajador.maquina_asignada,
                'observaciones': dia.observaciones,
                'registrado_por': self.usuario,
            }

            obj, created = AsistenciaDiaria.objects.update_or_create(
                trabajador=self.trabajador,
                fecha=dia.fecha,
                defaults=defaults,
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        return {'creados': creados, 'actualizados': actualizados, 'respetados': respetados}

    # ------------------------------------------------------------------
    # Capa 1 — Ancla del ciclo
    # ------------------------------------------------------------------

    def _determinar_fecha_inicio(self) -> date:
        """
        Determina desde qué fecha comenzar la proyección.

        Prioridad:
          1. Día siguiente al último registro real (es_proyeccion=False).
          2. fecha_inicio_labores del trabajador.
          3. TareoService.HISTORICO_START.
        """
        ultimo_real = (
            AsistenciaDiaria.objects
            .filter(trabajador=self.trabajador, es_proyeccion=False)
            .order_by('-fecha')
            .values_list('fecha', flat=True)
            .first()
        )

        if ultimo_real:
            # Continuar el ciclo desde el día siguiente al último registro real
            return ultimo_real + timedelta(days=1)

        # Si no hay historial, partir del inicio laboral o del epoch del sistema
        fecha_inicio_labores = getattr(self.trabajador, 'fecha_inicio_labores', None)
        if fecha_inicio_labores and fecha_inicio_labores >= TareoService.HISTORICO_START:
            return fecha_inicio_labores

        return TareoService.HISTORICO_START

    # ------------------------------------------------------------------
    # Capa de prefetch — evita N+1
    # ------------------------------------------------------------------

    def _prefetch(self, fecha_inicio: date, fecha_fin: date) -> None:
        """
        Pre-carga en memoria:
          - Todas las AsistenciaDiaria del rango para este trabajador.
          - Fechas cerradas del contrato en el rango.
          - Meses cerrados del contrato en el rango.
        """
        # Asistencias existentes (manuales y proyecciones anteriores)
        qs = AsistenciaDiaria.objects.filter(
            trabajador=self.trabajador,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        )
        self._asistencias_existentes = {a.fecha: a for a in qs}

        # Fechas cerradas
        if self.contrato:
            fechas_cerradas_qs = FechaCerrada.objects.filter(
                contrato=self.contrato,
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin,
            ).values_list('fecha', flat=True)
            self._fechas_cerradas = set(fechas_cerradas_qs)

            # Meses cerrados: (anio, mes) con estado CERRADO
            meses_cerrados_qs = CierreMensualTareo.objects.filter(
                contrato=self.contrato,
                estado='CERRADO',
            ).values_list('anio', 'mes')
            self._meses_cerrados = {(a, m) for a, m in meses_cerrados_qs}

    # ------------------------------------------------------------------
    # Iteración del rango
    # ------------------------------------------------------------------

    def _iterar_rango(
        self, fecha_inicio: date, fecha_fin: date
    ) -> List[DiaProyectado]:
        """
        Itera cada día entre fecha_inicio y fecha_fin aplicando las capas
        de validación en orden de prioridad.
        """
        resultado: List[DiaProyectado] = []
        estado_anterior: Optional[str] = None   # para validación de fatiga

        fecha = fecha_inicio
        while fecha <= fecha_fin:
            dia = self._resolver_dia(fecha, estado_anterior)
            resultado.append(dia)

            # Actualizar estado_anterior solo si es turno trabajado real
            if dia.estado in ('TD', 'TN'):
                estado_anterior = dia.estado

            # Truncar si el contrato finalizó
            if dia.fuente == 'FIN_CONTRATO':
                break

            fecha += timedelta(days=1)

        return resultado

    def _resolver_dia(self, fecha: date, estado_anterior: Optional[str]) -> DiaProyectado:
        """Determina el estado de un día aplicando todas las capas de validación."""

        # ── Capa: Fin de contrato (cese del trabajador) ──────────────────────
        fecha_cese = getattr(self.trabajador, 'fecha_cese', None)
        if (
            fecha_cese
            and fecha_cese != _SENTINEL_CESE
            and fecha > fecha_cese
        ):
            return DiaProyectado(
                fecha=fecha,
                estado='C',
                es_proyeccion=False,
                fuente='FIN_CONTRATO',
                trabajador_id=self.trabajador_id,
            )

        # ── Capa: Corrección manual existente (prioridad máxima) ─────────────
        existente = self._asistencias_existentes.get(fecha)
        if existente and not existente.es_proyeccion:
            return DiaProyectado(
                fecha=fecha,
                estado=existente.estado,
                es_proyeccion=False,
                fuente='MANUAL',
                observaciones=existente.observaciones or '',
                trabajador_id=self.trabajador_id,
            )

        # ── Capa: Fecha cerrada por el operador ──────────────────────────────
        if fecha in self._fechas_cerradas:
            estado_existente = existente.estado if existente else 'DL'
            return DiaProyectado(
                fecha=fecha,
                estado=estado_existente,
                es_proyeccion=False,
                fuente='CERRADO',
                trabajador_id=self.trabajador_id,
            )

        # ── Capa: Mes cerrado contablemente ──────────────────────────────────
        if (fecha.year, fecha.month) in self._meses_cerrados:
            estado_existente = existente.estado if existente else 'DL'
            return DiaProyectado(
                fecha=fecha,
                estado=estado_existente,
                es_proyeccion=False,
                fuente='CERRADO',
                trabajador_id=self.trabajador_id,
            )

        # ── Capa: Motor de proyección ─────────────────────────────────────────
        estado_raw = self._estado_para_dia(fecha)

        # Mapear DESCANSO → DL
        if estado_raw == 'DESCANSO':
            estado = 'DL'
        else:
            estado = estado_raw or 'DL'

        # ── Capa: Gestión de fatiga ───────────────────────────────────────────
        obs = self._validar_fatiga(estado, estado_anterior, fecha)

        return DiaProyectado(
            fecha=fecha,
            estado=estado,
            es_proyeccion=True,
            fuente='PROYECCION',
            observaciones=obs,
            trabajador_id=self.trabajador_id,
        )

    # ------------------------------------------------------------------
    # Capa 2 — Motor de estados
    # ------------------------------------------------------------------

    def _estado_para_dia(self, fecha: date) -> str:
        """
        Delega al motor adecuado según el régimen del trabajador:
          - 14x7 con guardia A/B/C → TareoEngine (determinista, respeta turno_inicio).
          - Otros regímenes → TareoService.calcular_estado_dia().
        """
        if TareoService._usa_rotacion_guardia(self.trabajador):
            # Motor determinista para guardias rotativas 14x7
            return TareoEngine.estado_para_fecha(self.trabajador, fecha)

        # Motor por ciclo aritmético para otros regímenes
        estado = TareoService.calcular_estado_dia(self.trabajador, fecha)
        return estado or 'DL'

    # ------------------------------------------------------------------
    # Capa 4 — Gestión de fatiga
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_fatiga(
        estado_actual: str,
        estado_anterior: Optional[str],
        fecha: date,
    ) -> str:
        """
        Valida el cambio de bloque entre turno día y turno noche.
        Dado que el modelo no contiene hora de inicio de turno, la
        validación es a nivel de día:
          - El cambio brusco TD→TN o TN→TD sin al menos 1 día libre
            en medio genera una advertencia en observaciones.

        TODO: cuando se agregue ``Contrato.hora_inicio_turno`` y
        ``Contrato.duracion_turno``, reemplazar esta lógica por validación
        horaria exacta (mínimo 11 h de descanso según DS 024-2016-EM).
        """
        if estado_anterior is None:
            return ''

        # Solo aplica cuando ambos días son turnos trabajados distintos
        if estado_actual not in ('TD', 'TN') or estado_anterior not in ('TD', 'TN'):
            return ''

        if estado_actual != estado_anterior:
            # Cambio de bloque directo sin día libre intermedio → advertencia
            return 'REVISAR_FATIGA: cambio de turno sin día libre intermedio'

        return ''


# ---------------------------------------------------------------------------
# Función de conveniencia para proyectar un rango por contrato
# ---------------------------------------------------------------------------

def proyectar_contrato(
    contrato,
    fecha_inicio: date,
    fecha_fin: date,
    usuario=None,
    sobrescribir: bool = False,
) -> dict:
    """
    Genera y persiste proyecciones para todos los trabajadores vigentes
    de un contrato en el rango de fechas dado.

    Args:
        contrato:       instancia de Contrato.
        fecha_inicio:   primera fecha del período.
        fecha_fin:      última fecha del período.
        usuario:        CustomUser que realiza la acción (para auditoría).
        sobrescribir:   si True ignora registros de proyección anteriores.

    Returns:
        dict con claves: trabajadores, creados, actualizados, respetados, errores.
    """
    from ..models import TrabajadorContratoHistorial
    from django.db.models import Q

    # Obtener trabajadores vigentes en el rango usando historial de contrato
    tiene_historial = TrabajadorContratoHistorial.objects.filter(contrato=contrato).exists()

    if tiene_historial:
        historial_q = Q(contrato_historial__contrato=contrato)
        historial_q &= Q(contrato_historial__fecha_inicio__lte=fecha_fin)
        historial_q &= (
            Q(contrato_historial__fecha_fin__isnull=True) |
            Q(contrato_historial__fecha_fin__gte=fecha_inicio)
        )
        trabajadores_qs = (
            Trabajador.objects
            .filter(historial_q)
            .select_related('contrato', 'maquina_asignada')
            .distinct()
        )
    else:
        trabajadores_qs = (
            Trabajador.objects
            .filter(contrato=contrato)
            .select_related('contrato', 'maquina_asignada')
        )

    totales = {'trabajadores_procesados': 0, 'registros_creados': 0, 'registros_actualizados': 0, 'registros_existentes_respetados': 0, 'errores': []}

    for trabajador in trabajadores_qs:
        if not trabajador.vigente_en_fecha(fecha_inicio) and not trabajador.vigente_en_fecha(fecha_fin):
            continue
        try:
            proj = AttendanceProjector(
                trabajador_id=trabajador.pk,
                fecha_objetivo=fecha_fin,
                usuario=usuario,
            )
            # Si sobrescribir=True, repartimos desde fecha_inicio sin tener en
            # cuenta el último registro real
            if sobrescribir:
                proj._determinar_fecha_inicio = lambda fi=fecha_inicio: fi  # type: ignore[method-assign]

            proj.project()
            stats = proj.save()
            totales['trabajadores_procesados'] += 1
            totales['registros_creados'] += stats['creados']
            totales['registros_actualizados'] += stats['actualizados']
            totales['registros_existentes_respetados'] += stats['respetados']
        except Exception as exc:
            logger.exception(
                "AttendanceProjector error para trabajador %s: %s", trabajador.pk, exc
            )
            totales['errores'].append({'trabajador_id': trabajador.pk, 'error': str(exc)})

    return totales



