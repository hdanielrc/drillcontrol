-- vw_tareo_trabajador_maquina.sql
-- Fuente canónica para ResumenDiasMaquina: un registro = un trabajador operando
-- una máquina en una fecha, según el tareo V2 (tareo_entry).
-- Solo incluye días efectivamente trabajados con máquina asignada.

CREATE OR REPLACE VIEW public.vw_tareo_trabajador_maquina AS
SELECT
    te.fecha,
    te.trabajador_id,
    te.maquina_snapshot_id AS maquina_id
FROM public.tareo_entry te
WHERE te.maquina_snapshot_id IS NOT NULL
  AND te.estado IN ('TRABAJO', 'TD', 'TN', 'TI', 'DA');

-- Índice sugerido si la vista se consulta frecuentemente:
-- (ya existen idx_tareo_trab_fecha y idx_tareo_fecha_estado en tareo_entry)
