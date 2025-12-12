-- Vista: vw_trabajadores
-- Describe: vista limpia de trabajadores (id + dni + datos personales)
CREATE OR REPLACE VIEW vw_trabajadores AS
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
