-- sync_sequence_turno_actividad.sql
-- Diagnóstico y sincronización segura de la secuencia asociada a turno_actividad.id
-- Ejecuta en un entorno de staging primero y haz backup antes en producción.

-- 1) Ver si la columna id es identity
SELECT column_name, is_identity, identity_generation
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'turno_actividad' AND column_name = 'id';

-- 2) Intentar obtener la secuencia asociada (si existe)
SELECT pg_get_serial_sequence('public.turno_actividad','id') AS seq_name;

-- 3) Si pg_get_serial_sequence devuelve NULL, obtener la secuencia por dependencia
SELECT seq_ns.nspname AS sequence_schema,
       seq.relname AS sequence_name
FROM pg_class seq
JOIN pg_namespace seq_ns ON seq.relnamespace = seq_ns.oid
JOIN pg_depend dep ON dep.objid = seq.oid
JOIN pg_class tab ON dep.refobjid = tab.oid
JOIN pg_attribute att ON att.attrelid = tab.oid AND att.attnum = dep.refobjsubid
WHERE seq.relkind = 'S'  -- sequence
  AND tab.relname = 'turno_actividad'
  AND att.attname = 'id';

-- 4) Ejecutar setval en la secuencia encontrada (reemplaza el nombre de secuencia si es distinto)
-- Sustituye 'public.turno_actividad_id_seq' por el valor obtenido en las consultas previas si es necesario.
SELECT setval('public.turno_actividad_id_seq', COALESCE((SELECT MAX(id) FROM public.turno_actividad), 1), true);

-- 5) Verificación final: comprobar próximo valor
SELECT nextval('public.turno_actividad_id_seq') AS next_after_setval;
-- Si no quieres consumir un valor real de la secuencia, en vez de nextval consulta currval si ya fue inicializada.

-- FIN
