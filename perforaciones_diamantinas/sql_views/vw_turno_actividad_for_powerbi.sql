-- vw_turno_actividad_for_powerbi.sql
-- Vista simple que expone la PK 'id' y la FK 'turno_id' para consumo en Power BI
-- Incluye las columnas principales usadas en análisis por actividad.

CREATE OR REPLACE VIEW public.vw_turno_actividad AS
SELECT
  ta.id,
  ta.turno AS turno_id,
  ta.actividad AS actividad_id,
  ta.hora_inicio,
  ta.hora_fin,
  ta.tiempo_calc,
  ta.observaciones
FROM public.turno_actividad ta;

-- Grant select if needed (opcional)
-- GRANT SELECT ON public.vw_turno_actividad TO your_powerbi_user;
