-- Vista: vw_abastecimiento_clean
-- Describe: Abastecimientos con nombres de tipo_complemento/tipo_aditivo y unidad
CREATE OR REPLACE VIEW vw_abastecimiento_clean AS
SELECT
    a.id AS abastecimiento_id,
    a.mes,
    a.fecha,
    a.contrato AS contrato_id,
    c.nombre_contrato AS contrato_nombre,
    a.codigo_producto,
    a.descripcion,
    a.familia,
    a.serie,
    u.id AS unidad_medida_id,
    u.simbolo AS unidad_simbolo,
    a.cantidad,
    a.precio_unitario,
    a.total,
    tc.id AS tipo_complemento_id,
    tc.nombre AS tipo_complemento_nombre,
    ta.id AS tipo_aditivo_id,
    ta.nombre AS tipo_aditivo_nombre,
    a.numero_guia,
    a.observaciones,
    a.created_at
FROM abastecimiento a
LEFT JOIN contratos c ON c.id = a.contrato
LEFT JOIN unidades_medida u ON u.id = a.unidad_medida
LEFT JOIN tipos_complemento tc ON tc.id = a.tipo_complemento
LEFT JOIN tipos_aditivo ta ON ta.id = a.tipo_aditivo;
