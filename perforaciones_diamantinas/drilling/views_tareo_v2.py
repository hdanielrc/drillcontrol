"""
=============================================================================
VISTAS PARA TAREO V2 - Modelo Normalizado con Pivot en Frontend
=============================================================================

Este módulo implementa la visualización tipo matriz (Excel) sobre el modelo
vertical AsistenciaDiaria, utilizando formsets de Django para edición masiva.

Arquitectura:
- Backend: Datos verticales (empleado, fecha, estado)
- Frontend: Transformación a matriz horizontal (estilo Excel)
- Formularios: ModelFormSet para edición masiva eficiente

Autor: Sistema DrillControl
Fecha: Enero 2026
=============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.forms import modelformset_factory, ModelForm
from datetime import datetime, timedelta, date
from calendar import monthrange
import json

from ..models import Contrato, Trabajador, AsistenciaDiaria
from ..utils.tareo_service import TareoService


# =============================================================================
# FORMULARIO PARA ASISTENCIA DIARIA
# =============================================================================
class AsistenciaDiariaForm(ModelForm):
    """
    Formulario individual para cada celda de la matriz de asistencia.
    Incluye validaciones y lógica de negocio específica.
    """
    class Meta:
        model = AsistenciaDiaria
        fields = ['empleado', 'fecha', 'estado', 'observaciones']
        widgets = {
            'observaciones': {'attrs': {'class': 'form-control', 'rows': 1}},
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deshabilitar campos que no deben editarse directamente
        self.fields['empleado'].widget.attrs['readonly'] = True
        self.fields['fecha'].widget.attrs['readonly'] = True


# =============================================================================
# VISTA PRINCIPAL: TAREO MENSUAL CON MATRIZ
# =============================================================================
@login_required
def tareo_v2_mensual_view(request):
    """
    Vista principal del Tareo V2 con arquitectura normalizada.
    
    Flujo:
    1. GET: Consulta datos verticales y los transforma a matriz para el template
    2. POST: Recibe formset, valida y actualiza masivamente en BD vertical
    
    Features:
    - Proyección automática mensual
    - Edición masiva con formsets
    - Renderizado eficiente para 70+ empleados
    - Navegación por meses
    """
    user = request.user
    
    # =========================================================================
    # 1. VALIDACIÓN DE PERMISOS
    # =========================================================================
    if not user.can_manage_contract_users():
        messages.error(request, 'No tienes permisos para gestionar el tareo de asistencia')
        return redirect('dashboard')
    
    # =========================================================================
    # 2. DETERMINAR CONTRATO
    # =========================================================================
    if user.has_access_to_all_contracts():
        contrato_id = request.GET.get('contrato')
        if contrato_id:
            contrato = get_object_or_404(Contrato, id=contrato_id, estado='ACTIVO')
        else:
            contrato = Contrato.objects.filter(estado='ACTIVO').first()
        contratos_disponibles = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    else:
        contrato = user.contrato
        contratos_disponibles = None
    
    if not contrato:
        messages.warning(request, 'No hay contratos activos disponibles')
        return redirect('dashboard')
    
    # =========================================================================
    # 3. CALCULAR RANGO DE FECHAS (MES COMPLETO)
    # =========================================================================
    mes_offset = int(request.GET.get('mes_offset', 0))
    
    # Calcular el mes a mostrar
    hoy = datetime.now().date()
    fecha_base = hoy
    
    # Navegación por meses
    if mes_offset != 0:
        for _ in range(abs(mes_offset)):
            if mes_offset > 0:
                # Mes siguiente
                if fecha_base.month == 12:
                    fecha_base = fecha_base.replace(year=fecha_base.year + 1, month=1, day=1)
                else:
                    fecha_base = fecha_base.replace(month=fecha_base.month + 1, day=1)
            else:
                # Mes anterior
                if fecha_base.month == 1:
                    fecha_base = fecha_base.replace(year=fecha_base.year - 1, month=12, day=1)
                else:
                    fecha_base = fecha_base.replace(month=fecha_base.month - 1, day=1)
    
    # Primer y último día del mes
    fecha_inicio = fecha_base.replace(day=1)
    num_dias = monthrange(fecha_inicio.year, fecha_inicio.month)[1]
    fecha_fin = date(fecha_inicio.year, fecha_inicio.month, num_dias)
    
    # Nombre del período para mostrar
    meses_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    nombre_periodo = f"{meses_es[fecha_inicio.month]} {fecha_inicio.year}"
    
    # =========================================================================
    # 4. GENERAR LISTA DE DÍAS DEL MES
    # =========================================================================
    dias_rango = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        nombres_dias = {
            0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue', 
            4: 'Vie', 5: 'Sáb', 6: 'Dom'
        }
        dias_rango.append({
            'fecha': fecha_actual,
            'dia': fecha_actual.day,
            'nombre_dia': nombres_dias[fecha_actual.weekday()],
            'es_domingo': fecha_actual.weekday() == 6,
            'es_sabado': fecha_actual.weekday() == 5,
        })
        fecha_actual += timedelta(days=1)
    
    # =========================================================================
    # 5. PROCESAMIENTO POST (GUARDAR CAMBIOS)
    # =========================================================================
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Parsear datos del formulario
                asistencias_data = []
                
                for key, value in request.POST.items():
                    if key.startswith('estado_'):
                        # Formato: estado_trabajadorID_YYYY-MM-DD
                        parts = key.split('_')
                        if len(parts) == 4:
                            _, trabajador_id, anio_str, mes_dia_str = parts
                            fecha_str = f"{anio_str}-{mes_dia_str}"
                            
                            try:
                                fecha_asistencia = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                                observaciones_key = f"observaciones_{trabajador_id}_{anio_str}_{mes_dia_str}"
                                observaciones = request.POST.get(observaciones_key, '')
                                
                                asistencias_data.append({
                                    'empleado_id': int(trabajador_id),
                                    'fecha': fecha_asistencia,
                                    'estado': value,
                                    'observaciones': observaciones
                                })
                            except ValueError:
                                continue
                
                # Actualización masiva usando el servicio
                resultado = TareoService.actualizar_masivo_desde_formset(
                    asistencias_data,
                    user
                )
                
                # Mensajes de resultado
                if resultado['errores']:
                    messages.warning(
                        request,
                        f"Guardado parcialmente. Errores: {len(resultado['errores'])}"
                    )
                else:
                    messages.success(
                        request,
                        f"Tareo guardado exitosamente. "
                        f"Actualizados: {resultado['actualizados']}, "
                        f"Creados: {resultado['creados']}"
                    )
                
                # Redirigir para evitar reenvío de formulario
                return redirect(f"{request.path}?contrato={contrato.id}&mes_offset={mes_offset}")
                
        except Exception as e:
            messages.error(request, f"Error al guardar: {str(e)}")
    
    # =========================================================================
    # 6. OBTENER DATOS PARA VISUALIZACIÓN (GET)
    # =========================================================================
    # Usar el servicio para obtener matriz pivoteada
    matriz_tareo = TareoService.obtener_matriz_tareo(contrato, fecha_inicio, fecha_fin)
    
    # =========================================================================
    # 7. CONTEXTO PARA EL TEMPLATE
    # =========================================================================
    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'nombre_periodo': nombre_periodo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'dias_rango': dias_rango,
        'matriz_tareo': matriz_tareo,
        'mes_offset': mes_offset,
        'estados_choices': AsistenciaDiaria.ESTADO_CHOICES,
        'mes_actual': fecha_inicio.month,
        'anio_actual': fecha_inicio.year,
    }
    
    return render(request, 'drilling/tareo/tareo_v2_mensual.html', context)


# =============================================================================
# API PARA PROYECCIÓN MENSUAL (AJAX)
# =============================================================================
@login_required
@require_http_methods(["POST"])
def api_generar_proyeccion(request):
    """
    Endpoint AJAX para generar proyección mensual automática.
    
    POST params:
        - contrato_id: ID del contrato
        - anio: Año de la proyección
        - mes: Mes de la proyección
        - sobrescribir: Boolean, si True elimina proyecciones previas
    
    Returns:
        JSON con estadísticas de la operación
    """
    try:
        # Validar permisos
        if not request.user.can_manage_contract_users():
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para esta operación'
            }, status=403)
        
        # Obtener parámetros
        contrato_id = request.POST.get('contrato_id')
        anio = int(request.POST.get('anio'))
        mes = int(request.POST.get('mes'))
        sobrescribir = request.POST.get('sobrescribir', 'false').lower() == 'true'
        
        # Validar contrato
        contrato = get_object_or_404(Contrato, id=contrato_id, estado='ACTIVO')
        
        # Ejecutar proyección
        resultado = TareoService.generar_proyeccion_mensual(
            anio=anio,
            mes=mes,
            contrato=contrato,
            sobrescribir=sobrescribir
        )
        
        return JsonResponse({
            'success': True,
            'data': resultado
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# API PARA CORRECCIÓN INDIVIDUAL (AJAX)
# =============================================================================
@login_required
@require_http_methods(["POST"])
def api_corregir_asistencia(request):
    """
    Endpoint AJAX para corrección individual de una asistencia.
    
    POST params (JSON):
        - empleado_id: ID del trabajador
        - fecha: Fecha en formato YYYY-MM-DD
        - estado: Nuevo estado
        - observaciones: Observaciones opcionales
    
    Returns:
        JSON con el registro actualizado
    """
    try:
        # Validar permisos
        if not request.user.can_manage_contract_users():
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para esta operación'
            }, status=403)
        
        # Parsear datos JSON
        data = json.loads(request.body)
        empleado_id = data.get('empleado_id')
        fecha_str = data.get('fecha')
        estado = data.get('estado')
        observaciones = data.get('observaciones', '')
        
        # Validar fecha
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        # Ejecutar corrección
        asistencia = TareoService.corregir_asistencia(
            empleado_id=empleado_id,
            fecha=fecha,
            nuevo_estado=estado,
            usuario=request.user,
            observaciones=observaciones
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': asistencia.id,
                'estado': asistencia.estado,
                'estado_display': asistencia.get_estado_display(),
                'es_proyeccion': asistencia.es_proyeccion
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# VISTA DE ESTADÍSTICAS (DASHBOARD)
# =============================================================================
@login_required
def tareo_v2_estadisticas(request):
    """
    Vista de estadísticas y resumen del tareo mensual.
    
    Muestra:
    - Total de días trabajados vs proyectados
    - Ausentismos por tipo
    - Trabajadores por guardia
    - Gráficos de tendencia
    """
    user = request.user
    
    # Determinar contrato
    if user.has_access_to_all_contracts():
        contrato_id = request.GET.get('contrato')
        contrato = get_object_or_404(Contrato, id=contrato_id, estado='ACTIVO') if contrato_id else None
        contratos_disponibles = Contrato.objects.filter(estado='ACTIVO')
    else:
        contrato = user.contrato
        contratos_disponibles = None
    
    if not contrato:
        messages.warning(request, 'Seleccione un contrato')
        return redirect('dashboard')
    
    # Calcular estadísticas del mes actual
    hoy = date.today()
    primer_dia_mes = hoy.replace(day=1)
    
    # Query de asistencias del mes
    asistencias_mes = AsistenciaDiaria.objects.filter(
        empleado__contrato=contrato,
        fecha__gte=primer_dia_mes,
        fecha__lte=hoy
    )
    
    # Estadísticas básicas
    total_registros = asistencias_mes.count()
    proyecciones = asistencias_mes.filter(es_proyeccion=True).count()
    correcciones = asistencias_mes.filter(es_proyeccion=False).count()
    
    # Por estado
    stats_por_estado = {}
    for estado_code, estado_label in AsistenciaDiaria.ESTADO_CHOICES:
        count = asistencias_mes.filter(estado=estado_code).count()
        if count > 0:
            stats_por_estado[estado_label] = count
    
    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'total_registros': total_registros,
        'proyecciones': proyecciones,
        'correcciones': correcciones,
        'stats_por_estado': stats_por_estado,
        'mes_actual': primer_dia_mes,
    }
    
    return render(request, 'drilling/tareo/tareo_v2_estadisticas.html', context)
