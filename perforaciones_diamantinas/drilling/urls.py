from django.urls import path
from . import views
from . import api_views
from . import auth_views
from .views_organigrama import organigrama_view
from .api_organigrama import (
    guardar_asignaciones_masivas, marcar_stand_by, 
    guardar_guardias_conductores, eliminar_asignacion,
    guardar_asignaciones_equipos
)
from .views_tareo import tareo_mensual_view, guardar_asistencia, guardar_asistencias_masivas as guardar_asistencias_masivas_tareo, exportar_asistencias_excel

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
    
    # Tareo de Asistencia
    path('tareo/', tareo_mensual_view, name='tareo-mensual'),
    path('tareo/guardar-asistencia/', guardar_asistencia, name='tareo-guardar-asistencia'),
    path('tareo/guardar-asistencias-masivas/', guardar_asistencias_masivas_tareo, name='tareo-guardar-masivas'),
    path('tareo/exportar-excel/', exportar_asistencias_excel, name='tareo-exportar-excel'),
    
    # Trabajadores - Hub y CRUD
    path('trabajadores/hub/', views.trabajadores_hub, name='trabajadores-hub'),
    path('trabajadores/', views.TrabajadorListView.as_view(), name='trabajador-list'),
    path('trabajadores/nuevo/', views.TrabajadorCreateView.as_view(), name='trabajador-create'),
    path('trabajadores/<int:pk>/editar/', views.TrabajadorUpdateView.as_view(), name='trabajador-update'),
    path('trabajadores/<int:pk>/eliminar/', views.TrabajadorDeleteView.as_view(), name='trabajador-delete'),
    
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
    
    # Abastecimiento CRUD Completo
    path('abastecimiento/', views.AbastecimientoListView.as_view(), name='abastecimiento-list'),
    path('abastecimiento/nuevo/', views.AbastecimientoCreateView.as_view(), name='abastecimiento-create'),
    path('abastecimiento/<int:pk>/', views.AbastecimientoDetailView.as_view(), name='abastecimiento-detail'),
    path('abastecimiento/<int:pk>/editar/', views.AbastecimientoUpdateView.as_view(), name='abastecimiento-update'),
    path('abastecimiento/<int:pk>/eliminar/', views.AbastecimientoDeleteView.as_view(), name='abastecimiento-delete'),
    path('abastecimiento/importar/', views.importar_abastecimiento_excel, name='importar-abastecimiento'),
    
    # Consumo CRUD Completo
    path('consumo/', views.ConsumoStockListView.as_view(), name='consumo-list'),
    path('consumo/nuevo/', views.ConsumoStockCreateView.as_view(), name='consumo-create'),
    path('consumo/<int:pk>/editar/', views.ConsumoStockUpdateView.as_view(), name='consumo-update'),
    path('consumo/<int:pk>/eliminar/', views.ConsumoStockDeleteView.as_view(), name='consumo-delete'),
    
    # Stock y Reportes
    path('stock/disponible/', views.StockDisponibleView.as_view(), name='stock-disponible'),
    
    # Metas de Máquinas
    path('metas/', views.metas_maquina_list, name='metas-maquina-list'),
    path('metas/gestionar/', views.metas_maquina_gestionar, name='metas-maquina-gestionar'),
    path('metas/nueva/', views.metas_maquina_create, name='metas-maquina-create'),
    path('metas/<int:pk>/editar/', views.metas_maquina_edit, name='metas-maquina-edit'),
    path('metas/<int:pk>/eliminar/', views.metas_maquina_delete, name='metas-maquina-delete'),
    path('metas/<int:pk>/dividir/', views.metas_maquina_dividir, name='metas-maquina-dividir'),
    path('metas/valorizacion/', views.metas_valorizacion_reporte, name='metas-valorizacion-reporte'),
    
    # Precios Unitarios
    path('precios-unitarios/', views.precios_unitarios_list, name='precios-unitarios-list'),
    path('precios-unitarios/nuevo/', views.precios_unitarios_create, name='precios-unitarios-create'),
    path('precios-unitarios/<int:pk>/editar/', views.precios_unitarios_edit, name='precios-unitarios-edit'),
    path('precios-unitarios/<int:pk>/eliminar/', views.precios_unitarios_delete, name='precios-unitarios-delete'),
    
    # APIs
    path('api/abastecimiento/<int:pk>/', views.api_abastecimiento_detalle, name='api-abastecimiento-detalle'),
]