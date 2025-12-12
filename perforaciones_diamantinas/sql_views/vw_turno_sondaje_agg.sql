-- Vista: vw_turno_sondaje_agg
-- Describe: agregados de TurnoSondaje por turno (conteo, suma, promedio)
CREATE OR REPLACE VIEW vw_turno_sondaje_agg AS
SELECT
    ts.turno AS turno_id,
    COUNT(*) AS sondaje_count,
    COALESCE(SUM(ts.metros_turno),0) AS total_metros_turno,
    CASE WHEN COUNT(*)>0 THEN SUM(ts.metros_turno)/COUNT(*) ELSE 0 END AS avg_metros_turno
FROM turno_sondaje ts
GROUP BY ts.turno;
