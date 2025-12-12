"""
Script de diagnóstico para verificar metas y turnos
Ejecutar con: python manage.py shell < test_metas_debug.py
"""

from drilling.models import MetaMaquina, Turno, TurnoAvance
from django.db.models import Sum
from decimal import Decimal

print("\n" + "="*60)
print("DIAGNÓSTICO DE METAS Y TURNOS")
print("="*60)

# Verificar metas
metas = MetaMaquina.objects.all()
print(f"\n📊 Total de metas registradas: {metas.count()}")

if metas.count() == 0:
    print("\n⚠️  NO HAY METAS REGISTRADAS")
    print("   Crea una meta desde /metas/nueva/")
else:
    for meta in metas:
        print(f"\n{'='*60}")
        print(f"Meta ID: {meta.id}")
        print(f"Máquina: {meta.maquina.nombre}")
        print(f"Contrato: {meta.contrato.nombre_contrato}")
        print(f"Año: {meta.año}, Mes: {meta.mes}")
        
        fecha_inicio = meta.get_fecha_inicio_periodo()
        fecha_fin = meta.get_fecha_fin_periodo()
        print(f"Período: {fecha_inicio} a {fecha_fin}")
        print(f"Meta: {meta.meta_metros}m")
        
        # Buscar turnos en el período
        turnos_periodo = Turno.objects.filter(
            maquina=meta.maquina,
            contrato=meta.contrato,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        )
        
        print(f"\n🔍 Turnos encontrados en el período:")
        print(f"   Total: {turnos_periodo.count()}")
        
        if turnos_periodo.count() > 0:
            for turno in turnos_periodo[:5]:  # Primeros 5
                print(f"   - Turno #{turno.id}: {turno.fecha} | Estado: {turno.estado}")
                try:
                    avance = turno.avance
                    print(f"     Metros: {avance.metros_perforados}m")
                except:
                    print(f"     ⚠️  Sin avance registrado")
        
        # Calcular metros reales
        turnos_con_avance = TurnoAvance.objects.filter(
            turno__maquina=meta.maquina,
            turno__contrato=meta.contrato,
            turno__fecha__gte=fecha_inicio,
            turno__fecha__lte=fecha_fin
        )
        
        print(f"\n📏 Turnos con avance:")
        print(f"   Total: {turnos_con_avance.count()}")
        
        # Sin filtrar por estado
        metros_totales = turnos_con_avance.aggregate(
            total=Sum('metros_perforados')
        )['total'] or Decimal('0')
        
        print(f"   Metros totales (todos): {metros_totales}m")
        
        # Filtrar por estado
        turnos_aprobados = turnos_con_avance.filter(
            turno__estado__in=['COMPLETADO', 'APROBADO']
        )
        
        metros_aprobados = turnos_aprobados.aggregate(
            total=Sum('metros_perforados')
        )['total'] or Decimal('0')
        
        print(f"   Metros aprobados: {metros_aprobados}m")
        print(f"   Turnos aprobados: {turnos_aprobados.count()}")
        
        # Estados de turnos
        print(f"\n📋 Estados de turnos en el período:")
        estados = turnos_periodo.values_list('estado', flat=True)
        for estado in set(estados):
            count = turnos_periodo.filter(estado=estado).count()
            print(f"   - {estado}: {count} turnos")
        
        # Cumplimiento
        if meta.meta_metros > 0:
            cumplimiento = (metros_aprobados / meta.meta_metros) * 100
            print(f"\n✅ Cumplimiento: {cumplimiento:.2f}%")

print("\n" + "="*60)
print("FIN DEL DIAGNÓSTICO")
print("="*60 + "\n")
