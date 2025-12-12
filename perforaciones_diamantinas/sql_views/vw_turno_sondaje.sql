-- Vista: vw_turno_sondaje
-- Describe: filas de TurnoSondaje con atributos del sondaje
CREATE OR REPLACE VIEW vw_turno_sondaje AS
SELECT
    ts.id AS turno_sondaje_id,
    ts.turno AS turno_id,
    ts.sondaje AS sondaje_id,
    ts.metros_turno,
    ts.created_at,

    s.nombre_sondaje,
    s.contrato AS sondaje_contrato_id,
    s.profundidad
FROM turno_sondaje ts
LEFT JOIN sondajes s ON s.id = ts.sondaje;
