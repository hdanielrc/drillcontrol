"""
Prueba detallada del Stock de Productos Diamantados (PDD) para CONDESTABLE
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
print("ANÁLISIS DE STOCK - PRODUCTOS DIAMANTADOS (PDD)")
print("CONTRATO: CONDESTABLE")
print("CENTRO DE COSTO: 000003")
print("=" * 80)

# Obtener cliente API
client = get_api_client()

# Obtener productos diamantados
print("\n🔄 Consultando API de Vilbragroup...")
productos = client.obtener_productos_diamantados(centro_costo=centro_costo)

if not productos:
    print("❌ No se obtuvieron productos")
    exit(1)

print(f"✅ Total de artículos: {len(productos)}")

# Analizar la estructura de datos
print("\n" + "=" * 80)
print("ESTRUCTURA DE DATOS")
print("=" * 80)

if productos:
    primer_producto = productos[0]
    print("\nCampos disponibles en cada artículo:")
    for key, value in primer_producto.items():
        tipo_valor = type(value).__name__
        print(f"  • {key}: {tipo_valor} - Ejemplo: {str(value)[:60]}")

# Agrupar por código de producto
print("\n" + "=" * 80)
print("AGRUPACIÓN POR CÓDIGO DE PRODUCTO")
print("=" * 80)

productos_por_codigo = defaultdict(list)
for p in productos:
    codigo = p.get('codigo', 'SIN_CODIGO')
    productos_por_codigo[codigo].append(p)

print(f"\nTotal de códigos únicos: {len(productos_por_codigo)}")
print(f"Total de series/unidades: {len(productos)}")

# Mostrar los 10 productos con más unidades
print("\nTop 10 productos con más unidades:")
top_productos = sorted(productos_por_codigo.items(), key=lambda x: len(x[1]), reverse=True)[:10]

for i, (codigo, items) in enumerate(top_productos, 1):
    descripcion = items[0].get('descripcion', 'Sin descripción')[:60]
    cantidad = len(items)
    print(f"{i:2}. {codigo} - {cantidad:3} unidades")
    print(f"    {descripcion}")

# Análisis detallado de series
print("\n" + "=" * 80)
print("ANÁLISIS DE SERIES")
print("=" * 80)

productos_con_serie = [p for p in productos if p.get('serie')]
print(f"\nProductos con número de serie: {len(productos_con_serie)}/{len(productos)}")

if productos_con_serie:
    print("\nEjemplos de productos con serie:")
    for i, p in enumerate(productos_con_serie[:5], 1):
        print(f"{i}. Código: {p.get('codigo', 'N/A')}")
        print(f"   Serie: {p.get('serie', 'N/A')}")
        print(f"   Descripción: {p.get('descripcion', 'N/A')[:60]}")
        print()

# Verificar campos adicionales
print("=" * 80)
print("CAMPOS ADICIONALES")
print("=" * 80)

campos_relevantes = ['stock', 'cantidad', 'unidad', 'familia', 'ubicacion', 'estado', 'almacen']
print("\nCampos encontrados en los datos:")
for campo in campos_relevantes:
    valores = [p.get(campo) for p in productos[:10] if campo in p]
    if valores:
        print(f"  ✓ {campo}: {valores[:3]}")
    else:
        print(f"  ✗ {campo}: No encontrado")

# Listado completo de los primeros 20 productos
print("\n" + "=" * 80)
print("LISTADO DETALLADO - PRIMEROS 20 PRODUCTOS")
print("=" * 80)

for i, producto in enumerate(productos[:20], 1):
    print(f"\n{i}. CÓDIGO: {producto.get('codigo', 'N/A')}")
    print(f"   SERIE: {producto.get('serie', 'N/A')}")
    print(f"   DESCRIPCIÓN: {producto.get('descripcion', 'N/A')}")
    # Mostrar otros campos si existen
    otros_campos = {k: v for k, v in producto.items() if k not in ['codigo', 'serie', 'descripcion']}
    if otros_campos:
        for key, value in otros_campos.items():
            print(f"   {key.upper()}: {value}")

# Resumen final
print("\n" + "=" * 80)
print("RESUMEN EJECUTIVO")
print("=" * 80)
print(f"""
📊 Estadísticas del Stock de Productos Diamantados:
  • Centro de Costo: {centro_costo}
  • Total de artículos/series: {len(productos)}
  • Códigos únicos: {len(productos_por_codigo)}
  • Productos con serie: {len(productos_con_serie)}
  
🔝 Producto con más stock:
  • Código: {top_productos[0][0]}
  • Cantidad: {len(top_productos[0][1])} unidades
  • Descripción: {top_productos[0][1][0].get('descripcion', 'N/A')[:60]}

✅ API funcionando correctamente
✅ Datos disponibles para integración en el sistema
""")

print("=" * 80)
print("Prueba completada exitosamente")
print("=" * 80)
