-- ============================================================
-- VISTA: vw_turnos_completo_powerbi
-- Descripción: Vista maestra de turnos con todas las métricas
-- Incluye trabajadores, avance, horas trabajadas, horas extras
-- ============================================================

CREATE OR REPLACE VIEW public.vw_turnos_completo_powerbi AS
SELECT
    -- Identificadores del Turno
    t.id AS turno_id,
    t.fecha AS fecha_turno,
    t.estado AS estado_turno,
    
    -- Información del Contrato
    t.contrato_id,
    c.nombre_contrato AS contrato_nombre,
    c.codigo_centro_costo AS contrato_codigo_cc,
    c.duracion_turno AS contrato_duracion_turno_horas,
    cli.nombre AS cliente_nombre,
    
    -- Información de la Máquina
    t.maquina_id,
    m.nombre AS maquina_nombre,
    m.tipo AS maquina_tipo,
    m.estado AS maquina_estado,
    m.horometro AS maquina_horometro_actual,
    
    -- Tipo de Turno
    t.tipo_turno_id,
    tt.nombre AS tipo_turno_nombre,
    
    -- Sondajes (agregado M2M)
    (SELECT COUNT(*) FROM turno_sondaje ts WHERE ts.turno_id = t.id) AS cantidad_sondajes,
    (SELECT STRING_AGG(s.nombre_sondaje, ', ') 
     FROM turno_sondaje ts 
     INNER JOIN sondajes s ON ts.sondaje_id = s.id 
     WHERE ts.turno_id = t.id) AS sondajes_nombres,
    (SELECT SUM(ts.metros_turno) FROM turno_sondaje ts WHERE ts.turno_id = t.id) AS metros_sondajes_total,
    
    -- Métricas de Avance
    COALESCE(ta.metros_perforados, 0) AS metros_perforados,
    
    -- Métricas de Máquina
    COALESCE(tm.horometro_inicio, 0) AS horometro_inicio,
    COALESCE(tm.horometro_fin, 0) AS horometro_fin,
    COALESCE(tm.horas_trabajadas_calc, 0) AS horas_trabajadas,
    tm.estado_bomba,
    tm.estado_unidad,
    tm.estado_rotacion,
    
    -- Trabajadores del Turno
    (SELECT COUNT(*) FROM turno_trabajador ttrab WHERE ttrab.turno_id = t.id) AS cantidad_trabajadores,
    (SELECT COUNT(*) FROM turno_trabajador ttrab WHERE ttrab.turno_id = t.id AND ttrab.funcion = 'PERFORISTA') AS cantidad_perforistas,
    (SELECT COUNT(*) FROM turno_trabajador ttrab WHERE ttrab.turno_id = t.id AND ttrab.funcion = 'AYUDANTE') AS cantidad_ayudantes,
    
    -- Horas Extras
    (SELECT COUNT(*) FROM turno_hora_extra the WHERE the.turno_id = t.id) AS cantidad_trabajadores_con_he,
    (SELECT SUM(the.horas_extra) FROM turno_hora_extra the WHERE the.turno_id = t.id) AS total_horas_extras_otorgadas,
    (SELECT AVG(the.horas_extra) FROM turno_hora_extra the WHERE the.turno_id = t.id) AS promedio_horas_extras,
    
    -- Productos Diamantados Usados
    (SELECT COUNT(*) FROM turno_complemento tcomp WHERE tcomp.turno_id = t.id) AS cantidad_complementos_usados,
    (SELECT SUM(tcomp.metros_turno_calc) FROM turno_complemento tcomp WHERE tcomp.turno_id = t.id) AS total_metros_complementos,
    
    -- Aditivos Usados
    (SELECT COUNT(*) FROM turno_aditivo tadit WHERE tadit.turno_id = t.id) AS cantidad_aditivos_usados,
    
    -- Actividades
    (SELECT COUNT(*) FROM turno_actividad tact WHERE tact.turno_id = t.id) AS cantidad_actividades,
    (SELECT SUM(tact.tiempo_calc) FROM turno_actividad tact WHERE tact.turno_id = t.id) AS total_horas_actividades,
    
    -- Corridas
    (SELECT COUNT(*) FROM turno_corrida tcor WHERE tcor.turno_id = t.id) AS cantidad_corridas,
    (SELECT AVG(tcor.pct_recuperacion) FROM turno_corrida tcor WHERE tcor.turno_id = t.id) AS promedio_recuperacion,
    (SELECT AVG(tcor.pct_retorno_agua) FROM turno_corrida tcor WHERE tcor.turno_id = t.id) AS promedio_retorno_agua,
    
    -- Dimensiones Temporales
    EXTRACT(YEAR FROM t.fecha) AS año,
    EXTRACT(MONTH FROM t.fecha) AS mes,
    EXTRACT(QUARTER FROM t.fecha) AS trimestre,
    EXTRACT(WEEK FROM t.fecha) AS semana,
    EXTRACT(DOW FROM t.fecha) AS dia_semana,
    TO_CHAR(t.fecha, 'YYYY-MM') AS año_mes,
    TO_CHAR(t.fecha, 'Month') AS mes_nombre,
    TO_CHAR(t.fecha, 'Day') AS dia_semana_nombre,
    
    -- Banderas de Cumplimiento
    CASE 
        WHEN COALESCE(ta.metros_perforados, 0) > 0 THEN TRUE 
        ELSE FALSE 
    END AS tiene_avance,
    
    CASE 
        WHEN (SELECT COUNT(*) FROM turno_hora_extra the WHERE the.turno_id = t.id) > 0 THEN TRUE 
        ELSE FALSE 
    END AS genero_horas_extras,
    
    CASE 
        WHEN t.estado = 'COMPLETADO' OR t.estado = 'APROBADO' THEN TRUE 
        ELSE FALSE 
    END AS turno_cerrado,
    
    -- Timestamps
    t.created_at AS turno_created_at,
    t.updated_at AS turno_updated_at

FROM public.turnos t
INNER JOIN public.contratos c ON t.contrato_id = c.id
INNER JOIN public.clientes cli ON c.cliente_id = cli.id
INNER JOIN public.maquinas m ON t.maquina_id = m.id
INNER JOIN public.tipo_turnos tt ON t.tipo_turno_id = tt.id
LEFT JOIN public.turno_avance ta ON ta.turno_id = t.id
LEFT JOIN public.turno_maquina tm ON tm.turno_id = t.id
ORDER BY t.fecha DESC, t.id DESC;

-- Comentarios
COMMENT ON VIEW public.vw_turnos_completo_powerbi IS 'Vista maestra para PowerBI: Turnos con todas las métricas agregadas';

-- GRANT SELECT ON public.vw_turnos_completo_powerbi TO your_powerbi_user;
