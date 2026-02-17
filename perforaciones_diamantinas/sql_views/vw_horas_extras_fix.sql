-- ============================================================
-- VISTA: vw_horas_extras (ACTUALIZADA)
-- Descripción: Vista optimizada para PowerBI de horas extras
-- Adaptada al nuevo modelo de datos (Sin tabla Cargo, campo apepat)
-- ============================================================

DROP VIEW IF EXISTS public.vw_horas_extras CASCADE;

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
    trab.apepat AS trabajador_apellidos,
    CONCAT(trab.nombres, ' ', COALESCE(trab.apepat, ''), ' ', COALESCE(trab.apemat, '')) AS trabajador_nombre_completo,
    
    -- Cargo (directo del trabajador ahora)
    NULL AS cargo_id, -- Mantenemos null por compatibilidad si es necesario
    trab.cargo AS cargo_nombre,
    
    trab.area AS trabajador_area,
    trab.estado AS trabajador_estado,
    
    -- Función en el turno - Ajustar si turno_trabajador tambien cambio
    -- Por ahora asumimos que turno_trabajador sigue igual o se arreglará aparte
    -- tt_func.funcion AS funcion_en_turno, 
    -- (Comentado temporalmente si da problemas, descomentar si turno_trabajador existe y tiene funcion)
    
    -- Horas Extras
    he.horas_extra,
    
    -- Campos adicionales que parecian estar en la vista original pero no en el modelo django visible
    -- he.metros_turno, 
    -- he.observaciones,

    -- Configuración Aplicada
    he.configuracion_aplicada_id,
    
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
LEFT JOIN public.maquinas m ON t.maquina_id = m.id
LEFT JOIN public.tipo_turnos tt ON t.tipo_turno_id = tt.id
INNER JOIN public.trabajadores trab ON he.trabajador_id = trab.id
-- LEFT JOIN public.cargos cg ON trab.cargo_id = cg.id_cargo -- ELIMINADO
-- LEFT JOIN public.turno_trabajador tt_func ON tt_func.turno_id = t.id AND tt_func.trabajador_id = trab.id
-- LEFT JOIN public.configuracion_hora_extra cfg ON he.configuracion_aplicada_id = cfg.id
ORDER BY t.fecha DESC, he.id;

-- Comentarios
COMMENT ON VIEW public.vw_horas_extras IS 'Vista optimizada para PowerBI: Horas extras con toda la información relacionada (V2 - Sin Cargo ID)';
