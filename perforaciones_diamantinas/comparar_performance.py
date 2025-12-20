"""
Comparación de performance ANTES vs DESPUÉS del caching
"""
import os
import sys
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings')
django.setup()

from django.db import connection, reset_queries
from django.conf import settings
from django.core.cache import cache
from drilling.models import (
    Sondaje, Maquina, Trabajador, TipoTurno, TipoActividad,
    TipoComplemento, TipoAditivo, UnidadMedida, Contrato
)

def test_with_caching():
    """Simula get_context_data CON caching"""
    print("\n" + "="*70)
    print("PRUEBA: get_context_data CON CACHING")
    print("="*70)
    
    reset_queries()
    settings.DEBUG = True
    contract = Contrato.objects.first()
    
    start = time.time()
    
    # Simular las queries de get_context_data con cache
    # 1. Sondajes (NO cacheado - datos dinámicos)
    sondajes = list(Sondaje.objects.filter(contrato=contract, estado='ACTIVO').only(
        'id', 'nombre_sondaje', 'estado', 'contrato'
    ))
    
    # 2. Maquinas (NO cacheado - datos dinámicos)
    maquinas = list(Maquina.objects.filter(contrato=contract, estado='OPERATIVO').only(
        'id', 'nombre', 'estado', 'contrato'
    ))
    
    # 3. Trabajadores (NO cacheado - datos dinámicos)
    trabajadores = list(Trabajador.objects.filter(contrato=contract, estado='ACTIVO').select_related('cargo').only(
        'id', 'nombres', 'apellidos', 'dni', 'estado', 'contrato', 'cargo__nombre'
    ))
    
    # 4. TipoTurno (CACHEADO)
    tipos_turno = cache.get('tipos_turno_all')
    
    # 5. TipoActividad (CACHEADO para admin)
    actividades = cache.get('tipos_actividad_all')
    
    # 6. TipoComplemento (NO cacheado - depende de estado)
    complementos = list(TipoComplemento.objects.filter(
        contrato=contract,
        estado='NUEVO'
    ).select_related('contrato').only('id', 'nombre', 'codigo', 'serie', 'contrato'))
    
    # 7. TipoAditivo (NO cacheado - puede cambiar)
    aditivos = list(TipoAditivo.objects.filter(
        contrato=contract
    ).select_related('contrato').only('id', 'nombre', 'codigo', 'contrato'))
    
    # 8. UnidadMedida (CACHEADO)
    unidades = cache.get('unidades_medida_all')
    
    end = time.time()
    elapsed = (end - start) * 1000
    num_queries = len(connection.queries)
    
    print(f"\n✅ Tiempo total: {elapsed:.2f}ms")
    print(f"✅ Queries ejecutadas: {num_queries}")
    print(f"\nDatos obtenidos:")
    print(f"  - Sondajes: {len(sondajes)}")
    print(f"  - Maquinas: {len(maquinas)}")
    print(f"  - Trabajadores: {len(trabajadores)}")
    print(f"  - TipoTurno: {len(tipos_turno) if tipos_turno else 'No cached'}")
    print(f"  - TipoActividad: {len(actividades) if actividades else 'No cached'}")
    print(f"  - TipoComplemento: {len(complementos)}")
    print(f"  - TipoAditivo: {len(aditivos)}")
    print(f"  - UnidadMedida: {len(unidades) if unidades else 'No cached'}")
    
    return elapsed, num_queries

def test_without_caching():
    """Simula get_context_data SIN caching (método anterior)"""
    print("\n" + "="*70)
    print("PRUEBA: get_context_data SIN CACHING (método anterior)")
    print("="*70)
    
    # Limpiar cache para simular sin caching
    cache.delete('tipos_turno_all')
    cache.delete('tipos_actividad_all')
    cache.delete('unidades_medida_all')
    
    reset_queries()
    settings.DEBUG = True
    contract = Contrato.objects.first()
    
    start = time.time()
    
    # Todas las queries sin cache
    sondajes = list(Sondaje.objects.filter(contrato=contract, estado='ACTIVO').only(
        'id', 'nombre_sondaje', 'estado', 'contrato'
    ))
    maquinas = list(Maquina.objects.filter(contrato=contract, estado='OPERATIVO').only(
        'id', 'nombre', 'estado', 'contrato'
    ))
    trabajadores = list(Trabajador.objects.filter(contrato=contract, estado='ACTIVO').select_related('cargo').only(
        'id', 'nombres', 'apellidos', 'dni', 'estado', 'contrato', 'cargo__nombre'
    ))
    tipos_turno = list(TipoTurno.objects.values('id', 'nombre'))
    actividades = list(TipoActividad.objects.values('id', 'nombre', 'descripcion_corta'))
    complementos = list(TipoComplemento.objects.filter(
        contrato=contract,
        estado='NUEVO'
    ).select_related('contrato').only('id', 'nombre', 'codigo', 'serie', 'contrato'))
    aditivos = list(TipoAditivo.objects.filter(
        contrato=contract
    ).select_related('contrato').only('id', 'nombre', 'codigo', 'contrato'))
    unidades = list(UnidadMedida.objects.values('id', 'nombre', 'simbolo'))
    
    end = time.time()
    elapsed = (end - start) * 1000
    num_queries = len(connection.queries)
    
    print(f"\n✅ Tiempo total: {elapsed:.2f}ms")
    print(f"✅ Queries ejecutadas: {num_queries}")
    
    # Recargar cache para próximas pruebas
    cache.set('tipos_turno_all', tipos_turno, timeout=86400)
    cache.set('tipos_actividad_all', actividades, timeout=3600)
    cache.set('unidades_medida_all', unidades, timeout=86400)
    
    return elapsed, num_queries

if __name__ == '__main__':
    print("\n" + "="*70)
    print("COMPARACIÓN: ANTES vs DESPUÉS del CACHING")
    print("="*70)
    
    # Probar SIN caching primero
    time_without, queries_without = test_without_caching()
    
    # Pequeña pausa para evitar efectos de cache de PostgreSQL
    time.sleep(0.5)
    
    # Probar CON caching
    time_with, queries_with = test_with_caching()
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE MEJORAS")
    print("="*70)
    print(f"\nSIN CACHING:")
    print(f"  Tiempo: {time_without:.2f}ms")
    print(f"  Queries: {queries_without}")
    
    print(f"\nCON CACHING:")
    print(f"  Tiempo: {time_with:.2f}ms")
    print(f"  Queries: {queries_with}")
    
    print(f"\nMEJORAS:")
    time_saved = time_without - time_with
    queries_saved = queries_without - queries_with
    percent_time = (time_saved / time_without * 100) if time_without > 0 else 0
    percent_queries = (queries_saved / queries_without * 100) if queries_without > 0 else 0
    
    print(f"  ✅ Tiempo ahorrado: {time_saved:.2f}ms ({percent_time:.1f}% más rápido)")
    print(f"  ✅ Queries ahorradas: {queries_saved} ({percent_queries:.1f}% menos queries)")
    
    print("\n" + "="*70)
    print("NOTA: El mayor impacto es la reducción de queries.")
    print("Con latencia de ~160ms por query, ahorrar 3 queries = ~480ms")
    print("="*70)
