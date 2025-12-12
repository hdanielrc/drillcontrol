-- Vista: vw_contrato_actividad
-- Describe: Normaliza la tabla legacy 'contratos_actividades' uniendo nombres legibles
CREATE OR REPLACE VIEW vw_contrato_actividad AS
SELECT
    ca.contrato_id,
    ca.tipoactividad_id,
    ta.nombre AS actividad_nombre,
    c.nombre_contrato AS contrato_nombre,
    ca.tipos_actividad,
    ca.contrato AS contrato_text
FROM contratos_actividades ca
LEFT JOIN contratos c ON c.id = ca.contrato_id
LEFT JOIN tipos_actividad ta ON ta.id = ca.tipoactividad_id;
