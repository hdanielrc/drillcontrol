-- Vista: vw_turno_complementos
-- Describe: TurnoComplemento con nombres de tipo y sondaje
CREATE OR REPLACE VIEW vw_turno_complementos AS
SELECT
    tc.id AS turno_complemento_id,
    tc.turno AS turno_id,
    tc.sondaje AS sondaje_id,
    s.nombre_sondaje,
    tc.tipo_complemento AS tipo_complemento_id,
    tcomp.nombre AS tipo_complemento_nombre,
    tc.codigo_serie,
    tc.metros_inicio,
    tc.metros_fin,
    tc.metros_turno_calc
FROM turno_complemento tc
LEFT JOIN tipos_complemento tcomp ON tcomp.id = tc.tipo_complemento
LEFT JOIN sondajes s ON s.id = tc.sondaje;
