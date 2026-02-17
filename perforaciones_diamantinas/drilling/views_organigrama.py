"""
Vista para el organigrama organizacional - Solo visualización

El organigrama muestra la estructura jerárquica de trabajadores por contrato
basándose en el nivel_jerarquico del cargo de cada trabajador.

Niveles:
- Nivel 1: Residente
- Nivel 2: Gerencias (Administrador, Jefe Logística, Ing. Seguridad, etc.)
- Nivel 3: Supervisión (Supervisores)
- Nivel 4: Operaciones (Perforistas, Ayudantes, Conductores, Técnicos)
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Contrato, Trabajador


@login_required
def organigrama_view(request):
    """Vista para mostrar el organigrama del contrato - Solo visualización"""
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
    
    # Obtener trabajadores activos del contrato
    trabajadores = Trabajador.objects.filter(
        contrato=contrato,
        estado='ACTIVO'
    ).order_by('cargo', 'apepat', 'nombres')
    
    # Organizar por jerarquía (4 niveles) - Heurística simple
    niveles = {1: [], 2: [], 3: [], 4: []}
    
    for trabajador in trabajadores:
        c = (trabajador.cargo or '').upper()
        if 'RESIDENTE' in c or 'GERENTE' in c:
            nivel = 1
        elif 'SUPERVISOR' in c or 'JEFE' in c:
            nivel = 2
        elif 'PERFORISTA' in c or 'OPERADOR' in c:
            nivel = 3
        else:
            nivel = 4
            
        niveles[nivel].append(trabajador)
    
    # Para nivel 4, agrupar por tipo de cargo
    nivel4_agrupado = {
        'perforistas': [],
        'ayudantes': [],
        'conductores': [],
        'tecnicos': [],
        'otros': []
    }
    
    for trabajador in niveles[4]:
        cargo_lower = trabajador.cargo.nombre.lower() if trabajador.cargo else ''
        
        if 'perforista' in cargo_lower:
            nivel4_agrupado['perforistas'].append(trabajador)
        elif 'ayudante' in cargo_lower:
            nivel4_agrupado['ayudantes'].append(trabajador)
        elif 'conductor' in cargo_lower:
            nivel4_agrupado['conductores'].append(trabajador)
        elif 'tecnico' in cargo_lower or 'técnico' in cargo_lower or 'mecanico' in cargo_lower or 'mecánico' in cargo_lower:
            nivel4_agrupado['tecnicos'].append(trabajador)
        else:
            nivel4_agrupado['otros'].append(trabajador)
    
    context = {
        'contrato': contrato,
        'niveles': niveles,
        'nivel4_agrupado': nivel4_agrupado,
        'contratos_disponibles': contratos_disponibles,
        'total_trabajadores': trabajadores.count(),
    }
    
    return render(request, 'drilling/organigrama/view.html', context)

