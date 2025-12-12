-- Vista: vw_turnos_detalle
-- Describe: Turnos con columnas 1:1 de TurnoAvance y TurnoMaquina (no agregaciones)
CREATE OR REPLACE VIEW vw_turnos_detalle AS
SELECT
    t.id AS turno_id,
    t.contrato AS contrato_id,
    t.maquina AS maquina_id,
    t.tipo_turno AS tipo_turno_id,
    t.fecha,
    t.estado,
    t.created_at,
    t.updated_at,

    ta.metros_perforados,

    tm.hora_inicio AS maquina_hora_inicio,
    tm.hora_fin AS maquina_hora_fin,
    tm.horas_trabajadas_calc AS maquina_horas_trabajadas,
    tm.estado_bomba AS maquina_estado_bomba,
    tm.estado_unidad AS maquina_estado_unidad,
    tm.estado_rotacion AS maquina_estado_rotacion
FROM turnos t
LEFT JOIN turno_avance ta ON ta.turno_id = t.id
LEFT JOIN turno_maquina tm ON tm.turno_id = t.id;
