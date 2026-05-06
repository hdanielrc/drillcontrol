from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import api_views
from . import auth_views
from . import views_gestion_proyectos
from . import views_stock
from . import views_consumo
from . import views_tareo          # módulo unificado V1 + V2
from . import views_headcount
from . import views_gerencia
from . import views_mantenimiento
from . import views_payroll
from .views_organigrama import organigrama_view
from .api_organigrama import (
    guardar_asignaciones_masivas, marcar_stand_by,
    guardar_guardias_conductores, eliminar_asignacion,
    guardar_asignaciones_equipos
)
# ── Tareo (todas las funciones V1 y V2 viven en views_tareo) ─────────────────
from .views_tareo import (
    # V1 / legacy
    tareo_mensual_view,
    guardar_asistencia,
    guardar_asistencias_masivas as guardar_asistencias_masivas_tareo,
    exportar_asistencias_excel,
    auto_rellenar_asistencia,
    actualizar_grupos_trabajadores,
    debug_trabajadores,
    # V2 / normalizado
    tareo_v2_mensual_view,
    api_generar_proyeccion,
    api_generar_proyeccion_todos,
    api_corregir_asistencia,
    api_guardar_dia_tareo,
    api_guardar_seleccion,
    api_obtener_maquinas,
    api_actualizar_guardia,
    tareo_v2_estadisticas,
    tareo_cierre_mensual,
    tareo_historial_trabajador,
    tareo_reporte_nomina,
    api_cerrar_mes,
    api_reabrir_mes,
    api_exportar_nomina_excel,
    api_importar_desde_v1,
    api_actualizar_turno_inicio,
)

urlpatterns = [
    # Autenticación
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Gestión de cuentas
    path('activate/<str:token>/', auth_views.activate_account, name='activate_account'),
    path('password-reset/', auth_views.request_password_reset, name='request_password_reset'),
    path('password-reset/<str:token>/', auth_views.reset_password, name='reset_password'),
    path('change-password/', auth_views.change_password, name='change_password'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Organigrama
    path('organigrama/', organigrama_view, name='organigrama'),
    path('api/organigrama/guardar-asignaciones/', guardar_asignaciones_masivas, name='api-guardar-asignaciones'),
    path('api/organigrama/marcar-stand-by/', marcar_stand_by, name='api-marcar-stand-by'),
    path('api/organigrama/guardar-guardias-conductores/', guardar_guardias_conductores, name='api-guardar-guardias-conductores'),
    path('api/organigrama/guardar-asignaciones-equipos/', guardar_asignaciones_equipos, name='api-guardar-asignaciones-equipos'),
    path('api/organigrama/eliminar-asignacion/', eliminar_asignacion, name='api-eliminar-asignacion'),
    
    # Tareo de Asistencia (V1 - Legacy)
    path('tareo/', tareo_mensual_view, name='tareo-mensual'),
    path('tareo/guardar-asistencia/', guardar_asistencia, name='tareo-guardar-asistencia'),
    path('tareo/guardar-asistencias-masivas/', guardar_asistencias_masivas_tareo, name='tareo-guardar-masivas'),
    path('tareo/auto-rellenar/', auto_rellenar_asistencia, name='tareo-auto-rellenar'),
    path('tareo/auto-rellenar-turno/', views_tareo.auto_rellenar_turno_view, name='tareo-auto-rellenar-turno'),
    path('tareo/limpiar-mes/', views_tareo.limpiar_asistencias_mes, name='tareo-limpiar-mes'),
    path('tareo/actualizar-grupos/', actualizar_grupos_trabajadores, name='tareo-actualizar-grupos'),
    path('tareo/debug-trabajadores/', debug_trabajadores, name='tareo-debug-trabajadores'),
    path('tareo/exportar-excel/', exportar_asistencias_excel, name='tareo-exportar-excel'),
    path('tareo/generar-guardias/', views_tareo.generar_guardias_automaticas, name='tareo-generar-guardias'),
    path('tareo/autocompletar-regimen/', views_tareo.autocompletar_tareo_por_regimen, name='tareo-autocompletar-regimen'),
    
    # =========================================================================
    # TAREO V2 - Sistema Normalizado con Proyección Automática
    # =========================================================================
    # Vista principal - Matriz tipo Excel con datos normalizados
    path('tareo/v2/', tareo_v2_mensual_view, name='tareo-v2-mensual'),
    
    # API para proyección mensual automática (AJAX)
    path('tareo/v2/api/generar-proyeccion/', api_generar_proyeccion, name='api-generar-proyeccion'),
    path('tareo/v2/api/generar-proyeccion-todos/', api_generar_proyeccion_todos, name='api-generar-proyeccion-todos'),
    
    # API para corrección individual de asistencia (AJAX)
    path('tareo/v2/api/corregir/', api_corregir_asistencia, name='api-corregir-asistencia'),
    
    # API para guardar asistencia por día (AJAX)
    path('tareo/v2/api/guardar-dia/', api_guardar_dia_tareo, name='api-guardar-dia-tareo'),

    # API para guardar selección arbitraria (fila / grupo) (AJAX)
    path('tareo/v2/api/guardar-seleccion/', api_guardar_seleccion, name='api-guardar-seleccion'),
    
    # API para obtener máquinas del contrato
    path('tareo/v2/api/maquinas/', api_obtener_maquinas, name='api-obtener-maquinas'),

    # API para actualizar guardia de un trabajador
    path('tareo/v2/api/actualizar-guardia/', api_actualizar_guardia, name='api-actualizar-guardia'),
    
    # Dashboard de estadísticas del tareo
    path('tareo/v2/estadisticas/', tareo_v2_estadisticas, name='tareo-v2-estadisticas'),

    # Exportador semanal (matriz + distribución por máquina)
    path('tareo/v2/exportar-semanal/', views_tareo.exportar_tareo_semanal, name='tareo-v2-exportar-semanal'),
    # Vista semanal (representación gráfica dentro de la app)
    path('tareo/v2/semana/visualizar/', views_tareo.mostrar_tareo_semanal, name='tareo-v2-semana-visualizar'),
    
    # Cierre Mensual y Auditoría
    path('tareo/v2/cierre-mensual/', tareo_cierre_mensual, name='tareo_cierre_mensual'),
    path('tareo/v2/historial/<int:trabajador_id>/', tareo_historial_trabajador, name='tareo_historial_trabajador'),
    path('tareo/v2/reporte-nomina/', tareo_reporte_nomina, name='tareo_reporte_nomina'),
    
    # APIs de Cierre
    path('tareo/v2/api/cerrar-mes/', api_cerrar_mes, name='api_cerrar_mes'),
    path('tareo/v2/api/reabrir-mes/', api_reabrir_mes, name='api_reabrir_mes'),
    path('tareo/v2/api/importar-v1/', api_importar_desde_v1, name='api_importar_desde_v1'),
    path('tareo/v2/exportar-nomina/<int:cierre_id>/', api_exportar_nomina_excel, name='api_exportar_nomina_excel'),
    path('contratos/<int:contrato_id>/turno-inicio/', api_actualizar_turno_inicio, name='api-contrato-turno-inicio'),
    
    # Trabajadores - Hub y CRUD
    path('trabajadores/hub/', views.trabajadores_hub, name='trabajadores-hub'),
    path('api/trabajadores/<int:pk>/grupo/', api_views.api_actualizar_grupo_trabajador, name='api-trabajador-grupo'),
    path('api/trabajadores/<int:pk>/maquina/', api_views.api_asignar_maquina_trabajador, name='api-trabajador-maquina'),
    path('api/trabajadores/<int:pk>/cargo-headcount/', api_views.api_set_cargo_headcount_trabajador, name='api-trabajador-cargo-headcount'),
    path('api/trabajadores/<int:pk>/fecha-inicio-labores/', api_views.api_set_fecha_inicio_labores, name='api-trabajador-fecha-inicio-labores'),
    path('trabajadores/', views.TrabajadorListView.as_view(), name='trabajador-list'),
    path('trabajadores/nuevo/', views.TrabajadorCreateView.as_view(), name='trabajador-create'),
    path('trabajadores/<int:pk>/editar/', views.TrabajadorUpdateView.as_view(), name='trabajador-update'),
    path('trabajadores/<int:pk>/eliminar/', views.TrabajadorDeleteView.as_view(), name='trabajador-delete'),
    path('trabajadores/estado-emo/', views.estado_emo_trabajadores, name='estado-emo-trabajadores'),
    path('api/emo/programar/', views.api_programar_emo, name='api-programar-emo'),
    path('api/emo/programaciones/<int:trabajador_id>/', views.api_programaciones_emo, name='api-programaciones-emo'),
    
    # Equipos - Dashboard y CRUD
    path('equipos/dashboard/', views.equipos_dashboard, name='equipos-dashboard'),
    path('equipos/', views.equipos_list, name='equipos-list'),
    path('equipos/nuevo/', views.equipo_create, name='equipo-create'),
    path('equipos/<int:pk>/editar/', views.equipo_update, name='equipo-update'),
    path('equipos/<int:pk>/eliminar/', views.equipo_delete, name='equipo-delete'),
    
    # Asignaciones de Equipos
    path('asignaciones-equipos/', views.asignaciones_equipos_list, name='asignaciones-equipos-list'),
    path('asignaciones-equipos/nueva/', views.asignacion_equipo_create, name='asignacion-equipo-create'),
    path('asignaciones-equipos/<int:pk>/editar/', views.asignacion_equipo_update, name='asignacion-equipo-update'),
    path('asignaciones-equipos/<int:pk>/eliminar/', views.asignacion_equipo_delete, name='asignacion-equipo-delete'),
    path('equipos/<int:pk>/editar/', views.equipo_update, name='equipo-update'),
    path('equipos/<int:pk>/eliminar/', views.equipo_delete, name='equipo-delete'),
    
    # Máquinas CRUD
    path('maquinas/', views.MaquinaListView.as_view(), name='maquina-list'),
    path('maquinas/nueva/', views.MaquinaCreateView.as_view(), name='maquina-create'),
    path('maquinas/<int:pk>/editar/', views.MaquinaUpdateView.as_view(), name='maquina-update'),
    path('maquinas/<int:pk>/eliminar/', views.MaquinaDeleteView.as_view(), name='maquina-delete'),
    path('maquinas/transferir/', views.transferir_maquina, name='maquina-transferir'),
    
    # Sondajes CRUD
    path('sondajes/', views.SondajeListView.as_view(), name='sondaje-list'),
    path('sondajes/seguimiento/', views.sondaje_seguimiento, name='sondaje-seguimiento'),
    path('sondajes/gantt/', views.sondaje_gantt, name='sondaje-gantt'),
    path('sondajes/nuevo/', views.SondajeCreateView.as_view(), name='sondaje-create'),
    path('sondajes/<int:pk>/editar/', views.SondajeUpdateView.as_view(), name='sondaje-update'),
    path('sondajes/<int:pk>/eliminar/', views.SondajeDeleteView.as_view(), name='sondaje-delete'),
    
    # Actividades CRUD
    path('actividades/', views.TipoActividadListView.as_view(), name='actividades-list'),
    path('actividades/nueva/', views.TipoActividadCreateView.as_view(), name='actividades-create'),
    path('actividades/<int:pk>/editar/', views.TipoActividadUpdateView.as_view(), name='actividades-update'),
    path('actividades/<int:pk>/eliminar/', views.TipoActividadDeleteView.as_view(), name='actividades-delete'),
    path('actividades/gestionar/', views.gestionar_actividades, name='gestionar-actividades'),
    path('actividades/asignar-contrato/', views.asignar_actividades_contrato, name='asignar-actividades-contrato'),
    path('contratos/<int:pk>/actividades/', views.ContratoActividadesUpdateView.as_view(), name='contrato-actividades'),
    
    # Horas Extras
    path('horas-extras/gestionar/', views.gestionar_horas_extras, name='gestionar-horas-extras'),
    path('horas-extras/reporte/', views.reporte_horas_extras, name='reporte-horas-extras'),
    
    # Tipos de Turno CRUD
    path('tipos-turno/', views.TipoTurnoListView.as_view(), name='tipo-turno-list'),
    path('tipos-turno/nuevo/', views.TipoTurnoCreateView.as_view(), name='tipo-turno-create'),
    path('tipos-turno/<int:pk>/editar/', views.TipoTurnoUpdateView.as_view(), name='tipo-turno-update'),
    path('tipos-turno/<int:pk>/eliminar/', views.TipoTurnoDeleteView.as_view(), name='tipo-turno-delete'),
    
    # Complementos CRUD
    path('complementos/', views.TipoComplementoListView.as_view(), name='complemento-list'),
    path('complementos/nuevo/', views.TipoComplementoCreateView.as_view(), name='complemento-create'),
    path('complementos/<int:pk>/editar/', views.TipoComplementoUpdateView.as_view(), name='complemento-update'),
    path('complementos/<int:pk>/eliminar/', views.TipoComplementoDeleteView.as_view(), name='complemento-delete'),
    path('complementos/reporte-metraje/', views.reporte_metraje_complementos, name='reporte-metraje-complementos'),
    
    # Aditivos CRUD
    path('aditivos/', views.TipoAditivoListView.as_view(), name='aditivo-list'),
    path('aditivos/nuevo/', views.TipoAditivoCreateView.as_view(), name='aditivo-create'),
    path('aditivos/<int:pk>/editar/', views.TipoAditivoUpdateView.as_view(), name='aditivo-update'),
    path('aditivos/<int:pk>/eliminar/', views.TipoAditivoDeleteView.as_view(), name='aditivo-delete'),
    
    # Unidades de Medida CRUD
    path('unidades/', views.UnidadMedidaListView.as_view(), name='unidad-list'),
    path('unidades/nueva/', views.UnidadMedidaCreateView.as_view(), name='unidad-create'),
    path('unidades/<int:pk>/editar/', views.UnidadMedidaUpdateView.as_view(), name='unidad-update'),
    path('unidades/<int:pk>/eliminar/', views.UnidadMedidaDeleteView.as_view(), name='unidad-delete'),
    
    # Turnos
    path('turno/nuevo/', views.crear_turno_completo, name='crear-turno-completo'),
    path('turno/<int:pk>/editar_completo/', views.crear_turno_completo, name='editar-turno-completo'),
    path('turnos/', views.listar_turnos, name='listar-turnos'),
    path('turnos/<int:pk>/', views.TurnoDetailView.as_view(), name='turno-detail'),
    # Edit uses the unified crear_turno_completo view (handles create and edit)
    path('turnos/<int:pk>/editar/', views.crear_turno_completo, name='turno-update'),
    path('turnos/<int:pk>/eliminar/', views.TurnoDeleteView.as_view(), name='turno-delete'),
    path('turnos/<int:pk>/aprobar/', views.aprobar_turno, name='turno-approve'),

    # API endpoints
    path('api/actividades/nuevo/', views.api_create_actividad, name='api-actividad-create'),
    
    # APIs Vilbragroup - Stock
    path('api/stock/productos-diamantados/', api_views.api_stock_productos_diamantados, name='api-stock-pdd'),
    path('api/stock/aditivos/', api_views.api_stock_aditivos, name='api-stock-aditivos'),
    path('almacen/stock/', api_views.vista_stock_almacen, name='vista-stock-almacen'),
    
    # APIs Sondajes
    path('api/sondaje/<int:sondaje_id>/estado/', api_views.api_sondaje_estado, name='api-sondaje-estado'),
    path('api/sondaje/<int:sondaje_id>/ultima-broca/', api_views.api_ultima_broca_sondaje, name='api-ultima-broca-sondaje'),
    path('api/sondaje/crear-rapido/', api_views.api_crear_sondaje_rapido, name='api-crear-sondaje-rapido'),
    path('api/maquina/<int:maquina_id>/ultimo-horometro/', api_views.api_ultimo_horometro_maquina, name='api-ultimo-horometro-maquina'),
    
    # APIs Tareo - Grupos y Trabajadores
    path('api/tareo/grupos-disponibles/', api_views.api_grupos_disponibles_por_fecha, name='api-grupos-disponibles'),
    path('api/tareo/trabajadores-por-grupo/', api_views.api_trabajadores_por_grupo_fecha, name='api-trabajadores-por-grupo'),
    path('api/tareo/trabajadores-por-maquina/', api_views.api_trabajadores_por_maquina, name='api-trabajadores-por-maquina'),
    
    # Abastecimiento CRUD Completo
    path('abastecimiento/', views.AbastecimientoListView.as_view(), name='abastecimiento-list'),
    path('abastecimiento/nuevo/', views.AbastecimientoCreateView.as_view(), name='abastecimiento-create'),
    path('abastecimiento/<int:pk>/', views.AbastecimientoDetailView.as_view(), name='abastecimiento-detail'),
    path('abastecimiento/<int:pk>/editar/', views.AbastecimientoUpdateView.as_view(), name='abastecimiento-update'),
    path('abastecimiento/<int:pk>/eliminar/', views.AbastecimientoDeleteView.as_view(), name='abastecimiento-delete'),

    
    # Consumo CRUD Completo
    path('consumo/', views.ConsumoStockListView.as_view(), name='consumo-list'),
    path('consumo/nuevo/', views.ConsumoStockCreateView.as_view(), name='consumo-create'),
    path('consumo/<int:pk>/editar/', views.ConsumoStockUpdateView.as_view(), name='consumo-update'),
    path('consumo/<int:pk>/eliminar/', views.ConsumoStockDeleteView.as_view(), name='consumo-delete'),
    
    # Stock y Reportes
    path('stock/disponible/', views.StockDisponibleView.as_view(), name='stock-disponible'),
    
    # Metas de Máquinas → redirigido a Programación
    path('metas/', RedirectView.as_view(pattern_name='gerencia-programacion', permanent=True), name='metas-maquina-list'),
    path('metas/gestionar/', RedirectView.as_view(pattern_name='gerencia-programacion', permanent=True), name='metas-maquina-gestionar'),
    path('metas/nueva/', RedirectView.as_view(pattern_name='gerencia-programacion', permanent=True), name='metas-maquina-create'),
    path('metas/<int:pk>/editar/', RedirectView.as_view(url='/gerencia/programacion/', permanent=True), name='metas-maquina-edit'),
    path('metas/<int:pk>/eliminar/', RedirectView.as_view(url='/gerencia/programacion/', permanent=True), name='metas-maquina-delete'),
    path('metas/<int:pk>/dividir/', RedirectView.as_view(url='/gerencia/programacion/', permanent=True), name='metas-maquina-dividir'),
    path('metas/valorizacion/', RedirectView.as_view(pattern_name='gerencia-programacion', permanent=True), name='metas-valorizacion-reporte'),
    
    # Precios Unitarios
    path('precios-unitarios/', views.precios_unitarios_list, name='precios-unitarios-list'),
    path('precios-unitarios/nuevo/', views.precios_unitarios_create, name='precios-unitarios-create'),
    path('precios-unitarios/<int:pk>/editar/', views.precios_unitarios_edit, name='precios-unitarios-edit'),
    path('precios-unitarios/<int:pk>/eliminar/', views.precios_unitarios_delete, name='precios-unitarios-delete'),
    
    # Gestión de Proyectos - Stock y Turnos
    path('gestion-proyectos/stock-turnos/', views_gestion_proyectos.gestion_proyectos_stock_turnos, name='gestion-proyectos-stock-turnos'),
    
    # =========================================================================
    # STOCK v2.0 - Dashboard con Histórico y Alertas
    # =========================================================================
    
    # Verificación de Consumos y Stock (API)
    path('consumos/verificacion/', views_consumo.lista_consumos, name='lista-consumos-api'),
    path('stock/inventario-actual/', views_consumo.inventario_actual_list, name='inventario-actual-list'),
    
    # Dashboard de Stock
    path('stock/dashboard/', views_stock.dashboard_stock, name='dashboard-stock'),
    path('stock/articulo/<int:contrato_id>/<str:codigo_articulo>/', views_stock.detalle_articulo_stock, name='detalle-articulo-stock'),
    path('stock/historial-sincronizaciones/', views_stock.historial_sincronizaciones, name='historial-sincronizaciones'),
    
    # Alertas de Stock
    path('stock/alertas/', views_stock.AlertaStockListView.as_view(), name='alertas-stock-list'),
    path('stock/alertas/<int:alerta_id>/leer/', views_stock.marcar_alerta_leida, name='alerta-stock-leer'),
    path('stock/alertas/<int:alerta_id>/resolver/', views_stock.resolver_alerta, name='alerta-stock-resolver'),
    
    # API endpoints para Stock v2.0
    path('api/stock/v2/resumen/<int:contrato_id>/', views_stock.api_resumen_stock, name='api-stock-resumen'),
    path('api/stock/v2/proyecciones/<int:contrato_id>/', views_stock.api_proyecciones_stock, name='api-stock-proyecciones'),
    path('api/stock/v2/actual/<int:contrato_id>/', views_stock.api_stock_actual, name='api-stock-actual'),
    path('api/stock/v2/tendencia/<int:contrato_id>/<str:codigo_articulo>/', views_stock.api_tendencia_articulo, name='api-stock-tendencia'),
    path('api/stock/v2/alertas/', views_stock.api_alertas_activas, name='api-alertas-activas'),
    path('api/stock/v2/sincronizar/<int:contrato_id>/', views_stock.sincronizar_stock_contrato, name='api-sincronizar-stock'),
    
    # =========================================================================
    # ABASTECIMIENTOS - Integración con API Externa
    # =========================================================================
    
    # Dashboard Control de Proyectos (Multi-Contrato)
    path('abastecimientos/control-proyectos/', views_stock.dashboard_control_proyectos_abastecimientos, name='dashboard-control-proyectos-abastecimientos'),
    
    # Lista y gestión de abastecimientos
    path('abastecimientos/', views_stock.lista_abastecimientos, name='lista-abastecimientos'),
    path('abastecimientos/<int:abastecimiento_id>/', views_stock.detalle_abastecimiento, name='detalle-abastecimiento'),
    path('abastecimientos/sincronizar/', views_stock.sincronizar_abastecimientos_manual, name='sincronizar-abastecimientos'),
    
    # Dashboard de brocas disponibles
    path('abastecimientos/brocas-disponibles/', views_stock.dashboard_brocas_disponibles, name='dashboard-brocas-disponibles'),
    
    # APIs
    path('api/abastecimiento/<int:pk>/', views.api_abastecimiento_detalle, name='api-abastecimiento-detalle'),
    
    # HEADCOUNT - Planificacion de Personal
    path('headcount/', views_headcount.headcount_dashboard, name='headcount-dashboard'),
    path('headcount/list/', views_headcount.headcount_list, name='headcount-list'),
    path('headcount/create/', views_headcount.headcount_create, name='headcount-create'),
    path('headcount/<int:pk>/update/', views_headcount.headcount_update, name='headcount-update'),
    path('headcount/<int:pk>/delete/', views_headcount.headcount_delete, name='headcount-delete'),
    path('headcount/api/maquinas/', views_headcount.get_maquinas_by_contrato, name='headcount-api-maquinas'),
    path('headcount/debug/', views_headcount.debug_headcounts, name='headcount-debug'),
    
    # GERENCIA - Dashboard Ejecutivo
    path('gerencia/', views_gerencia.gerencia_dashboard, name='gerencia-dashboard'),
    # GERENCIA - Programación Mensual
    path('gerencia/programacion/', views_gerencia.gerencia_programacion, name='gerencia-programacion'),
    path('gerencia/programacion/guardar/', views_gerencia.programacion_save, name='gerencia-programacion-save'),
    # GERENCIA - Meta por Turno (override de celda individual)
    path('gerencia/meta-turno/guardar/', views_gerencia.meta_turno_save, name='gerencia-meta-turno-save'),
    path('gerencia/meta-turno/<int:pk>/eliminar/', views_gerencia.meta_turno_delete, name='gerencia-meta-turno-delete'),
    # GERENCIA - Días por máquina (resumen tareo)
    path('gerencia/dias-maquina/', views_gerencia.dias_maquina, name='gerencia-dias-maquina'),
    
    # =========================================================================
    # MANTENIMIENTO DE MÁQUINAS
    # =========================================================================
    path('mantenimiento/', views_mantenimiento.mantenimiento_dashboard, name='mantenimiento-dashboard'),
    path('mantenimiento/maquinas/', views_mantenimiento.mantenimiento_maquinas, name='mantenimiento-maquinas'),
    path('mantenimiento/maquinas/nueva/', views_mantenimiento.mantenimiento_maquina_form, name='mantenimiento-maquina-nueva'),
    path('mantenimiento/maquinas/<int:pk>/editar/', views_mantenimiento.mantenimiento_maquina_form, name='mantenimiento-maquina-edit'),
    path('mantenimiento/maquinas/<int:pk>/', views_mantenimiento.mantenimiento_maquina_detalle, name='mantenimiento-maquina-detalle'),
    path('mantenimiento/maquinas/<int:maquina_pk>/bitacora/nueva/', views_mantenimiento.bitacora_form, name='bitacora-nueva'),
    path('mantenimiento/maquinas/<int:maquina_pk>/bitacora/<int:pk>/editar/', views_mantenimiento.bitacora_form, name='bitacora-edit'),
    path('mantenimiento/bitacora/<int:pk>/eliminar/', views_mantenimiento.bitacora_delete, name='bitacora-delete'),
    path('mantenimiento/traslado/', views_mantenimiento.mantenimiento_traslado, name='mantenimiento-traslado'),
    path('mantenimiento/traslado/<int:pk>/', views_mantenimiento.mantenimiento_traslado, name='mantenimiento-traslado-maquina'),
    path('mantenimiento/maquinas/<int:pk>/estado/', views_mantenimiento.api_cambiar_estado_maquina, name='api-cambiar-estado-maquina'),

    # HISTORIAL DE BROCAS - Trazabilidad y Seguimiento
    path('historial-brocas/', views.historial_brocas_lista, name='historial-brocas-lista'),
    path('historial-brocas/<str:serie>/', views.historial_broca_detalle, name='historial-broca-detalle'),
    path('historial-brocas/<str:serie>/marcar-quemada/', views.historial_broca_marcar_quemada, name='historial-broca-marcar-quemada'),

    # =========================================================================
    # PLANILLA - CÁLCULO DE BONOS
    # =========================================================================
    path('planilla/', views_payroll.planilla_hub, name='planilla-hub'),
    # Tipos de Bono
    path('planilla/tipos-bono/', views_payroll.tipo_bono_list, name='planilla-tipo-bono-list'),
    path('planilla/tipos-bono/crear/', views_payroll.tipo_bono_create, name='planilla-tipo-bono-create'),
    path('planilla/tipos-bono/<int:pk>/editar/', views_payroll.tipo_bono_update, name='planilla-tipo-bono-edit'),
    path('planilla/conceptos/<int:concepto_pk>/criterios/', views_payroll.criterios_concepto, name='planilla-criterios-concepto'),
    # Configuraciones por Contrato
    path('planilla/configuraciones/', views_payroll.config_bono_list, name='planilla-config-bono-list'),
    path('planilla/configuraciones/crear/', views_payroll.config_bono_create, name='planilla-config-bono-create'),
    path('planilla/configuraciones/<int:pk>/editar/', views_payroll.config_bono_edit, name='planilla-config-bono-edit'),
    # Períodos
    path('planilla/periodos/', views_payroll.periodo_list, name='planilla-periodo-list'),
    path('planilla/periodos/abrir/', views_payroll.periodo_abrir, name='planilla-periodo-abrir'),
    path('planilla/periodos/<int:pk>/', views_payroll.periodo_detalle, name='planilla-periodo-detalle'),
    path('planilla/periodos/<int:pk>/calcular/', views_payroll.periodo_calcular, name='planilla-periodo-calcular'),
    path('planilla/periodos/<int:pk>/aprobar/', views_payroll.periodo_aprobar, name='planilla-periodo-aprobar'),
    path('planilla/periodos/<int:pk>/validar/', views_payroll.periodo_validar, name='planilla-periodo-validar'),
    path('planilla/periodos/<int:pk>/conciliacion/', views_payroll.periodo_conciliacion, name='planilla-periodo-conciliacion'),
    path('planilla/periodos/<int:pk>/trabajador/<int:trabajador_pk>/', views_payroll.periodo_resumen_trabajador, name='planilla-resumen-trabajador'),
    path('planilla/periodos/<int:pk>/boleta/<int:trabajador_pk>/', views_payroll.periodo_boleta, name='planilla-boleta'),
    path('planilla/presupuesto/', views_payroll.presupuesto_planilla, name='planilla-presupuesto'),
    # Evaluaciones
    path('planilla/bono/<int:bono_pk>/evaluar/', views_payroll.evaluar_bono, name='planilla-evaluar-bono'),
    path('planilla/periodos/<int:periodo_pk>/tipo/<int:tipo_bono_pk>/evaluar/', views_payroll.evaluar_bono_masivo, name='planilla-evaluar-masivo'),
    # APIs
    path('planilla/api/conceptos/<int:tipo_bono_pk>/', views_payroll.api_conceptos_tipo_bono, name='planilla-api-conceptos'),
    path('planilla/periodos/<int:periodo_pk>/exportar/', views_payroll.api_exportar_bonos_excel, name='planilla-exportar-excel'),
    # Demo standalone del cuadro de evaluación
    path('planilla/cuadro/demo/', views_payroll.cuadro_evaluacion_demo, name='planilla-cuadro-demo'),
    # Cuadro de Evaluación (formato Excel)
    path('planilla/cuadro/<int:tipo_bono_pk>/', views_payroll.cuadro_evaluacion, name='planilla-cuadro'),
    path('planilla/cuadro/<int:tipo_bono_pk>/guardar/', views_payroll.cuadro_guardar, name='planilla-cuadro-guardar'),
    path('planilla/cuadro/<int:tipo_bono_pk>/calcular/', views_payroll.cuadro_calcular, name='planilla-cuadro-calcular'),
    # Conceptos Globales
    path('planilla/conceptos-globales/', views_payroll.conceptos_globales, name='planilla-conceptos-globales'),
    path('planilla/conceptos-globales/guardar/', views_payroll.conceptos_globales_guardar, name='planilla-conceptos-globales-guardar'),
    path('planilla/conceptos-globales/calcular/', views_payroll.conceptos_globales_calcular, name='planilla-conceptos-globales-calcular'),
    path('planilla/api/conceptos-globales/<int:contrato_id>/<int:anio>/<int:mes>/', views_payroll.api_conceptos_globales_contrato, name='planilla-api-conceptos-globales'),
    path('planilla/api/diagnostico-conceptos/', views_payroll.api_diagnostico_conceptos, name='planilla-api-diagnostico-conceptos'),
    # Estructura Salarial
    path('planilla/estructura-salarial/', views_payroll.estructura_salarial_list, name='planilla-estructura-salarial-list'),
    path('planilla/estructura-salarial/crear/', views_payroll.estructura_salarial_create, name='planilla-estructura-salarial-create'),
    path('planilla/estructura-salarial/<int:pk>/editar/', views_payroll.estructura_salarial_edit, name='planilla-estructura-salarial-edit'),
    path('planilla/estructura-salarial/<int:pk>/historial/', views_payroll.estructura_salarial_historial, name='planilla-estructura-salarial-historial'),
    # DEPRECADO — AsignacionEstructuraSalarial reemplazado por lookup automático por máquina
    # path('planilla/asignacion-estructura/', views_payroll.asignacion_estructura_list, name='planilla-asignacion-estructura-list'),
    # path('planilla/asignacion-estructura/<int:trabajador_pk>/asignar/', views_payroll.asignacion_estructura_asignar, name='planilla-asignacion-estructura-asignar'),
    # path('planilla/asignacion-estructura/<int:pk>/desactivar/', views_payroll.asignacion_estructura_desactivar, name='planilla-asignacion-estructura-desactivar'),
    path('planilla/api/estructuras-por-cargo/', views_payroll.api_estructuras_por_cargo, name='planilla-api-estructuras-por-cargo'),
    path('planilla/api/ctr-por-contrato/<int:contrato_id>/', views_payroll.api_ctr_por_contrato, name='planilla-api-ctr-contrato'),
    path('planilla/api/maquinas-por-contrato/<int:contrato_id>/', views_payroll.api_maquinas_por_contrato, name='planilla-api-maquinas-contrato'),
    path('planilla/api/cargos-por-ctr/<int:contrato_id>/<int:ctr_id>/', views_payroll.api_cargos_por_ctr, name='planilla-api-cargos-ctr'),
    path('planilla/api/cargos-activos/<int:contrato_id>/', views_payroll.api_cargos_activos_contrato, name='planilla-api-cargos-activos'),
    path('planilla/api/bonificacion-area/', views_payroll.api_bonificacion_area_cargo, name='planilla-api-bonificacion-area'),
    path('planilla/api/trabajadores-por-cargo/', views_payroll.api_trabajadores_por_cargo, name='planilla-api-trabajadores-por-cargo'),
]