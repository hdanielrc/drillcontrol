-- ============================================================
-- VISTA: vw_cumplimiento_metas
-- Descripción: Comparativa de metas vs metraje real por máquina
-- Calcula automáticamente el cumplimiento considerando meses operativos (26-25)
-- ============================================================

CREATE OR REPLACE VIEW public.vw_cumplimiento_metas AS
WITH metas_expandidas AS (
    -- Expandir las fechas de las metas (calculando fechas operativas si no son personalizadas)
    SELECT
        mm.id AS meta_id,
        mm.contrato_id,
        c.nombre_contrato AS contrato_nombre,
        c.codigo_centro_costo AS contrato_codigo_cc,
        mm.maquina_id,
        m.nombre AS maquina_nombre,
        m.tipo AS maquina_tipo,
        mm.año,
        mm.mes,
        -- Calcular fecha de inicio del período
        CASE 
            WHEN mm.fecha_inicio IS NOT NULL THEN mm.fecha_inicio
            ELSE MAKE_DATE(mm.año, mm.mes, 1) - INTERVAL '1 month' + INTERVAL '25 days'
        END AS fecha_inicio_periodo,
        -- Calcular fecha de fin del período
        CASE 
            WHEN mm.fecha_fin IS NOT NULL THEN mm.fecha_fin
            ELSE MAKE_DATE(mm.año, mm.mes, 25)
        END AS fecha_fin_periodo,
        -- Indicador de si es período personalizado
        CASE 
            WHEN mm.fecha_inicio IS NOT NULL AND mm.fecha_fin IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS es_periodo_personalizado,
        mm.meta_metros,
        mm.activo,
        mm.observaciones,
        mm.created_by_id,
        mm.created_at,
        mm.updated_at
    FROM public.meta_maquina mm
    INNER JOIN public.contratos c ON mm.contrato_id = c.id
    INNER JOIN public.maquinas m ON mm.maquina_id = m.id
),
metraje_real AS (
    -- Calcular el metraje real perforado por cada máquina en cada período de meta
    SELECT
        me.meta_id,
        me.contrato_id,
        me.maquina_id,
        me.fecha_inicio_periodo,
        me.fecha_fin_periodo,
        COUNT(DISTINCT t.id) AS total_turnos,
        COALESCE(SUM(ta.metros_perforados), 0) AS metros_reales,
        COALESCE(AVG(ta.metros_perforados), 0) AS promedio_metros_turno,
        MIN(t.fecha) AS fecha_primer_turno,
        MAX(t.fecha) AS fecha_ultimo_turno
    FROM metas_expandidas me
    LEFT JOIN public.turnos t ON 
        t.contrato_id = me.contrato_id 
        AND t.maquina_id = me.maquina_id
        AND t.fecha >= me.fecha_inicio_periodo
        AND t.fecha <= me.fecha_fin_periodo
        AND t.estado IN ('COMPLETADO', 'APROBADO')
    LEFT JOIN public.turno_avance ta ON ta.turno_id = t.id
    GROUP BY
        me.meta_id,
        me.contrato_id,
        me.maquina_id,
        me.fecha_inicio_periodo,
        me.fecha_fin_periodo
)
SELECT
    -- Identificadores
    me.meta_id,
    me.contrato_id,
    me.contrato_nombre,
    me.contrato_codigo_cc,
    me.maquina_id,
    me.maquina_nombre,
    me.maquina_tipo,
    
    -- Información del Período
    me.año,
    me.mes,
    TO_CHAR(MAKE_DATE(me.año, me.mes, 1), 'Month') AS mes_nombre,
    TO_CHAR(MAKE_DATE(me.año, me.mes, 1), 'YYYY-MM') AS año_mes,
    me.fecha_inicio_periodo,
    me.fecha_fin_periodo,
    (me.fecha_fin_periodo - me.fecha_inicio_periodo + 1) AS dias_periodo,
    me.es_periodo_personalizado,
    CASE 
        WHEN me.es_periodo_personalizado THEN 'PERSONALIZADO'
        ELSE 'MES OPERATIVO'
    END AS tipo_periodo,
    
    -- Meta
    me.meta_metros,
    me.activo AS meta_activa,
    
    -- Métricas Reales
    mr.total_turnos,
    mr.metros_reales,
    mr.promedio_metros_turno,
    mr.fecha_primer_turno,
    mr.fecha_ultimo_turno,
    
    -- Cálculos de Cumplimiento
    (me.meta_metros - mr.metros_reales) AS brecha_metros,
    CASE 
        WHEN me.meta_metros > 0 THEN 
            ROUND((mr.metros_reales / me.meta_metros * 100)::numeric, 2)
        ELSE 0
    END AS porcentaje_cumplimiento,
    
    -- Categorización de Cumplimiento
    CASE 
        WHEN me.meta_metros = 0 THEN 'SIN META'
        WHEN mr.metros_reales = 0 THEN 'SIN AVANCE'
        WHEN (mr.metros_reales / me.meta_metros * 100) >= 100 THEN 'CUMPLIDO'
        WHEN (mr.metros_reales / me.meta_metros * 100) >= 90 THEN 'CERCA'
        WHEN (mr.metros_reales / me.meta_metros * 100) >= 70 THEN 'REGULAR'
        WHEN (mr.metros_reales / me.meta_metros * 100) >= 50 THEN 'BAJO'
        ELSE 'CRÍTICO'
    END AS estado_cumplimiento,
    
    -- Proyecciones (si aún está en curso el período)
    CASE 
        WHEN CURRENT_DATE > me.fecha_fin_periodo THEN 'FINALIZADO'
        WHEN CURRENT_DATE < me.fecha_inicio_periodo THEN 'FUTURO'
        ELSE 'EN CURSO'
    END AS estado_periodo,
    
    -- Cálculo de días transcurridos y días restantes
    CASE 
        WHEN CURRENT_DATE >= me.fecha_inicio_periodo AND CURRENT_DATE <= me.fecha_fin_periodo THEN
            (CURRENT_DATE - me.fecha_inicio_periodo)
        WHEN CURRENT_DATE > me.fecha_fin_periodo THEN
            (me.fecha_fin_periodo - me.fecha_inicio_periodo + 1)
        ELSE 0
    END AS dias_transcurridos,
    
    CASE 
        WHEN CURRENT_DATE >= me.fecha_inicio_periodo AND CURRENT_DATE <= me.fecha_fin_periodo THEN
            (me.fecha_fin_periodo - CURRENT_DATE)
        ELSE 0
    END AS dias_restantes,
    
    -- Proyección de cumplimiento (solo para períodos en curso)
    CASE 
        WHEN CURRENT_DATE >= me.fecha_inicio_periodo 
             AND CURRENT_DATE <= me.fecha_fin_periodo 
             AND (CURRENT_DATE - me.fecha_inicio_periodo) > 0 THEN
            ROUND(
                (mr.metros_reales / (CURRENT_DATE - me.fecha_inicio_periodo)::numeric * 
                (me.fecha_fin_periodo - me.fecha_inicio_periodo + 1))::numeric, 
                2
            )
        ELSE NULL
    END AS metros_proyectados,
    
    CASE 
        WHEN CURRENT_DATE >= me.fecha_inicio_periodo 
             AND CURRENT_DATE <= me.fecha_fin_periodo 
             AND (CURRENT_DATE - me.fecha_inicio_periodo) > 0 
             AND me.meta_metros > 0 THEN
            ROUND(
                ((mr.metros_reales / (CURRENT_DATE - me.fecha_inicio_periodo)::numeric * 
                (me.fecha_fin_periodo - me.fecha_inicio_periodo + 1)) / me.meta_metros * 100)::numeric, 
                2
            )
        ELSE NULL
    END AS porcentaje_cumplimiento_proyectado,
    
    -- Meta diaria promedio
    ROUND((me.meta_metros / (me.fecha_fin_periodo - me.fecha_inicio_periodo + 1))::numeric, 2) AS meta_diaria_promedio,
    
    -- Ritmo real de perforación
    CASE 
        WHEN mr.total_turnos > 0 THEN
            ROUND((mr.metros_reales / mr.total_turnos)::numeric, 2)
        ELSE 0
    END AS metros_promedio_por_turno,
    
    -- Observaciones y auditoría
    me.observaciones,
    me.created_at AS meta_created_at,
    me.updated_at AS meta_updated_at,
    
    -- Timestamp de actualización de la vista
    NOW() AS fecha_actualizacion_vista

FROM metas_expandidas me
LEFT JOIN metraje_real mr ON mr.meta_id = me.meta_id
WHERE me.activo = TRUE
ORDER BY 
    me.fecha_inicio_periodo DESC,
    me.contrato_nombre,
    me.maquina_nombre;

-- Comentarios
COMMENT ON VIEW public.vw_cumplimiento_metas IS 'Vista de cumplimiento de metas vs metraje real por máquina. Soporta meses operativos (26-25) y períodos personalizados.';

-- GRANT SELECT ON public.vw_cumplimiento_metas TO powerbi_user;
