-- =============================================================================
-- VISTAS SQL PARA POWER BI - STOCK HISTÓRICO Y ALERTAS
-- Sistema de Stock DrillControl v2.0
-- Autor: DrillControl
-- Fecha: Diciembre 2024
-- =============================================================================

-- =============================================================================
-- VISTA: Stock Actual por Contrato
-- Última foto del stock de cada artículo por contrato
-- =============================================================================
CREATE OR REPLACE VIEW vw_stock_actual AS
WITH ultimo_sync AS (
    SELECT 
        contrato_id,
        codigo_articulo,
        MAX(fecha_sync) as ultima_fecha
    FROM stock_snapshot
    GROUP BY contrato_id, codigo_articulo
)
SELECT 
    ss.id,
    c.id as contrato_id,
    c.nombre_contrato,
    cl.nombre as cliente,
    ss.familia,
    ss.codigo_articulo,
    ss.descripcion,
    ss.stock_cantidad,
    ss.unidad_medida,
    ss.lote,
    ss.ubicacion,
    ss.precio_unitario,
    ss.valor_total,
    ss.fecha_sync,
    CASE 
        WHEN ss.stock_cantidad <= 0 THEN 'AGOTADO'
        WHEN ss.stock_cantidad <= 10 THEN 'CRITICO'
        WHEN ss.stock_cantidad <= 50 THEN 'BAJO'
        ELSE 'OK'
    END as estado_stock
FROM stock_snapshot ss
INNER JOIN ultimo_sync us ON ss.contrato_id = us.contrato_id 
    AND ss.codigo_articulo = us.codigo_articulo 
    AND ss.fecha_sync = us.ultima_fecha
INNER JOIN contratos c ON ss.contrato_id = c.id
INNER JOIN clientes cl ON c.cliente_id = cl.id
ORDER BY c.nombre_contrato, ss.familia, ss.descripcion;

COMMENT ON VIEW vw_stock_actual IS 'Stock actual de todos los artículos por contrato (última sincronización)';


-- =============================================================================
-- VISTA: Histórico de Stock para Tendencias
-- Todos los snapshots para análisis de tendencias
-- =============================================================================
CREATE OR REPLACE VIEW vw_stock_historico AS
SELECT 
    ss.id,
    c.id as contrato_id,
    c.nombre_contrato,
    ss.familia,
    ss.codigo_articulo,
    ss.descripcion,
    ss.stock_cantidad,
    ss.unidad_medida,
    ss.precio_unitario,
    ss.valor_total,
    ss.fecha_sync,
    DATE(ss.fecha_sync) as fecha,
    EXTRACT(YEAR FROM ss.fecha_sync) as anio,
    EXTRACT(MONTH FROM ss.fecha_sync) as mes,
    EXTRACT(WEEK FROM ss.fecha_sync) as semana,
    TO_CHAR(ss.fecha_sync, 'YYYY-MM') as periodo
FROM stock_snapshot ss
INNER JOIN contratos c ON ss.contrato_id = c.id
WHERE c.estado = 'ACTIVO'
ORDER BY ss.fecha_sync DESC;

COMMENT ON VIEW vw_stock_historico IS 'Histórico completo de snapshots de stock para análisis de tendencias';


-- =============================================================================
-- VISTA: Alertas de Stock para Monitoreo
-- Alertas activas y resueltas con detalles
-- =============================================================================
CREATE OR REPLACE VIEW vw_alertas_stock AS
SELECT 
    a.id,
    c.id as contrato_id,
    c.nombre_contrato,
    cl.nombre as cliente,
    a.codigo_articulo,
    a.descripcion_articulo,
    a.familia,
    a.tipo_alerta,
    CASE a.tipo_alerta
        WHEN 'AGOTADO' THEN 'Artículo Agotado'
        WHEN 'STOCK_CRITICO' THEN 'Stock Crítico'
        WHEN 'STOCK_BAJO' THEN 'Stock Bajo'
        WHEN 'SIN_ROTACION' THEN 'Sin Rotación'
        WHEN 'CONSUMO_ANORMAL' THEN 'Consumo Anormal'
        WHEN 'REPOSICION_URGENTE' THEN 'Reposición Urgente'
        ELSE a.tipo_alerta
    END as tipo_alerta_display,
    a.prioridad,
    CASE a.prioridad
        WHEN 1 THEN 'Crítica'
        WHEN 2 THEN 'Alta'
        WHEN 3 THEN 'Media'
        WHEN 4 THEN 'Baja'
        ELSE 'Desconocida'
    END as prioridad_display,
    a.mensaje,
    a.stock_actual,
    a.consumo_diario_promedio,
    a.dias_stock_restante,
    a.fecha_creacion,
    DATE(a.fecha_creacion) as fecha_alerta,
    a.leida,
    a.fecha_lectura,
    a.resuelta,
    a.fecha_resolucion,
    a.nota_resolucion,
    CASE 
        WHEN a.resuelta THEN 'Resuelta'
        WHEN a.leida THEN 'Leída'
        ELSE 'Nueva'
    END as estado_alerta,
    -- Tiempo de resolución en horas
    CASE 
        WHEN a.resuelta THEN 
            EXTRACT(EPOCH FROM (a.fecha_resolucion - a.fecha_creacion)) / 3600
        ELSE NULL
    END as horas_resolucion
FROM alerta_stock a
INNER JOIN contratos c ON a.contrato_id = c.id
INNER JOIN clientes cl ON c.cliente_id = cl.id
ORDER BY a.prioridad, a.fecha_creacion DESC;

COMMENT ON VIEW vw_alertas_stock IS 'Alertas de stock con información detallada para monitoreo';


-- =============================================================================
-- VISTA: Resumen de Stock por Contrato
-- KPIs principales de stock por contrato
-- =============================================================================
CREATE OR REPLACE VIEW vw_stock_resumen_contrato AS
WITH stock_actual AS (
    SELECT 
        contrato_id,
        codigo_articulo,
        familia,
        stock_cantidad,
        valor_total,
        ROW_NUMBER() OVER (
            PARTITION BY contrato_id, codigo_articulo 
            ORDER BY fecha_sync DESC
        ) as rn
    FROM stock_snapshot
),
alertas_activas AS (
    SELECT 
        contrato_id,
        COUNT(*) as total_alertas,
        SUM(CASE WHEN prioridad = 1 THEN 1 ELSE 0 END) as alertas_criticas
    FROM alerta_stock
    WHERE resuelta = FALSE
    GROUP BY contrato_id
)
SELECT 
    c.id as contrato_id,
    c.nombre_contrato,
    cl.nombre as cliente,
    COUNT(DISTINCT sa.codigo_articulo) as total_articulos,
    COUNT(DISTINCT CASE WHEN sa.familia = 'PDD' THEN sa.codigo_articulo END) as articulos_pdd,
    COUNT(DISTINCT CASE WHEN sa.familia = 'ADIT' THEN sa.codigo_articulo END) as articulos_adit,
    SUM(sa.stock_cantidad) as stock_total_unidades,
    SUM(sa.valor_total) as valor_inventario,
    COUNT(CASE WHEN sa.stock_cantidad <= 0 THEN 1 END) as articulos_agotados,
    COUNT(CASE WHEN sa.stock_cantidad > 0 AND sa.stock_cantidad <= 10 THEN 1 END) as articulos_criticos,
    COUNT(CASE WHEN sa.stock_cantidad > 10 AND sa.stock_cantidad <= 50 THEN 1 END) as articulos_bajo,
    COUNT(CASE WHEN sa.stock_cantidad > 50 THEN 1 END) as articulos_ok,
    COALESCE(aa.total_alertas, 0) as alertas_activas,
    COALESCE(aa.alertas_criticas, 0) as alertas_criticas
FROM contratos c
INNER JOIN clientes cl ON c.cliente_id = cl.id
LEFT JOIN stock_actual sa ON c.id = sa.contrato_id AND sa.rn = 1
LEFT JOIN alertas_activas aa ON c.id = aa.contrato_id
WHERE c.estado = 'ACTIVO'
GROUP BY c.id, c.nombre_contrato, cl.nombre, aa.total_alertas, aa.alertas_criticas
ORDER BY c.nombre_contrato;

COMMENT ON VIEW vw_stock_resumen_contrato IS 'Resumen ejecutivo de stock y alertas por contrato';


-- =============================================================================
-- VISTA: Consumo de Stock por Período
-- Análisis de consumos para calcular rotación
-- =============================================================================
CREATE OR REPLACE VIEW vw_consumo_stock_periodo AS
SELECT 
    c.id as contrato_id,
    c.nombre_contrato,
    a.codigo_producto as codigo_articulo,
    a.descripcion,
    a.familia,
    DATE_TRUNC('month', t.fecha) as periodo,
    TO_CHAR(t.fecha, 'YYYY-MM') as periodo_texto,
    EXTRACT(YEAR FROM t.fecha) as anio,
    EXTRACT(MONTH FROM t.fecha) as mes,
    SUM(cs.cantidad_consumida) as cantidad_consumida,
    COUNT(DISTINCT t.id) as turnos_con_consumo,
    AVG(cs.cantidad_consumida) as consumo_promedio_turno
FROM consumo_stock cs
INNER JOIN turno t ON cs.turno_id = t.id
INNER JOIN contratos c ON t.contrato_id = c.id
INNER JOIN abastecimiento a ON cs.abastecimiento_id = a.id
GROUP BY 
    c.id, c.nombre_contrato, 
    a.codigo_producto, a.descripcion, a.familia,
    DATE_TRUNC('month', t.fecha), TO_CHAR(t.fecha, 'YYYY-MM'),
    EXTRACT(YEAR FROM t.fecha), EXTRACT(MONTH FROM t.fecha)
ORDER BY periodo DESC, c.nombre_contrato;

COMMENT ON VIEW vw_consumo_stock_periodo IS 'Consumo de stock agrupado por período para análisis de rotación';


-- =============================================================================
-- VISTA: Proyección de Agotamiento
-- Artículos con días estimados de stock restante
-- =============================================================================
CREATE OR REPLACE VIEW vw_stock_proyeccion AS
WITH stock_actual AS (
    SELECT 
        ss.contrato_id,
        ss.codigo_articulo,
        ss.descripcion,
        ss.familia,
        ss.stock_cantidad,
        ss.unidad_medida,
        ss.fecha_sync,
        ROW_NUMBER() OVER (
            PARTITION BY ss.contrato_id, ss.codigo_articulo 
            ORDER BY ss.fecha_sync DESC
        ) as rn
    FROM stock_snapshot ss
),
consumo_30d AS (
    SELECT 
        c.id as contrato_id,
        a.codigo_producto as codigo_articulo,
        SUM(cs.cantidad_consumida) as consumo_total,
        SUM(cs.cantidad_consumida) / 30.0 as consumo_diario
    FROM consumo_stock cs
    INNER JOIN turno t ON cs.turno_id = t.id
    INNER JOIN contratos c ON t.contrato_id = c.id
    INNER JOIN abastecimiento a ON cs.abastecimiento_id = a.id
    WHERE t.fecha >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY c.id, a.codigo_producto
)
SELECT 
    c.id as contrato_id,
    c.nombre_contrato,
    sa.codigo_articulo,
    sa.descripcion,
    sa.familia,
    sa.stock_cantidad,
    sa.unidad_medida,
    COALESCE(co.consumo_diario, 0) as consumo_diario,
    CASE 
        WHEN COALESCE(co.consumo_diario, 0) > 0 THEN 
            ROUND(sa.stock_cantidad / co.consumo_diario, 1)
        ELSE NULL
    END as dias_restantes,
    CASE 
        WHEN sa.stock_cantidad <= 0 THEN 'AGOTADO'
        WHEN COALESCE(co.consumo_diario, 0) > 0 AND (sa.stock_cantidad / co.consumo_diario) <= 5 THEN 'CRITICO'
        WHEN COALESCE(co.consumo_diario, 0) > 0 AND (sa.stock_cantidad / co.consumo_diario) <= 15 THEN 'BAJO'
        WHEN COALESCE(co.consumo_diario, 0) > 0 AND (sa.stock_cantidad / co.consumo_diario) <= 30 THEN 'ALERTA'
        ELSE 'OK'
    END as estado,
    CASE 
        WHEN COALESCE(co.consumo_diario, 0) > 0 THEN 
            CURRENT_DATE + (sa.stock_cantidad / co.consumo_diario)::INTEGER
        ELSE NULL
    END as fecha_agotamiento_estimada,
    sa.fecha_sync as ultima_actualizacion
FROM contratos c
INNER JOIN stock_actual sa ON c.id = sa.contrato_id AND sa.rn = 1
LEFT JOIN consumo_30d co ON c.id = co.contrato_id AND sa.codigo_articulo = co.codigo_articulo
WHERE c.estado = 'ACTIVO'
ORDER BY 
    CASE 
        WHEN sa.stock_cantidad <= 0 THEN 0
        WHEN COALESCE(co.consumo_diario, 0) > 0 THEN sa.stock_cantidad / co.consumo_diario
        ELSE 9999
    END ASC,
    c.nombre_contrato;

COMMENT ON VIEW vw_stock_proyeccion IS 'Proyección de agotamiento de stock basada en consumo histórico';


-- =============================================================================
-- ÍNDICES RECOMENDADOS PARA MEJOR RENDIMIENTO
-- =============================================================================

-- Índices para stock_snapshot (si no existen)
-- CREATE INDEX IF NOT EXISTS idx_stock_snapshot_contrato_fecha ON stock_snapshot(contrato_id, fecha_sync DESC);
-- CREATE INDEX IF NOT EXISTS idx_stock_snapshot_codigo ON stock_snapshot(codigo_articulo);
-- CREATE INDEX IF NOT EXISTS idx_stock_snapshot_familia ON stock_snapshot(familia);

-- Índices para alerta_stock (si no existen)
-- CREATE INDEX IF NOT EXISTS idx_alerta_stock_contrato_resuelta ON alerta_stock(contrato_id, resuelta);
-- CREATE INDEX IF NOT EXISTS idx_alerta_stock_prioridad ON alerta_stock(prioridad, fecha_creacion DESC);
