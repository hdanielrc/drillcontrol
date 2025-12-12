-- ============================================================
-- VISTA: vw_horas_extras
-- Descripción: Vista optimizada para PowerBI de horas extras
-- Incluye toda la información necesaria para análisis
-- ============================================================

CREATE OR REPLACE VIEW public.vw_horas_extras AS
SELECT
    -- Identificadores
    he.id AS hora_extra_id,
    he.turno_id,
    he.trabajador_id,
    
    -- Información del Turno
    t.fecha AS fecha_turno,
    t.estado AS estado_turno,
    t.contrato_id,
    c.nombre_contrato AS contrato_nombre,
    c.codigo_centro_costo AS contrato_codigo_cc,
    t.maquina_id,
    m.nombre AS maquina_nombre,
    m.tipo AS maquina_tipo,
    t.tipo_turno_id,
    tt.nombre AS tipo_turno_nombre,
    
    -- Información del Trabajador
    trab.dni AS trabajador_dni,
    trab.nombres AS trabajador_nombres,
    trab.apellidos AS trabajador_apellidos,
    CONCAT(trab.nombres, ' ', COALESCE(trab.apellidos, '')) AS trabajador_nombre_completo,
    trab.cargo_id,
    cg.nombre AS cargo_nombre,
    trab.area AS trabajador_area,
    trab.estado AS trabajador_estado,
    
    -- Función en el turno
    tt_func.funcion AS funcion_en_turno,
    
    -- Horas Extras
    he.horas_extra,
    he.metros_turno,
    he.observaciones AS he_observaciones,
    
    -- Configuración Aplicada
    he.configuracion_aplicada_id,
    CASE 
        WHEN cfg.id IS NOT NULL THEN cfg.metros_minimos
        ELSE NULL
    END AS config_metros_minimos,
    CASE 
        WHEN cfg.id IS NOT NULL THEN cfg.horas_extra
        ELSE NULL
    END AS config_horas_extra,
    CASE 
        WHEN cfg.maquina_id IS NOT NULL THEN 'ESPECÍFICA'
        WHEN cfg.maquina_id IS NULL THEN 'GENERAL'
        ELSE 'MANUAL'
    END AS config_tipo,
    
    -- Dimensiones Temporales
    EXTRACT(YEAR FROM t.fecha) AS año,
    EXTRACT(MONTH FROM t.fecha) AS mes,
    EXTRACT(QUARTER FROM t.fecha) AS trimestre,
    TO_CHAR(t.fecha, 'YYYY-MM') AS año_mes,
    TO_CHAR(t.fecha, 'Month') AS mes_nombre,
    EXTRACT(DOW FROM t.fecha) AS dia_semana,
    TO_CHAR(t.fecha, 'Day') AS dia_semana_nombre,
    
    -- Timestamps
    he.created_at AS he_created_at
    
FROM public.turno_hora_extra he
INNER JOIN public.turnos t ON he.turno_id = t.id
INNER JOIN public.contratos c ON t.contrato_id = c.id
INNER JOIN public.maquinas m ON t.maquina_id = m.id
INNER JOIN public.tipo_turnos tt ON t.tipo_turno_id = tt.id
INNER JOIN public.trabajadores trab ON he.trabajador_id = trab.id
LEFT JOIN public.cargos cg ON trab.cargo_id = cg.id_cargo
LEFT JOIN public.turno_trabajador tt_func ON tt_func.turno_id = t.id AND tt_func.trabajador_id = trab.id
LEFT JOIN public.configuracion_hora_extra cfg ON he.configuracion_aplicada_id = cfg.id
ORDER BY t.fecha DESC, he.id;

-- Comentarios
COMMENT ON VIEW public.vw_horas_extras IS 'Vista optimizada para PowerBI: Horas extras con toda la información relacionada';

-- GRANT SELECT ON public.vw_horas_extras TO your_powerbi_user;
