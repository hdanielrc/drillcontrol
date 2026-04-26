-- vw_produccion_maquina_mes.sql
-- Producción real vs meta programada por máquina y período operativo (26-25).
--
-- Período operativo:
--   Si fecha.day >= 26 → pertenece al mes siguiente (anio/mes ajustados).
--   Si fecha.day <= 25 → pertenece al mes actual.
--
-- Metros acumulados: suma de turno_avance.metros_perforados
--   para turnos en estado COMPLETADO o APROBADO.
--
-- Meta maquina: programacion_mes.meta_metros
--   (valor base mensual por máquina; los overrides diarios de MetaTurno
--    requieren el motor Python en conceptos_globales_engine.py para
--    calcular el PROG.FINAL exacto).

CREATE OR REPLACE VIEW public.vw_produccion_maquina_mes AS
WITH turnos_metros AS (
    SELECT
        t.maquina_id,
        -- Calcular año y mes operativo a partir de la fecha del turno
        CASE
            WHEN EXTRACT(DAY FROM t.fecha) >= 26
                 AND EXTRACT(MONTH FROM t.fecha) = 12
                THEN EXTRACT(YEAR FROM t.fecha)::int + 1
            WHEN EXTRACT(DAY FROM t.fecha) >= 26
                THEN EXTRACT(YEAR FROM t.fecha)::int
            ELSE EXTRACT(YEAR FROM t.fecha)::int
        END AS anio_op,
        CASE
            WHEN EXTRACT(DAY FROM t.fecha) >= 26
                 AND EXTRACT(MONTH FROM t.fecha) = 12
                THEN 1
            WHEN EXTRACT(DAY FROM t.fecha) >= 26
                THEN EXTRACT(MONTH FROM t.fecha)::int + 1
            ELSE EXTRACT(MONTH FROM t.fecha)::int
        END AS mes_op,
        COALESCE(ta.metros_perforados, 0) AS metros
    FROM public.turnos t
    LEFT JOIN public.turno_avance ta ON ta.turno = t.id
    WHERE t.estado IN ('COMPLETADO', 'APROBADO')
),
metros_por_maquina AS (
    SELECT
        maquina_id,
        anio_op,
        mes_op,
        SUM(metros) AS metros_acumulados
    FROM turnos_metros
    GROUP BY maquina_id, anio_op, mes_op
)
SELECT
    m.maquina_id,
    maq.nombre                          AS maquina_nombre,
    maq.contrato_id,
    m.anio_op,
    m.mes_op,
    -- Fecha inicio y fin del período operativo (26 del mes anterior → 25 del mes)
    CASE
        WHEN m.mes_op = 1
            THEN make_date(m.anio_op - 1, 12, 26)
        ELSE make_date(m.anio_op, m.mes_op - 1, 26)
    END                                 AS periodo_inicio,
    make_date(m.anio_op, m.mes_op, 25) AS periodo_fin,
    m.metros_acumulados,
    COALESCE(pm.meta_metros, 0)         AS meta_maquina,
    CASE
        WHEN COALESCE(pm.meta_metros, 0) > 0
            THEN ROUND(m.metros_acumulados / pm.meta_metros * 100, 2)
        ELSE NULL
    END                                 AS cumplimiento_pct
FROM metros_por_maquina m
JOIN public.maquinas maq ON maq.id = m.maquina_id
LEFT JOIN public.programacion_mes pm
       ON pm.maquina_id = m.maquina_id
      AND pm.año        = m.anio_op
      AND pm.mes        = m.mes_op
ORDER BY m.anio_op DESC, m.mes_op DESC, maq.nombre;

-- GRANT SELECT ON public.vw_produccion_maquina_mes TO your_powerbi_user;
