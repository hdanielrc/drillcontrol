-- ============================================================
-- SCRIPT: Crear todas las vistas optimizadas para PowerBI
-- Ejecutar en orden para crear el esquema completo de vistas
-- ============================================================

-- 1. Vista de Horas Extras
\i vw_horas_extras.sql

-- 2. Vista de Metraje de Productos Diamantados
\i vw_metraje_productos_diamantados.sql

-- 3. Vista Completa de Turnos para PowerBI
\i vw_turnos_completo_powerbi.sql

-- 4. Vista de Performance de Trabajadores
\i vw_trabajadores_performance.sql

-- ============================================================
-- Verificar que las vistas se crearon correctamente
-- ============================================================

SELECT 
    schemaname,
    viewname,
    viewowner,
    definition
FROM pg_views 
WHERE schemaname = 'public' 
AND viewname IN (
    'vw_horas_extras',
    'vw_metraje_productos_diamantados',
    'vw_turnos_completo_powerbi',
    'vw_trabajadores_performance'
)
ORDER BY viewname;

-- ============================================================
-- Otorgar permisos (reemplazar 'powerbi_user' con tu usuario)
-- ============================================================

-- GRANT SELECT ON public.vw_horas_extras TO powerbi_user;
-- GRANT SELECT ON public.vw_metraje_productos_diamantados TO powerbi_user;
-- GRANT SELECT ON public.vw_turnos_completo_powerbi TO powerbi_user;
-- GRANT SELECT ON public.vw_trabajadores_performance TO powerbi_user;

-- ============================================================
-- Consultas de prueba
-- ============================================================

-- Probar vista de horas extras
SELECT COUNT(*) AS total_registros FROM public.vw_horas_extras;

-- Probar vista de metraje productos
SELECT COUNT(*) AS total_productos FROM public.vw_metraje_productos_diamantados;

-- Probar vista de turnos completo
SELECT COUNT(*) AS total_turnos FROM public.vw_turnos_completo_powerbi;

-- Probar vista de trabajadores
SELECT COUNT(*) AS total_trabajadores FROM public.vw_trabajadores_performance;

COMMIT;
