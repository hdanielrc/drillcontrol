-- vw_turnos_fact.sql
-- Vista aplanada (fact) pensada para Power BI: trae turno + métricas relacionadas
-- Evita duplicaciones por M2M; si necesitas detalle por sondaje/actividad importa esas vistas por separado.

CREATE OR REPLACE VIEW public.vw_turnos_fact AS
SELECT
  t.id AS turno_id,
  t.fecha::date AS fecha,
  t.contrato_id,
  t.maquina_id,
  t.tipo_turno_id,
  t.estado,
  COALESCE(tm.horometro_inicio, NULL) AS horometro_inicio,
  COALESCE(tm.horometro_fin, NULL) AS horometro_fin,
  COALESCE(tm.horas_trabajadas_calc, 0) AS horas_trabajadas_calc,
  COALESCE(ta.metros_perforados, 0) AS metros_perforados,
  -- Suma de metrajes por sondaje (detalle)
  COALESCE((SELECT SUM(ts.metros_turno) FROM public.turno_sondaje ts WHERE ts.turno = t.id), 0) AS metros_sondajes_total,
  t.created_at,
  t.updated_at
FROM public.turnos t
LEFT JOIN public.turno_maquina tm ON tm.turno = t.id
LEFT JOIN public.turno_avance ta ON ta.turno = t.id;

-- GRANT SELECT ON public.vw_turnos_fact TO your_powerbi_user;
