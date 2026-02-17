import os
import sys
import django
from decimal import Decimal

# Configurar el entorno de Django
# Asumiendo que el script está en la raíz del proyecto o en una subcarpeta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.getcwd()) # Add current directory for module resolution
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perforaciones_diamantinas.settings') 
try:
    django.setup()
except Exception as e:
    print(f"Error configuring Django settings: {e}")
    sys.exit(1)

from drilling.models import (
    Turno, TurnoTrabajador, TurnoSondaje, TurnoAvance, 
    TurnoActividad, TurnoComplemento, TurnoAditivo, TurnoCorrida
)

def validar_ultimo_turno():
    print("="*60)
    print(" QA/QC: VERIFICACIÓN DE INTEGRIDAD DE DATOS (ÚLTIMO TURNO)")
    print("="*60)

    # 1. Obtener el último turno creado
    try:
        ultimo_turno = Turno.objects.latest('id')
    except Turno.DoesNotExist:
        print(" [ERROR]: No hay turnos registrados en la base de datos.")
        return

    print(f"📌 TURNO ID: {ultimo_turno.id}")
    print(f"   Fecha: {ultimo_turno.fecha}")
    print(f"   Máquina: {ultimo_turno.maquina}")
    print(f"   Tipo: {ultimo_turno.tipo_turno}")
    print(f"   Estado: {ultimo_turno.estado}")
    print("-" * 60)

    # 2. Validar Sondajes (Many-to-Many a través de TurnoSondaje)
    turnos_sondaje = TurnoSondaje.objects.filter(turno=ultimo_turno)
    print(f"📍 SONDAJES ASOCIADOS ({turnos_sondaje.count()})")
    if turnos_sondaje.exists():
        for ts in turnos_sondaje:
            print(f"   - Sondaje: {ts.sondaje.nombre_sondaje} | Metros Turno: {ts.metros_turno}")
    else:
        print("   [ALERTA]: El turno no tiene sondajes asociados.")
    
    # 3. Validar Avance Total (TurnoAvance - OneToOne)
    try:
        if hasattr(ultimo_turno, 'avance'):
            avance = ultimo_turno.avance
            print(f"\n📏 AVANCE TOTAL (Tabla: turno_avance)")
            print(f"   - Metros Perforados: {avance.metros_perforados}")
        else:
            print("\n   [ALERTA]: No existe registro en tabla 'TurnoAvance'.")
    except Exception as e:
        print(f"   [ERROR leyendo avance]: {e}")

    # 4. Validar Trabajadores
    trabajadores = TurnoTrabajador.objects.filter(turno=ultimo_turno)
    print(f"\n👷 TRABAJADORES ({trabajadores.count()})")
    for tr in trabajadores:
        print(f"   - {tr.funcion}: {tr.trabajador.nombres} {tr.trabajador.apellidos}")

    # 5. Validar Corridas (Detalle de perforación)
    corridas = TurnoCorrida.objects.filter(turno=ultimo_turno).order_by('corrida_numero')
    print(f"\n📉 CORRIDAS DE PERFORACIÓN ({corridas.count()})")
    total_corridas = Decimal('0.00')
    for c in corridas:
        longitud = c.hasta - c.desde
        total_corridas += longitud
        print(f"   - #{c.corrida_numero}: De {c.desde} a {c.hasta} ({longitud}m) - Rec: {c.pct_recuperacion}%")
    
    print(f"   >> Suma calculada de corridas: {total_corridas}m")
    
    # Cross-check
    if hasattr(ultimo_turno, 'avance'):
        if abs(total_corridas - ultimo_turno.avance.metros_perforados) < Decimal('0.01'):
            print("   ✅ [OK] La suma de corridas coincide con el avance total.")
        else:
            print("   ❌ [FAIL] Discrepancia: Suma corridas != Avance total.")

    # 6. Validar Actividades
    actividades = TurnoActividad.objects.filter(turno=ultimo_turno).order_by('hora_inicio')
    print(f"\n⏱️ CONTROL DE TIEMPOS (ACTIVIDADES) ({actividades.count()})")
    for act in actividades:
        print(f"   - {act.hora_inicio} a {act.hora_fin}: {act.actividad.nombre}")

    # 7. Validar Consumos
    aditivos = TurnoAditivo.objects.filter(turno=ultimo_turno)
    complementos = TurnoComplemento.objects.filter(turno=ultimo_turno)
    
    print(f"\n📦 CONSUMIBLES")
    print(f"   - Aditivos registrados: {aditivos.count()}")
    for a in aditivos:
         # Acceso seguro a nombre
         try:
            nombre_aditivo = a.tipo_aditivo.nombre if a.tipo_aditivo else "N/A"
         except:
            nombre_aditivo = "Desconocido"
         print(f"     * {nombre_aditivo}: {a.cantidad_usada}")

    print(f"   - Herramientas/Complementos: {complementos.count()}")
    for c in complementos:
         try:
            nombre_comp = c.tipo_complemento.nombre if c.tipo_complemento else "N/A"
         except:
            nombre_comp = "Desconocido"
         print(f"     * {nombre_comp} (Serie: {c.codigo_serie})")

    print("\n" + "="*60)
    print(" FIN DE LA VERIFICACIÓN")
    print("="*60)

if __name__ == "__main__":
    validar_ultimo_turno()
