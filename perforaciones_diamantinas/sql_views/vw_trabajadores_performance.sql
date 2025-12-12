-- ============================================================
-- VISTA: vw_trabajadores_performance
-- Descripción: Vista de rendimiento de trabajadores
-- Incluye métricas de turnos, horas extras, y productividad
-- ============================================================

CREATE OR REPLACE VIEW public.vw_trabajadores_performance AS
SELECT
    -- Identificadores del Trabajador
    trab.id AS trabajador_id,
    trab.dni AS trabajador_dni,
    trab.nombres AS trabajador_nombres,
    trab.apellidos AS trabajador_apellidos,
    CONCAT(trab.nombres, ' ', COALESCE(trab.apellidos, '')) AS trabajador_nombre_completo,
    
    -- Información del Trabajador
    trab.cargo_id,
    cg.nombre AS cargo_nombre,
    trab.area AS trabajador_area,
    trab.estado AS trabajador_estado,
    trab.subestado AS trabajador_subestado,
    trab.fecha_ingreso,
    
    -- Información del Contrato
    trab.contrato_id,
    c.nombre_contrato AS contrato_nombre,
    cli.nombre AS cliente_nombre,
    
    -- Métricas de Participación en Turnos
    COUNT(DISTINCT tt.turno_id) AS total_turnos_participados,
    COUNT(DISTINCT CASE WHEN tt.funcion = 'PERFORISTA' THEN tt.turno_id END) AS turnos_como_perforista,
    COUNT(DISTINCT CASE WHEN tt.funcion = 'AYUDANTE' THEN tt.turno_id END) AS turnos_como_ayudante,
    
    -- Métricas por Mes (últimos 30 días)
    COUNT(DISTINCT CASE WHEN t.fecha >= CURRENT_DATE - INTERVAL '30 days' THEN tt.turno_id END) AS turnos_ultimo_mes,
    
    -- Métricas de Horas Extras
    COUNT(DISTINCT the.id) AS total_horas_extras_registros,
    COALESCE(SUM(the.horas_extra), 0) AS total_horas_extras_acumuladas,
    COALESCE(AVG(the.horas_extra), 0) AS promedio_horas_extras,
    
    -- Horas Extras por Mes
    COUNT(DISTINCT CASE WHEN t.fecha >= CURRENT_DATE - INTERVAL '30 days' THEN the.id END) AS he_ultimo_mes_cantidad,
    COALESCE(SUM(CASE WHEN t.fecha >= CURRENT_DATE - INTERVAL '30 days' THEN the.horas_extra END), 0) AS he_ultimo_mes_total,
    
    -- Métricas de Metraje (cuando es perforista)
    AVG(CASE WHEN tt.funcion = 'PERFORISTA' THEN ta.metros_perforados END) AS promedio_metros_como_perforista,
    SUM(CASE WHEN tt.funcion = 'PERFORISTA' THEN ta.metros_perforados END) AS total_metros_como_perforista,
    
    -- Fechas de Actividad
    MIN(t.fecha) AS fecha_primer_turno,
    MAX(t.fecha) AS fecha_ultimo_turno,
    MAX(t.fecha) - MIN(t.fecha) AS dias_antiguedad_turnos,
    
    -- Estado de Documentación
    trab.fotocheck_fecha_caducidad,
    CASE 
        WHEN trab.fotocheck_fecha_caducidad < CURRENT_DATE THEN 'VENCIDO'
        WHEN trab.fotocheck_fecha_caducidad < CURRENT_DATE + INTERVAL '30 days' THEN 'POR VENCER'
        ELSE 'VIGENTE'
    END AS estado_fotocheck,
    
    trab.emo_fecha_vencimiento,
    CASE 
        WHEN trab.emo_fecha_vencimiento < CURRENT_DATE THEN 'VENCIDO'
        WHEN trab.emo_fecha_vencimiento < CURRENT_DATE + INTERVAL '30 days' THEN 'POR VENCER'
        ELSE 'VIGENTE'
    END AS estado_emo,
    
    -- Timestamp de última actualización
    trab.updated_at AS trabajador_updated_at,
    NOW() AS fecha_actualizacion_vista

FROM public.trabajadores trab
INNER JOIN public.contratos c ON trab.contrato_id = c.id
INNER JOIN public.clientes cli ON c.cliente_id = cli.id
LEFT JOIN public.cargos cg ON trab.cargo_id = cg.id_cargo
LEFT JOIN public.turno_trabajador tt ON tt.trabajador_id = trab.id
LEFT JOIN public.turnos t ON tt.turno_id = t.id
LEFT JOIN public.turno_avance ta ON ta.turno_id = t.id
LEFT JOIN public.turno_hora_extra the ON the.turno_id = t.id AND the.trabajador_id = trab.id
GROUP BY 
    trab.id,
    trab.dni,
    trab.nombres,
    trab.apellidos,
    trab.cargo_id,
    cg.nombre,
    trab.area,
    trab.estado,
    trab.subestado,
    trab.fecha_ingreso,
    trab.contrato_id,
    c.nombre_contrato,
    cli.nombre,
    trab.fotocheck_fecha_caducidad,
    trab.emo_fecha_vencimiento,
    trab.updated_at
ORDER BY total_turnos_participados DESC;

-- Comentarios
COMMENT ON VIEW public.vw_trabajadores_performance IS 'Vista de performance para PowerBI: Métricas de rendimiento y participación de trabajadores';

-- GRANT SELECT ON public.vw_trabajadores_performance TO your_powerbi_user;
