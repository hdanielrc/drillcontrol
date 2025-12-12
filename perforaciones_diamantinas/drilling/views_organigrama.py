"""
Vista para el organigrama organizacional con gestión semanal

IMPORTANTE: Ahora las asignaciones se guardan por semana en la tabla AsignacionOrganigrama
permitiendo edición, histórico y consulta similar al tareo mensual.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, timedelta
from .models import (
    Contrato, Trabajador, Maquina, Vehiculo, Equipo,
    OrganigramaSemanal, AsignacionOrganigrama, GuardiaConductor, AsignacionEquipo
)


def obtener_semana_actual():
    """Obtiene la fecha de inicio y fin de la semana actual (Lunes a Domingo)"""
    hoy = datetime.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
    fin_semana = inicio_semana + timedelta(days=6)  # Domingo
    return inicio_semana, fin_semana


@login_required
def organigrama_view(request):
    """Vista para mostrar el organigrama del contrato con gestión semanal"""
    user = request.user
    
    # Determinar contratos accesibles
    if user.has_access_to_all_contracts():
        contrato_id = request.GET.get('contrato')
        if contrato_id:
            try:
                contrato = Contrato.objects.get(id=contrato_id, estado='ACTIVO')
            except Contrato.DoesNotExist:
                messages.error(request, 'Contrato no encontrado')
                contrato = None
        else:
            contrato = Contrato.objects.filter(estado='ACTIVO').first()
        
        contratos_disponibles = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    else:
        contrato = user.contrato
        contratos_disponibles = None
    
    if not contrato:
        messages.warning(request, 'No hay contratos activos disponibles')
        return redirect('dashboard')
    
    # Obtener fecha de semana (desde query params o semana actual)
    fecha_inicio_str = request.GET.get('fecha_inicio')
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            # Ajustar al lunes de esa semana
            fecha_inicio = fecha_inicio - timedelta(days=fecha_inicio.weekday())
        except:
            fecha_inicio, _ = obtener_semana_actual()
    else:
        fecha_inicio, _ = obtener_semana_actual()
    
    fecha_fin = fecha_inicio + timedelta(days=6)
    semana_numero = fecha_inicio.isocalendar()[1]
    anio = fecha_inicio.year
    
    # Obtener o crear organigrama semanal
    organigrama_semanal, created = OrganigramaSemanal.objects.get_or_create(
        contrato=contrato,
        anio=anio,
        semana_numero=semana_numero,
        defaults={
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'creado_por': user
        }
    )
    
    if not created and request.method == 'POST':
        organigrama_semanal.modificado_por = user
        organigrama_semanal.save()
    
    # Obtener trabajadores activos del contrato
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).select_related('cargo').order_by('cargo__nivel_jerarquico', 'apellidos', 'nombres')
    
    # Organizar por jerarquía (4 niveles)
    niveles = {1: [], 2: [], 3: [], 4: []}
    
    for trabajador in trabajadores:
        nivel = trabajador.cargo.nivel_jerarquico
        if nivel in [1, 2, 3, 4]:
            niveles[nivel].append(trabajador)
    
    # Obtener asignaciones existentes para esta semana
    asignaciones_existentes = AsignacionOrganigrama.objects.filter(
        organigrama_semanal=organigrama_semanal
    ).select_related('trabajador', 'maquina')
    
    # Crear diccionario de asignaciones por trabajador
    asignaciones_dict = {
        asig.trabajador.id: asig for asig in asignaciones_existentes
    }
    
    # Clasificar trabajadores del nivel 4
    trabajadores_nivel4 = niveles[4]
    conductores = []
    personal_standby = []
    trabajadores_operativos = []
    
    for trabajador in trabajadores_nivel4:
        cargo_lower = trabajador.cargo.nombre.lower()
        asignacion = asignaciones_dict.get(trabajador.id)
        
        # Clasificar conductores primero
        if 'conductor' in cargo_lower:
            conductores.append({
                'trabajador': trabajador,
                'asignacion': asignacion
            })
        # Si tiene asignación y está operativo con máquina asignada
        elif asignacion and asignacion.estado == 'OPERATIVO' and asignacion.maquina:
            trabajadores_operativos.append({
                'trabajador': trabajador,
                'asignacion': asignacion
            })
        # Todos los demás van a Stand By (sin asignación o marcados como Stand By)
        else:
            personal_standby.append({
                'trabajador': trabajador,
                'asignacion': asignacion
            })
    
    # Estructura de asignaciones por máquina: {maquina_id: {guardia: [trabajadores]}}
    asignaciones_actuales = {}
    for asig in asignaciones_existentes:
        if asig.maquina and asig.guardia and asig.estado == 'OPERATIVO':
            maq_id = asig.maquina.id
            guardia = asig.guardia
            
            if maq_id not in asignaciones_actuales:
                asignaciones_actuales[maq_id] = {
                    'maquina': asig.maquina,
                    'guardias': {'A': [], 'B': [], 'C': []}
                }
            
            asignaciones_actuales[maq_id]['guardias'][guardia].append(asig.trabajador)
    
    # Obtener guardias de conductores
    guardias_conductores = GuardiaConductor.objects.filter(
        organigrama_semanal=organigrama_semanal
    ).select_related('conductor', 'vehiculo')
    
    # Organizar guardias de conductores por guardia
    conductores_por_guardia = {'A': [], 'B': [], 'C': []}
    for guardia_cond in guardias_conductores:
        conductores_por_guardia[guardia_cond.guardia].append(guardia_cond)
    
    # Obtener máquinas y vehículos del contrato
    maquinas_disponibles = Maquina.objects.filter(
        contrato=contrato,
        estado='OPERATIVO'
    ).order_by('nombre')
    
    vehiculos_disponibles = Vehiculo.objects.filter(
        contrato=contrato,
        estado='OPERATIVO'
    ).order_by('placa')
    
    # Obtener equipos disponibles del contrato
    equipos_disponibles = Equipo.objects.filter(
        contrato=contrato,
        estado__in=['DISPONIBLE', 'ASIGNADO']
    ).order_by('tipo', 'codigo_interno')
    
    # Obtener asignaciones de equipos actuales para esta semana
    asignaciones_equipos = AsignacionEquipo.objects.filter(
        organigrama_semanal=organigrama_semanal,
        estado='ACTIVO'
    ).select_related('trabajador', 'equipo')
    
    # Organizar equipos por trabajador
    equipos_por_trabajador = {}
    for asig_equipo in asignaciones_equipos:
        trabajador_id = asig_equipo.trabajador.id
        if trabajador_id not in equipos_por_trabajador:
            equipos_por_trabajador[trabajador_id] = []
        equipos_por_trabajador[trabajador_id].append(asig_equipo)
    
    # Navegación de semanas
    semana_anterior = fecha_inicio - timedelta(days=7)
    semana_siguiente = fecha_inicio + timedelta(days=7)
    
    context = {
        'contrato': contrato,
        'organigrama_semanal': organigrama_semanal,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'semana_numero': semana_numero,
        'anio': anio,
        'semana_anterior': semana_anterior,
        'semana_siguiente': semana_siguiente,
        'niveles': niveles,
        'maquinas_disponibles': maquinas_disponibles,
        'vehiculos_disponibles': vehiculos_disponibles,
        'equipos_disponibles': equipos_disponibles,
        'equipos_por_trabajador': equipos_por_trabajador,
        'conductores': conductores,
        'personal_standby': personal_standby,
        'trabajadores_operativos': trabajadores_operativos,
        'asignaciones_actuales': asignaciones_actuales,
        'conductores_por_guardia': conductores_por_guardia,
        'contratos_disponibles': contratos_disponibles,
        'total_trabajadores': trabajadores.count(),
    }
    
    return render(request, 'drilling/organigrama/view.html', context)

