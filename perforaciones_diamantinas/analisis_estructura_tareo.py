"""
ANÁLISIS COMPLETO DE LA ESTRUCTURA DEL TAREO - CONTRATO ROMINA
================================================================

ESTRUCTURA GENERAL DEL EXCEL:
=============================

El archivo tiene 7 hojas:
1. **Tareo** (Principal) - 116 filas x 79 columnas
2. **Informe** - 42 filas x 9 columnas
3. **LEYENDA** - 57 filas x 15 columnas (códigos de asistencia)
4. **Transferencia** - 88 filas x 79 columnas
5. **Calendario** - 366 filas x 12 columnas
6. **MAquinas** - 79 filas x 7 columnas
7. **n** - 111 filas x 43 columnas

ESTRUCTURA DE LA HOJA "Tareo" (PRINCIPAL):
==========================================

FORMATO:
- Fila 0: Encabezado "TAREO MES DE : NOVIEMBRE 2025" / "CONTRATO : ROMINA"
- Fila 1: Etiquetas de semanas (Semana 40, 41, 42, 43)
- Fila 2: Headers de columnas (ITEM, CODIGO, APELLIDOS Y NOMBRES, etc.)
- Fila 3+: Datos de trabajadores

COLUMNAS PRINCIPALES (8 columnas fijas):
=========================================
0. ITEM - Número secuencial del trabajador (1, 2, 3...)
1. CODIGO - DNI del trabajador (ej: 43055604, 70267766)
2. APELLIDOS Y NOMBRES - Nombre completo
3. Cargo - Puesto del trabajador (ej: RESIDENTE, ASISTENTE DE RESIDENTE, INGENIERO DE SEGURIDAD)
4. Fecha de Ingreso - Fecha de inicio en el contrato
5. Tipo de Trabajod - Tipo de contrato (INT = Interno)
6. GRUPO - Clasificación del trabajador (ej: "0 Linea de Mando")
7. GUARDIA - Turno asignado (ej: B, o NaN para no aplica)
8. Situacion - Estado del trabajador

COLUMNAS DE ASISTENCIA DIARIA (38 columnas):
=============================================
- Columnas 9-46: Cada columna representa un día del mes
- Formato de fecha: 2025-10-24, 2025-10-25, etc.
- Valores posibles en cada celda:
  * T - Trabajado
  * T1 - Trabajado + 1 H.E.
  * DL - Día Libre
  * DA - Día Apoyo
  * PT - Permiso Paternidad
  * DM - Descanso Médico
  * SB - Stand By
  * SUB - Subsidio
  * I - Inducción
  * IV - Inducción Virtual
  * R - Recorrido
  * F - Falta
  * (Vacío) - Sin registro

COLUMNAS DE RESUMEN (aprox. 30 columnas finales):
==================================================
Después de las columnas de días, hay columnas de totales/resumen:
- DIAS TRABAJADOS
- DIAS APOYO
- Por Superar Metros
- DIAS PATERNIDAD
- CAPACITACION INDUCCION + RECORRIDO
- DIAS VACACIONES
- DIAS DM (Descanso Médico)
- SUB (Subsidio)
- DIAS PROYECCION
- DIAS FERIADO
- INDUCION ISEM
- DIAS PERMISO + DIAS SUSPENDIDOS + DIAS FALTO
- TOTAL DIAS
- Total H. (Total Horas)
- comentarios
- (Columna 70) RESUMEN
- PARA BONOS
- P, F, S, SB, V, DM, PT
- TOTAL AUSENCIAS

CARACTERÍSTICAS CLAVE:
======================

1. **Header multi-fila**: Las primeras 2 filas contienen metadata (mes, contrato, semanas)

2. **Datos por trabajador**: Cada fila = 1 trabajador con toda su asistencia del mes

3. **Marcación diaria**: Un código de letra(s) por día indica el tipo de asistencia

4. **Totalizadores**: Al final de cada fila se calculan automáticamente los totales

5. **Grupos de trabajadores**:
   - Línea de Mando (gerentes, residentes, ingenieros)
   - Operadores (perforistas, ayudantes)
   - Servicios (geología, mecánicos)
   - Personal auxiliar

6. **Guardias/Turnos**: 
   - B (probablemente Turno B)
   - NaN (no aplica para personal de línea de mando)

HOJA "LEYENDA":
===============
Contiene la descripción completa de todos los códigos:
- TRABAJADO: T
- TRABAJADO + 1 H.E.: T1
- DIA LIBRE: DL
- DIA APOYO: DA
- PERMISO PATERNIDAD: PT
- DESCANSO MEDICO: DM
- STAND BY: SB
- SUBSIDIO: SUB
- INDUCCION: I
- INDUCCION VIRTUAL: IV
- RECORRIDO: R
- FALTA: F

HOJA "MAquinas":
================
Probablemente contiene información de las máquinas/equipos usados en el contrato:
- 79 filas de máquinas
- 7 columnas de información

HOJA "Calendario":
==================
366 filas = 1 año completo (2025)
12 columnas probablemente con información de feriados, días no laborables, etc.

IMPLICACIONES PARA EL SISTEMA:
===============================

1. **Importación**: Necesitarás skipear las primeras 2 filas al importar
2. **Mapeo de códigos**: Cada código de asistencia debe mapearse a estados en el sistema
3. **Validación**: El sistema debe validar que los códigos existen en la leyenda
4. **Totales**: Los totales pueden recalcularse automáticamente
5. **Estructura relacional**: 
   - 1 Contrato (Romina)
   - N Trabajadores
   - N Días del mes
   - N Marcaciones (TrabajadorXDía)

DATOS DE EJEMPLO:
=================

Trabajador 1:
- ITEM: 1
- CODIGO: 43055604
- NOMBRE: SUCAPUCA APAZA ALFREDO
- CARGO: RESIDENTE
- GRUPO: 0 Linea de Mando
- GUARDIA: B
- Día 24/10: T (Trabajado)
- Día 25/10: T (Trabajado)
- Día 26/10: T (Trabajado)
- Día 27/10: T (Trabajado)
- Día 28/10: T (Trabajado)
- Día 29/10: T (Trabajado)
- Día 30/10: DL (Día Libre)

"""

import pandas as pd

file_path = r'C:\Users\PERDLAP140.VILBRAGROUP\Downloads\T- Romina Nov. 2025.xlsx'

print(__doc__)

print("\n" + "="*80)
print("ANÁLISIS ESTADÍSTICO ADICIONAL")
print("="*80)

# Leer con header correcto
df = pd.read_excel(file_path, sheet_name='Tareo', header=2)

print("\nDISTRIBUCIÓN DE CARGOS:")
print("-"*80)
if len(df.columns) > 3:
    cargo_col = df.columns[3]
    cargos = df[cargo_col].value_counts()
    for cargo, count in cargos.head(15).items():
        if pd.notna(cargo):
            print(f"{cargo:40s}: {count:3d} trabajadores")

print("\nDISTRIBUCIÓN DE GRUPOS:")
print("-"*80)
if len(df.columns) > 6:
    grupo_col = df.columns[6]
    grupos = df[grupo_col].value_counts()
    for grupo, count in grupos.items():
        if pd.notna(grupo):
            print(f"{grupo:40s}: {count:3d} trabajadores")

print("\nDISTRIBUCIÓN DE GUARDIAS:")
print("-"*80)
if len(df.columns) > 7:
    guardia_col = df.columns[7]
    guardias = df[guardia_col].value_counts()
    for guardia, count in guardias.items():
        if pd.notna(guardia):
            print(f"{str(guardia):40s}: {count:3d} trabajadores")

# Analizar marcaciones
print("\nANÁLISIS DE MARCACIONES (primeros 30 días):")
print("-"*80)
fecha_cols = [col for col in df.columns if '2025-' in str(col)][:30]
if len(fecha_cols) > 0:
    # Contar tipos de marcación
    todas_marcaciones = []
    for col in fecha_cols:
        todas_marcaciones.extend(df[col].dropna().tolist())
    
    from collections import Counter
    conteo = Counter(todas_marcaciones)
    print("\nCódigos de asistencia más usados:")
    for codigo, count in conteo.most_common(20):
        print(f"  {str(codigo):6s}: {count:4d} registros")

print("\n" + "="*80)
print("FIN DEL ANÁLISIS")
print("="*80)
