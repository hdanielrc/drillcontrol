"""
Script para medir el performance de la carga del template de crear turno completo
"""
import os
import sys
import django
import time
from django.db import connection, reset_queries
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from drilling.models import (
    Sondaje, Maquina, Trabajador, TipoTurno, TipoActividad,
    TipoComplemento, TipoAditivo, UnidadMedida, Contrato
)
from django.contrib.auth import get_user_model

User = get_user_model()

def measure_query(name, func):
    """Mide el tiempo de ejecución de una función y cuenta queries"""
    reset_queries()
    settings.DEBUG = True
    
    start = time.time()
    result = func()
    end = time.time()
    
    elapsed = (end - start) * 1000  # ms
    num_queries = len(connection.queries)
    
    print(f"\n{'='*70}")
    print(f"Query: {name}")
    print(f"Tiempo: {elapsed:.2f}ms")
    print(f"Queries ejecutadas: {num_queries}")
    
    if num_queries > 0:
        print(f"\nDetalle de queries:")
        for i, q in enumerate(connection.queries[:10], 1):  # Mostrar primeras 10
            print(f"{i}. {q['sql'][:150]}... ({q['time']}s)")
        if num_queries > 10:
            print(f"... y {num_queries - 10} queries más")
    
    print(f"{'='*70}")
    
    return result, elapsed, num_queries

def test_admin_queries():
    """Simula las queries de un usuario admin"""
    print("\n" + "="*70)
    print("PRUEBA: Usuario ADMIN (puede ver todos los contratos)")
    print("="*70)
    
    # Buscar un usuario admin
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No se encontró usuario admin, creando uno...")
        admin_user = User.objects.create_superuser('test_admin', 'admin@test.com', 'test123')
    
    total_time = 0
    total_queries = 0
    
    # 1. Sondajes
    _, t, q = measure_query(
        "Sondajes.filter(estado='ACTIVO').only()",
        lambda: list(Sondaje.objects.filter(estado='ACTIVO').only('id', 'nombre_sondaje', 'estado', 'contrato'))
    )
    total_time += t
    total_queries += q
    
    # 2. Maquinas
    _, t, q = measure_query(
        "Maquinas.filter(estado='OPERATIVO').only()",
        lambda: list(Maquina.objects.filter(estado='OPERATIVO').only('id', 'nombre', 'estado', 'contrato'))
    )
    total_time += t
    total_queries += q
    
    # 3. Trabajadores
    _, t, q = measure_query(
        "Trabajadores.select_related('cargo').only()",
        lambda: list(Trabajador.objects.filter(estado='ACTIVO').select_related('cargo').only(
            'id', 'nombres', 'apellidos', 'dni', 'estado', 'contrato', 'cargo__nombre'
        ))
    )
    total_time += t
    total_queries += q
    
    # 4. TiposTurno
    _, t, q = measure_query(
        "TipoTurno.objects.only()",
        lambda: list(TipoTurno.objects.only('id', 'nombre'))
    )
    total_time += t
    total_queries += q
    
    # 5. TiposActividad
    _, t, q = measure_query(
        "TipoActividad.objects.only()",
        lambda: list(TipoActividad.objects.only('id', 'nombre', 'descripcion_corta'))
    )
    total_time += t
    total_queries += q
    
    # 6. TiposComplemento (requiere contrato)
    contrato = Contrato.objects.first()
    if contrato:
        _, t, q = measure_query(
            "TipoComplemento.filter(contrato).select_related().only()",
            lambda: list(TipoComplemento.objects.filter(
                contrato=contrato,
                estado='NUEVO'
            ).select_related('contrato').only('id', 'nombre', 'codigo', 'serie', 'contrato'))
        )
        total_time += t
        total_queries += q
    
    # 7. TiposAditivo
    if contrato:
        _, t, q = measure_query(
            "TipoAditivo.filter(contrato).select_related().only()",
            lambda: list(TipoAditivo.objects.filter(
                contrato=contrato
            ).select_related('contrato').only('id', 'nombre', 'codigo', 'contrato'))
        )
        total_time += t
        total_queries += q
    
    # 8. UnidadesMedida
    _, t, q = measure_query(
        "UnidadMedida.objects.only()",
        lambda: list(UnidadMedida.objects.only('id', 'nombre', 'simbolo'))
    )
    total_time += t
    total_queries += q
    
    print(f"\n{'='*70}")
    print(f"RESUMEN TOTAL (Admin)")
    print(f"Tiempo total: {total_time:.2f}ms")
    print(f"Queries totales: {total_queries}")
    print(f"{'='*70}")
    
    return total_time, total_queries

def test_regular_user_queries():
    """Simula las queries de un usuario regular con contrato específico"""
    print("\n" + "="*70)
    print("PRUEBA: Usuario REGULAR (limitado a su contrato)")
    print("="*70)
    
    # Buscar un contrato y usuario regular
    contrato = Contrato.objects.first()
    if not contrato:
        print("No hay contratos disponibles")
        return 0, 0
    
    regular_user = User.objects.filter(contrato=contrato, is_superuser=False).first()
    if not regular_user:
        print(f"No se encontró usuario regular para contrato {contrato.nombre}")
        # Podríamos crear uno, pero por ahora solo reportamos
    
    total_time = 0
    total_queries = 0
    
    # 1. Sondajes filtrados por contrato
    _, t, q = measure_query(
        "Sondajes.filter(contrato, estado='ACTIVO').only()",
        lambda: list(Sondaje.objects.filter(contrato=contrato, estado='ACTIVO').only(
            'id', 'nombre_sondaje', 'estado', 'contrato'
        ))
    )
    total_time += t
    total_queries += q
    
    # 2. Maquinas filtradas por contrato
    _, t, q = measure_query(
        "Maquinas.filter(contrato, estado='OPERATIVO').only()",
        lambda: list(Maquina.objects.filter(contrato=contrato, estado='OPERATIVO').only(
            'id', 'nombre', 'estado', 'contrato'
        ))
    )
    total_time += t
    total_queries += q
    
    # 3. Trabajadores filtrados por contrato
    _, t, q = measure_query(
        "Trabajadores.filter(contrato).select_related('cargo').only()",
        lambda: list(Trabajador.objects.filter(contrato=contrato, estado='ACTIVO').select_related('cargo').only(
            'id', 'nombres', 'apellidos', 'dni', 'estado', 'contrato', 'cargo__nombre'
        ))
    )
    total_time += t
    total_queries += q
    
    # 4. TiposTurno
    _, t, q = measure_query(
        "TipoTurno.objects.only()",
        lambda: list(TipoTurno.objects.only('id', 'nombre'))
    )
    total_time += t
    total_queries += q
    
    # 5. TiposActividad (relacionadas al contrato)
    _, t, q = measure_query(
        "contrato.actividades.only()",
        lambda: list(contrato.actividades.only('id', 'nombre', 'descripcion_corta'))
    )
    total_time += t
    total_queries += q
    
    # 6. TiposComplemento
    _, t, q = measure_query(
        "TipoComplemento.filter(contrato).select_related().only()",
        lambda: list(TipoComplemento.objects.filter(
            contrato=contrato,
            estado='NUEVO'
        ).select_related('contrato').only('id', 'nombre', 'codigo', 'serie', 'contrato'))
    )
    total_time += t
    total_queries += q
    
    # 7. TiposAditivo
    _, t, q = measure_query(
        "TipoAditivo.filter(contrato).select_related().only()",
        lambda: list(TipoAditivo.objects.filter(
            contrato=contrato
        ).select_related('contrato').only('id', 'nombre', 'codigo', 'contrato'))
    )
    total_time += t
    total_queries += q
    
    # 8. UnidadesMedida
    _, t, q = measure_query(
        "UnidadMedida.objects.only()",
        lambda: list(UnidadMedida.objects.only('id', 'nombre', 'simbolo'))
    )
    total_time += t
    total_queries += q
    
    print(f"\n{'='*70}")
    print(f"RESUMEN TOTAL (Usuario Regular)")
    print(f"Tiempo total: {total_time:.2f}ms")
    print(f"Queries totales: {total_queries}")
    print(f"{'='*70}")
    
    return total_time, total_queries

def analyze_slowest_tables():
    """Analiza qué tablas tienen más registros y podrían ser más lentas"""
    print("\n" + "="*70)
    print("ANÁLISIS DE VOLUMETRÍA DE TABLAS")
    print("="*70)
    
    tables = [
        ('Sondaje', Sondaje),
        ('Maquina', Maquina),
        ('Trabajador', Trabajador),
        ('TipoTurno', TipoTurno),
        ('TipoActividad', TipoActividad),
        ('TipoComplemento', TipoComplemento),
        ('TipoAditivo', TipoAditivo),
        ('UnidadMedida', UnidadMedida),
    ]
    
    for name, model in tables:
        total = model.objects.count()
        activos = model.objects.filter(estado='ACTIVO').count() if hasattr(model, 'estado') else total
        print(f"{name:20s} - Total: {total:5d} | Activos: {activos:5d}")

if __name__ == '__main__':
    print("\n" + "="*70)
    print("PRUEBAS DE PERFORMANCE - CREAR TURNO COMPLETO")
    print("="*70)
    
    # Analizar volumetría
    analyze_slowest_tables()
    
    # Probar queries de admin
    admin_time, admin_queries = test_admin_queries()
    
    # Probar queries de usuario regular
    regular_time, regular_queries = test_regular_user_queries()
    
    print("\n" + "="*70)
    print("COMPARACIÓN FINAL")
    print("="*70)
    print(f"Admin:    {admin_time:.2f}ms ({admin_queries} queries)")
    print(f"Regular:  {regular_time:.2f}ms ({regular_queries} queries)")
    print(f"\nTiempo esperado de carga del template: ~{max(admin_time, regular_time):.0f}ms")
    print("="*70)
    
    print("\n✅ Análisis completado. Revisa los detalles arriba para identificar cuellos de botella.")
