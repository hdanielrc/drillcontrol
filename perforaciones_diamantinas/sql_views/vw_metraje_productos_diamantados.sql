-- ============================================================
-- VISTA: vw_metraje_productos_diamantados
-- Descripción: Vista agregada de metraje por producto diamantado
-- Ideal para dashboards de desgaste y análisis de productos
-- ============================================================

CREATE OR REPLACE VIEW public.vw_metraje_productos_diamantados AS
SELECT
    -- Identificadores del Producto
    tc.tipo_complemento_id,
    tp.nombre AS producto_nombre,
    tp.categoria AS producto_categoria,
    tp.estado AS producto_estado,
    tc.codigo_serie,
    tp.codigo AS producto_codigo_api,
    tp.serie AS producto_serie_api,
    
    -- Información del Contrato
    tp.contrato_id,
    c.nombre_contrato AS contrato_nombre,
    
    -- Métricas Agregadas
    COUNT(tc.id) AS cantidad_usos,
    SUM(tc.metros_turno_calc) AS total_metros_acumulados,
    AVG(tc.metros_turno_calc) AS promedio_metros_por_uso,
    MIN(tc.metros_turno_calc) AS metros_minimo_uso,
    MAX(tc.metros_turno_calc) AS metros_maximo_uso,
    STDDEV(tc.metros_turno_calc) AS desviacion_std_metros,
    
    -- Fechas de Uso
    MIN(t.fecha) AS fecha_primer_uso,
    MAX(t.fecha) AS fecha_ultimo_uso,
    MAX(t.fecha) - MIN(t.fecha) AS dias_vida_util,
    
    -- Estado de Desgaste (categorización)
    CASE
        WHEN SUM(tc.metros_turno_calc) < 100 THEN 'BAJO USO'
        WHEN SUM(tc.metros_turno_calc) BETWEEN 100 AND 500 THEN 'USO MODERADO'
        WHEN SUM(tc.metros_turno_calc) BETWEEN 500 AND 1000 THEN 'USO ALTO'
        WHEN SUM(tc.metros_turno_calc) > 1000 THEN 'USO INTENSIVO'
        ELSE 'SIN USO'
    END AS categoria_uso,
    
    -- Máquinas que lo han usado
    COUNT(DISTINCT t.maquina_id) AS cantidad_maquinas_usadas,
    
    -- Sondajes en los que se ha usado
    COUNT(DISTINCT tc.sondaje_id) AS cantidad_sondajes,
    
    -- Timestamp de última actualización
    NOW() AS fecha_actualizacion_vista

FROM public.turno_complemento tc
INNER JOIN public.tipos_complemento tp ON tc.tipo_complemento_id = tp.id
INNER JOIN public.turnos t ON tc.turno_id = t.id
LEFT JOIN public.contratos c ON tp.contrato_id = c.id
GROUP BY 
    tc.tipo_complemento_id,
    tp.nombre,
    tp.categoria,
    tp.estado,
    tc.codigo_serie,
    tp.codigo,
    tp.serie,
    tp.contrato_id,
    c.nombre_contrato
ORDER BY total_metros_acumulados DESC;

-- Comentarios
COMMENT ON VIEW public.vw_metraje_productos_diamantados IS 'Vista agregada para PowerBI: Metraje acumulado y análisis de productos diamantados';

-- GRANT SELECT ON public.vw_metraje_productos_diamantados TO your_powerbi_user;
