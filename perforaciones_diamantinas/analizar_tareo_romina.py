import pandas as pd
import sys

# Leer el archivo Excel
file_path = r'C:\Users\PERDLAP140.VILBRAGROUP\Downloads\T- Romina Nov. 2025.xlsx'

print("="*80)
print("ANÁLISIS DEL TAREO - CONTRATO ROMINA")
print("="*80)

# Leer todas las hojas
hojas = pd.read_excel(file_path, sheet_name=None)
print("\nHOJAS DISPONIBLES:")
for i, nombre in enumerate(hojas.keys(), 1):
    df = hojas[nombre]
    print(f"{i}. {nombre} - Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")

print("\n" + "="*80)
print("ANÁLISIS DETALLADO DE LA HOJA 'Tareo'")
print("="*80)

# Leer la hoja Tareo con header en la fila 2 (0-indexed)
df_tareo = pd.read_excel(file_path, sheet_name='Tareo', header=2)

print("\nESTRUCTURA DE COLUMNAS:")
print("-"*80)
cols_importantes = []
for i, col in enumerate(df_tareo.columns):
    col_str = str(col)
    if not col_str.startswith('Unnamed') and not '2025-' in col_str:
        print(f"{i:3d}. {col}")
        cols_importantes.append((i, col))

print("\n\nCOLUMNAS DE FECHAS (Días del mes):")
print("-"*80)
fecha_cols = []
for i, col in enumerate(df_tareo.columns):
    col_str = str(col)
    if '2025-' in col_str or 'Timestamp' in col_str:
        fecha_cols.append((i, col))
        if len(fecha_cols) <= 3 or len(fecha_cols) >= len([c for c in df_tareo.columns if '2025-' in str(c)])-2:
            print(f"{i:3d}. {col}")
        elif len(fecha_cols) == 4:
            print(f"      ... ({len([c for c in df_tareo.columns if '2025-' in str(c)])-6} columnas más)")

print(f"\nTotal de días en el tareo: {len(fecha_cols)}")

print("\n\nMUESTRA DE DATOS (Primeros 5 trabajadores):")
print("-"*80)
# Verificar qué columnas existen realmente
print("Columnas que existen:")
for col in df_tareo.columns[:15]:
    print(f"  - {col}")
print(f"\nTotal columnas: {len(df_tareo.columns)}")
print("\nPrimeras 5 filas completas:")
print(df_tareo.iloc[:5, :8].to_string())

print("\n\nRESUMEN DE LA HOJA:")
print("-"*80)
# Buscar la columna ITEM o similar
item_col = None
for col in df_tareo.columns:
    if 'ITEM' in str(col).upper() or col == 0:
        item_col = col
        break

if item_col is not None:
    print(f"Total de trabajadores registrados: {df_tareo[item_col].notna().sum()}")
else:
    print(f"Total de filas: {len(df_tareo)}")

# Buscar columnas de grupo y guardia
for col in df_tareo.columns[:10]:
    col_str = str(col).upper()
    if 'GRUPO' in col_str or 'GUARDIA' in col_str:
        print(f"{col}: {df_tareo[col].dropna().unique().tolist()[:5]}")

print("\n\nCOLUMNAS DE RESUMEN (después de los días):")
print("-"*80)
resumen_start = max([i for i, c in enumerate(df_tareo.columns) if '2025-' in str(c)]) + 1
for i in range(resumen_start, min(resumen_start + 20, len(df_tareo.columns))):
    col = df_tareo.columns[i]
    col_str = str(col)
    if not col_str.startswith('Unnamed'):
        print(f"{i:3d}. {col}")

print("\n\nMUESTRA DE MARCACIONES (Primeros 3 trabajadores, primeros 7 días):")
print("-"*80)
primeros_dias = [col for col in df_tareo.columns if '2025-' in str(col)][:7]
if len(primeros_dias) > 0 and len(df_tareo.columns) > 2:
    nombre_col = df_tareo.columns[2]  # Asumiendo que nombres está en columna 2
    df_marcaciones = df_tareo[[nombre_col] + primeros_dias].head(3)
    for idx, row in df_marcaciones.iterrows():
        nombre = row[nombre_col]
        if pd.notna(nombre):
            print(f"\n{nombre}:")
            for dia in primeros_dias:
                valor = row[dia]
                if pd.notna(valor):
                    print(f"  {str(dia)[:10]}: {valor}")
else:
    print("No se encontraron columnas de fechas")

print("\n" + "="*80)
print("ANÁLISIS DE OTRAS HOJAS")
print("="*80)

# Analizar hoja Informe
if 'Informe' in hojas:
    df_informe = hojas['Informe']
    print("\nHOJA 'Informe':")
    print(f"  Dimensiones: {df_informe.shape}")
    print(f"  Primeras columnas: {df_informe.columns[:10].tolist()}")

# Analizar hoja LEYENDA
if 'LEYENDA' in hojas:
    df_leyenda = hojas['LEYENDA']
    print("\nHOJA 'LEYENDA':")
    print(f"  Dimensiones: {df_leyenda.shape}")
    print("  Contenido (códigos de asistencia):")
    for i in range(min(15, len(df_leyenda))):
        row = df_leyenda.iloc[i]
        if pd.notna(row[0]):
            print(f"    {row[0]}: {row[1] if len(row) > 1 and pd.notna(row[1]) else 'N/A'}")

print("\n" + "="*80)
