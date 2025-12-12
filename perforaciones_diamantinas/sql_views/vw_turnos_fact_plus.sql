-- vw_turnos_fact_plus.sql
-- Vista aplanada para Power BI: trae turno + atributos descriptivos y métricas
-- Incluye: cliente, contrato, maquina, tipo_turno, métricas de horómetro y metros, conteos de actividades/trabajadores
-- Ejecutar en Neon/Postgres. Prueba en staging antes de producción.

CREATE OR REPLACE VIEW public.vw_turnos_fact_plus AS
SELECT
  t.id AS turno_id,
  t.fecha::date AS fecha,

  -- Contrato / Cliente
  c.id AS contrato_id,
  c.nombre_contrato AS contrato_nombre,
  cl.id AS cliente_id,
  cl.nombre AS cliente_nombre,

  -- Máquina
  m.id AS maquina_id,
  m.nombre AS maquina_nombre,
  m.horometro AS maquina_horometro,

  -- Tipo de turno
  tt.id AS tipo_turno_id,
  tt.nombre AS tipo_turno_nombre,

  -- Estado y timestamps
  t.estado AS turno_estado,
  t.created_at,
  t.updated_at,

  -- Lecturas de máquina / métricas
  tm.horometro_inicio,
  tm.horometro_fin,
  COALESCE(tm.horas_trabajadas_calc, 0) AS horas_trabajadas_calc,

  -- Avance guardado en TurnoAvance (metros perforados) si existe
  COALESCE(ta.metros_perforados, 0) AS metros_perforados,

  -- Suma de metrajes por sondaje (detalle)
  COALESCE((SELECT SUM(ts.metros_turno) FROM public.turno_sondaje ts WHERE ts.turno = t.id), 0) AS metros_sondajes_total,

  -- Conteos (actividad / trabajadores / complementos / corridas)
  (SELECT COUNT(*) FROM public.turno_actividad a WHERE a.turno = t.id) AS actividades_count,
  (SELECT COUNT(*) FROM public.turno_trabajador tr WHERE tr.turno = t.id) AS trabajadores_count,
  (SELECT COUNT(*) FROM public.turno_complemento c2 WHERE c2.turno = t.id) AS complementos_count,
  (SELECT COUNT(*) FROM public.turno_corrida cr WHERE cr.turno = t.id) AS corridas_count

FROM public.turnos t
LEFT JOIN public.contratos c ON c.id = t.contrato_id
LEFT JOIN public.clientes cl ON cl.id = c.cliente_id
LEFT JOIN public.maquinas m ON m.id = t.maquina_id
LEFT JOIN public.tipo_turnos tt ON tt.id = t.tipo_turno_id
LEFT JOIN public.turno_maquina tm ON tm.turno = t.id
LEFT JOIN public.turno_avance ta ON ta.turno = t.id;

-- Opcional: otorgar permisos (descomentar y adaptar usuario/rol si es necesario)
-- GRANT SELECT ON public.vw_turnos_fact_plus TO your_powerbi_user;

-- FIN
