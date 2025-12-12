-- create_all_views_neon.sql
-- SQL combinado para crear las vistas recomendadas en una base Postgres (NeonDB)
-- Recomendación: ejecutar con un usuario que tenga permisos CREATE VIEW / USAGE en el schema destino (por defecto: public).
-- Ejecución sugerida desde cmd.exe (Windows):
-- set PGPASSWORD=YourPassword
-- psql "host=<NEON_HOST> port=5432 dbname=<DBNAME> user=<USER> sslmode=require" -f "path\to\create_all_views_neon.sql"
-- set PGPASSWORD=

SET search_path = public;

-- =====================================
-- vw_turnos_detalle
-- =====================================
CREATE OR REPLACE VIEW public.vw_turnos_detalle AS
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

-- =====================================
-- vw_turno_sondaje
-- =====================================
CREATE OR REPLACE VIEW public.vw_turno_sondaje AS
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

-- =====================================
-- vw_turno_sondaje_agg
-- =====================================
CREATE OR REPLACE VIEW public.vw_turno_sondaje_agg AS
SELECT
    ts.turno AS turno_id,
    COUNT(*) AS sondaje_count,
    COALESCE(SUM(ts.metros_turno),0) AS total_metros_turno,
    CASE WHEN COUNT(*)>0 THEN SUM(ts.metros_turno)/COUNT(*) ELSE 0 END AS avg_metros_turno
FROM turno_sondaje ts
GROUP BY ts.turno;

-- =====================================
-- vw_trabajadores
-- =====================================
CREATE OR REPLACE VIEW public.vw_trabajadores AS
SELECT
    id AS trabajador_id,
    dni,
    nombres,
    apellidos,
    contrato AS contrato_id,
    cargo,
    telefono,
    email,
    fecha_ingreso,
    is_active,
    created_at,
    updated_at
FROM trabajadores;

-- =====================================
-- vw_contrato_actividad
-- =====================================
CREATE OR REPLACE VIEW public.vw_contrato_actividad AS
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

-- =====================================
-- vw_abastecimiento_clean
-- =====================================
CREATE OR REPLACE VIEW public.vw_abastecimiento_clean AS
SELECT
    a.id AS abastecimiento_id,
    a.mes,
    a.fecha,
    a.contrato AS contrato_id,
    c.nombre_contrato AS contrato_nombre,
    a.codigo_producto,
    a.descripcion,
    a.familia,
    a.serie,
    u.id AS unidad_medida_id,
    u.simbolo AS unidad_simbolo,
    a.cantidad,
    a.precio_unitario,
    a.total,
    tc.id AS tipo_complemento_id,
    tc.nombre AS tipo_complemento_nombre,
    ta.id AS tipo_aditivo_id,
    ta.nombre AS tipo_aditivo_nombre,
    a.numero_guia,
    a.observaciones,
    a.created_at
FROM abastecimiento a
LEFT JOIN contratos c ON c.id = a.contrato
LEFT JOIN unidades_medida u ON u.id = a.unidad_medida
LEFT JOIN tipos_complemento tc ON tc.id = a.tipo_complemento
LEFT JOIN tipos_aditivo ta ON ta.id = a.tipo_aditivo;

-- =====================================
-- vw_turno_complementos
-- =====================================
CREATE OR REPLACE VIEW public.vw_turno_complementos AS
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

-- FIN del script
