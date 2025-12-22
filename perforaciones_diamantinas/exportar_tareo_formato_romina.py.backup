"""
Script para exportar tareo en formato Excel similar al contrato Romina
Genera un archivo Excel con:
- Hoja Tareo con formato tabla (trabajadores x días)
- Hoja Leyenda con códigos de asistencia
- Hoja Informe con resúmenes
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.db.models import Count, Q
from drilling.models import Contrato, Trabajador, AsistenciaTrabajador
from datetime import datetime, timedelta
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import locale

# Configurar locale para español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except:
        pass

# MAPEO DE ESTADOS DEL SISTEMA A CÓDIGOS DE ROMINA
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

# LEYENDA INVERSA
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


def generar_tareo_excel(contrato_id, año, mes, output_path=None):
    """
    Genera un Excel de tareo en formato Romina para un contrato específico
    
    Args:
        contrato_id: ID del contrato
        año: Año (ej: 2025)
        mes: Mes (1-12)
        output_path: Ruta del archivo de salida (opcional)
    """
    # Obtener contrato
    try:
        contrato = Contrato.objects.get(id=contrato_id)
    except Contrato.DoesNotExist:
        print(f"Error: Contrato ID {contrato_id} no encontrado")
        return None
    
    # Calcular rango de fechas
    fecha_inicio = datetime(año, mes, 1).date()
    if mes == 12:
        fecha_fin = datetime(año + 1, 1, 1).date() - timedelta(days=1)
    else:
        fecha_fin = datetime(año, mes + 1, 1).date() - timedelta(days=1)
    
    num_dias = (fecha_fin - fecha_inicio).days + 1
    
    print(f"\n{'='*80}")
    print(f"GENERANDO TAREO - CONTRATO: {contrato.nombre_contrato}")
    print(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}")
    print(f"Total días: {num_dias}")
    print(f"{'='*80}\n")
    
    # Crear workbook
    wb = Workbook()
    wb.remove(wb.active)  # Remover hoja por defecto
    
    # 1. CREAR HOJA TAREO
    ws_tareo = wb.create_sheet("Tareo", 0)
    crear_hoja_tareo(ws_tareo, contrato, fecha_inicio, fecha_fin, num_dias)
    
    # 2. CREAR HOJA LEYENDA
    ws_leyenda = wb.create_sheet("LEYENDA", 1)
    crear_hoja_leyenda(ws_leyenda)
    
    # 3. CREAR HOJA INFORME
    ws_informe = wb.create_sheet("Informe", 2)
    crear_hoja_informe(ws_informe, contrato, fecha_inicio, fecha_fin)
    
    # Guardar archivo
    if output_path is None:
        mes_nombre = fecha_inicio.strftime('%B').capitalize()
        output_path = f"Tareo_{contrato.nombre_contrato.replace(' ', '_')}_{mes_nombre}_{año}.xlsx"
    
    wb.save(output_path)
    print(f"\n✓ Archivo generado: {output_path}")
    return output_path


def crear_hoja_tareo(ws, contrato, fecha_inicio, fecha_fin, num_dias):
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
    col_actual = 9  # Columna I (después de las 8 columnas fijas)
    fecha_actual = fecha_inicio
    num_semana = fecha_actual.isocalendar()[1]
    
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
        'Fecha de Ingreso', 'Tipo de Trabajo', 'GRUPO', 'GUARDIA', 'Situacion'
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
    col_num = 10  # Después de "Situacion"
    while fecha_actual <= fecha_fin:
        cell = ws.cell(row=3, column=col_num)
        cell.value = fecha_actual
        cell.number_format = 'DD/MM/YYYY'
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border_thin
        col_num += 1
        fecha_actual += timedelta(days=1)
    
    # Headers de resumen (después de los días)
    headers_resumen = [
        'DIAS TRABAJADOS', 'DIAS APOYO', 'Por Superar Metros', 'DIAS PATERNIDAD',
        'CAPACITACION INDUCCION + RECORRIDO', 'DIAS VACACIONES', 'DIAS DM', 'SUB',
        'DIAS PROYECCION', 'DIAS FERIADO', 'INDUCION ISEM', 
        'DIAS PERMISO + DIAS SUSPENDIDOS + DIAS FALTO', 'TOTAL DIAS', 'Total H.',
        'comentarios', 'RESUMEN', 'PARA BONOS', 'P', 'F', 'S', 'SB', 'V', 'DM', 'PT', 'TOTAL AUSENCIAS'
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
    ).select_related('cargo').order_by('grupo', 'apellidos', 'nombres')
    
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
        ws.cell(row=row_num, column=4).value = trabajador.cargo.nombre if trabajador.cargo else ""
        ws.cell(row=row_num, column=5).value = trabajador.fecha_ingreso
        ws.cell(row=row_num, column=5).number_format = 'DD/MM/YYYY'
        ws.cell(row=row_num, column=6).value = "INT"  # Tipo de trabajo
        ws.cell(row=row_num, column=7).value = trabajador.get_grupo_display() if trabajador.grupo else ""
        ws.cell(row=row_num, column=8).value = trabajador.guardia if trabajador.guardia else ""
        ws.cell(row=row_num, column=9).value = "ACTIVO"
        
        # Marcaciones diarias
        fecha_actual = fecha_inicio
        col_num = 10
        contadores = {'T': 0, 'DL': 0, 'F': 0, 'P': 0, 'S': 0, 'SB': 0, 'V': 0, 'DM': 0, 'PT': 0, 'DA': 0}
        
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
        
        # Totales
        ws.cell(row=row_num, column=col_num).value = contadores['T']  # DIAS TRABAJADOS
        ws.cell(row=row_num, column=col_num+1).value = contadores['DA']  # DIAS APOYO
        ws.cell(row=row_num, column=col_num+3).value = contadores['PT']  # DIAS PATERNIDAD
        ws.cell(row=row_num, column=col_num+5).value = contadores['V']  # DIAS VACACIONES
        ws.cell(row=row_num, column=col_num+6).value = contadores['DM']  # DIAS DM
        
        total_dias = sum(contadores.values())
        ws.cell(row=row_num, column=col_num+12).value = total_dias  # TOTAL DIAS
        
        # Para bonos
        ws.cell(row=row_num, column=col_num+17).value = contadores['P']  # P
        ws.cell(row=row_num, column=col_num+18).value = contadores['F']  # F
        ws.cell(row=row_num, column=col_num+19).value = contadores['S']  # S
        ws.cell(row=row_num, column=col_num+20).value = contadores['SB']  # SB
        ws.cell(row=row_num, column=col_num+21).value = contadores['V']  # V
        ws.cell(row=row_num, column=col_num+22).value = contadores['DM']  # DM
        ws.cell(row=row_num, column=col_num+23).value = contadores['PT']  # PT
        
        total_ausencias = contadores['F'] + contadores['P'] + contadores['S']
        ws.cell(row=row_num, column=col_num+24).value = total_ausencias  # TOTAL AUSENCIAS
        
        row_num += 1
    
    # Ajustar anchos de columna
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 30
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 20
    ws.column_dimensions['H'].width = 10
    ws.column_dimensions['I'].width = 12
    
    # Días (columnas de marcación)
    for col in range(10, 10 + num_dias):
        ws.column_dimensions[get_column_letter(col)].width = 5
    
    print(f"✓ Hoja Tareo creada: {len(trabajadores)} trabajadores, {num_dias} días")


def crear_hoja_leyenda(ws):
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
    print("✓ Hoja Leyenda creada")


def crear_hoja_informe(ws, contrato, fecha_inicio, fecha_fin):
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
    
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 15
    print("✓ Hoja Informe creada")


if __name__ == "__main__":
    # Ejemplo de uso
    print("\n" + "="*80)
    print("GENERADOR DE TAREO EN FORMATO ROMINA")
    print("="*80)
    
    # Listar contratos disponibles
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    print("\nContratos disponibles:")
    for contrato in contratos:
        print(f"  {contrato.id}. {contrato.nombre_contrato}")
    
    # Generar para un contrato específico
    contrato_id = input("\nIngrese ID del contrato (o Enter para el primero): ").strip()
    if not contrato_id:
        contrato_id = contratos.first().id
    else:
        contrato_id = int(contrato_id)
    
    año = int(input("Ingrese año (ej: 2025): ").strip() or "2025")
    mes = int(input("Ingrese mes (1-12): ").strip() or str(datetime.now().month))
    
    generar_tareo_excel(contrato_id, año, mes)
    
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80 + "\n")
