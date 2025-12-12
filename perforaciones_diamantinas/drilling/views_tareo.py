"""
Vistas para el tareo de asistencia de trabajadores
Permite a los managers de contrato registrar la asistencia diaria
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import datetime, timedelta, date
from calendar import monthrange
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
    
    # Determinar el rango de fechas a mostrar
    modo = request.GET.get('modo', 'semana')  # 'semana', 'quincena', 'mes', 'personalizado'
    
    # Obtener fecha de inicio
    fecha_inicio_str = request.GET.get('fecha_inicio')
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_inicio = datetime.now().date()
    else:
        # Por defecto, inicio de la semana actual (lunes)
        hoy = datetime.now().date()
        fecha_inicio = hoy - timedelta(days=hoy.weekday())
    
    # Calcular fecha fin según el modo
    if modo == 'semana':
        fecha_fin = fecha_inicio + timedelta(days=6)  # 7 días
        dias_a_mostrar = 7
    elif modo == 'quincena':
        fecha_fin = fecha_inicio + timedelta(days=14)  # 15 días
        dias_a_mostrar = 15
    elif modo == 'mes':
        # Mes completo
        fecha_inicio = fecha_inicio.replace(day=1)
        num_dias = monthrange(fecha_inicio.year, fecha_inicio.month)[1]
        fecha_fin = fecha_inicio + timedelta(days=num_dias - 1)
        dias_a_mostrar = num_dias
    else:  # personalizado
        fecha_fin_str = request.GET.get('fecha_fin')
        if fecha_fin_str:
            try:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                fecha_fin = fecha_inicio + timedelta(days=6)
        else:
            fecha_fin = fecha_inicio + timedelta(days=6)
        dias_a_mostrar = (fecha_fin - fecha_inicio).days + 1
    
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
    
    # Obtener trabajadores activos del contrato ordenados por grupo y guardia
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).select_related('cargo').order_by('grupo', 'guardia_asignada', 'apellidos', 'nombres')
    
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
    
    # Combinar trabajadores con sus asistencias y agrupar
    trabajadores_por_grupo = {}
    
    for trabajador in trabajadores:
        # Determinar grupo (usar el grupo del trabajador o crear uno genérico)
        grupo_key = trabajador.grupo if trabajador.grupo else 'SIN_GRUPO'
        guardia_key = trabajador.guardia_asignada if trabajador.guardia_asignada else 'SIN_GUARDIA'
        
        # Crear estructura de grupos si no existe
        if grupo_key not in trabajadores_por_grupo:
            trabajadores_por_grupo[grupo_key] = {
                'nombre': trabajador.get_grupo_display() if trabajador.grupo else 'Sin Grupo',
                'guardias': {}
            }
        
        # Crear estructura de guardias si no existe
        if guardia_key not in trabajadores_por_grupo[grupo_key]['guardias']:
            trabajadores_por_grupo[grupo_key]['guardias'][guardia_key] = {
                'nombre': f"Guardia {trabajador.guardia_asignada}" if trabajador.guardia_asignada else 'Sin Guardia',
                'trabajadores': []
            }
        
        # Preparar asistencias del trabajador
        asistencias_trabajador = []
        for dia_info in dias_rango:
            fecha = dia_info['fecha']
            asist_dia = asistencias_dict.get(trabajador.id, {}).get(fecha)
            asistencias_trabajador.append({
                'fecha': fecha,
                'estado': asist_dia['estado'] if asist_dia else None,
                'estado_display': asist_dia['estado_display'] if asist_dia else '-',
                'tipo': asist_dia['tipo'] if asist_dia else 'PAGABLE',
                'tipo_display': asist_dia['tipo_display'] if asist_dia else 'Pagable',
                'observaciones': asist_dia['observaciones'] if asist_dia else '',
                'es_domingo': dia_info['es_domingo'],
                'es_sabado': dia_info['es_sabado']
            })
        
        trabajadores_por_grupo[grupo_key]['guardias'][guardia_key]['trabajadores'].append({
            'trabajador': trabajador,
            'asistencias': asistencias_trabajador
        })
    
    # Convertir a lista ordenada para el template
    grupos_ordenados = []
    orden_grupos = ['LINEA_MANDO', 'OPERADORES', 'SERVICIOS_GEOLOGICOS', 'PERSONAL_AUXILIAR', 'SIN_GRUPO']
    
    for grupo_key in orden_grupos:
        if grupo_key in trabajadores_por_grupo:
            grupo_data = trabajadores_por_grupo[grupo_key]
            # Ordenar guardias (A, B, C, luego sin guardia)
            guardias_ordenadas = []
            for guardia_key in ['A', 'B', 'C', 'SIN_GUARDIA']:
                if guardia_key in grupo_data['guardias']:
                    guardias_ordenadas.append({
                        'key': guardia_key,
                        'nombre': grupo_data['guardias'][guardia_key]['nombre'],
                        'trabajadores': grupo_data['guardias'][guardia_key]['trabajadores']
                    })
            
            grupos_ordenados.append({
                'key': grupo_key,
                'nombre': grupo_data['nombre'],
                'guardias': guardias_ordenadas,
                'total_trabajadores': sum(len(g['trabajadores']) for g in guardias_ordenadas)
            })
    
    # Navegación
    if modo == 'semana':
        fecha_anterior = fecha_inicio - timedelta(days=7)
        fecha_siguiente = fecha_inicio + timedelta(days=7)
    elif modo == 'quincena':
        fecha_anterior = fecha_inicio - timedelta(days=15)
        fecha_siguiente = fecha_inicio + timedelta(days=15)
    elif modo == 'mes':
        # Mes anterior
        if fecha_inicio.month == 1:
            fecha_anterior = fecha_inicio.replace(year=fecha_inicio.year - 1, month=12, day=1)
        else:
            fecha_anterior = fecha_inicio.replace(month=fecha_inicio.month - 1, day=1)
        # Mes siguiente
        if fecha_inicio.month == 12:
            fecha_siguiente = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1)
        else:
            fecha_siguiente = fecha_inicio.replace(month=fecha_inicio.month + 1, day=1)
    else:
        dias_diff = dias_a_mostrar
        fecha_anterior = fecha_inicio - timedelta(days=dias_diff)
        fecha_siguiente = fecha_inicio + timedelta(days=dias_diff)
    
    # Nombre del período
    meses_es = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    if modo == 'mes':
        nombre_periodo = f"{meses_es[fecha_inicio.month]} {fecha_inicio.year}"
    elif modo == 'semana':
        if fecha_inicio.month == fecha_fin.month:
            nombre_periodo = f"Semana del {fecha_inicio.day} al {fecha_fin.day} de {meses_es[fecha_inicio.month]} {fecha_inicio.year}"
        else:
            nombre_periodo = f"Semana del {fecha_inicio.day} {meses_es[fecha_inicio.month]} al {fecha_fin.day} {meses_es[fecha_fin.month]} {fecha_inicio.year}"
    else:
        nombre_periodo = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
    
    context = {
        'contrato': contrato,
        'contratos_disponibles': contratos_disponibles,
        'modo': modo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'nombre_periodo': nombre_periodo,
        'dias_rango': dias_rango,
        'grupos_ordenados': grupos_ordenados,
        'total_trabajadores': trabajadores.count(),
        'total_dias': dias_a_mostrar,
        'estados_asistencia': AsistenciaTrabajador.ESTADO_ASISTENCIA_CHOICES,
        'fecha_anterior': fecha_anterior,
        'fecha_siguiente': fecha_siguiente,
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
                'registrado_por': user
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
        errores = []
        
        with transaction.atomic():
            for item in asistencias_data:
                try:
                    trabajador_id = item.get('trabajador_id')
                    fecha_str = item.get('fecha')
                    estado = item.get('estado')
                    observaciones = item.get('observaciones', '')
                    
                    if not all([trabajador_id, fecha_str, estado]):
                        continue
                    
                    trabajador = Trabajador.objects.get(id=trabajador_id)
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    
                    # Verificar permisos
                    if not user.has_contract_permission(trabajador.contrato):
                        continue
                    
                    AsistenciaTrabajador.objects.update_or_create(
                        trabajador=trabajador,
                        fecha=fecha,
                        defaults={
                            'estado': estado,
                            'observaciones': observaciones,
                            'registrado_por': user
                        }
                    )
                    guardadas += 1
                    
                except Exception as e:
                    errores.append(f"Error en trabajador {trabajador_id}: {str(e)}")
        
        if errores:
            return JsonResponse({
                'success': True,
                'message': f'Guardadas {guardadas} asistencias con {len(errores)} errores',
                'errores': errores
            })
        
        return JsonResponse({
            'success': True,
            'message': f'{guardadas} asistencias guardadas correctamente'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)


@login_required
def exportar_asistencias_excel(request):
    """Exportar asistencias a Excel en formato de matriz día por día"""
    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
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
            contratos = Contrato.objects.filter(estado='ACTIVO').first()
            contrato = contratos if contratos else None
        else:
            contrato = Contrato.objects.filter(id=contrato_id, estado='ACTIVO').first()
    else:
        contrato = user.contrato
    
    if not contrato:
        return HttpResponse('Contrato no encontrado', status=404)
    
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
    
    # Obtener trabajadores
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).select_related('cargo').order_by('apellidos', 'nombres')
    
    # Obtener asistencias
    asistencias = AsistenciaTrabajador.objects.filter(
        trabajador__contrato=contrato,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    ).select_related('trabajador')
    
    # Crear diccionario de asistencias
    asistencias_dict = {}
    for asist in asistencias:
        if asist.trabajador.id not in asistencias_dict:
            asistencias_dict[asist.trabajador.id] = {}
        asistencias_dict[asist.trabajador.id][asist.fecha] = {
            'estado': asist.estado,
            'tipo': asist.tipo
        }
    
    # Crear Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Asistencias"
    
    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=10)
    trabajado_fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")  # Verde claro
    falta_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")  # Rojo claro
    especial_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")  # Amarillo claro
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_alignment = Alignment(horizontal='left', vertical='center')
    
    # Título
    total_cols = 3 + dias_a_mostrar  # DNI + Nombre + Cargo + días
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    ws['A1'] = f"REPORTE DE ASISTENCIAS - {contrato.nombre_contrato}"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = center_alignment
    
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
    ws['A2'] = f"Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
    ws['A2'].font = Font(size=11)
    ws['A2'].alignment = center_alignment
    
    # Encabezados principales (fila 4)
    ws.cell(row=4, column=1, value='DNI')
    ws.cell(row=4, column=2, value='NOMBRE COMPLETO')
    ws.cell(row=4, column=3, value='CARGO')
    
    # Encabezados de fechas
    col_num = 4
    for dia in range(dias_a_mostrar):
        fecha_actual = fecha_inicio + timedelta(days=dia)
        cell = ws.cell(row=4, column=col_num)
        
        # Día de la semana abreviado
        dias_semana = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']
        dia_semana = dias_semana[fecha_actual.weekday()]
        
        cell.value = f"{dia_semana}\n{fecha_actual.strftime('%d/%m')}"
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = center_alignment
        ws.column_dimensions[cell.column_letter].width = 10
        
        col_num += 1
    
    # Aplicar estilo a encabezados fijos
    for col in range(1, 4):
        cell = ws.cell(row=4, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = center_alignment
    
    # Ajustar anchos de columnas fijas
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 20
    
    # Datos de trabajadores
    row_num = 5
    estados_cortos = {
        'TRABAJADO': 'T',
        'FALTA': 'F',
        'DESCANSO_MEDICO': 'DM',
        'LICENCIA': 'L',
        'PERMISO': 'P',
        'VACACIONES': 'V',
        'DIA_LIBRE': 'DL',
        'INDUCCION': 'I',
        'INDUCCION_VIRTUAL': 'IV',
        'SUSPENDIDO': 'S'
    }
    
    for trabajador in trabajadores:
        # Columnas fijas
        ws.cell(row=row_num, column=1, value=trabajador.dni or 'S/N').alignment = center_alignment
        ws.cell(row=row_num, column=1).border = border
        
        ws.cell(row=row_num, column=2, value=f"{trabajador.apellidos} {trabajador.nombres}").alignment = left_alignment
        ws.cell(row=row_num, column=2).border = border
        
        ws.cell(row=row_num, column=3, value=trabajador.cargo.nombre).alignment = left_alignment
        ws.cell(row=row_num, column=3).border = border
        
        # Asistencias por día
        asist_trabajador = asistencias_dict.get(trabajador.id, {})
        
        col_num = 4
        for dia in range(dias_a_mostrar):
            fecha_actual = fecha_inicio + timedelta(days=dia)
            cell = ws.cell(row=row_num, column=col_num)
            
            asist_data = asist_trabajador.get(fecha_actual)
            
            if asist_data:
                estado = asist_data['estado']
                tipo = asist_data.get('tipo', 'PAGABLE')
                
                # Mostrar estado abreviado
                estado_corto = estados_cortos.get(estado, estado[:2])
                cell.value = estado_corto
                
                # Colorear según estado
                if estado == 'TRABAJADO':
                    cell.fill = trabajado_fill
                    cell.font = Font(bold=True, color="155724")
                elif estado == 'FALTA':
                    cell.fill = falta_fill
                    cell.font = Font(bold=True, color="721C24")
                else:
                    cell.fill = especial_fill
                    cell.font = Font(color="856404")
                
                # Si el admin marcó como NO_PAGABLE, añadir indicador
                if tipo == 'NO_PAGABLE':
                    cell.value = f"{estado_corto}*"
            else:
                cell.value = "-"
                cell.font = Font(color="999999")
            
            cell.border = border
            cell.alignment = center_alignment
            col_num += 1
        
        row_num += 1
    
    # Leyenda
    row_num += 2
    ws.cell(row=row_num, column=1, value="LEYENDA:").font = Font(bold=True)
    row_num += 1
    
    leyenda = [
        "T = Trabajado", "F = Falta", "DM = Descanso Médico", "L = Licencia",
        "P = Permiso", "V = Vacaciones", "DL = Día Libre", "I = Inducción",
        "IV = Inducción Virtual", "S = Suspendido", "* = No Pagable"
    ]
    
    for i, texto in enumerate(leyenda):
        col = (i % 3) + 1
        row = row_num + (i // 3)
        ws.cell(row=row, column=col, value=texto).font = Font(size=9)
    
    # Preparar respuesta
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Asistencias_{contrato.nombre_contrato}_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response

