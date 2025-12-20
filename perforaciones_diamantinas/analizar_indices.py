"""
Script para analizar índices faltantes y sugerir optimizaciones
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import (
    Sondaje, Maquina, Trabajador, TipoComplemento, TipoAditivo
)

def check_indexes():
    """Verifica qué índices existen en las tablas principales"""
    print("\n" + "="*70)
    print("ANÁLISIS DE ÍNDICES EN LAS TABLAS")
    print("="*70)
    
    tables = [
        'sondajes',
        'maquinas',
        'trabajadores',
        'tipos_complemento',
        'tipos_aditivo',
        'tipo_turnos',
        'tipos_actividad',
        'unidades_medida'
    ]
    
    with connection.cursor() as cursor:
        for table in tables:
            print(f"\n{table.upper()}:")
            cursor.execute("""
                SELECT 
                    indexname, 
                    indexdef
                FROM pg_indexes 
                WHERE tablename = %s
                ORDER BY indexname
            """, [table])
            
            indexes = cursor.fetchall()
            if indexes:
                for idx_name, idx_def in indexes:
                    print(f"  ✓ {idx_name}")
                    if 'estado' in idx_def.lower():
                        print(f"    → Incluye campo 'estado'")
                    if 'contrato' in idx_def.lower():
                        print(f"    → Incluye campo 'contrato'")
            else:
                print(f"  ⚠ Sin índices adicionales (solo PK)")

def check_table_stats():
    """Obtiene estadísticas de las tablas para entender el problema de latencia"""
    print("\n" + "="*70)
    print("ESTADÍSTICAS DE TABLAS (ANALYZE)")
    print("="*70)
    
    tables = [
        ('sondajes', 'Sondajes'),
        ('maquinas', 'Maquinas'),
        ('trabajadores', 'Trabajadores'),
        ('tipos_complemento', 'TipoComplemento'),
        ('tipos_aditivo', 'TipoAditivo'),
    ]
    
    with connection.cursor() as cursor:
        for table_name, display_name in tables:
            cursor.execute(f"""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE tablename = '{table_name}'
            """)
            
            stats = cursor.fetchone()
            if stats:
                print(f"\n{display_name}:")
                print(f"  Filas vivas: {stats[5]}")
                print(f"  Filas muertas: {stats[6]}")
                print(f"  Último ANALYZE: {stats[9] or 'Nunca'}")
                
                if stats[6] > stats[5] * 0.2:  # Más de 20% filas muertas
                    print(f"  ⚠ ALERTA: {stats[6]} filas muertas ({stats[6]/max(stats[5],1)*100:.1f}%)")
                    print(f"    → Ejecutar VACUUM ANALYZE {table_name};")

def suggest_optimizations():
    """Sugiere optimizaciones basadas en el análisis"""
    print("\n" + "="*70)
    print("RECOMENDACIONES")
    print("="*70)
    
    print("\n1. ÍNDICES COMPUESTOS RECOMENDADOS:")
    print("   - sondajes: CREATE INDEX idx_sondajes_contrato_estado ON sondajes(contrato_id, estado);")
    print("   - maquinas: CREATE INDEX idx_maquinas_contrato_estado ON maquinas(contrato_id, estado);")
    print("   - trabajadores: CREATE INDEX idx_trabajadores_contrato_estado ON trabajadores(contrato_id, estado);")
    print("   - tipos_complemento: Ya tiene índice compuesto ✓")
    print("   - tipos_aditivo: CREATE INDEX idx_tipos_aditivo_contrato ON tipos_aditivo(contrato_id);")
    
    print("\n2. LATENCIA DE RED:")
    print("   El problema principal parece ser latencia de ~150ms por query")
    print("   Esto sugiere:")
    print("   - Conexión a BD remota con alta latencia")
    print("   - Pool de conexiones no configurado correctamente")
    print("   - Falta de connection pooling (pgBouncer)")
    
    print("\n3. CACHE DE QUERIES:")
    print("   Considera implementar caching de Django para datos estáticos:")
    print("   - TipoTurno (2 registros, casi nunca cambian)")
    print("   - UnidadMedida (1 registro, nunca cambia)")
    print("   - TipoActividad (82 registros, cambian poco)")
    
    print("\n4. CONNECTION POOLING:")
    print("   Configurar django-db-connection-pool o pgBouncer")
    print("   Esto reduce overhead de crear nuevas conexiones")
    
    print("\n5. PREFETCH EN TEMPLATE:")
    print("   Cargar todos los datos en una sola vista y renderizar en JavaScript")
    print("   Evitar múltiples queries al cargar el formulario")

def test_connection_speed():
    """Prueba la velocidad de conexión a PostgreSQL"""
    import time
    
    print("\n" + "="*70)
    print("PRUEBA DE VELOCIDAD DE CONEXIÓN")
    print("="*70)
    
    with connection.cursor() as cursor:
        # Prueba 1: Query simple
        start = time.time()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        elapsed1 = (time.time() - start) * 1000
        
        # Prueba 2: Query con COUNT
        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM trabajadores")
        cursor.fetchone()
        elapsed2 = (time.time() - start) * 1000
        
        # Prueba 3: Query con JOIN
        start = time.time()
        cursor.execute("""
            SELECT t.id, t.nombres, t.apellidos
            FROM trabajadores t 
            LIMIT 10
        """)
        cursor.fetchall()
        elapsed3 = (time.time() - start) * 1000
    
    print(f"\nQuery simple (SELECT 1): {elapsed1:.2f}ms")
    print(f"Query COUNT: {elapsed2:.2f}ms")
    print(f"Query SELECT (10 rows): {elapsed3:.2f}ms")
    
    if elapsed1 > 50:
        print("\n⚠ ALERTA: Latencia alta en query simple")
        print("  Esto indica problema de red o conexión PostgreSQL")
        print("  Latencia esperada: <10ms para BD local, <50ms para BD remota")
    else:
        print("\n✓ Latencia de conexión es aceptable")

if __name__ == '__main__':
    test_connection_speed()
    check_indexes()
    check_table_stats()
    suggest_optimizations()
    
    print("\n" + "="*70)
    print("SIGUIENTE PASO: Aplicar índices y optimizaciones sugeridas")
    print("="*70)
