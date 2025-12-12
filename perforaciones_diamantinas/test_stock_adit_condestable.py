"""
Prueba detallada del Stock de Aditivos (ADIT) para CONDESTABLE
Centro de Costo: 000003
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import CustomUser
from drilling.api_client import get_api_client
from collections import defaultdict

# Obtener usuario CTRCONDESTABLE
usuario = CustomUser.objects.get(username='CTRCONDESTABLE')
centro_costo = usuario.contrato.codigo_centro_costo

print("=" * 80)
print("ANÁLISIS DE STOCK - ADITIVOS (ADIT)")
print("CONTRATO: CONDESTABLE")
print("CENTRO DE COSTO: 000003")
print("=" * 80)

# Obtener cliente API
client = get_api_client()

# Obtener aditivos
print("\n🔄 Consultando API de Vilbragroup...")
aditivos = client.obtener_aditivos(centro_costo=centro_costo)

if not aditivos:
    print("❌ No se obtuvieron aditivos")
    exit(1)

print(f"✅ Total de artículos: {len(aditivos)}")

# Analizar la estructura de datos
print("\n" + "=" * 80)
print("ESTRUCTURA DE DATOS")
print("=" * 80)

if aditivos:
    primer_aditivo = aditivos[0]
    print("\nCampos disponibles en cada artículo:")
    for key, value in primer_aditivo.items():
        tipo_valor = type(value).__name__
        valor_ejemplo = str(value)[:60] if value else "NULL"
        print(f"  • {key}: {tipo_valor} - Ejemplo: {valor_ejemplo}")

# Agrupar por código de producto
print("\n" + "=" * 80)
print("AGRUPACIÓN POR CÓDIGO DE PRODUCTO")
print("=" * 80)

aditivos_por_codigo = defaultdict(list)
for a in aditivos:
    codigo = a.get('codigo', 'SIN_CODIGO')
    aditivos_por_codigo[codigo].append(a)

print(f"\nTotal de códigos únicos: {len(aditivos_por_codigo)}")
print(f"Total de series/unidades: {len(aditivos)}")

# Mostrar todos los productos ordenados por cantidad
print("\nAditivos disponibles (ordenados por cantidad):")
aditivos_ordenados = sorted(aditivos_por_codigo.items(), key=lambda x: len(x[1]), reverse=True)

for i, (codigo, items) in enumerate(aditivos_ordenados, 1):
    descripcion = items[0].get('descripcion', 'Sin descripción')[:70]
    cantidad = len(items)
    print(f"\n{i:2}. {codigo}")
    print(f"    Descripción: {descripcion}")
    print(f"    Cantidad: {cantidad} unidad(es)")

# Análisis detallado de series
print("\n" + "=" * 80)
print("ANÁLISIS DE SERIES")
print("=" * 80)

aditivos_con_serie = [a for a in aditivos if a.get('serie')]
print(f"\nAditivos con número de serie: {len(aditivos_con_serie)}/{len(aditivos)}")

if aditivos_con_serie:
    print("\nEjemplos de aditivos con serie:")
    for i, a in enumerate(aditivos_con_serie[:5], 1):
        print(f"{i}. Código: {a.get('codigo', 'N/A')}")
        print(f"   Serie: {a.get('serie', 'N/A')}")
        print(f"   Descripción: {a.get('descripcion', 'N/A')[:60]}")
        print()

# Verificar campos adicionales
print("=" * 80)
print("CAMPOS ADICIONALES")
print("=" * 80)

campos_relevantes = ['stock', 'cantidad', 'unidad', 'familia', 'ubicacion', 'estado', 'almacen', 'lote']
print("\nCampos encontrados en los datos:")
for campo in campos_relevantes:
    valores = [a.get(campo) for a in aditivos[:10] if campo in a and a.get(campo)]
    if valores:
        print(f"  ✓ {campo}: {valores[:3]}")
    else:
        print(f"  ✗ {campo}: No encontrado o vacío")

# Listado completo de todos los aditivos
print("\n" + "=" * 80)
print("LISTADO DETALLADO - TODOS LOS ADITIVOS")
print("=" * 80)

for i, aditivo in enumerate(aditivos, 1):
    print(f"\n{i}. CÓDIGO: {aditivo.get('codigo', 'N/A')}")
    print(f"   SERIE: {aditivo.get('serie', 'N/A')}")
    print(f"   DESCRIPCIÓN: {aditivo.get('descripcion', 'N/A')}")
    # Mostrar otros campos si existen
    otros_campos = {k: v for k, v in aditivo.items() if k not in ['codigo', 'serie', 'descripcion'] and v}
    if otros_campos:
        for key, value in otros_campos.items():
            print(f"   {key.upper()}: {value}")

# Análisis de tipos de aditivos
print("\n" + "=" * 80)
print("CLASIFICACIÓN DE ADITIVOS")
print("=" * 80)

tipos_aditivos = {
    'BENTONITA': [],
    'CONTROLADOR': [],
    'ESTABILIZADOR': [],
    'POLÍMERO': [],
    'OTROS': []
}

for aditivo in aditivos:
    descripcion = aditivo.get('descripcion', '').upper()
    clasificado = False
    
    if 'BENTONITA' in descripcion:
        tipos_aditivos['BENTONITA'].append(aditivo)
        clasificado = True
    if 'CONTROLAD' in descripcion or 'PERDIDA' in descripcion:
        tipos_aditivos['CONTROLADOR'].append(aditivo)
        clasificado = True
    if 'ESTABILIZ' in descripcion:
        tipos_aditivos['ESTABILIZADOR'].append(aditivo)
        clasificado = True
    if 'POLÍMERO' in descripcion or 'POLYMER' in descripcion:
        tipos_aditivos['POLÍMERO'].append(aditivo)
        clasificado = True
    
    if not clasificado:
        tipos_aditivos['OTROS'].append(aditivo)

print("\nDistribución por tipo:")
for tipo, items in tipos_aditivos.items():
    if items:
        print(f"  • {tipo}: {len(items)} unidad(es)")

# Resumen final
print("\n" + "=" * 80)
print("RESUMEN EJECUTIVO")
print("=" * 80)

aditivo_mas_comun = max(aditivos_ordenados, key=lambda x: len(x[1]))

print(f"""
📊 Estadísticas del Stock de Aditivos:
  • Centro de Costo: {centro_costo}
  • Total de artículos/series: {len(aditivos)}
  • Códigos únicos: {len(aditivos_por_codigo)}
  • Aditivos con serie: {len(aditivos_con_serie)}
  
🔝 Aditivo con más stock:
  • Código: {aditivo_mas_comun[0]}
  • Cantidad: {len(aditivo_mas_comun[1])} unidad(es)
  • Descripción: {aditivo_mas_comun[1][0].get('descripcion', 'N/A')[:70]}

📦 Clasificación:
""")

for tipo, items in tipos_aditivos.items():
    if items:
        porcentaje = (len(items) / len(aditivos)) * 100
        print(f"  • {tipo}: {len(items)} ({porcentaje:.1f}%)")

print("""
✅ API funcionando correctamente
✅ Datos disponibles para integración en el sistema
""")

print("=" * 80)
print("Prueba completada exitosamente")
print("=" * 80)
