"""
Vistas para el tareo de asistencia de trabajadores
Permite a los managers de contrato registrar la asistencia diaria

Formato de Exportación:
- Formato completo con 3 hojas (Tareo, Leyenda, Informe)
- Incluye totalizadores y estadísticas detalladas
- Agrupación por semanas y resúmenes por trabajador
"""
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Count
from datetime import datetime, timedelta, date
from calendar import monthrange
from openpyxl import Workbook
import json
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from .models import Contrato, Trabajador, AsistenciaTrabajador
import json
import locale

# Configurar locale para español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except:
        pass  # Usar locale por defecto si no se puede configurar español


@login_required
def tareo_mensual_view(request):
    """Vista principal del tareo por semanas/rango personalizado"""
    user = request.user
    
    # Verificar permisos (solo managers de contrato y superiores)
    if not user.can_manage_contract_users():
        messages.error(request, 'No tienes permisos para gestionar el tareo de asistencia')
        return redirect('dashboard')
    
    # Determinar contrato
    if user.has_access_to_all_contracts():
        contrato_id = request.GET.get('contrato')
        if contrato_id:
            try:
                contrato = Contrato.objects.get(id=contrato_id, estado='ACTIVO')
            except Contrato.DoesNotExist:
                messages.error(request, 'Contrato no encontrado')
                contrato = None
        else:
            contrato = Contrato.objects.filter(estado='ACTIVO').first()
        contratos_disponibles = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    else:
        contrato = user.contrato
        contratos_disponibles = None
    
    if not contrato:
        messages.warning(request, 'No hay contratos activos disponibles')
        return redirect('dashboard')
    
    # NUEVA LÓGICA: Siempre mostrar mes completo, navegación por meses
    mes_offset = int(request.GET.get('mes_offset', 0))
    
    # Calcular el mes a mostrar
    hoy = datetime.now().date()
    if mes_offset == 0:
        # Mes actual
        fecha_base = hoy
    else:
        # Agregar/restar meses
        fecha_base = hoy
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
    
    # Calcular primer y último día del mes operativo (26 al 25)
    mes_anterior = fecha_base.month - 1 if fecha_base.month > 1 else 12
    anio_anterior = fecha_base.year if fecha_base.month > 1 else fecha_base.year - 1
    
    fecha_inicio = date(anio_anterior, mes_anterior, 26)
    fecha_fin = date(fecha_base.year, fecha_base.month, 25)
    dias_a_mostrar = (fecha_fin - fecha_inicio).days + 1
    
    # Nombre del período (usar el mes operativo objetivo)
    meses_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    nombre_periodo = f"{meses_es[fecha_base.month]} {fecha_base.year}"
    
    # Generar lista de días del rango
    dias_rango = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        # Nombres de días en español
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
    
    # Obtener trabajadores activos del contrato
    from django.db.models import Case, When, Value, IntegerField as IntF
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).select_related('maquina_asignada').annotate(
        grupo_ord=Case(
            When(grupo='LINEA_MANDO',          then=Value(1)),
            When(grupo='OPERADORES',            then=Value(2)),
            When(grupo='SERVICIOS_GEOLOGICOS',  then=Value(3)),
            When(grupo='PERSONAL_AUXILIAR',     then=Value(4)),
            default=Value(5),
            output_field=IntF()
        ),
        cargo_ord=Case(
            When(cargo__icontains='RESIDENTE',  then=Value(1)),
            When(cargo__icontains='JEFE',       then=Value(2)),
            When(cargo__icontains='SUPERVISOR', then=Value(3)),
            When(cargo__icontains='INGENIERO',  then=Value(4)),
            When(cargo__icontains='PERFORISTA', then=Value(1)),
            When(cargo__icontains='AYUDANTE',   then=Value(2)),
            default=Value(9),
            output_field=IntF()
        )
    ).order_by('grupo_ord', 'guardia_asignada', 'cargo_ord', 'apepat', 'nombres')
    
    # Obtener asistencias del rango
    asistencias = AsistenciaTrabajador.objects.filter(
        trabajador__contrato=contrato,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    ).select_related('trabajador')
    
    # Crear diccionario de asistencias: {trabajador_id: {fecha: estado}}
    asistencias_dict = {}
    for asist in asistencias:
        if asist.trabajador.id not in asistencias_dict:
            asistencias_dict[asist.trabajador.id] = {}
        asistencias_dict[asist.trabajador.id][asist.fecha] = {
            'estado': asist.estado,
            'estado_display': asist.get_estado_display(),
            'tipo': asist.tipo,
            'tipo_display': asist.get_tipo_display(),
            'observaciones': asist.observaciones
        }
    
    # Combinar trabajadores con sus asistencias y agrupar por campo `grupo`
    GRUPO_META = {
        'LINEA_MANDO':         {'nombre': 'Línea de Mando',       'order': 1},
        'OPERADORES':          {'nombre': 'Operadores',            'order': 2},
        'SERVICIOS_GEOLOGICOS':{'nombre': 'Servicios Geológicos',  'order': 3},
        'PERSONAL_AUXILIAR':   {'nombre': 'Personal Auxiliar',     'order': 4},
        '__STAND_BY__':        {'nombre': 'Personal Stand By',     'order': 5},
        '__SIN_GRUPO__':       {'nombre': 'Sin Grupo Asignado',    'order': 6},
    }

    trabajadores_por_grupo = {}

    for trabajador in trabajadores:
        if trabajador.es_standby:
            primary_key = '__STAND_BY__'
        else:
            primary_key = trabajador.grupo if trabajador.grupo else '__SIN_GRUPO__'
        guardia_key = trabajador.guardia_asignada if trabajador.guardia_asignada else 'SIN_GUARDIA'

        if primary_key not in trabajadores_por_grupo:
            meta = GRUPO_META.get(primary_key, {'nombre': primary_key, 'order': 99})
            trabajadores_por_grupo[primary_key] = {
                'nombre': meta['nombre'],
                'order': meta['order'],
                'guardias': {}
            }

        if guardia_key not in trabajadores_por_grupo[primary_key]['guardias']:
            trabajadores_por_grupo[primary_key]['guardias'][guardia_key] = {
                'nombre': f"Guardia {guardia_key}" if guardia_key != 'SIN_GUARDIA' else 'Sin Guardia',
                'trabajadores': []
            }

        # Preparar asistencias del trabajador
        asistencias_trabajador = []
        for dia_info in dias_rango:
            fecha = dia_info['fecha']
            asist_dia = asistencias_dict.get(trabajador.id, {}).get(fecha)
            
            # Celda bloqueada si la fecha es anterior al inicio de labores del trabajador
            bloqueada = bool(trabajador.fecha_inicio_labores and fecha < trabajador.fecha_inicio_labores)

            # Calcular estado sugerido si no hay asistencia (solo celdas no bloqueadas)
            estado_sugerido = None
            if not asist_dia and not bloqueada:
                estado_sugerido = trabajador.calcular_estado_regimen(fecha)

            asistencias_trabajador.append({
                'fecha': fecha,
                'bloqueada': bloqueada,
                'estado': asist_dia['estado'] if asist_dia else None,
                'estado_sugerido': estado_sugerido,
                'estado_display': asist_dia['estado_display'] if asist_dia else '-',
                'tipo': asist_dia['tipo'] if asist_dia else 'PAGABLE',
                'tipo_display': asist_dia['tipo_display'] if asist_dia else 'Pagable',
                'observaciones': asist_dia['observaciones'] if asist_dia else '',
                'es_domingo': dia_info['es_domingo'],
                'es_sabado': dia_info['es_sabado']
            })
        
        trabajadores_por_grupo[primary_key]['guardias'][guardia_key]['trabajadores'].append({
            'trabajador': trabajador,
            'asistencias': asistencias_trabajador
        })
    
    # 3. Construir lista ordenada final
    grupos_ordenados = []

    ordered_keys = sorted(
        trabajadores_por_grupo.keys(),
        key=lambda k: trabajadores_por_grupo[k]['order']
    )

    for grupo_key in ordered_keys:
        grupo_data = trabajadores_por_grupo[grupo_key]

        # Ordenar guardias (A, B, C, luego sin guardia)
        guardias_ordenadas = []
        for guardia_key in ['A', 'B', 'C', 'SIN_GUARDIA']:
            if guardia_key in grupo_data['guardias']:
                guardia_info = grupo_data['guardias'][guardia_key]
                guardias_ordenadas.append({
                    'key': guardia_key,
                    'nombre': guardia_info['nombre'],
                    'trabajadores': guardia_info['trabajadores']
                })

        grupos_ordenados.append({
            'key': grupo_key,
            'nombre': grupo_data['nombre'],
            'guardias': guardias_ordenadas,
            'total_trabajadores': sum(len(g['trabajadores']) for g in guardias_ordenadas)
        })

    
    # Contexto para el template
    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'nombre_periodo': nombre_periodo,
        'dias_rango': dias_rango,
        'grupos_ordenados': grupos_ordenados,
        'total_trabajadores': trabajadores.count(),
        'total_dias': dias_a_mostrar,
        'estados_asistencia': AsistenciaTrabajador.ESTADO_ASISTENCIA_CHOICES,
        'mes_offset': mes_offset,
    }
    
    return render(request, 'drilling/tareo/mensual.html', context)


@login_required
@require_http_methods(["POST"])
def guardar_asistencia(request):
    """API para guardar asistencia individual"""
    user = request.user
    
    if not user.can_manage_contract_users():
        return JsonResponse({'success': False, 'message': 'Sin permisos'}, status=403)
    
    try:
        data = json.loads(request.body)
        trabajador_id = data.get('trabajador_id')
        fecha_str = data.get('fecha')
        estado = data.get('estado')
        tipo = data.get('tipo', 'PAGABLE')  # Por defecto PAGABLE
        observaciones = data.get('observaciones', '')
        
        # Validaciones
        if not all([trabajador_id, fecha_str, estado]):
            return JsonResponse({'success': False, 'message': 'Datos incompletos'}, status=400)
        
        trabajador = Trabajador.objects.get(id=trabajador_id)
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        # Verificar que el usuario tenga acceso al contrato del trabajador
        if not user.has_contract_permission(trabajador.contrato):
            return JsonResponse({'success': False, 'message': 'Sin acceso a este contrato'}, status=403)
        
        # Crear o actualizar asistencia
        asistencia, created = AsistenciaTrabajador.objects.update_or_create(
            trabajador=trabajador,
            fecha=fecha,
            defaults={
                'estado': estado,
                'tipo': tipo,
                'observaciones': observaciones,
                'registrado_por': user,
                'cargo_snapshot': trabajador.cargo or None,
                'guardia_snapshot': trabajador.guardia_asignada
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Asistencia guardada correctamente',
            'estado_display': asistencia.get_estado_display(),
            'tipo_display': asistencia.get_tipo_display()
        })
        
    except Trabajador.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Trabajador no encontrado'}, status=404)
    except ValueError as e:
        return JsonResponse({'success': False, 'message': f'Error en formato de fecha: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def guardar_asistencias_masivas(request):
    """API para guardar múltiples asistencias en una sola operación"""
    user = request.user
    
    if not user.can_manage_contract_users():
        return JsonResponse({'success': False, 'message': 'Sin permisos'}, status=403)
    
    try:
        data = json.loads(request.body)
        asistencias_data = data.get('asistencias', [])
        
        if not asistencias_data:
            return JsonResponse({'success': False, 'message': 'No hay datos para guardar'}, status=400)
        
        guardadas = 0
        turnos_actualizados = 0
        errores = []

        with transaction.atomic():
            for item in asistencias_data:
                trabajador_id = item.get('trabajador_id')
                fecha_str = item.get('fecha')
                estado = item.get('estado')
                turno = item.get('turno')
                observaciones = item.get('observaciones', '')
                tipo = item.get('tipo', None)

                # Validar existencia
                try:
                    trabajador = Trabajador.objects.get(id=trabajador_id)
                except Trabajador.DoesNotExist:
                    errores.append(f"Trabajador {trabajador_id} no existe")
                    continue

                # Verificar permisos al contrato
                if not user.has_contract_permission(trabajador.contrato):
                    errores.append(f"Sin permiso en trabajador {trabajador_id}")
                    continue

                try:
                    # Si se envía turno, actualizar la guardia asignada del trabajador
                    if turno:
                        trabajador.guardia_asignada = turno
                        trabajador.save(update_fields=['guardia_asignada'])
                        turnos_actualizados += 1

                    # Si se envía estado, crear/actualizar asistencia
                    if estado:
                        if not fecha_str:
                            errores.append(f"Falta fecha para trabajador {trabajador_id}")
                            continue
                        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                        defaults = {
                            'estado': estado,
                            'observaciones': observaciones,
                            'registrado_por': user,
                            'cargo_snapshot': trabajador.cargo or None,
                            'guardia_snapshot': trabajador.guardia_asignada
                        }
                        if tipo:
                            defaults['tipo'] = tipo

                        AsistenciaTrabajador.objects.update_or_create(
                            trabajador=trabajador,
                            fecha=fecha,
                            defaults=defaults
                        )
                        guardadas += 1

                except Exception as e:
                    errores.append(f"Error en trabajador {trabajador_id}: {str(e)}")

        mensaje = f'{guardadas} asistencias guardadas, {turnos_actualizados} turnos actualizados'
        if errores:
            return JsonResponse({
                'success': True,
                'message': mensaje + f' con {len(errores)} errores',
                'errores': errores
            })

        return JsonResponse({
            'success': True,
            'message': mensaje
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)


# MAPEO DE ESTADOS DEL SISTEMA A CÓDIGOS
MAPEO_CODIGOS = {
    'TRABAJADO': 'T',
    'DIA_LIBRE': 'DL',
    'DIA_APOYO': 'DA',
    'PERMISO_PATERNIDAD': 'PT',
    'DESCANSO_MEDICO': 'DM',
    'STAND_BY': 'SB',
    'SUBSIDIO': 'SUB',
    'INDUCCION': 'I',
    'INDUCCION_VIRTUAL': 'IV',
    'RECORRIDO': 'R',
    'FALTA': 'F',
    'PERMISO': 'P',
    'SUSPENSION': 'S',
    'VACACIONES': 'V',
    'LICENCIA_SIN_GOCE': 'LSG',
    'CESADO': 'C',
    'TRABAJO_CALIENTE': 'TC',
    'LICENCIA_FALLECIMIENTO': 'LF',
    'LICENCIA_CON_GOCE': 'LCG',
}

# LEYENDA DE CÓDIGOS
LEYENDA = {
    'T': 'TRABAJADO',
    'T1': 'TRABAJADO + 1 H.E.',
    'T2': 'TRABAJADO + 2 H.E.',
    'DL': 'DIA LIBRE',
    'DA': 'DIA APOYO',
    'PT': 'PERMISO PATERNIDAD',
    'DM': 'DESCANSO MEDICO',
    'SB': 'STAND BY',
    'SUB': 'SUBSIDIO',
    'I': 'INDUCCION',
    'IV': 'INDUCCION VIRTUAL',
    'R': 'RECORRIDO',
    'F': 'FALTA',
    'P': 'PERMISO',
    'S': 'SUSPENSION',
    'V': 'VACACIONES',
    'LSG': 'LICENCIA SIN GOCE',
    'C': 'CESADO',
    'TC': 'TRABAJO EN CALIENTE',
    'LF': 'LICENCIA FALLECIMIENTO',
    'LCG': 'LICENCIA CON GOCE',
}


@login_required
def exportar_asistencias_excel(request):
    """
    Exportar asistencias a Excel en formato completo con 3 hojas:
    - Tareo: Tabla principal con trabajadores y marcaciones diarias
    - Leyenda: Códigos de asistencia
    - Informe: Estadísticas y resúmenes
    """
    from django.http import HttpResponse
    from django.db.models import Count
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    
    user = request.user
    
    if not user.can_manage_contract_users():
        return HttpResponse('Sin permisos', status=403)
    
    # Obtener parámetros
    contrato_id = request.GET.get('contrato')
    modo = request.GET.get('modo', 'semana')
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    # Validar contrato
    if user.has_access_to_all_contracts():
        if not contrato_id:
            contrato = Contrato.objects.filter(estado='ACTIVO').first()
        else:
            contrato = Contrato.objects.filter(id=contrato_id, estado='ACTIVO').first()
    else:
        contrato = user.contrato
    
    if not contrato:
        return HttpResponse('Contrato no encontrado', status=404)
    
    try:
        # Calcular rango de fechas
        if fecha_inicio_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            except:
                fecha_inicio = date.today()
        else:
            fecha_inicio = date.today()
        
        # Calcular fecha_fin según modo
        if modo == 'semana':
            dias_a_mostrar = 7
            dia_semana = fecha_inicio.weekday()
            fecha_inicio = fecha_inicio - timedelta(days=dia_semana)
            fecha_fin = fecha_inicio + timedelta(days=dias_a_mostrar - 1)
        elif modo == 'quincena':
            dias_a_mostrar = 15
            fecha_fin = fecha_inicio + timedelta(days=dias_a_mostrar - 1)
        elif modo == 'mes':
            primer_dia = fecha_inicio.replace(day=1)
            if primer_dia.month == 12:
                ultimo_dia = primer_dia.replace(year=primer_dia.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                ultimo_dia = primer_dia.replace(month=primer_dia.month + 1, day=1) - timedelta(days=1)
            fecha_inicio = primer_dia
            fecha_fin = ultimo_dia
            dias_a_mostrar = (fecha_fin - fecha_inicio).days + 1
        else:  # personalizado
            if fecha_fin_str:
                try:
                    fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
                except:
                    fecha_fin = fecha_inicio + timedelta(days=7)
            else:
                fecha_fin = fecha_inicio + timedelta(days=7)
            dias_a_mostrar = (fecha_fin - fecha_inicio).days + 1
        
        num_dias = dias_a_mostrar
        
        # Crear workbook
        wb = Workbook()
        wb.remove(wb.active)  # Remover hoja por defecto
        
        # 1. CREAR HOJA TAREO
        ws_tareo = wb.create_sheet("Tareo", 0)
        _crear_hoja_tareo(ws_tareo, contrato, fecha_inicio, fecha_fin, num_dias)
        
        # 2. CREAR HOJA LEYENDA
        ws_leyenda = wb.create_sheet("LEYENDA", 1)
        _crear_hoja_leyenda(ws_leyenda)
        
        # 3. CREAR HOJA INFORME
        ws_informe = wb.create_sheet("Informe", 2)
        _crear_hoja_informe(ws_informe, contrato, fecha_inicio, fecha_fin)
        
        # Preparar respuesta
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        mes_nombre = fecha_inicio.strftime('%B').capitalize()
        filename = f"Tareo_{contrato.nombre_contrato.replace(' ', '_')}_{mes_nombre}_{fecha_inicio.year}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'Error al generar Excel: {str(e)}', status=500)


def _crear_hoja_tareo(ws, contrato, fecha_inicio, fecha_fin, num_dias):
    """Crea la hoja principal de tareo"""
    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    subheader_fill = PatternFill(start_color="B7DEE8", end_color="B7DEE8", fill_type="solid")
    border_thin = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # FILA 1: Encabezado principal
    ws.merge_cells('A1:D1')
    cell = ws['A1']
    cell.value = f"TAREO MES DE : {fecha_inicio.strftime('%B %Y').upper()}"
    cell.font = Font(bold=True, size=12)
    cell.alignment = Alignment(horizontal='center', vertical='center')
    
    ws.merge_cells('E1:H1')
    cell = ws['E1']
    cell.value = f"CONTRATO : {contrato.nombre_contrato.upper()}"
    cell.font = Font(bold=True, size=12)
    cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # FILA 2: Etiquetas de semanas
    col_actual = 7  # Columna G (después de las 6 columnas fijas)
    fecha_actual = fecha_inicio
    
    while fecha_actual <= fecha_fin:
        # Calcular semana
        semana = fecha_actual.isocalendar()[1]
        col_letter = get_column_letter(col_actual)
        
        # Buscar inicio de semana
        if fecha_actual.weekday() == 0 or fecha_actual == fecha_inicio:  # Lunes o primer día
            inicio_semana = col_actual
            # Contar días de esta semana en el rango
            dias_semana = 0
            temp_fecha = fecha_actual
            while temp_fecha <= fecha_fin and temp_fecha.weekday() < 7:
                dias_semana += 1
                temp_fecha += timedelta(days=1)
                if temp_fecha.weekday() == 0:
                    break
            
            # Merge cells para la semana
            if dias_semana > 1:
                fin_semana = inicio_semana + dias_semana - 1
                ws.merge_cells(start_row=2, start_column=inicio_semana, end_row=2, end_column=fin_semana)
            
            cell = ws.cell(row=2, column=inicio_semana)
            cell.value = f"Semana {semana}"
            cell.font = Font(bold=True, size=10)
            cell.fill = subheader_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        col_actual += 1
        fecha_actual += timedelta(days=1)
    
    # FILA 3: Headers de columnas
    headers = [
        'ITEM', 'CODIGO', 'APELLIDOS Y NOMBRES', 'Cargo', 
        'GRUPO', 'GUARDIA'
    ]
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = border_thin
    
    # Headers de días
    fecha_actual = fecha_inicio
    col_num = 7  # Después de "GUARDIA"
    while fecha_actual <= fecha_fin:
        cell = ws.cell(row=3, column=col_num)
        cell.value = fecha_actual
        cell.number_format = 'DD/MM'
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border_thin
        col_num += 1
        fecha_actual += timedelta(days=1)
    
    # Headers de resumen (SIMPLIFICADO)
    headers_resumen = [
        'TRABAJADO (T)', 'DIAS LIBRES (DL)', 'FALTAS (F)', 
        'VACACIONES (V)', 'D. MEDICO (DM)', 'TOTAL DIAS'
    ]
    
    for header in headers_resumen:
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = border_thin
        col_num += 1
    
    # DATOS DE TRABAJADORES
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).order_by('grupo', 'apepat', 'apemat', 'nombres')
    
    # Obtener asistencias
    asistencias = AsistenciaTrabajador.objects.filter(
        trabajador__contrato=contrato,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    ).select_related('trabajador')
    
    # Diccionario de asistencias
    asist_dict = {}
    for asist in asistencias:
        if asist.trabajador.id not in asist_dict:
            asist_dict[asist.trabajador.id] = {}
        asist_dict[asist.trabajador.id][asist.fecha] = asist
    
    row_num = 4
    for idx, trabajador in enumerate(trabajadores, 1):
        # Datos fijos
        ws.cell(row=row_num, column=1).value = idx
        ws.cell(row=row_num, column=2).value = trabajador.dni
        ws.cell(row=row_num, column=3).value = f"{trabajador.apellidos}, {trabajador.nombres}"
        ws.cell(row=row_num, column=4).value = trabajador.cargo or ""
        ws.cell(row=row_num, column=5).value = trabajador.cargo or ""
        ws.cell(row=row_num, column=6).value = trabajador.guardia_asignada if trabajador.guardia_asignada else ""
        
        # Marcaciones diarias
        fecha_actual = fecha_inicio
        col_num = 7
        contadores = {'T': 0, 'DL': 0, 'F': 0, 'V': 0, 'DM': 0}
        
        while fecha_actual <= fecha_fin:
            asist = asist_dict.get(trabajador.id, {}).get(fecha_actual)
            if asist:
                codigo = MAPEO_CODIGOS.get(asist.estado, asist.estado)
                ws.cell(row=row_num, column=col_num).value = codigo
                # Contar para resumen
                if codigo in contadores:
                    contadores[codigo] += 1
            else:
                ws.cell(row=row_num, column=col_num).value = ""
            
            ws.cell(row=row_num, column=col_num).alignment = Alignment(horizontal='center', vertical='center')
            ws.cell(row=row_num, column=col_num).border = border_thin
            col_num += 1
            fecha_actual += timedelta(days=1)
        
        # Totales Simplificados
        ws.cell(row=row_num, column=col_num).value = contadores['T']
        ws.cell(row=row_num, column=col_num+1).value = contadores['DL']
        ws.cell(row=row_num, column=col_num+2).value = contadores['F']
        ws.cell(row=row_num, column=col_num+3).value = contadores['V']
        ws.cell(row=row_num, column=col_num+4).value = contadores['DM']
        
        # Total Días (Suma de todo lo registrado)
        # Ojo: Si quieres total de días del mes, es num_dias. Si es total de registros, es la suma.
        # Generalmente en tareo se quiere saber cuántos días se han contabilizado.
        total_registrados = sum(contadores.values())
        ws.cell(row=row_num, column=col_num+5).value = total_registrados
        
        row_num += 1
    
    # Ajustar anchos de columna
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 25
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 10
    
    # Días (columnas de marcación)
    for col in range(7, 7 + num_dias):
        ws.column_dimensions[get_column_letter(col)].width = 4


def _crear_hoja_leyenda(ws):
    """Crea la hoja de leyenda con códigos"""
    ws.merge_cells('A1:B1')
    cell = ws['A1']
    cell.value = "LEYENDA: CODIFICACION"
    cell.font = Font(bold=True, size=14)
    cell.alignment = Alignment(horizontal='center', vertical='center')
    
    row = 3
    for codigo, descripcion in LEYENDA.items():
        ws.cell(row=row, column=1).value = codigo
        ws.cell(row=row, column=1).font = Font(bold=True)
        ws.cell(row=row, column=2).value = descripcion
        row += 1
    
    ws.column_dimensions['A'].width = 10
    ws.column_dimensions['B'].width = 40


def _crear_hoja_informe(ws, contrato, fecha_inicio, fecha_fin):
    """Crea la hoja de informe con estadísticas"""
    ws['A1'] = f"INFORME DE TAREO - {contrato.nombre_contrato.upper()}"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f"Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
    
    # Estadísticas
    trabajadores = Trabajador.objects.filter(contrato=contrato, estado='ACTIVO')
    asistencias = AsistenciaTrabajador.objects.filter(
        trabajador__contrato=contrato,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    )
    
    row = 4
    ws.cell(row=row, column=1).value = "Total Trabajadores"
    ws.cell(row=row, column=2).value = trabajadores.count()
    ws.cell(row=row, column=1).font = Font(bold=True)
    
    row += 1
    ws.cell(row=row, column=1).value = "Total Registros de Asistencia"
    ws.cell(row=row, column=2).value = asistencias.count()
    ws.cell(row=row, column=1).font = Font(bold=True)
    
    row += 2
    ws.cell(row=row, column=1).value = "Distribución por Estado:"
    ws.cell(row=row, column=1).font = Font(bold=True, underline="single")
    
    row += 1
    # Contar por estado
    estados = asistencias.values('estado').annotate(total=Count('estado')).order_by('-total')
    for estado in estados:
        row += 1
        codigo = MAPEO_CODIGOS.get(estado['estado'], estado['estado'])
        descripcion = LEYENDA.get(codigo, estado['estado'])
        ws.cell(row=row, column=1).value = f"{codigo} - {descripcion}"
        ws.cell(row=row, column=2).value = estado['total']


@login_required
@require_http_methods(["POST"])
@login_required
@require_http_methods(["POST"])
def limpiar_asistencias_mes(request):
    """
    Limpia todas las asistencias del contrato para el rango de fechas especificado.
    Elimina registros de AsistenciaTrabajador excepto los estados protegidos si se solicita.
    """
    user = request.user
    if not user.can_manage_contract_users():
        return JsonResponse({'success': False, 'message': 'Sin permisos'}, status=403)
        
    try:
        data = json.loads(request.body)
        contrato_id = data.get('contrato_id')
        fecha_inicio_str = data.get('fecha_inicio')
        fecha_fin_str = data.get('fecha_fin')
        mantener_protegidos = data.get('mantener_protegidos', True)
        
        print(f"DEBUG Limpiar mes - Contrato: {contrato_id}, Fechas: {fecha_inicio_str} a {fecha_fin_str}")
        
        if not all([contrato_id, fecha_inicio_str, fecha_fin_str]):
            return JsonResponse({'success': False, 'message': 'Faltan datos requeridos'}, status=400)
            
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        
        # Validar periodo (máximo 40 días para evitar limpiezas masivas accidentales)
        dias = (fecha_fin - fecha_inicio).days + 1
        print(f"DEBUG - Días en el rango: {dias}")
        
        if dias > 40:
             return JsonResponse({'success': False, 'message': f'Rango de fechas demasiado amplio ({dias} días, máx 40)'}, status=400)
             
        query = AsistenciaTrabajador.objects.filter(
            trabajador__contrato_id=contrato_id,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        )
        
        total_antes = query.count()
        print(f"DEBUG - Total registros antes de filtrar: {total_antes}")
        
        if mantener_protegidos:
            ESTADOS_PROTEGIDOS = ['VACACIONES', 'DESCANSO_MEDICO', 'LICENCIA', 'PERMISO', 'SUBSIDIO']
            query = query.exclude(estado__in=ESTADOS_PROTEGIDOS)
            
        total_a_eliminar = query.count()
        print(f"DEBUG - Total a eliminar (sin protegidos): {total_a_eliminar}")
        
        count, _ = query.delete()
        
        print(f"DEBUG - Registros eliminados: {count}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Se eliminaron {count} de {total_antes} registros de asistencia.'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def auto_rellenar_turno_view(request):
    """
    Retorna trabajadores sugeridos para un turno en fecha y guardia específica.
    Se basa en la asistencia ya registrada (tareo).
    Si el trabajador tiene asistencia 'TRABAJADO' y coincide la guardia, se sugiere.
    """
    try:
        data = json.loads(request.body)
        contrato_id = data.get('contrato_id')
        fecha_str = data.get('fecha')
        guardia = data.get('guardia')
        
        if not all([contrato_id, fecha_str, guardia]):
            return JsonResponse({'success': False, 'message': 'Faltan datos'}, status=400)
            
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        # 1. Obtener trabajadores que tengan asistencia TRABAJADO en esa fecha
        asistencias = AsistenciaTrabajador.objects.filter(
            trabajador__contrato_id=contrato_id,
            fecha=fecha,
            estado='TRABAJADO' # Solo los que han ido a trabajar
        ).select_related('trabajador')
        
        # 2. Filtrar por guardia.
        # La guardia se puede tomar de la asistencia (parametro 'turno') o del perfil del trabajador.
        # Prioridad: turno en asistencia > perfil trabajador.
        
        trabajadores_list = []
        for a in asistencias:
            t = a.trabajador
            
            # Verificar guardia
            guardia_trabajador = a.turno if a.turno else t.guardia_asignada
            
            # Si coincide la guardia, agregar
            if guardia_trabajador == guardia:
                trabajadores_list.append({
                    'id': t.id,
                    'nombres': t.nombres,
                    'apellidos': t.apellidos,
                    'cargo': t.cargo or '',
                    'observaciones': ''
                })
        
        # Si no hay asistencias registradas (quizás no se ha hecho el tareo aún), 
        # fallback a sugerir según asignación estática del perfil
        if not trabajadores_list:
            trabajadores_perfil = Trabajador.objects.filter(
                contrato_id=contrato_id,
                estado='ACTIVO',
                subestado='EN_OPERACION',
                guardia_asignada=guardia
            )
            
            for t in trabajadores_perfil:
                # Verificar si hoy le toca trabajar según régimen (opcional, para no sugerir en días libres)
                # estado_calc = t.calcular_estado_regimen(fecha)
                # if estado_calc != 'TRABAJADO': continue 
                
                trabajadores_list.append({
                    'id': t.id,
                    'nombres': t.nombres,
                    'apellidos': t.apellidos,
                    'cargo': t.cargo or '',
                    'observaciones': 'Sugerido por perfil'
                })

        return JsonResponse({
            'success': True, 
            'trabajadores': trabajadores_list
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def auto_rellenar_asistencia(request):
    """
    Auto-rellena la asistencia basada en el régimen laboral.
    Sobrescribe estados 'TRABAJADO', 'DIA_LIBRE', 'FALTA' o vacíos.
    Respeta licencias, vacaciones, descansos médicos.
    """
    user = request.user
    if not user.can_manage_contract_users():
        return JsonResponse({'success': False, 'message': 'Sin permisos'}, status=403)

    try:
        data = json.loads(request.body)
        contrato_id = data.get('contrato_id')
        fecha_inicio_str = data.get('fecha_inicio')
        fecha_fin_str = data.get('fecha_fin')

        if not all([contrato_id, fecha_inicio_str, fecha_fin_str]):
            return JsonResponse({'success': False, 'message': 'Faltan datos'}, status=400)

        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()

        # Obtener trabajadores
        trabajadores = Trabajador.objects.filter(
            contrato_id=contrato_id,
            estado='ACTIVO'
        )

        count_updated = 0
        
        # Estados que NO se deben sobrescribir (protegidos)
        ESTADOS_PROTEGIDOS = ['VACACIONES', 'DESCANSO_MEDICO', 'LICENCIA', 'PERMISO', 'SUBSIDIO']

        with transaction.atomic():
            # 1. ASIGNACIÓN AUTOMÁTICA DE GUARDIAS (BALANCEO)
            # Si hay trabajadores sin guardia, asignarlos para balancear A, B, C
            # EXCEPCIÓN: No asignar guardia a LINEA_MANDO
            trabajadores_sin_guardia = [
                t for t in trabajadores 
                if not t.guardia_asignada and not any(c in (t.cargo or '').upper() for c in ('RESIDENTE','SUPERVISOR','JEFE','ADMINISTRADOR','INGENIERO','GERENTE'))
            ]
            
            if trabajadores_sin_guardia:
                # Contar actuales (excluyendo linea de mando)
                conteos = {'A': 0, 'B': 0, 'C': 0}
                for t in trabajadores:
                    if t.guardia_asignada in conteos and not any(c in (t.cargo or '').upper() for c in ('RESIDENTE','SUPERVISOR','JEFE','ADMINISTRADOR','INGENIERO','GERENTE')):
                        conteos[t.guardia_asignada] += 1
                
                # Asignar round-robin a la guardia con menos gente
                for t in trabajadores_sin_guardia:
                    # Encontrar guardia con menor conteo
                    min_guardia = min(conteos, key=conteos.get)
                    t.guardia_asignada = min_guardia
                    t.save(update_fields=['guardia_asignada'])
                    conteos[min_guardia] += 1

            # 2. GENERACIÓN DE ASISTENCIA CON ROTACIÓN
            for trabajador in trabajadores:
                # Iterar días
                delta = (fecha_fin - fecha_inicio).days + 1
                for i in range(delta):
                    fecha = fecha_inicio + timedelta(days=i)
                    
                    # Calcular estado según régimen y guardia (ROTACIÓN 14x7)
                    estado_regimen = None
                    
                    # CASO ESPECIAL: LINEA DE MANDO (Siempre TRABAJADO, excepto domingos si aplica, o según régimen simple)
                    if any(c in (trabajador.cargo or '').upper() for c in ('RESIDENTE','SUPERVISOR','JEFE','ADMINISTRADOR','INGENIERO','GERENTE')):
                        # Asumimos TRABAJADO por defecto para línea de mando, o lógica simple
                        # Si tienen régimen, intentar respetarlo, pero sin offsets de guardia
                        if trabajador.regimen_laboral:
                             try:
                                dias_trabajo, dias_descanso = map(int, trabajador.regimen_laboral.lower().split('x'))
                                # Para linea de mando, a veces es continuo. 
                                # Si es 14x7 pero sin guardia, ¿cómo sabemos cuándo empieza?
                                # Usamos fecha_inicio_ciclo si existe, sino asumimos TRABAJADO siempre
                                if trabajador.fecha_inicio_ciclo:
                                    ciclo_total = dias_trabajo + dias_descanso
                                    delta_ciclo = (fecha - trabajador.fecha_inicio_ciclo).days
                                    if delta_ciclo >= 0:
                                        dia_en_ciclo = delta_ciclo % ciclo_total
                                        if dia_en_ciclo < dias_trabajo:
                                            estado_regimen = 'TRABAJADO'
                                        else:
                                            estado_regimen = 'DIA_LIBRE'
                                else:
                                    # Si no hay fecha inicio ciclo, asumir TRABAJADO siempre (ej. régimen administrativo)
                                    estado_regimen = 'TRABAJADO'
                             except:
                                 estado_regimen = 'TRABAJADO'
                        else:
                            estado_regimen = 'TRABAJADO'

                    # Lógica específica para 14x7 con rotación de 3 guardias (SOLO SI TIENE GUARDIA)
                    elif trabajador.regimen_laboral == '14x7' and trabajador.guardia_asignada:
                        # Offsets para escalonar las guardias:
                        # Guardia A: Inicia día 1 (Offset 0)
                        # Guardia B: Inicia día 8 (Offset 7)
                        # Guardia C: Inicia día 15 (Offset 14)
                        offsets = {'A': 0, 'B': 7, 'C': 14}
                        offset = offsets.get(trabajador.guardia_asignada, 0)
                        
                        # Ciclo de 21 días (14 trabajo + 7 descanso)
                        # Ajustar el día del mes con el offset
                        dia_mes = fecha.day
                        dia_ciclo = (dia_mes - 1 - offset) % 21
                        
                        # Días 0-13 son trabajo (14 días), 14-20 son descanso (7 días)
                        # Nota: El módulo puede dar negativo en Python, ajustar si es necesario
                        # (a % n) tiene el mismo signo que n en Python, así que -7 % 21 = 14. Correcto.
                        
                        if 0 <= dia_ciclo < 14:
                            estado_regimen = 'TRABAJADO'
                        else:
                            estado_regimen = 'DIA_LIBRE'
                            
                    # Fallback para otros regímenes (lógica simple inicio mes)
                    elif trabajador.regimen_laboral:
                        try:
                            dias_trabajo, dias_descanso = map(int, trabajador.regimen_laboral.lower().split('x'))
                            ciclo_total = dias_trabajo + dias_descanso
                            inicio_mes = fecha.replace(day=1)
                            delta_dias = (fecha - inicio_mes).days
                            dia_en_ciclo = delta_dias % ciclo_total
                            
                            if dia_en_ciclo < dias_trabajo:
                                estado_regimen = 'TRABAJADO'
                            else:
                                estado_regimen = 'DIA_LIBRE'
                        except ValueError:
                            pass

                    if not estado_regimen:
                        continue 

                    # Verificar estado actual
                    asistencia, created = AsistenciaTrabajador.objects.get_or_create(
                        trabajador=trabajador,
                        fecha=fecha,
                        defaults={
                            'estado': estado_regimen,
                            'registrado_por': user
                        }
                    )

                    if created:
                        count_updated += 1
                    else:
                        # Si ya existe, verificar si es sobrescribible
                        if asistencia.estado not in ESTADOS_PROTEGIDOS:
                            if asistencia.estado != estado_regimen:
                                asistencia.estado = estado_regimen
                                asistencia.save()
                                count_updated += 1
        
        # --- VALIDACIÓN DE COBERTURA ---
        # "SIEMPRE debemos de tener 1 perforista y por lo menos 1 ayudante" por turno (Guardia)
        
        alertas = []
        
        # Consultar asistencias del rango para verificar
        asistencias = AsistenciaTrabajador.objects.filter(
            trabajador__contrato_id=contrato_id,
            fecha__range=[fecha_inicio, fecha_fin],
            estado='TRABAJADO'
        ).select_related('trabajador')

        # Agrupar por Fecha -> Guardia
        cobertura = {}
        for asist in asistencias:
            fecha_str = asist.fecha.strftime('%Y-%m-%d')
            guardia = asist.trabajador.guardia_asignada
            if not guardia:
                continue # Ignorar si no tiene guardia asignada
            
            key = f"{fecha_str}|{guardia}"
            if key not in cobertura:
                cobertura[key] = {'perforistas': 0, 'ayudantes': 0}
            
            cargo_nombre = (asist.trabajador.cargo or '').upper()
            if 'PERFORISTA' in cargo_nombre and 'AYUDANTE' not in cargo_nombre:
                cobertura[key]['perforistas'] += 1
            elif 'AYUDANTE' in cargo_nombre:
                cobertura[key]['ayudantes'] += 1

        # Verificar mínimos
        for key, counts in cobertura.items():
            fecha_s, guardia = key.split('|')
            perf = counts['perforistas']
            ayu = counts['ayudantes']
            
            if perf < 1 or ayu < 1:
                # Formatear fecha para mensaje
                f_obj = datetime.strptime(fecha_s, '%Y-%m-%d')
                f_fmt = f_obj.strftime('%d/%m')
                alertas.append(f"Día {f_fmt} Guardia {guardia}: {perf} Perf. / {ayu} Ayud. (Mínimo 1 Perf + 1 Ayud)")

        msg = f'Se actualizaron {count_updated} registros.'
        if alertas:
            msg += " ADVERTENCIA DE COBERTURA: " + "; ".join(alertas[:5])
            if len(alertas) > 5:
                msg += f" ... y {len(alertas)-5} más."

        return JsonResponse({
            'success': True, 
            'message': msg,
            'alertas': alertas
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def actualizar_grupos_trabajadores(request):
    """
    Solo lee el estado actual de los trabajadores y devuelve un resumen.
    NO modifica ningún dato — la tabla del tareo se reconstruye con un reload
    usando los grupos y el flag es_standby ya guardados en cada trabajador.
    """
    try:
        contrato_id = request.POST.get('contrato_id')

        qs = Trabajador.objects.filter(estado='ACTIVO')
        if contrato_id:
            qs = qs.filter(contrato_id=contrato_id)

        stats = {}
        standby_count = 0
        for t in qs.only('grupo', 'es_standby'):
            if t.es_standby:
                standby_count += 1
                key = 'Stand By'
            else:
                key = t.grupo or 'Sin Grupo'
            stats[key] = stats.get(key, 0) + 1

        total = sum(stats.values())
        detalles = ", ".join([f"{k}: {v}" for k, v in sorted(stats.items())])
        message = f'Tareo actualizado — {total} trabajadores activos. Distribución: {detalles}.'

        return JsonResponse({'success': True, 'message': message})
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'message': str(e) + '\n' + traceback.format_exc()}, status=500)

@login_required
def debug_trabajadores(request):
    """Vista de depuración para listar trabajadores y sus grupos"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Solo staff")
        
    contrato_id = request.GET.get('contrato')
    if contrato_id:
        trabajadores = Trabajador.objects.filter(contrato_id=contrato_id).select_related('contrato').order_by('grupo', 'apepat', 'apemat')
    else:
        trabajadores = Trabajador.objects.all().select_related('contrato').order_by('contrato', 'grupo', 'apepat', 'apemat')
        
    html = """
    <html>
    <head>
        <title>Debug Trabajadores</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="p-4">
        <h1>Debug Trabajadores</h1>
        <table class="table table-striped table-bordered table-sm">
            <thead class="table-dark">
                <tr>
                    <th>ID</th>
                    <th>Contrato</th>
                    <th>Nombres</th>
                    <th>Apellidos</th>
                    <th>Cargo</th>
                    <th>Grupo (DB)</th>
                    <th>Grupo (Calculado)</th>
                    <th>Estado</th>
                    <th>Guardia</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for t in trabajadores:
        grupo_calc = t.asignar_grupo_automatico()
        match_style = "text-success" if t.grupo == grupo_calc else "text-danger fw-bold"
        
        html += f"""
        <tr>
            <td>{t.id}</td>
            <td>{t.contrato.nombre_contrato if t.contrato else '-'}</td>
            <td>{t.nombres}</td>
            <td>{t.apellidos}</td>
            <td>{t.cargo or '-'}</td>
            <td>{t.grupo or '-'}</td>
            <td class="{match_style}">{grupo_calc}</td>
            <td>{t.estado}</td>
            <td>{t.guardia_asignada}</td>
        </tr>
        """
        
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return HttpResponse(html)


@login_required
@require_http_methods(["POST"])
@login_required
@require_http_methods(["POST"])
def generar_guardias_automaticas(request):
    """
    Genera y asigna guardias A, B, C automáticamente con lógica flexible:
    - EXCLUYE personal marcado como STANDBY (personal de reserva)
    - Distribuye perforistas y ayudantes proporcionalmente según disponibilidad
    - Si no hay suficiente para 3 guardias completas, forma las que sean posibles
    - Línea de mando no recibe guardias (trabajan independiente)
    
    Composición ideal por guardia: 1 perforista + 2 ayudantes
    Pero se adapta al personal disponible
    """
    user = request.user
    
    if not user.can_manage_contract_users():
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)
    
    # Determinar contrato
    if user.has_access_to_all_contracts():
        contrato_id = request.POST.get('contrato_id')
        if not contrato_id:
            return JsonResponse({'success': False, 'error': 'Debe especificar contrato'}, status=400)
        try:
            contrato = Contrato.objects.get(id=contrato_id)
        except Contrato.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Contrato no encontrado'}, status=404)
    else:
        contrato = user.contrato
        if not contrato:
            return JsonResponse({'success': False, 'error': 'Usuario sin contrato asignado'}, status=400)
    
    try:
        # Separar trabajadores por tipo de cargo
        perforistas = []
        ayudantes = []
        otros_operadores = []
        personal_standby = []
        
        trabajadores = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        ).order_by('cargo', 'apepat', 'nombres')
        
        # .exclude(grupo='LINEA_MANDO') # TODO: Restaurar cuando el campo grupo exista
        
        if not trabajadores.exists():
            return JsonResponse({
                'success': False,
                'error': 'No hay trabajadores para asignar guardias'
            }, status=400)
        
        # Clasificar trabajadores según cargo y si son STANDBY
        for trabajador in trabajadores:
            # Separar personal STANDBY
            if trabajador.es_standby:
                personal_standby.append(trabajador)
                continue
            
            cargo_upper = (trabajador.cargo or '').upper()
            
            # Identificar PERFORISTAS
            if 'PERFORISTA' in cargo_upper and 'AYUDANTE' not in cargo_upper:
                perforistas.append(trabajador)
            # Identificar AYUDANTES
            elif 'AYUDANTE' in cargo_upper:
                ayudantes.append(trabajador)
            # Otros (auxiliares, conductores, etc.)
            else:
                otros_operadores.append(trabajador)
        
        num_perforistas = len(perforistas)
        num_ayudantes = len(ayudantes)
        num_otros = len(otros_operadores)
        num_standby = len(personal_standby)
        
        # Validar que haya al menos algo para asignar
        if num_perforistas == 0 and num_ayudantes == 0:
            return JsonResponse({
                'success': False,
                'error': 'No hay perforistas ni ayudantes activos para asignar guardias (excluidos STANDBY).',
                'personal_standby': num_standby
            }, status=400)
        
        # Calcular cuántas guardias podemos formar
        # Idealmente: 1 perforista + 2 ayudantes por guardia (maqueta completa)
        # Pero flexible: Aceptamos formar con menos si falta gente (priorizar A, B, C)
        
        # Siempre intentamos formar 3 guardias si hay suficiente personal mínimo
        num_guardias = 3
        
        # Validar si realmente tenemos CERO capacidad para 3
        if num_perforistas < 1 and num_ayudantes < 1:
            num_guardias = 0
        elif num_perforistas < 3 and num_ayudantes < 3:
             # Si hay muy poco personal total, reducir guardias (solo si es extremo)
             # Ej: 1 Perforista total -> 1 Guardia
             # Ej: 2 Perforistas total -> 2 Guardias
             # Pero si hay 3 perforistas, o 2P + 3A, intentamos estirar a 3
             if num_perforistas > 0:
                 num_guardias = min(3, num_perforistas) 
             else:
                 # Solo ayudantes
                 num_guardias = min(3, max(1, num_ayudantes // 2))
        
        # Forzar 3 guardias si el usuario lo pide implícitamente (lógica de negocio habitual)
        # Salvo que sea absurdo (ej: 1 sola persona)
        if (num_perforistas + num_ayudantes) >= 3:
             num_guardias = 3

        guardias = ['A', 'B', 'C'][:num_guardias]  # Guardias activas
        
        asignados = 0
        distribucion = {g: 0 for g in guardias}
        detalles = {
            'perforistas': {g: 0 for g in guardias}, 
            'ayudantes': {g: 0 for g in guardias}, 
            'otros': {g: 0 for g in guardias}
        }
        
        with transaction.atomic():
            # 1. Asignar PERFORISTAS de forma cíclica (A, B, C, A, B...)
            for i, perforista in enumerate(perforistas):
                guardia = guardias[i % len(guardias)]
                perforista.guardia_asignada = guardia
                perforista.save(update_fields=['guardia_asignada'])
                asignados += 1
                distribucion[guardia] += 1
                detalles['perforistas'][guardia] += 1
            
            # 2. Asignar AYUDANTES de forma cíclica (repartir equitativamente)
            # Antes: 2xA, 2xB... (llenado agresivo)
            # Ahora: A, B, C, A, B, C... (reparto equilibrado para cubrir mínimos)
            for i, ayudante in enumerate(ayudantes):
                guardia = guardias[i % len(guardias)]
                ayudante.guardia_asignada = guardia
                ayudante.save(update_fields=['guardia_asignada'])
                asignados += 1
                distribucion[guardia] += 1
                detalles['ayudantes'][guardia] += 1
            
            # 3. Asignar OTROS de forma equitativa
            for i, trabajador in enumerate(otros_operadores):
                guardia = guardias[i % len(guardias)]
                trabajador.guardia_asignada = guardia
                trabajador.save(update_fields=['guardia_asignada'])
                asignados += 1
                distribucion[guardia] += 1
                detalles['otros'][guardia] += 1
            
            # 4. Limpiar guardias del personal STANDBY (no tienen guardia fija)
            for trabajador in personal_standby:
                if trabajador.guardia_asignada:
                    trabajador.guardia_asignada = None
                    trabajador.save(update_fields=['guardia_asignada'])
        
        # Preparar mensaje informativo
        mensaje = f'✅ Guardias asignadas exitosamente'
        advertencias = []
        
        if num_guardias < 3:
            advertencias.append(f'⚠️ Solo se formaron {num_guardias} guardia(s) por personal limitado')
        
        if num_standby > 0:
            advertencias.append(f'ℹ️ {num_standby} trabajador(es) STANDBY excluidos (sin guardia fija)')
        
        # Verificar composición
        for g in guardias:
            perf = detalles['perforistas'][g]
            ayud = detalles['ayudantes'][g]
            if perf == 0:
                advertencias.append(f'⚠️ Guardia {g} sin perforistas')
            if ayud < 2:
                advertencias.append(f'⚠️ Guardia {g} con solo {ayud} ayudante(s)')
        
        if advertencias:
            mensaje += '\n\n' + '\n'.join(advertencias)
        
        return JsonResponse({
            'success': True,
            'message': mensaje,
            'asignados': asignados,
            'guardias_formadas': num_guardias,
            'distribucion_total': distribucion,
            'detalles': detalles,
            'resumen': {
                'perforistas_totales': num_perforistas,
                'ayudantes_totales': num_ayudantes,
                'otros_totales': num_otros,
                'personal_standby': num_standby
            },
            'advertencias': advertencias
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error al generar guardias: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@login_required
@require_http_methods(["POST"])
def autocompletar_tareo_por_regimen(request):
    """
    Autocompleta el tareo del mes según el régimen laboral de cada trabajador.
    
    Lógica:
    - Calcula días de trabajo/descanso según régimen (14x7, 20x10, etc.)
    - Asegura que siempre hay 2 guardias activas cada día
    - Rota las guardias para cumplir con sus regímenes
    - Línea de mando trabaja todos los días hábiles
    """
    user = request.user
    
    if not user.can_manage_contract_users():
        return JsonResponse({'success': False, 'message': 'Sin permisos'}, status=403)
    
    try:
        # Obtener datos de POST (FormData)
        contrato_id = request.POST.get('contrato_id')
        fecha_inicio_str = request.POST.get('fecha_inicio')
        fecha_fin_str = request.POST.get('fecha_fin')
        
        if not fecha_inicio_str or not fecha_fin_str:
            return JsonResponse({'success': False, 'message': 'Fechas no especificadas'}, status=400)
        
        # Parsear fechas
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        
        # Determinar contrato
        if user.has_access_to_all_contracts():
            if not contrato_id:
                return JsonResponse({'success': False, 'message': 'Debe especificar contrato'}, status=400)
            contrato = Contrato.objects.get(id=contrato_id)
        else:
            contrato = user.contrato
        
        # Obtener trabajadores activos
        trabajadores = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        )
        
        registros_creados = 0
        registros_actualizados = 0
        trabajadores_sin_ciclo = 0
        
        with transaction.atomic():
            # Recalcular fecha_inicio_ciclo para TODOS los operadores según su guardia
            # Para régimen 14x7 (ciclo de 21 días), con 3 guardias, el desfase es 7 días
            # Esto garantiza que siempre haya 2 guardias trabajando y 1 descansando
            for trabajador in trabajadores:
                if not any(c in (trabajador.cargo or '').upper() for c in ('RESIDENTE','SUPERVISOR','JEFE','ADMINISTRADOR','INGENIERO','GERENTE')):
                    fecha_anterior = trabajador.fecha_inicio_ciclo
                    
                    # Recalcular inicio de ciclo según guardia (desfase de 7 días por guardia)
                    if trabajador.guardia_asignada == 'A':
                        nueva_fecha_ciclo = fecha_inicio
                    elif trabajador.guardia_asignada == 'B':
                        nueva_fecha_ciclo = fecha_inicio - timedelta(days=7)
                    elif trabajador.guardia_asignada == 'C':
                        nueva_fecha_ciclo = fecha_inicio - timedelta(days=14)
                    else:
                        nueva_fecha_ciclo = fecha_inicio
                    
                    if fecha_anterior != nueva_fecha_ciclo:
                        # Usar QuerySet.update() para evitar disparar el save() hook
                        # (que llama a asignar_grupo_automatico() y sobrescribe el grupo manual)
                        Trabajador.objects.filter(pk=trabajador.pk).update(fecha_inicio_ciclo=nueva_fecha_ciclo)
                        trabajador.fecha_inicio_ciclo = nueva_fecha_ciclo  # actualizar instancia en memoria
                        trabajadores_sin_ciclo += 1
            
            # Recorrer cada día del mes
            fecha_actual = fecha_inicio
            while fecha_actual <= fecha_fin:
                
                # Para cada trabajador, determinar su estado ese día
                for trabajador in trabajadores:
                    # Respetar fecha_inicio_labores: no crear tareo antes del inicio
                    if trabajador.fecha_inicio_labores and fecha_actual < trabajador.fecha_inicio_labores:
                        continue

                    # Intenta calcular según régimen configurado (para TODOS, incluida Línea de Mando)
                    estado = trabajador.calcular_estado_regimen(fecha_actual)
                    
                    # Si no tiene régimen configurado (return None), aplicar defaults por grupo
                    if not estado:
                        if any(c in (trabajador.cargo or '').upper() for c in ('RESIDENTE','SUPERVISOR','JEFE','ADMINISTRADOR','INGENIERO','GERENTE')):
                            # Default para oficina: Lunes a Viernes
                            estado = 'TRABAJADO' if fecha_actual.weekday() < 5 else 'DIA_LIBRE'
                        else:
                            # Default para operativos: Siempre Trabajo
                            estado = 'TRABAJADO'
                    
                    # Verificar si ya existe registro
                    asistencia, created = AsistenciaTrabajador.objects.get_or_create(
                        trabajador=trabajador,
                        fecha=fecha_actual,
                        defaults={
                            'estado': estado,
                            'guardia_snapshot': trabajador.guardia_asignada,
                            'cargo_snapshot': trabajador.cargo or '',
                            'registrado_por': user
                        }
                    )
                    
                    if created:
                        registros_creados += 1
                    else:
                        # Actualizar si cambió el estado
                        if asistencia.estado != estado:
                            asistencia.estado = estado
                            asistencia.guardia_snapshot = trabajador.guardia_asignada
                            asistencia.cargo_snapshot = trabajador.cargo or ''
                            asistencia.save()
                            registros_actualizados += 1
                
                fecha_actual += timedelta(days=1)
        
        mensaje = f'✅ Tareo autocompletado: {registros_creados} registros creados, {registros_actualizados} actualizados'
        if trabajadores_sin_ciclo > 0:
            mensaje += f' ({trabajadores_sin_ciclo} trabajadores inicializados con fecha de ciclo)'
        
        return JsonResponse({
            'success': True,
            'message': mensaje,
            'creados': registros_creados,
            'actualizados': registros_actualizados,
            'inicializados': trabajadores_sin_ciclo,
            'periodo': f'{fecha_inicio.strftime("%d/%m/%Y")} - {fecha_fin.strftime("%d/%m/%Y")}'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error al autocompletar tareo: {str(e)}'
        }, status=500)
