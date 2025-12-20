"""
Test de latencia de conexión a PostgreSQL LOCAL
"""
import os
import sys
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.db import connection
from django.conf import settings

def test_connection_latency():
    """Prueba la latencia real de la conexión PostgreSQL"""
    
    print("\n" + "="*70)
    print("PRUEBA DE LATENCIA - POSTGRESQL LOCAL")
    print("="*70)
    
    # Mostrar configuración actual
    db_config = settings.DATABASES['default']
    print(f"\nConfiguración actual:")
    print(f"  Host: {db_config['HOST']}")
    print(f"  Puerto: {db_config['PORT']}")
    print(f"  Base de datos: {db_config['NAME']}")
    print(f"  Usuario: {db_config['USER']}")
    
    # Forzar nueva conexión
    connection.close()
    
    # Test 1: Query simple
    latencies = []
    for i in range(10):
        with connection.cursor() as cursor:
            start = time.time()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
    
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    
    print(f"\n{'='*70}")
    print(f"RESULTADOS (10 queries 'SELECT 1')")
    print(f"{'='*70}")
    print(f"  Latencia promedio: {avg_latency:.2f}ms")
    print(f"  Latencia mínima:   {min_latency:.2f}ms")
    print(f"  Latencia máxima:   {max_latency:.2f}ms")
    
    # Diagnóstico
    print(f"\n{'='*70}")
    print(f"DIAGNÓSTICO")
    print(f"{'='*70}")
    
    if avg_latency < 10:
        print(f"  ✅ EXCELENTE - Base de datos local funcionando perfectamente")
        print(f"  ✅ Latencia esperada para localhost")
    elif avg_latency < 50:
        print(f"  🟡 ACEPTABLE - Conexión local pero con overhead")
        print(f"  Posible causa: PostgreSQL con configuración no optimizada")
    elif avg_latency < 100:
        print(f"  ⚠️  LENTA - No parece conexión local")
        print(f"  Posible causa: PostgreSQL en red local pero no localhost")
    else:
        print(f"  🔴 MUY LENTA - Probablemente conectando a BD remota")
        print(f"  ⚠️  VERIFICAR: ¿Está PostgreSQL corriendo localmente?")
        print(f"  ⚠️  VERIFICAR: ¿Las variables de entorno están configuradas?")
    
    # Verificar si realmente es localhost
    print(f"\n{'='*70}")
    print(f"VERIFICACIÓN DE HOST")
    print(f"{'='*70}")
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT inet_server_addr(), inet_server_port()")
        result = cursor.fetchone()
        if result[0]:
            print(f"  Dirección del servidor: {result[0]}:{result[1]}")
        else:
            print(f"  ✅ Conexión vía Unix socket o localhost")
    
    return avg_latency

if __name__ == '__main__':
    avg = test_connection_latency()
    
    print(f"\n{'='*70}")
    if avg < 10:
        print(f"RESULTADO: ✅ Base de datos local configurada correctamente")
        print(f"El problema de latencia de 160ms está RESUELTO")
    else:
        print(f"RESULTADO: ⚠️  Todavía hay problemas de latencia")
        print(f"Revisar configuración de PostgreSQL o variables de entorno")
    print(f"{'='*70}\n")
