TAREO ENGINE 3.0 - Plan de Refactorización (resumen)

Objetivo
--------
Refactorizar el módulo de tareo para eliminar lógica mutable y ambigua, y sustituirla
por un motor determinista basado en aritmética modular (TareoEngine).

Alcance
-------
- Eliminar funciones que calculan estados consultando días previos o iterando
  manualmente sobre registros en `views.py`, `utils/tareo_service.py` y `models.py`.
- Consolidar origen de verdad para cálculos en `TareoEngine` (archivo `tareo_service.py`).
- Mantener `AsistenciaDiaria` como la tabla de referencia para escrituras.

Pasos propuestos
----------------
1) Auditoría de puntos de escritura
   - Buscar y listar todos los lugares donde se escriben registros en
     `AsistenciaTrabajador` (V1) y `AsistenciaDiaria` (V2). Marcar como
     "solo-lectura" los endpoints que aún usan V1.

2) Establecer `TareoEngine` como la única fuente de cálculo
   - Implementar y testear la clase `TareoEngine` (ya añadida).
   - Actualizar vistas y servicios para usar exclusivamente `TareoEngine` cuando
     se calcule un estado determinista.

3) Migración de datos (Dry-run primero)
   - Ejecutar `TareoService.importar_desde_v1(contrato, fecha_inicio, fecha_fin, usuario, sobrescribir_proyecciones=False)`
     para generar un reporte de cuántos registros faltarían y cuántos colisionan.
   - Revisar diferencias y tomar decisiones (mantener correcciones manuales: `es_proyeccion=False`).
   - Aplicar migración real con `sobrescribir_proyecciones=True` tras validación.

4) Limpieza de código
   - Eliminar funciones y bloques que: hacen cálculos por inspeccionar días previos,
     mantienen contadores manuales o dependen de orden de ejecución.
   - Dejar únicamente adaptadores: endpoints que reciben correcciones manuales y las
     persisten en `AsistenciaDiaria` con `es_proyeccion=False`.

5) Pruebas y despliegue
   - Añadir tests unitarios para `TareoEngine.estado_para_fecha` y `proyectar_rango`.
   - Ejecutar staging con dataset real y validar visualmente (UI) durante 1 ciclo.
   - Desplegar a producción fuera de horario crítico.

Reglas clave
-----------
- Determinismo absoluto: misma fecha + misma guardia -> siempre mismo estado.
- `dia_cambio_guardia` es la ancla canónica. Si no está configurado, usar la
  `created_at` del contrato o 2024-01-01.
- Nunca sobreescribir `es_proyeccion=False` sin intervención manual.

Notas finales
------------
Este plan minimiza la lógica ad-hoc y deja la responsabilidad de decisión al
usuario cuando exista conflicto (registros manuales vs proyecciones). Las pruebas
unitarias y la migración dry-run son críticas antes de eliminar cualquier código
legacy.
