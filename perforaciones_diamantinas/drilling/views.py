import json
from decimal import Decimal
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.db import transaction, models
from django.db.models import Sum, Count, Avg, Max, Min, OuterRef, Subquery
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from .models import *
from .mixins import AdminOrContractFilterMixin, SystemAdminRequiredMixin
from .forms import *
from .utils.excel_importer import AbastecimientoExcelImporter

from datetime import datetime, time, timedelta
import json

def convert_to_time(value):
    """Convierte 'HH:MM' o 'HH:MM:SS' a time, o devuelve None si estÃ¡ vacÃ­o o invÃ¡lido."""
    if not value:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        parts = s.split(':')
        try:
            h = int(parts[0]); m = int(parts[1]) if len(parts) > 1 else 0; s_ = int(parts[2]) if len(parts) > 2 else 0
            return time(h, m, s_)
        except Exception:
            return None
    return None

# ===============================
# AUTHENTICATION VIEWS
# ===============================

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Credenciales incorrectas o usuario inactivo')
    return render(request, 'drilling/login.html')

@login_required
@require_http_methods(["POST", "GET"])
def user_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    # Si es GET, redirigir al dashboard con mensaje
    messages.warning(request, 'Por favor use el botÃ³n de cerrar sesiÃ³n correctamente.')
    return redirect('dashboard')

# ===============================
# DASHBOARD
# ===============================
@login_required
def dashboard(request):
    user = request.user
    contract = user.contrato
    hoy = timezone.now().date()
    
    # Determinar quÃ© template usar segÃºn el rol
    is_admin = user.role in ['GERENCIA', 'CONTROL_PROYECTOS'] and user.is_system_admin
    is_manager = user.role == 'ADMINISTRADOR'
    
    # DASHBOARD PARA ADMINISTRADOR DEL SISTEMA
    if is_admin:
        # MÃ©tricas consolidadas de todos los contratos
        contratos_activos = Contrato.objects.filter(estado='ACTIVO').count()
        usuarios_activos = CustomUser.objects.filter(is_active=True, is_account_active=True).count()
        
        # Metros perforados del mes (todos los contratos)
        metros_perforados_mes = TurnoAvance.objects.filter(
            turno__fecha__month=hoy.month,
            turno__fecha__year=hoy.year
        ).aggregate(total=models.Sum('metros_perforados'))['total'] or 0
        
        # Turnos hoy (todos los contratos)
        turnos_hoy_total = Turno.objects.filter(fecha=hoy).count()
        
        # MÃ©tricas por contrato - OPTIMIZADO con annotate para evitar N+1 queries
        from django.db.models import Q, Count, Sum, F
        
        # Calcular metros usando subconsulta para evitar duplicación por ManyToMany
        # Subconsulta para metros perforados del mes actual
        metros_subquery = TurnoAvance.objects.filter(
            turno__contrato=OuterRef('pk'),
            turno__fecha__month=hoy.month,
            turno__fecha__year=hoy.year
        ).values('turno__contrato').annotate(
            total=Sum('metros_perforados')
        ).values('total')
        
        metricas_por_contrato_qs = Contrato.objects.filter(
            estado='ACTIVO'
        ).select_related('cliente').annotate(
            sondajes_activos_count=Count('sondajes', filter=Q(sondajes__estado='ACTIVO'), distinct=True),
            trabajadores_activos_count=Count('trabajadores', filter=Q(trabajadores__estado='ACTIVO'), distinct=True),
            turnos_mes_count=Count(
                'turnos',
                filter=Q(turnos__fecha__month=hoy.month, turnos__fecha__year=hoy.year),
                distinct=True
            ),
            metros_mes_total=Subquery(metros_subquery)
        ).order_by('nombre_contrato')
        
        # Convertir a lista de diccionarios para el template
        metricas_por_contrato = []
        for contrato in metricas_por_contrato_qs:
            metricas_por_contrato.append({
                'nombre_contrato': contrato.nombre_contrato,
                'cliente': contrato.cliente.nombre,
                'sondajes_activos': contrato.sondajes_activos_count,
                'trabajadores_activos': contrato.trabajadores_activos_count,
                'turnos_mes': contrato.turnos_mes_count,
                'metros_mes': contrato.metros_mes_total or 0,
                'estado': contrato.estado,
            })
        
        # Ãšltimos turnos (todos los contratos)
        ultimos_turnos_raw = Turno.objects.select_related(
            'tipo_turno'
        ).prefetch_related('sondajes__contrato').order_by('-fecha')[:10]
        
        ultimos_turnos = []
        for turno in ultimos_turnos_raw:
            # Obtener el nombre del contrato del primer sondaje
            primer_sondaje = turno.sondajes.first()
            contrato_nombre = primer_sondaje.contrato.nombre_contrato if primer_sondaje else 'N/A'
            turno.contrato_nombre = contrato_nombre
            ultimos_turnos.append(turno)
        
        # Stock crÃ­tico (todos los contratos) - OPTIMIZADO con annotate
        try:
            from django.db.models import F, DecimalField, ExpressionWrapper
            
            stock_critico = Abastecimiento.objects.select_related(
                'unidad_medida', 'contrato'
            ).annotate(
                total_consumido=Sum('consumostock__cantidad_consumida'),
                disponible=ExpressionWrapper(
                    F('cantidad') - Sum('consumostock__cantidad_consumida'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ).filter(
                disponible__lte=5
            ).order_by('disponible')[:10]
            
            # Convertir a lista de diccionarios
            stock_critico_list = []
            for abast in stock_critico:
                stock_critico_list.append({
                    'descripcion': abast.descripcion,
                    'disponible': abast.disponible or 0,
                    'unidad_medida': abast.unidad_medida,
                    'contrato_nombre': abast.contrato.nombre_contrato if abast.contrato else 'N/A',
                })
            stock_critico = stock_critico_list
        except Exception as e:
            print(f"Error en stock crÃ­tico: {e}")
            stock_critico = []
        
        context = {
            'contratos_activos': contratos_activos,
            'usuarios_activos': usuarios_activos,
            'metros_perforados_mes': metros_perforados_mes,
            'turnos_hoy_total': turnos_hoy_total,
            'metricas_por_contrato': metricas_por_contrato,
            'ultimos_turnos': ultimos_turnos,
            'stock_critico': stock_critico,
        }
        
        return render(request, 'drilling/dashboards/admin_dashboard.html', context)
    
    # DASHBOARD PARA MANAGER DE CONTRATO
    elif is_manager:
        # Verificar que el manager tenga contrato asignado
        if not contract:
            messages.warning(request, 'No tienes un contrato asignado. Contacta al administrador.')
            return redirect('logout')
        
        # MÃ©tricas del contrato del manager - OPTIMIZADO
        trabajadores_activos = Trabajador.objects.filter(contrato=contract, estado='ACTIVO').count()
        
        # Trabajadores presentes hoy (basado en turnos del contrato)
        trabajadores_presentes_hoy = TurnoTrabajador.objects.filter(
            turno__contrato=contract,
            turno__fecha=hoy
        ).values('trabajador').distinct().count()
        
        sondajes_activos = Sondaje.objects.filter(contrato=contract, estado='ACTIVO').count()
        turnos_hoy = Turno.objects.filter(contrato=contract, fecha=hoy).count()
        
        maquinas_operativas = Maquina.objects.filter(contrato=contract, estado='OPERATIVO').count()
        
        # Ãšltimos turnos del contrato - OPTIMIZADO
        ultimos_turnos = Turno.objects.filter(
            contrato=contract
        ).select_related('tipo_turno', 'maquina').prefetch_related('sondajes').order_by('-fecha')[:5]
        
        # Trabajadores recientes
        trabajadores_recientes = Trabajador.objects.filter(
            contrato=contract
        ).select_related('cargo').order_by('-id')[:5]
        
        context = {
            'trabajadores_activos': trabajadores_activos,
            'trabajadores_presentes_hoy': trabajadores_presentes_hoy,
            'sondajes_activos': sondajes_activos,
            'turnos_hoy': turnos_hoy,
            'maquinas_operativas': maquinas_operativas,
            'ultimos_turnos': ultimos_turnos,
            'trabajadores_recientes': trabajadores_recientes,
        }
        
        return render(request, 'drilling/dashboards/manager_dashboard.html', context)
    
    # DASHBOARD DEFAULT (otros roles - por ahora usan el de manager)
    else:
        # Si no tiene contrato, asignar uno por defecto
        if not contract:
            cliente, _ = Cliente.objects.get_or_create(nombre='Cliente Demo')
            contrato_obj, _ = Contrato.objects.get_or_create(
                nombre_contrato='Sistema Principal',
                defaults={'cliente': cliente, 'duracion_turno': 8, 'estado': 'ACTIVO'}
            )
            user.contrato = contrato_obj
            user.save()
            contract = contrato_obj
        
        # MÃ©tricas bÃ¡sicas - OPTIMIZADO
        sondajes_activos = Sondaje.objects.filter(contrato=contract, estado='ACTIVO').count()
        turnos_hoy = Turno.objects.filter(contrato=contract, fecha=hoy).count()
        
        metros_perforados_mes = TurnoAvance.objects.filter(
            turno__contrato=contract,
            turno__fecha__month=hoy.month,
            turno__fecha__year=hoy.year
        ).aggregate(total=models.Sum('metros_perforados'))['total'] or 0
        
        maquinas_operativas = Maquina.objects.filter(contrato=contract, estado='OPERATIVO').count()
        
        ultimos_turnos = Turno.objects.filter(
            contrato=contract
        ).select_related('tipo_turno').prefetch_related('sondajes').order_by('-fecha').distinct()[:5]
        
        try:
            stock_critico = []
            abastecimientos = Abastecimiento.objects.filter(contrato=contract)
            
            for abastecimiento in abastecimientos[:10]:
                total_consumido = ConsumoStock.objects.filter(
                    abastecimiento=abastecimiento
                ).aggregate(total=models.Sum('cantidad_consumida'))['total'] or 0
                
                disponible = abastecimiento.cantidad - total_consumido
                
                if disponible <= 5:
                    stock_critico.append({
                        'descripcion': abastecimiento.descripcion,
                        'disponible': disponible,
                        'unidad_medida': abastecimiento.unidad_medida,
                    })
            
            stock_critico = sorted(stock_critico, key=lambda x: x['disponible'])[:10]
        except Exception as e:
            print(f"Error en stock crÃ­tico: {e}")
            stock_critico = []
        
        context = {
            'contract': contract,
            'is_system_admin': user.can_manage_all_contracts(),
            'sondajes_activos': sondajes_activos,
            'turnos_hoy': turnos_hoy,
            'metros_perforados_mes': metros_perforados_mes,
            'maquinas_operativas': maquinas_operativas,
            'ultimos_turnos': ultimos_turnos,
            'stock_critico': stock_critico,
        }
        
        return render(request, 'drilling/dashboard.html', context)

# ===============================
# TRABAJADOR VIEWS - CRUD COMPLETO
# ===============================

class TrabajadorListView(AdminOrContractFilterMixin, ListView):
    model = Trabajador
    template_name = 'drilling/trabajadores/list.html'
    context_object_name = 'trabajadores'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cargo', 'contrato').order_by('apellidos', 'nombres')
        
        # Filtros adicionales
        cargo = self.request.GET.get('cargo')
        if cargo:
            queryset = queryset.filter(cargo=cargo)
        
        grupo = self.request.GET.get('grupo')
        if grupo:
            queryset = queryset.filter(grupo=grupo)
            
        activo = self.request.GET.get('activo')
        if activo:
            queryset = queryset.filter(estado='ACTIVO' if activo == 'true' else 'CESADO')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cargos'] = Cargo.objects.filter(is_active=True).order_by('nombre')
        context['grupos'] = Trabajador.GRUPO_CHOICES
        context['filtros'] = self.request.GET
        return context

@login_required
def trabajadores_hub(request):
    """Hub centralizado de gestiÃ³n de trabajadores"""
    # Obtener trabajadores segÃºn permisos
    if request.user.has_access_to_all_contracts():
        trabajadores = Trabajador.objects.filter(estado='ACTIVO')
    else:
        trabajadores = Trabajador.objects.filter(
            contrato=request.user.contrato,
            estado='ACTIVO'
        )
    
    context = {
        'total_trabajadores': trabajadores.count(),
    }
    
    return render(request, 'drilling/trabajadores/hub.html', context)

class TrabajadorCreateView(AdminOrContractFilterMixin, CreateView):
    model = Trabajador
    form_class = TrabajadorForm
    template_name = 'drilling/trabajadores/form.html'
    success_url = reverse_lazy('trabajador-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Si el usuario no tiene acceso total y tiene contrato, asegurarse de usarlo
        if not self.request.user.has_access_to_all_contracts() and self.request.user.contrato:
            form.instance.contrato = self.request.user.contrato
        messages.success(self.request, 'Trabajador creado exitosamente')
        return super().form_valid(form)

class TrabajadorUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = Trabajador
    form_class = TrabajadorForm
    template_name = 'drilling/trabajadores/form.html'
    success_url = reverse_lazy('trabajador-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Trabajador actualizado exitosamente')
        return super().form_valid(form)

class TrabajadorDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = Trabajador
    template_name = 'drilling/trabajadores/confirm_delete.html'
    success_url = reverse_lazy('trabajador-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Trabajador eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

# ===============================
# MAQUINA VIEWS - CRUD COMPLETO
# ===============================

class MaquinaListView(AdminOrContractFilterMixin, ListView):
    model = Maquina
    template_name = 'drilling/maquinas/list.html'
    context_object_name = 'maquinas'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by('nombre')
        
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Maquina.ESTADO_CHOICES
        context['filtros'] = self.request.GET
        # Agregar lista de contratos para el modal de transferencia
        if self.request.user.can_manage_all_contracts():
            context['contratos'] = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
        else:
            # Para usuarios no admin, solo mostrar otros contratos activos
            context['contratos'] = Contrato.objects.filter(estado='ACTIVO').exclude(
                id=self.request.user.contrato.id
            ).order_by('nombre_contrato')
        return context

class MaquinaCreateView(AdminOrContractFilterMixin, CreateView):
    model = Maquina
    form_class = MaquinaForm
    template_name = 'drilling/maquinas/form.html'
    success_url = reverse_lazy('maquina-list')

    def form_valid(self, form):
        if not self.request.user.can_manage_all_contracts():
            form.instance.contrato = self.request.user.contrato
        messages.success(self.request, 'MÃ¡quina creada exitosamente')
        return super().form_valid(form)

class MaquinaUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = Maquina
    form_class = MaquinaForm
    template_name = 'drilling/maquinas/form.html'
    success_url = reverse_lazy('maquina-list')

    def form_valid(self, form):
        messages.success(self.request, 'MÃ¡quina actualizada exitosamente')
        return super().form_valid(form)

class MaquinaDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = Maquina
    template_name = 'drilling/maquinas/confirm_delete.html'
    success_url = reverse_lazy('maquina-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'MÃ¡quina eliminada exitosamente')
        return super().delete(request, *args, **kwargs)

@login_required
@require_http_methods(["POST"])
@login_required
def gestionar_actividades(request):
    """
    Vista para gestionar actividades: listar todas y editar si son cobrables
    Solo accesible para superadmin
    """
    if not request.user.can_manage_all_contracts():
        messages.error(request, "No tiene permisos para gestionar actividades")
        return redirect('dashboard')
    
    # OPTIMIZADO: Solo cargar campos necesarios
    actividades = TipoActividad.objects.only('id', 'nombre', 'es_cobrable').order_by('nombre')
    
    if request.method == 'POST':
        # Procesar cambios en es_cobrable
        for actividad in actividades:
            campo_cobrable = f'cobrable_{actividad.id}'
            es_cobrable = request.POST.get(campo_cobrable) == 'on'
            if actividad.es_cobrable != es_cobrable:
                actividad.es_cobrable = es_cobrable
                actividad.save(update_fields=['es_cobrable'])
        
        messages.success(request, 'Actividades actualizadas correctamente')
        return redirect('gestionar-actividades')
    
    context = {
        'actividades': actividades,
    }
    return render(request, 'drilling/actividades/gestionar.html', context)


@login_required
def reporte_horas_extras(request):
    """
    Reporte de horas extras por trabajador en un rango de fechas
    """
    if not request.user.can_supervise_operations():
        messages.error(request, "No tiene permisos para ver este reporte")
        return redirect('dashboard')
    
    # Obtener parÃ¡metros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    contrato_id = request.GET.get('contrato')
    trabajador_dni = request.GET.get('trabajador')
    
    # Inicializar queryset
    horas_extras_qs = TurnoHoraExtra.objects.select_related(
        'turno', 'trabajador', 'configuracion_aplicada'
    ).order_by('-turno__fecha', 'trabajador__apellidos')
    
    # Aplicar filtros
    if fecha_inicio:
        horas_extras_qs = horas_extras_qs.filter(turno__fecha__gte=fecha_inicio)
    if fecha_fin:
        horas_extras_qs = horas_extras_qs.filter(turno__fecha__lte=fecha_fin)
    if contrato_id:
        horas_extras_qs = horas_extras_qs.filter(turno__maquina__contrato_id=contrato_id)
    if trabajador_dni:
        horas_extras_qs = horas_extras_qs.filter(trabajador__dni=trabajador_dni)
    
    # Filtrar por contrato del usuario si no es admin
    if not request.user.can_manage_all_contracts():
        horas_extras_qs = horas_extras_qs.filter(turno__maquina__contrato=request.user.contrato)
    
    # Calcular totales
    from django.db.models import Sum, Count
    totales = horas_extras_qs.aggregate(
        total_horas=Sum('horas_extra'),
        total_turnos=Count('turno', distinct=True),
        total_trabajadores=Count('trabajador', distinct=True)
    )
    
    # Agrupar por trabajador
    from django.db.models import Q
    trabajadores_resumen = horas_extras_qs.values(
        'trabajador__dni',
        'trabajador__nombres',
        'trabajador__apellidos',
        'trabajador__cargo__nombre'
    ).annotate(
        total_horas_extra=Sum('horas_extra'),
        cantidad_turnos=Count('turno', distinct=True)
    ).order_by('-total_horas_extra')
    
    # Datos para filtros
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
    
    context = {
        'horas_extras': horas_extras_qs[:100],  # Limitar a 100 registros para no sobrecargar
        'trabajadores_resumen': trabajadores_resumen,
        'totales': totales,
        'contratos': contratos,
        'filtros': {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'contrato_id': contrato_id,
            'trabajador_dni': trabajador_dni,
        }
    }
    return render(request, 'drilling/horas_extras/reporte.html', context)


@login_required
def gestionar_horas_extras(request):
    """
    Vista para gestionar configuraciones de horas extras por contrato
    Solo accesible para superadmin
    """
    if not request.user.can_manage_all_contracts():
        messages.error(request, "No tiene permisos para gestionar horas extras")
        return redirect('dashboard')
    
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    contrato_seleccionado = None
    configuraciones = []
    configuraciones_dict = {}
    maquinas_contrato = []
    
    # Si hay un contrato en GET o POST, cargar sus configuraciones
    contrato_id = request.GET.get('contrato') or request.POST.get('contrato_id')
    
    if request.method == 'POST' and contrato_id:
        contrato_seleccionado = get_object_or_404(Contrato, id=contrato_id)
        maquinas_contrato = Maquina.objects.filter(contrato=contrato_seleccionado, estado='OPERATIVO')
        
        # Procesar configuraciÃ³n general del contrato
        metros_general = request.POST.get('metros_general')
        horas_general = request.POST.get('horas_general', '1.0')
        activo_general = request.POST.get('activo_general') == 'on'
        
        if metros_general:
            with transaction.atomic():
                # Actualizar o crear configuraciÃ³n general (sin mÃ¡quina especÃ­fica)
                config_general, created = ConfiguracionHoraExtra.objects.update_or_create(
                    contrato=contrato_seleccionado,
                    maquina=None,
                    defaults={
                        'metros_minimos': metros_general,
                        'horas_extra': horas_general,
                        'activo': activo_general
                    }
                )
        
        # Procesar configuraciones por mÃ¡quina
        for maquina in maquinas_contrato:
            metros_key = f'metros_maquina_{maquina.id}'
            horas_key = f'horas_maquina_{maquina.id}'
            activo_key = f'activo_maquina_{maquina.id}'
            eliminar_key = f'eliminar_maquina_{maquina.id}'
            
            if request.POST.get(eliminar_key) == 'on':
                # Eliminar configuraciÃ³n especÃ­fica de esta mÃ¡quina
                ConfiguracionHoraExtra.objects.filter(
                    contrato=contrato_seleccionado,
                    maquina=maquina
                ).delete()
            elif request.POST.get(metros_key):
                # Crear o actualizar configuraciÃ³n especÃ­fica
                with transaction.atomic():
                    ConfiguracionHoraExtra.objects.update_or_create(
                        contrato=contrato_seleccionado,
                        maquina=maquina,
                        defaults={
                            'metros_minimos': request.POST.get(metros_key),
                            'horas_extra': request.POST.get(horas_key, '1.0'),
                            'activo': request.POST.get(activo_key) == 'on'
                        }
                    )
        
        messages.success(request, f'ConfiguraciÃ³n de horas extras actualizada para {contrato_seleccionado.nombre_contrato}')
        return redirect(f'{request.path}?contrato={contrato_id}')
    
    if contrato_id:
        try:
            contrato_seleccionado = Contrato.objects.get(id=contrato_id)
            configuraciones = ConfiguracionHoraExtra.objects.filter(
                contrato=contrato_seleccionado
            ).select_related('maquina').order_by('maquina__nombre')
            maquinas_contrato = Maquina.objects.filter(
                contrato=contrato_seleccionado, 
                estado='OPERATIVO'
            ).order_by('nombre')
            
            # Crear diccionario de configuraciones por mÃ¡quina para acceso fÃ¡cil en template
            configuraciones_dict = {}
            for config in configuraciones:
                if config.maquina:
                    configuraciones_dict[config.maquina.id] = config
                else:
                    configuraciones_dict['general'] = config
                    
        except Contrato.DoesNotExist:
            pass
    
    context = {
        'contratos': contratos,
        'contrato_seleccionado': contrato_seleccionado,
        'configuraciones': configuraciones,
        'configuraciones_dict': configuraciones_dict,
        'maquinas_contrato': maquinas_contrato,
    }
    return render(request, 'drilling/horas_extras/gestionar.html', context)


@login_required
def asignar_actividades_contrato(request):
    """
    Vista para asignar actividades a un contrato mediante checkboxes
    Solo accesible para superadmin
    """
    if not request.user.can_manage_all_contracts():
        messages.error(request, "No tiene permisos para asignar actividades")
        return redirect('dashboard')
    
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    actividades = TipoActividad.objects.all().order_by('nombre')
    
    contrato_seleccionado = None
    actividades_asignadas = []
    
    if request.method == 'POST':
        contrato_id = request.POST.get('contrato_id')
        
        if contrato_id:
            contrato_seleccionado = get_object_or_404(Contrato, id=contrato_id)
            
            # Obtener actividades seleccionadas
            actividades_seleccionadas = []
            for actividad in actividades:
                if request.POST.get(f'actividad_{actividad.id}') == 'on':
                    actividades_seleccionadas.append(actividad.id)
            
            # Actualizar asignaciones
            with transaction.atomic():
                # Obtener actividades actualmente asignadas
                actividades_actuales = set(
                    ContratoActividad.objects.filter(contrato=contrato_seleccionado)
                    .values_list('tipoactividad_id', flat=True)
                )
                
                # Actividades seleccionadas
                actividades_nuevas = set(actividades_seleccionadas)
                
                # Eliminar las que ya no estÃ¡n seleccionadas
                a_eliminar = actividades_actuales - actividades_nuevas
                if a_eliminar:
                    ContratoActividad.objects.filter(
                        contrato=contrato_seleccionado,
                        tipoactividad_id__in=a_eliminar
                    ).delete()
                
                # Crear las nuevas (solo las que no existen)
                a_crear = actividades_nuevas - actividades_actuales
                for actividad_id in a_crear:
                    actividad = TipoActividad.objects.get(id=actividad_id)
                    ContratoActividad.objects.create(
                        contrato=contrato_seleccionado,
                        tipoactividad=actividad
                    )
            
            messages.success(
                request,
                f'Se asignaron {len(actividades_seleccionadas)} actividades al contrato {contrato_seleccionado.nombre_contrato}'
            )
            return redirect('asignar-actividades-contrato')
    
    # Si hay un contrato en GET, cargar sus actividades
    contrato_id_get = request.GET.get('contrato')
    if contrato_id_get:
        try:
            contrato_seleccionado = Contrato.objects.get(id=contrato_id_get)
            actividades_asignadas = list(
                ContratoActividad.objects.filter(contrato=contrato_seleccionado)
                .values_list('tipoactividad_id', flat=True)
            )
        except Contrato.DoesNotExist:
            pass
    
    context = {
        'contratos': contratos,
        'actividades': actividades,
        'contrato_seleccionado': contrato_seleccionado,
        'actividades_asignadas': actividades_asignadas,
    }
    return render(request, 'drilling/actividades/asignar_contrato.html', context)


def transferir_maquina(request):
    """
    Vista para transferir una mÃ¡quina a otro contrato
    """
    if not request.user.can_supervise_operations():
        messages.error(request, "No tiene permisos para transferir mÃ¡quinas")
        return redirect('maquina-list')
    
    try:
        maquina_id = request.POST.get('maquina_id')
        nuevo_contrato_id = request.POST.get('nuevo_contrato')
        observaciones = request.POST.get('observaciones', '')
        
        if not maquina_id or not nuevo_contrato_id:
            messages.error(request, "Faltan datos requeridos para la transferencia")
            return redirect('maquina-list')
        
        maquina = get_object_or_404(Maquina, id=maquina_id)
        nuevo_contrato = get_object_or_404(Contrato, id=nuevo_contrato_id)
        
        # Verificar permisos: usuarios no admin solo pueden transferir mÃ¡quinas de su contrato
        if not request.user.can_manage_all_contracts():
            if maquina.contrato != request.user.contrato:
                messages.error(request, "No tiene permisos para transferir esta mÃ¡quina")
                return redirect('maquina-list')
        
        # Verificar que no se estÃ¡ transfiriendo al mismo contrato
        if maquina.contrato == nuevo_contrato:
            messages.warning(request, f"La mÃ¡quina '{maquina.nombre}' ya pertenece al contrato {nuevo_contrato.nombre_contrato}")
            return redirect('maquina-list')
        
        # Guardar informaciÃ³n para el mensaje y el historial
        contrato_anterior = maquina.contrato
        
        # Realizar la transferencia
        with transaction.atomic():
            # Cambiar el contrato de la mÃ¡quina
            maquina.contrato = nuevo_contrato
            maquina.save(update_fields=['contrato'])
            
            # Registrar en el historial de transferencias
            MaquinaTransferenciaHistorial.objects.create(
                maquina=maquina,
                contrato_origen=contrato_anterior,
                contrato_destino=nuevo_contrato,
                usuario=request.user,
                observaciones=observaciones
            )
        
        messages.success(
            request, 
            f'MÃ¡quina "{maquina.nombre}" transferida exitosamente de {contrato_anterior.nombre_contrato} a {nuevo_contrato.nombre_contrato}'
        )
        
        if observaciones:
            messages.info(request, f'Observaciones: {observaciones}')
        
    except Exception as e:
        messages.error(request, f'Error al transferir mÃ¡quina: {str(e)}')
    
    return redirect('maquina-list')

# ===============================
# SONDAJE VIEWS - CRUD COMPLETO
# ===============================

class SondajeListView(AdminOrContractFilterMixin, ListView):
    model = Sondaje
    template_name = 'drilling/sondajes/list.html'
    context_object_name = 'sondajes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('contrato').order_by('-fecha_inicio')
        
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Sondaje.ESTADO_CHOICES
        context['filtros'] = self.request.GET
        return context

class SondajeCreateView(AdminOrContractFilterMixin, CreateView):
    model = Sondaje
    form_class = SondajeForm
    template_name = 'drilling/sondajes/form.html'
    success_url = reverse_lazy('sondaje-list')

    def form_valid(self, form):
        if not self.request.user.can_manage_all_contracts():
            form.instance.contrato = self.request.user.contrato
        messages.success(self.request, 'Sondaje creado exitosamente')
        return super().form_valid(form)

class SondajeUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = Sondaje
    form_class = SondajeForm
    template_name = 'drilling/sondajes/form.html'
    success_url = reverse_lazy('sondaje-list')

    def form_valid(self, form):
        messages.success(self.request, 'Sondaje actualizado exitosamente')
        return super().form_valid(form)

class SondajeDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = Sondaje
    template_name = 'drilling/sondajes/confirm_delete.html'
    success_url = reverse_lazy('sondaje-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Sondaje eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

# ===============================
# TIPO ACTIVIDAD VIEWS - CRUD COMPLETO
# ===============================

class TipoActividadListView(AdminOrContractFilterMixin, ListView):
    model = TipoActividad
    template_name = 'drilling/actividades/list.html'
    context_object_name = 'actividades'
    paginate_by = 20

class TipoActividadCreateView(AdminOrContractFilterMixin, CreateView):
    model = TipoActividad
    form_class = TipoActividadForm
    template_name = 'drilling/actividades/form.html'
    success_url = reverse_lazy('actividades-list')

    def form_valid(self, form):
        messages.success(self.request, 'Actividad creada exitosamente')
        return super().form_valid(form)

class TipoActividadUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = TipoActividad
    form_class = TipoActividadForm
    template_name = 'drilling/actividades/form.html'
    success_url = reverse_lazy('actividades-list')

    def form_valid(self, form):
        messages.success(self.request, 'Actividad actualizada exitosamente')
        return super().form_valid(form)

class TipoActividadDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = TipoActividad
    template_name = 'drilling/actividades/confirm_delete.html'
    success_url = reverse_lazy('actividades-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Actividad eliminada exitosamente')
        return super().delete(request, *args, **kwargs)


class ContratoActividadesUpdateView(SystemAdminRequiredMixin, TemplateView):
    """Vista para asignar/desasignar actividades (maestro) a un contrato.
    Solo los admins del sistema pueden gestionar esto; contract managers deberÃ¡n
    usar su propia secciÃ³n para ver las actividades asignadas.
    """
    template_name = 'drilling/contratos/actividades_form.html'

    def get(self, request, pk):
        contrato = get_object_or_404(Contrato, pk=pk)
        # OPTIMIZADO: Solo cargar campos necesarios
        actividades = TipoActividad.objects.only('id', 'nombre', 'descripcion_corta').order_by('nombre')
        context = {
            'contrato': contrato,
            'actividades': actividades,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        contrato = get_object_or_404(Contrato, pk=pk)
        actividad_ids = request.POST.getlist('actividades')
        actividades = TipoActividad.objects.filter(id__in=actividad_ids)
        contrato.actividades.set(actividades)
        messages.success(request, 'Actividades asignadas al contrato correctamente')
        return redirect('contrato-actividades', pk=contrato.pk)

# ===============================
# TIPO TURNO VIEWS - CRUD COMPLETO
# ===============================

class TipoTurnoListView(AdminOrContractFilterMixin, ListView):
    model = TipoTurno
    template_name = 'drilling/tipo_turnos/list.html'
    context_object_name = 'tipos_turno'
    paginate_by = 20

class TipoTurnoCreateView(AdminOrContractFilterMixin, CreateView):
    model = TipoTurno
    form_class = TipoTurnoForm
    template_name = 'drilling/tipo_turnos/form.html'
    success_url = reverse_lazy('tipo-turno-list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de turno creado exitosamente')
        return super().form_valid(form)

class TipoTurnoUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = TipoTurno
    form_class = TipoTurnoForm
    template_name = 'drilling/tipo_turnos/form.html'
    success_url = reverse_lazy('tipo-turno-list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de turno actualizado exitosamente')
        return super().form_valid(form)

class TipoTurnoDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = TipoTurno
    template_name = 'drilling/tipo_turnos/confirm_delete.html'
    success_url = reverse_lazy('tipo-turno-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Tipo de turno eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

# ===============================
# TIPO COMPLEMENTO VIEWS - CRUD COMPLETO
# ===============================

class TipoComplementoListView(AdminOrContractFilterMixin, ListView):
    model = TipoComplemento
    template_name = 'drilling/complementos/list.html'
    context_object_name = 'complementos'
    paginate_by = 20

class TipoComplementoCreateView(AdminOrContractFilterMixin, CreateView):
    model = TipoComplemento
    form_class = TipoComplementoForm
    template_name = 'drilling/complementos/form.html'
    success_url = reverse_lazy('complemento-list')

    def form_valid(self, form):
        messages.success(self.request, 'Complemento creado exitosamente')
        return super().form_valid(form)

class TipoComplementoUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = TipoComplemento
    form_class = TipoComplementoForm
    template_name = 'drilling/complementos/form.html'
    success_url = reverse_lazy('complemento-list')

    def form_valid(self, form):
        messages.success(self.request, 'Complemento actualizado exitosamente')
        return super().form_valid(form)

class TipoComplementoDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = TipoComplemento
    template_name = 'drilling/complementos/confirm_delete.html'
    success_url = reverse_lazy('complemento-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Complemento eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

# ===============================
# TIPO ADITIVO VIEWS - CRUD COMPLETO
# ===============================

class TipoAditivoListView(AdminOrContractFilterMixin, ListView):
    model = TipoAditivo
    template_name = 'drilling/aditivos/list.html'
    context_object_name = 'aditivos'
    paginate_by = 20

class TipoAditivoCreateView(AdminOrContractFilterMixin, CreateView):
    model = TipoAditivo
    form_class = TipoAditivoForm
    template_name = 'drilling/aditivos/form.html'
    success_url = reverse_lazy('aditivo-list')

    def form_valid(self, form):
        messages.success(self.request, 'Aditivo creado exitosamente')
        return super().form_valid(form)

class TipoAditivoUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = TipoAditivo
    form_class = TipoAditivoForm
    template_name = 'drilling/aditivos/form.html'
    success_url = reverse_lazy('aditivo-list')

    def form_valid(self, form):
        messages.success(self.request, 'Aditivo actualizado exitosamente')
        return super().form_valid(form)

class TipoAditivoDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = TipoAditivo
    template_name = 'drilling/aditivos/confirm_delete.html'
    success_url = reverse_lazy('aditivo-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Aditivo eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

# ===============================
# UNIDAD MEDIDA VIEWS - CRUD COMPLETO
# ===============================

class UnidadMedidaListView(AdminOrContractFilterMixin, ListView):
    model = UnidadMedida
    template_name = 'drilling/unidades/list.html'
    context_object_name = 'unidades'
    paginate_by = 20

class UnidadMedidaCreateView(AdminOrContractFilterMixin, CreateView):
    model = UnidadMedida
    form_class = UnidadMedidaForm
    template_name = 'drilling/unidades/form.html'
    success_url = reverse_lazy('unidad-list')

    def form_valid(self, form):
        messages.success(self.request, 'Unidad de medida creada exitosamente')
        return super().form_valid(form)

class UnidadMedidaUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = UnidadMedida
    form_class = UnidadMedidaForm
    template_name = 'drilling/unidades/form.html'
    success_url = reverse_lazy('unidad-list')

    def form_valid(self, form):
        messages.success(self.request, 'Unidad de medida actualizada exitosamente')
        return super().form_valid(form)

class UnidadMedidaDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = UnidadMedida
    template_name = 'drilling/unidades/confirm_delete.html'
    success_url = reverse_lazy('unidad-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Unidad de medida eliminada exitosamente')
        return super().delete(request, *args, **kwargs)

# ===============================
# TURNO VIEWS - COMPLETO Y AVANZADO
# ===============================

from datetime import datetime, time
import json
from django.db import transaction
from django.contrib import messages
from django.shortcuts import render, redirect

@login_required
def crear_turno_completo(request, pk=None):
    if not request.user.can_supervise_operations():
        messages.error(request, "Acceso denegado. Requiere permisos de Supervisor o superior.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            # Obtener datos bÃ¡sicos del turno
            # soporte para mÃºltiples sondajes: 'sondajes' (multiselect) o 'sondaje' (compatibilidad)
            sondaje_ids = request.POST.getlist('sondajes') or []
            if not sondaje_ids:
                single = request.POST.get('sondaje')
                if single:
                    sondaje_ids = [single]
            maquina_id = request.POST.get('maquina')
            tipo_turno_id = request.POST.get('tipo_turno')
            fecha = request.POST.get('fecha')
            
            # Validar campos requeridos
            if not sondaje_ids or not all([maquina_id, tipo_turno_id, fecha]):
                messages.error(request, "Faltan campos requeridos: sondaje(s), mÃ¡quina, tipo de turno y fecha.")
                return redirect('crear-turno-completo')

            # Obtener objetos relacionados EN EL MISMO ORDEN en que fueron seleccionados
            sondajes_list = []
            try:
                for sid in sondaje_ids:
                    sondajes_list.append(Sondaje.objects.get(id=int(sid)))
            except (ValueError, Sondaje.DoesNotExist):
                messages.error(request, 'Sondaje(s) seleccionado(s) invÃ¡lido(s)')
                return redirect('crear-turno-completo')
            # Para compatibilidad con el cÃ³digo existente que usa una Ãºnica variable 'sondaje',
            # tomamos el primero para lecturas puntuales (duraciÃ³n, contrato) y mantenemos la lista
            sondaje = sondajes_list[0]
            maquina = Maquina.objects.get(id=maquina_id)
            tipo_turno = TipoTurno.objects.get(id=tipo_turno_id)
            
            # Verificar permisos de contrato: todos los sondajes deben pertenecer al mismo contrato
            contratos_ids = set([s.contrato_id for s in sondajes_list])
            if len(contratos_ids) > 1:
                messages.error(request, 'Los sondajes seleccionados pertenecen a contratos diferentes.')
                return redirect('crear-turno-completo')
            contrato_sondajes = sondajes_list[0].contrato
            if not request.user.can_manage_all_contracts() and contrato_sondajes != request.user.contrato:
                messages.error(request, "No tiene permisos para crear turnos en este contrato.")
                return redirect('dashboard')
            
            # Parsear y validar datos complejos ANTES de abrir la transacciÃ³n
            # Esto evita abrir la transacciÃ³n si los datos estÃ¡n corruptos
            trabajadores_parsed = []
            complementos_parsed = []
            aditivos_parsed = []
            actividades_parsed = []
            corridas_parsed = []
            metros_perforados_val = None

            # Trabajadores
            trabajadores_data = request.POST.get('trabajadores')
            if trabajadores_data:
                try:
                    trabajadores_raw = json.loads(trabajadores_data)
                    for t in trabajadores_raw:
                        if 'trabajador_id' not in t or 'funcion' not in t:
                            messages.warning(request, 'Trabajador con datos incompletos serÃ¡ omitido')
                            continue
                        trabajadores_parsed.append({
                            'trabajador_id': t['trabajador_id'],
                            'funcion': t['funcion'],
                            'observaciones': t.get('observaciones', '')
                        })
                except json.JSONDecodeError as e:
                    messages.error(request, f'JSON invÃ¡lido en trabajadores: {e}')
                    return redirect('crear-turno-completo')

            # Complementos
            complementos_data = request.POST.get('complementos')
            if complementos_data:
                try:
                    complementos_raw = json.loads(complementos_data)
                    for c in complementos_raw:
                        try:
                            complementos_parsed.append({
                                'tipo_complemento_id': int(c['tipo_complemento_id']),
                                'codigo_serie': c.get('codigo_serie', ''),
                                'metros_inicio': Decimal(str(c['metros_inicio'])),
                                'metros_fin': Decimal(str(c['metros_fin'])),
                                'sondaje_id': int(c.get('sondaje_id')) if c.get('sondaje_id') else None,
                            })
                        except (KeyError, ValueError, TypeError) as e:
                            messages.warning(request, f'Complemento con datos invÃ¡lidos serÃ¡ omitido: {e}')
                        except Exception as e:
                            messages.warning(request, f'Error inesperado en complemento: {e}')
                except json.JSONDecodeError as e:
                    messages.error(request, f'JSON invÃ¡lido en complementos: {e}')
                    return redirect('crear-turno-completo')

            # Aditivos
            aditivos_data = request.POST.get('aditivos')
            if aditivos_data:
                try:
                    aditivos_raw = json.loads(aditivos_data)
                    for a in aditivos_raw:
                        try:
                            aditivos_parsed.append({
                                'tipo_aditivo_id': int(a['tipo_aditivo_id']),
                                'cantidad_usada': float(a['cantidad_usada']),
                                'unidad_medida_id': int(a['unidad_medida_id']),
                                'sondaje_id': int(a.get('sondaje_id')) if a.get('sondaje_id') else None,
                            })
                        except (KeyError, ValueError):
                            messages.warning(request, 'Aditivo con datos invÃ¡lidos serÃ¡ omitido')
                except json.JSONDecodeError as e:
                    messages.error(request, f'JSON invÃ¡lido en aditivos: {e}')
                    return redirect('crear-turno-completo')

            # Actividades
            actividades_data = request.POST.get('actividades')
            if actividades_data:
                try:
                    actividades_raw = json.loads(actividades_data)
                    for act in actividades_raw:
                        try:
                            actividades_parsed.append({
                                'actividad_id': int(act['actividad_id']),
                                'hora_inicio': convert_to_time(act.get('hora_inicio')),
                                'hora_fin': convert_to_time(act.get('hora_fin')),
                                'observaciones': act.get('observaciones', '')
                            })
                        except (KeyError, ValueError):
                            messages.warning(request, 'Actividad con datos invÃ¡lidos serÃ¡ omitida')
                except json.JSONDecodeError as e:
                    messages.error(request, f'JSON invÃ¡lido en actividades: {e}')
                    return redirect('crear-turno-completo')

            # Corridas
            corridas_data = request.POST.get('corridas')
            if corridas_data:
                try:
                    corridas_raw = json.loads(corridas_data)
                    for cr in corridas_raw:
                        try:
                            corridas_parsed.append({
                                'corrida_numero': int(cr['corrida_numero']),
                                'desde': float(cr['desde']),
                                'hasta': float(cr['hasta']),
                                'longitud_testigo': float(cr['longitud_testigo']),
                                'pct_recuperacion': float(cr['pct_recuperacion']),
                                'pct_retorno_agua': float(cr['pct_retorno_agua']),
                                'litologia': cr.get('litologia', '')
                            })
                        except (KeyError, ValueError):
                            messages.warning(request, 'Corrida con datos invÃ¡lidos serÃ¡ omitida')
                except json.JSONDecodeError as e:
                    messages.error(request, f'JSON invÃ¡lido en corridas: {e}')
                    return redirect('crear-turno-completo')

            # Metrajes por sondaje: preferimos la lista de metrajes por sondaje
            # que viene en el formulario (name='sondajes_metraje'). Sumaremos
            # esos valores y los usaremos como avance total del turno.
            metrajes_raw = request.POST.getlist('sondajes_metraje') or []
            if not metrajes_raw:
                single_m = request.POST.get('sondaje_metraje')
                if single_m:
                    metrajes_raw = [single_m]

            metros_perforados_val = None
            if metrajes_raw:
                try:
                    total_m = 0.0
                    for mv in metrajes_raw:
                        if mv in [None, '']:
                            continue
                        total_m += float(mv)
                    metros_perforados_val = total_m
                except ValueError:
                    # Si algÃºn valor no es numÃ©rico, ignoramos el avance calculado
                    messages.warning(request, 'Algunos metrajes por sondaje no son numÃ©ricos; avance serÃ¡ 0 o calculado desde TurnoSondaje')

            # Procesar datos de mÃ¡quina: aceptamos lecturas de horÃ³metro (numÃ©ricas)
            # o tiempos en formato HH:MM. Si el valor es numÃ©rico serÃ¡ tratado como
            # lectura de horÃ³metro (horometro_inicio/horometro_fin).
            hora_inicio_maq = request.POST.get('hora_inicio_maq')
            hora_fin_maq = request.POST.get('hora_fin_maq')
            hora_inicio_maq_parsed = None
            hora_fin_maq_parsed = None
            horometro_inicio_val = None
            horometro_fin_val = None
            # Intentar parsear como Decimal (horÃ³metro)
            from decimal import InvalidOperation
            try:
                if hora_inicio_maq is not None and hora_inicio_maq.strip() != '':
                    try:
                        horometro_inicio_val = Decimal(hora_inicio_maq)
                    except Exception:
                        hora_inicio_maq_parsed = convert_to_time(hora_inicio_maq)
                if hora_fin_maq is not None and hora_fin_maq.strip() != '':
                    try:
                        horometro_fin_val = Decimal(hora_fin_maq)
                    except Exception:
                        hora_fin_maq_parsed = convert_to_time(hora_fin_maq)
            except Exception:
                # En caso de cualquier error, fallback a tratar como time strings
                hora_inicio_maq_parsed = convert_to_time(hora_inicio_maq) if hora_inicio_maq else None
                hora_fin_maq_parsed = convert_to_time(hora_fin_maq) if hora_fin_maq else None

            # ----------------------------------
            # VALIDACIÃ“N: sumar horas de actividades
            # ----------------------------------
            try:
                total_horas_post = 0.0
                for a in actividades_parsed:
                    hi = a.get('hora_inicio')
                    hf = a.get('hora_fin')
                    if hi and hf:
                        # hi/hf are time objects (convert_to_time)
                        start_dt = datetime.combine(datetime.today().date(), hi)
                        end_dt = datetime.combine(datetime.today().date(), hf)
                        if end_dt < start_dt:
                            end_dt = end_dt + timedelta(days=1)
                        total_horas_post += (end_dt - start_dt).total_seconds() / 3600.0
                # Prefer the current user's contrato.duracion_turno for non-admin users
                if request.user.can_manage_all_contracts():
                    duracion_esperada = float(sondaje.contrato.duracion_turno or 0)
                else:
                    duracion_esperada = float(getattr(request.user.contrato, 'duracion_turno', 0) or 0)
                if duracion_esperada > 0 and total_horas_post < duracion_esperada:
                    faltan = duracion_esperada - total_horas_post
                    # TambiÃ©n incluir el valor de duraciÃ³n en el contrato del usuario por si hay discrepancias
                    try:
                        usuario_duracion = float(request.user.contrato.duracion_turno or 0)
                    except Exception:
                        usuario_duracion = None
                    msg = (f'Faltan horas al turno: se han registrado {total_horas_post:.2f}h, '
                           f'se requieren {duracion_esperada:.2f}h (faltan {faltan:.2f}h).')
                    if usuario_duracion is not None:
                        msg += f' [duraciÃ³n contrato sondaje={duracion_esperada:.2f}h, duraciÃ³n contrato usuario={usuario_duracion:.2f}h]'
                    messages.error(request, msg)
                    # Volver a renderizar el formulario con los datos pre-llenados
                    context = get_context_data(request)
                    import json as _json
                    context.update({
                        'edit_mode': True,
                        'edit_trabajadores_json': _json.dumps(trabajadores_parsed),
                        'edit_complementos_json': _json.dumps(complementos_parsed),
                        'edit_aditivos_json': _json.dumps(aditivos_parsed),
                        'edit_actividades_json': _json.dumps([
                            {
                                'actividad_id': a['actividad_id'],
                                'hora_inicio': a['hora_inicio'].isoformat() if a.get('hora_inicio') else '',
                                'hora_fin': a['hora_fin'].isoformat() if a.get('hora_fin') else '',
                                'observaciones': a.get('observaciones', '')
                            } for a in actividades_parsed
                        ]),
                        'edit_corridas_json': _json.dumps(corridas_parsed),
                        # pasar lista de sondajes para que la plantilla preseleccione
                        'edit_sondaje_ids': _json.dumps([int(x) for x in sondaje_ids]) if sondaje_ids else _json.dumps([]),
                        'edit_sondaje_id': int(sondaje_ids[0]) if sondaje_ids else None,
                        'edit_maquina_id': int(maquina_id) if maquina_id else None,
                        'edit_tipo_turno_id': int(tipo_turno_id) if tipo_turno_id else None,
                        'edit_fecha': fecha,
                            # Si hubo metrajes en POST, ofrecer la suma; si no, 0
                            'edit_metros_perforados': (metros_perforados_val or 0),
                        'edit_hora_inicio_maq': hora_inicio_maq_parsed.isoformat() if hora_inicio_maq_parsed else '',
                        'edit_hora_fin_maq': hora_fin_maq_parsed.isoformat() if hora_fin_maq_parsed else '',
                        'edit_estado_bomba': request.POST.get('estado_bomba', ''),
                        'edit_estado_unidad': request.POST.get('estado_unidad', ''),
                        'edit_estado_rotacion': request.POST.get('estado_rotacion', ''),
                    })
                    return render(request, 'drilling/turno/crear_completo.html', context)
            except Exception:
                # Si falla la validaciÃ³n por cualquier razÃ³n, seguimos con el flujo
                pass

            # Ahora que todo estÃ¡ parseado/validado, crear o actualizar registros en una transacciÃ³n
            with transaction.atomic():
                if pk:
                    # Editar turno existente
                    turno = get_object_or_404(Turno, pk=pk)
                    turno.maquina = maquina
                    turno.tipo_turno = tipo_turno
                    turno.fecha = fecha
                    turno.contrato = contrato_sondajes
                    turno.save()
                    # actualizar asociaciones many-to-many de sondajes
                    try:
                        # Usar un savepoint (atomic anidado) para que si falla la asignaciÃ³n
                        # M2M no deje la transacciÃ³n completa en estado roto.
                        with transaction.atomic():
                            turno.sondajes.set([s.id for s in sondajes_list])
                    except Exception:
                        # No bloquear el flujo por fallos en la asociaciÃ³n M2M; el savepoint
                        # asegura que la transacciÃ³n externa no quede marcada como rollback.
                        pass

                    # Eliminar relaciones existentes y recrear desde los datos enviados
                    # TambiÃ©n eliminar asociaciones TurnoSondaje para rehacer con metrajes
                    TurnoSondaje.objects.filter(turno=turno).delete()
                    TurnoMaquina.objects.filter(turno=turno).delete()
                    TurnoTrabajador.objects.filter(turno=turno).delete()
                    TurnoComplemento.objects.filter(turno=turno).delete()
                    TurnoAditivo.objects.filter(turno=turno).delete()
                    TurnoActividad.objects.filter(turno=turno).delete()
                    TurnoCorrida.objects.filter(turno=turno).delete()
                    TurnoAvance.objects.filter(turno=turno).delete()
                else:
                    # Crear el turno principal CON relaciÃ³n directa a contrato
                    turno = Turno.objects.create(
                        fecha=fecha,
                        contrato=contrato_sondajes,
                        maquina=maquina,
                        tipo_turno=tipo_turno,
                    )
                    # asignar sondajes seleccionados
                    try:
                        # Mismo tratamiento en la rama de creaciÃ³n: usar savepoint para M2M
                        with transaction.atomic():
                            turno.sondajes.set([s.id for s in sondajes_list])
                    except Exception:
                        pass

                # Guardar metrajes por sondaje si fueron enviados (usar metrajes_raw
                # ya parseados arriba). Se espera una lista paralela 'sondajes_metraje'
                # en el POST
                try:
                    # Asegurar que los pares (sondaje_id, metraje) respeten el orden de selecciÃ³n
                    pairs = list(zip([int(s.id) for s in sondajes_list], metrajes_raw)) if metrajes_raw else []
                    objs = []
                    if pairs:
                        for sid, m in pairs:
                            try:
                                metros_val = Decimal(str(m)) if m not in [None, ''] else Decimal('0')
                            except Exception:
                                metros_val = Decimal('0')
                            objs.append(TurnoSondaje(turno=turno, sondaje_id=sid, metros_turno=metros_val))
                        if objs:
                            # bulk_create en su propio savepoint para aislar errores
                            try:
                                with transaction.atomic():
                                    TurnoSondaje.objects.bulk_create(objs)
                            except Exception:
                                # No bloquear el flujo si falla la bulk_create; ya hay asociaciÃ³n M2M
                                pass
                    else:
                        # Si no se enviaron metrajes, asegurarse de que existan filas TurnoSondaje
                        # (la asignaciÃ³n M2M previa puede haber creado entradas con valores por defecto)
                        pass
                except Exception:
                    # No bloquear el flujo si algo falla al preparar metrajes; la transacciÃ³n global seguirÃ¡ intacta
                    pass

                # Crear TurnoMaquina si corresponde
                if hora_inicio_maq_parsed or hora_fin_maq_parsed or horometro_inicio_val is not None or horometro_fin_val is not None or request.POST.get('estado_bomba'):
                    # Si estamos editando (pk) y existÃ­a un TurnoMaquina previo, restar sus horas del horometro
                    if pk:
                        prev_tm = TurnoMaquina.objects.filter(turno=turno).first()
                        if prev_tm and prev_tm.horas_trabajadas_calc:
                            try:
                                maquina.horometro = maquina.horometro - prev_tm.horas_trabajadas_calc
                                maquina.save(update_fields=['horometro'])
                            except Exception:
                                # No bloquear el flujo si falla la resta
                                pass

                    tm = TurnoMaquina.objects.create(
                        turno=turno,
                        hora_inicio=hora_inicio_maq_parsed,
                        hora_fin=hora_fin_maq_parsed,
                        horometro_inicio=horometro_inicio_val,
                        horometro_fin=horometro_fin_val,
                        estado_bomba=request.POST.get('estado_bomba', 'OPERATIVO'),
                        estado_unidad=request.POST.get('estado_unidad', 'OPERATIVO'),
                        estado_rotacion=request.POST.get('estado_rotacion', 'OPERATIVO')
                    )

                    # DespuÃ©s de crear TurnoMaquina, su save() habrÃ¡ calculado horas_trabajadas_calc.
                    # Sumar ese valor al horÃ³metro de la mÃ¡quina asociada.
                    try:
                        if tm.horas_trabajadas_calc and tm.horas_trabajadas_calc > 0:
                            # usar Decimal para mantener precisiÃ³n
                            incremento = Decimal(str(tm.horas_trabajadas_calc))
                            # Actualizar horÃ³metro en un savepoint para evitar marcar la transacciÃ³n si falla
                            try:
                                with transaction.atomic():
                                    horometro_anterior = maquina.horometro or Decimal('0')
                                    maquina.horometro = horometro_anterior + incremento
                                    maquina.save(update_fields=['horometro'])
                                    messages.info(
                                        request,
                                        f'HorÃ³metro de la mÃ¡quina actualizado: {horometro_anterior} + {incremento} = {maquina.horometro} horas'
                                    )
                            except Exception as e:
                                # Log del error para debugging
                                messages.warning(request, f'Error al actualizar horÃ³metro: {str(e)}')
                    except Exception as e:
                        # Log del error para debugging
                        messages.warning(request, f'Error al calcular incremento de horÃ³metro: {str(e)}')

                # Crear trabajadores usando bulk_create para mejor rendimiento
                if trabajadores_parsed:
                    dnis = [str(t['trabajador_id']) for t in trabajadores_parsed]
                    trabajadores_dict = Trabajador.objects.in_bulk(dnis, field_name='dni')
                    turno_trabajadores = []
                    for t in trabajadores_parsed:
                        trabajador_obj = trabajadores_dict.get(str(t['trabajador_id']))
                        if trabajador_obj:
                            turno_trabajadores.append(TurnoTrabajador(
                                turno=turno,
                                trabajador=trabajador_obj,
                                funcion=t['funcion'],
                                observaciones=t['observaciones']
                            ))
                    if turno_trabajadores:
                        TurnoTrabajador.objects.bulk_create(turno_trabajadores)

                # Crear complementos usando bulk_create (sin triggers de save)
                complementos_objetos = []
                if complementos_parsed:
                    for c in complementos_parsed:
                        obj = TurnoComplemento(
                            turno=turno,
                            tipo_complemento_id=c['tipo_complemento_id'],
                            codigo_serie=c['codigo_serie'],
                            metros_inicio=c['metros_inicio'],
                            metros_fin=c['metros_fin'],
                            metros_turno_calc=c['metros_fin'] - c['metros_inicio'],
                            sondaje_id=c.get('sondaje_id')
                        )
                        complementos_objetos.append(obj)
                    if complementos_objetos:
                        TurnoComplemento.objects.bulk_create(complementos_objetos)
                        # Actualizar HistorialBroca en batch despuÃ©s del bulk_create
                        from django.db.models import F
                        from collections import defaultdict
                        series_metrajes = defaultdict(Decimal)
                        for obj in complementos_objetos:
                            series_metrajes[obj.codigo_serie] += obj.metros_turno_calc
                        
                        for serie, metraje_total in series_metrajes.items():
                            historial, created = HistorialBroca.objects.get_or_create(
                                serie=serie,
                                defaults={
                                    'tipo_complemento_id': complementos_objetos[0].tipo_complemento_id,
                                    'contrato_actual': turno.contrato,
                                    'fecha_primer_uso': turno.fecha,
                                    'estado': 'NUEVA'
                                }
                            )
                            # Contar cuÃ¡ntas veces se usÃ³ esta serie en este turno
                            num_usos = sum(1 for obj in complementos_objetos if obj.codigo_serie == serie)
                            historial.metraje_acumulado = F('metraje_acumulado') + metraje_total
                            historial.numero_usos = F('numero_usos') + num_usos
                            historial.fecha_ultimo_uso = turno.fecha
                            if created or historial.estado == 'NUEVA':
                                historial.estado = 'EN_USO'
                            historial.save(update_fields=['metraje_acumulado', 'numero_usos', 'fecha_ultimo_uso', 'estado'])

                # Crear aditivos usando bulk_create
                if aditivos_parsed:
                    aditivos_objetos = [
                        TurnoAditivo(
                            turno=turno,
                            tipo_aditivo_id=a['tipo_aditivo_id'],
                            cantidad_usada=a['cantidad_usada'],
                            unidad_medida_id=a['unidad_medida_id'],
                            sondaje_id=a.get('sondaje_id')
                        ) for a in aditivos_parsed
                    ]
                    TurnoAditivo.objects.bulk_create(aditivos_objetos)

                # Crear actividades usando bulk_create
                if actividades_parsed:
                    from datetime import datetime, timedelta
                    
                    def calcular_tiempo_actividad(hora_inicio, hora_fin):
                        """Calcula tiempo_calc en horas con 2 decimales"""
                        if not hora_inicio or not hora_fin:
                            return Decimal('0')
                        inicio = datetime.combine(datetime.today(), hora_inicio)
                        fin = datetime.combine(datetime.today(), hora_fin)
                        if fin < inicio:
                            fin += timedelta(days=1)
                        diff = fin - inicio
                        return Decimal(str(diff.total_seconds() / 3600))
                    
                    actividades_objetos = [
                        TurnoActividad(
                            turno=turno,
                            actividad_id=act['actividad_id'],
                            hora_inicio=act['hora_inicio'],
                            hora_fin=act['hora_fin'],
                            tiempo_calc=calcular_tiempo_actividad(act['hora_inicio'], act['hora_fin']),
                            observaciones=act['observaciones']
                        ) for act in actividades_parsed
                    ]
                    TurnoActividad.objects.bulk_create(actividades_objetos)

                # Crear corridas usando bulk_create
                if corridas_parsed:
                    corridas_objetos = [
                        TurnoCorrida(
                            turno=turno,
                            corrida_numero=cr['corrida_numero'],
                            desde=cr['desde'],
                            hasta=cr['hasta'],
                            longitud_testigo=cr['longitud_testigo'],
                            pct_recuperacion=cr['pct_recuperacion'],
                            pct_retorno_agua=cr['pct_retorno_agua'],
                            litologia=cr['litologia']
                        ) for cr in corridas_parsed
                    ]
                    TurnoCorrida.objects.bulk_create(corridas_objetos)

                # Crear avance: preferimos sumar los metrajes guardados en TurnoSondaje
                # (si la bulk_create funcionÃ³). Como fallback, usamos el valor sumado
                # recibido en POST (metros_perforados_val) si existe.
                try:
                    from django.db.models import Sum
                    total_db = TurnoSondaje.objects.filter(turno=turno).aggregate(total=Sum('metros_turno'))['total']
                    total_db = float(total_db) if total_db is not None else 0.0
                except Exception:
                    total_db = 0.0

                final_total_metros = total_db if total_db > 0 else (metros_perforados_val or 0)
                try:
                    if final_total_metros and float(final_total_metros) > 0:
                        TurnoAvance.objects.create(
                            turno=turno,
                            metros_perforados=final_total_metros
                        )
                except Exception:
                    # No bloquear el flujo si falla la creaciÃ³n del avance
                    pass
                
                # Procesar cambios de estado de sondajes
                cambios_estado_data = request.POST.get('cambios_estado_sondaje')
                if cambios_estado_data:
                    try:
                        cambios_estado_raw = json.loads(cambios_estado_data)
                        for cambio in cambios_estado_raw:
                            try:
                                sondaje_id = int(cambio['sondaje_id'])
                                nuevo_estado = cambio['nuevo_estado']
                                
                                # Validar que el estado es vÃ¡lido
                                estados_validos = ['ACTIVO', 'PAUSADO', 'FINALIZADO', 'CANCELADO']
                                if nuevo_estado not in estados_validos:
                                    continue
                                
                                # Obtener el sondaje y actualizar su estado
                                sondaje_obj = Sondaje.objects.get(id=sondaje_id)
                                estado_anterior = sondaje_obj.estado
                                sondaje_obj.estado = nuevo_estado
                                sondaje_obj.save(update_fields=['estado'])
                                
                                messages.info(request, f'Estado del sondaje "{sondaje_obj.nombre_sondaje}" cambiado de {estado_anterior} a {nuevo_estado}')
                            except (KeyError, ValueError, Sondaje.DoesNotExist) as e:
                                messages.warning(request, f'No se pudo actualizar el estado de un sondaje: {str(e)}')
                    except json.JSONDecodeError:
                        messages.warning(request, 'No se pudieron procesar los cambios de estado de sondajes')

            if pk:
                messages.success(request, f'Turno #{turno.id} actualizado exitosamente para {sondaje.nombre_sondaje}')
            else:
                messages.success(request, f'Turno #{turno.id} creado exitosamente para {sondaje.nombre_sondaje}')
            # DespuÃ©s de crear/actualizar, verificar si las actividades suman la duraciÃ³n del turno
            try:
                # Sumar horas de actividades guardadas
                total_horas = 0
                for act_obj in TurnoActividad.objects.filter(turno=turno):
                    if act_obj.tiempo_calc:
                        total_horas += float(act_obj.tiempo_calc)
                # Obtener duraciÃ³n esperada desde el contrato del sondaje
                # Same logic as above: for non-admin users prefer their contrato.duracion_turno
                if request.user.can_manage_all_contracts():
                    duracion_esperada = float(sondaje.contrato.duracion_turno or 0)
                else:
                    duracion_esperada = float(getattr(request.user.contrato, 'duracion_turno', 0) or 0)
                if total_horas >= duracion_esperada and duracion_esperada > 0:
                    turno.estado = 'COMPLETADO'
                    turno.save(update_fields=['estado'])
            except Exception:
                # No bloquear el flujo si falla esta comprobaciÃ³n
                pass
            return redirect('listar-turnos')
            
        except Exception as e:
            messages.error(request, f'Error al crear turno: {str(e)}')
            return redirect('crear-turno-completo')
    
    # GET request - si es modo ediciÃ³n pre-popular datos
    context = get_context_data(request)
    if pk:
        turno = get_object_or_404(Turno, pk=pk)
        # preparar listas JSON para inyectar en template
        trabajadores = []
        for tt in TurnoTrabajador.objects.filter(turno=turno).select_related('trabajador'):
            trabajadores.append({
                # Serializar por DNI para que la plantilla pueda preseleccionar por value="dni"
                'trabajador_id': getattr(tt.trabajador, 'dni', None),
                'funcion': tt.funcion,
                'observaciones': tt.observaciones,
            })

        # Usar select_related para evitar N+1 queries
        complementos = []
        for c in TurnoComplemento.objects.filter(turno=turno).select_related('tipo_complemento', 'sondaje'):
            complementos.append({
                'tipo_complemento_id': c.tipo_complemento_id,
                'codigo_serie': c.codigo_serie,
                'metros_inicio': str(c.metros_inicio),
                'metros_fin': str(c.metros_fin),
                'sondaje_id': c.sondaje_id,
            })

        aditivos = []
        for a in TurnoAditivo.objects.filter(turno=turno).select_related('tipo_aditivo', 'unidad_medida', 'sondaje'):
            aditivos.append({
                'tipo_aditivo_id': a.tipo_aditivo_id,
                'cantidad_usada': float(a.cantidad_usada),
                'unidad_medida_id': a.unidad_medida_id,
                'sondaje_id': a.sondaje_id,
            })

        actividades = []
        for act in TurnoActividad.objects.filter(turno=turno).select_related('actividad'):
            actividades.append({
                'actividad_id': act.actividad_id,
                'hora_inicio': act.hora_inicio.isoformat() if act.hora_inicio else '',
                'hora_fin': act.hora_fin.isoformat() if act.hora_fin else '',
                'observaciones': act.observaciones,
            })

        corridas = []
        for cr in TurnoCorrida.objects.filter(turno=turno).only('corrida_numero', 'desde', 'hasta', 'longitud_testigo', 'pct_recuperacion', 'pct_retorno_agua', 'litologia'):
            corridas.append({
                'corrida_numero': cr.corrida_numero,
                'desde': float(cr.desde),
                'hasta': float(cr.hasta),
                'longitud_testigo': float(cr.longitud_testigo),
                'pct_recuperacion': float(cr.pct_recuperacion),
                'pct_retorno_agua': float(cr.pct_retorno_agua),
                'litologia': cr.litologia,
            })

        # Preferir sumar los metrajes guardados en TurnoSondaje para obtener el avance
        try:
            from django.db.models import Sum
            metros_sum = TurnoSondaje.objects.filter(turno=turno).aggregate(total=Sum('metros_turno'))['total']
            metros = float(metros_sum) if metros_sum is not None else 0
        except Exception:
            # Fallback a TurnoAvance si algo falla
            avance = TurnoAvance.objects.filter(turno=turno).first()
            metros = float(avance.metros_perforados) if avance else 0

        # aÃ±adir datos al contexto serializados
        import json as _json
        # Asegurar que el conjunto de tipos de actividad presente en la plantilla
        # incluya las actividades ya asociadas al turno (si las hubiera). Esto
        # evita que, al editar un turno, el <select> quede vacÃ­o si la actividad
        # no estÃ¡ asignada al contrato actual.
        try:
            actividad_ids = [int(a['actividad_id']) for a in actividades if a.get('actividad_id')]
            if actividad_ids:
                extra_qs = TipoActividad.objects.filter(id__in=actividad_ids)
                existing_qs = context.get('tipos_actividad')
                try:
                    context['tipos_actividad'] = (existing_qs | extra_qs).distinct()
                except Exception:
                    context['tipos_actividad'] = extra_qs
        except Exception:
            pass

        # Cuando exista lectura de horÃ³metro, exponerla; si no, usar hora ISO para prefill
        _maquina_estado = getattr(turno, 'maquina_estado', None)
        edit_h_ini = ''
        edit_h_fin = ''
        try:
            if _maquina_estado and getattr(_maquina_estado, 'horometro_inicio', None) is not None:
                edit_h_ini = str(_maquina_estado.horometro_inicio)
            elif _maquina_estado and getattr(_maquina_estado, 'hora_inicio', None):
                edit_h_ini = _maquina_estado.hora_inicio.isoformat()
        except Exception:
            edit_h_ini = ''
        try:
            if _maquina_estado and getattr(_maquina_estado, 'horometro_fin', None) is not None:
                edit_h_fin = str(_maquina_estado.horometro_fin)
            elif _maquina_estado and getattr(_maquina_estado, 'hora_fin', None):
                edit_h_fin = _maquina_estado.hora_fin.isoformat()
        except Exception:
            edit_h_fin = ''

        context.update({
            'edit_mode': True,
            'edit_turno_id': turno.id,
            # Previously single sondaje id; now expose list of sondaje ids for the template
            'edit_sondaje_ids': list(turno.sondajes.values_list('id', flat=True)),
            # Lista de objetos {'id': sondaje_id, 'metros': metros_turno} para prellenado de metrajes
            'edit_sondajes_json': _json.dumps([
                {'id': ts.sondaje_id, 'metros': float(ts.metros_turno or 0)}
                for ts in TurnoSondaje.objects.filter(turno=turno)
            ]),
            'edit_maquina_id': turno.maquina_id,
            'edit_tipo_turno_id': turno.tipo_turno_id,
            'edit_fecha': turno.fecha.isoformat(),
            'edit_trabajadores_json': _json.dumps(trabajadores),
            'edit_complementos_json': _json.dumps(complementos),
            'edit_aditivos_json': _json.dumps(aditivos),
            'edit_actividades_json': _json.dumps(actividades),
            'edit_corridas_json': _json.dumps(corridas),
            'edit_metros_perforados': metros,
            'edit_hora_inicio_maq': edit_h_ini,
            'edit_hora_fin_maq': edit_h_fin,
            'edit_estado_bomba': getattr(getattr(turno, 'maquina_estado', None), 'estado_bomba', ''),
            'edit_estado_unidad': getattr(getattr(turno, 'maquina_estado', None), 'estado_unidad', ''),
            'edit_estado_rotacion': getattr(getattr(turno, 'maquina_estado', None), 'estado_rotacion', ''),
        })

    return render(request, 'drilling/turno/crear_completo.html', context)

def convert_to_time(time_str):
    """Convierte string de hora a objeto time"""
    if not time_str:
        return None
    
    try:
        # Si ya es un objeto time, devolverlo tal como estÃ¡
        if isinstance(time_str, time):
            return time_str
            
        # Si es string, convertir
        if isinstance(time_str, str):
            # Formato HH:MM o HH:MM:SS
            time_parts = time_str.split(':')
            if len(time_parts) >= 2:
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                second = int(time_parts[2]) if len(time_parts) > 2 else 0
                return time(hour, minute, second)
        
        return None
    except (ValueError, AttributeError):
        return None

def get_context_data(request):
    """Obtener datos de contexto para el formulario - OPTIMIZADO CON CACHE"""
    from django.core.cache import cache
    
    contract = request.user.contrato
    
    if request.user.can_manage_all_contracts():
        # Admin: usar only() para cargar solo campos necesarios
        sondajes = Sondaje.objects.only('id', 'nombre_sondaje', 'estado', 'contrato')
        maquinas = Maquina.objects.only('id', 'nombre', 'estado', 'contrato')
        trabajadores = Trabajador.objects.select_related('cargo').only(
            'id', 'nombres', 'apellidos', 'dni', 'estado', 'contrato', 'cargo__nombre'
        )
    else:
        sondajes = Sondaje.objects.filter(contrato=contract).only(
            'id', 'nombre_sondaje', 'estado', 'contrato'
        )
        maquinas = Maquina.objects.filter(contrato=contract).only(
            'id', 'nombre', 'estado', 'contrato'
        )
        trabajadores = Trabajador.objects.filter(contrato=contract).select_related('cargo').only(
            'id', 'nombres', 'apellidos', 'dni', 'estado', 'contrato', 'cargo__nombre'
        )
    
    # Actividades: usar cache si es admin, o relaciÃ³n contrato si es usuario normal
    if request.user.can_manage_all_contracts():
        # Intentar obtener de cache, si no existe hacer query
        tipos_actividad_data = cache.get('tipos_actividad_all')
        if tipos_actividad_data is None:
            tipos_actividad_data = list(TipoActividad.objects.values('id', 'nombre', 'descripcion_corta'))
            cache.set('tipos_actividad_all', tipos_actividad_data, timeout=3600)  # 1 hora
        tipos_actividad_qs = tipos_actividad_data
    else:
        # request.user.contrato puede ser None; manejar ese caso
        tipos_actividad_qs = TipoActividad.objects.none()
        if contract:
            try:
                tipos_actividad_qs = contract.actividades.only('id', 'nombre', 'descripcion_corta')
            except Exception:
                tipos_actividad_qs = TipoActividad.objects.none()
    
    # Tipos de turno: usar cache (datos estÃ¡ticos, 2 registros)
    tipos_turno_data = cache.get('tipos_turno_all')
    if tipos_turno_data is None:
        tipos_turno_data = list(TipoTurno.objects.values('id', 'nombre'))
        cache.set('tipos_turno_all', tipos_turno_data, timeout=86400)  # 24 horas
    
    # Unidades de medida: usar cache (datos estÃ¡ticos, 1 registro)
    unidades_data = cache.get('unidades_medida_all')
    if unidades_data is None:
        unidades_data = list(UnidadMedida.objects.values('id', 'nombre', 'simbolo'))
        cache.set('unidades_medida_all', unidades_data, timeout=86400)  # 24 horas

    return {
        'sondajes': sondajes.filter(estado='ACTIVO'),
        'maquinas': maquinas.filter(estado='OPERATIVO'),
        'trabajadores': trabajadores.filter(estado='ACTIVO'),
        'tipos_turno': tipos_turno_data,
        'tipos_actividad': tipos_actividad_qs,
        'tipos_complemento': TipoComplemento.objects.filter(
            contrato=contract,
            estado='NUEVO'
        ).select_related('contrato').only('id', 'nombre', 'codigo', 'serie', 'contrato'),
        'tipos_aditivo': TipoAditivo.objects.filter(
            contrato=contract
        ).select_related('contrato').only('id', 'nombre', 'codigo', 'contrato'),
        'unidades_medida': unidades_data,
        'today': timezone.now().date(),
    }


@login_required
def api_create_actividad(request):
    """API pequeÃ±a para crear un TipoActividad desde un modal (POST: {'nombre': '...'}).
    Retorna JSON {'ok': True, 'id': x, 'nombre': '...'} o {'ok': False, 'error': '...'}
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'MÃ©todo no permitido'}, status=405)

    # Permisos: solo usuarios con contrato pueden crear (ajustar segÃºn reglas reales)
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'No autenticado'}, status=403)

    nombre = request.POST.get('nombre') or request.POST.get('name')
    if not nombre or not nombre.strip():
        return JsonResponse({'ok': False, 'error': 'Nombre requerido'}, status=400)

    nombre = nombre.strip()
    try:
        actividad = TipoActividad.objects.create(nombre=nombre)
        # Si el usuario no es admin del sistema y tiene contrato, asignar la actividad al contrato
        try:
            if not request.user.can_manage_all_contracts() and getattr(request.user, 'contrato', None):
                request.user.contrato.actividades.add(actividad)
        except Exception:
            # No bloquear la creaciÃ³n por problemas secundarios en la asignaciÃ³n M2M
            pass
        return JsonResponse({'ok': True, 'id': actividad.id, 'nombre': actividad.nombre})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@login_required
def listar_turnos(request):
    # Filtrar turnos por permisos del usuario - OPTIMIZADO
    if request.user.can_manage_all_contracts():
        base_turnos = Turno.objects.select_related('contrato')
        sondajes_filtro = Sondaje.objects.only('id', 'nombre_sondaje', 'contrato')
    else:
        # Use the M2M relation 'sondajes' instead of the old FK
        base_turnos = Turno.objects.filter(contrato=request.user.contrato).select_related('contrato')
        sondajes_filtro = Sondaje.objects.filter(contrato=request.user.contrato).only(
            'id', 'nombre_sondaje', 'contrato'
        )
    
    # Aplicar filtros de bÃºsqueda
    filtros = {
        'sondaje': request.GET.get('sondaje', ''),
        'fecha_desde': request.GET.get('fecha_desde', ''),
        'fecha_hasta': request.GET.get('fecha_hasta', ''),
    }
    
    turnos_query = base_turnos
    
    if filtros['sondaje']:
        # filter by selected sondaje id (M2M)
        turnos_query = turnos_query.filter(sondajes__id=filtros['sondaje'])
    
    if filtros['fecha_desde']:
        turnos_query = turnos_query.filter(fecha__gte=filtros['fecha_desde'])
    
    if filtros['fecha_hasta']:
        turnos_query = turnos_query.filter(fecha__lte=filtros['fecha_hasta'])
    
    # SELECT_RELATED y PREFETCH_RELATED con nombres correctos
    # For M2M relations use prefetch_related; select_related only for FKs
    turnos = turnos_query.select_related(
        'maquina', 'tipo_turno'
    ).prefetch_related(
        'sondajes__contrato',
        'trabajadores_turno__trabajador',
    ).order_by('-fecha', '-id')
    
    # Agregar otros prefetch segÃºn los nombres reales de tus modelos
    try:
        # TurnoAvance declara related_name='avance' en el modelo, es OneToOne -> usar select_related
        turnos = turnos.select_related('avance')
        # Anotar avance_metros desde TurnoAvance para evitar errores cuando no exista la relaciÃ³n
        from django.db.models import OuterRef, Subquery, DecimalField
        avance_sq = TurnoAvance.objects.filter(turno=OuterRef('pk')).values('metros_perforados')[:1]
        turnos = turnos.annotate(avance_metros=Subquery(avance_sq, output_field=DecimalField()))
    except Exception:
        # Si el nombre difiere en tu modelo, ignorar y continuar
        pass
    
    # EstadÃ­sticas
    total_turnos = turnos.count()
    
    # Metros con nombre correcto del modelo
    metros_total = 0
    try:
        # Ajustar segÃºn el nombre real de tu modelo de avance
        from django.db.models import Sum
        metros_result = TurnoAvance.objects.filter(
            turno__in=turnos
        ).aggregate(total=Sum('metros_perforados'))
        metros_total = metros_result['total'] or 0
    except:
        metros_total = 0
    
    # Turnos mes actual
    from django.utils import timezone
    hoy = timezone.now().date()
    turnos_mes = turnos.filter(fecha__month=hoy.month, fecha__year=hoy.year).count()
    
    # Promedio
    promedio_avance = metros_total / total_turnos if total_turnos > 0 else 0
    
    # PaginaciÃ³n
    from django.core.paginator import Paginator
    paginator = Paginator(turnos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'turnos': page_obj,
        'sondajes_filtro': sondajes_filtro.filter(estado='ACTIVO'),
        'filtros': filtros,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'total_turnos': total_turnos,
        'metros_total': metros_total,
        'turnos_mes': turnos_mes,
        'promedio_avance': promedio_avance,
    }
    
    return render(request, 'drilling/turno/listar.html', context)


class TurnoDetailView(AdminOrContractFilterMixin, DetailView):
    model = Turno
    template_name = 'drilling/turno/detail.html'
    context_object_name = 'turno'


class TurnoDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = Turno
    template_name = 'drilling/turno/confirm_delete.html'
    success_url = reverse_lazy('listar-turnos')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Turno eliminado exitosamente')
        return super().delete(request, *args, **kwargs)


@login_required
def aprobar_turno(request, pk):
    """Vista para que un admin o supervisor apruebe un turno (marca APROBADO)."""
    # Solo admin del sistema o usuarios con rol RESIDENTE pueden aprobar
    if not (request.user.is_system_admin or request.user.role == 'RESIDENTE'):
        messages.error(request, 'No tiene permisos para aprobar turnos')
        return redirect('listar-turnos')

    turno = get_object_or_404(Turno, pk=pk)

    if request.method == 'POST':
        turno.estado = 'APROBADO'
        turno.save(update_fields=['estado'])
        messages.success(request, f'Turno #{turno.id} marcado como APROBADO')
        return redirect('listar-turnos')

    return render(request, 'drilling/turno/confirm_approve.html', {'turno': turno})

# ===============================
# ABASTECIMIENTO VIEWS - COMPLETO
# ===============================

class AbastecimientoListView(AdminOrContractFilterMixin, ListView):
    model = Abastecimiento
    template_name = 'drilling/abastecimiento/list.html'
    context_object_name = 'abastecimientos'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'contrato', 'unidad_medida', 'tipo_complemento', 'tipo_aditivo'
        ).order_by('-fecha', '-created_at')
        
        # Filtros adicionales
        familia = self.request.GET.get('familia')
        if familia:
            queryset = queryset.filter(familia=familia)
            
        contrato_id = self.request.GET.get('contrato')
        if contrato_id and self.request.user.can_manage_all_contracts():
            queryset = queryset.filter(contrato_id=contrato_id)
            
        fecha_desde = self.request.GET.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha__gte=fecha_desde)
            
        fecha_hasta = self.request.GET.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha__lte=fecha_hasta)
        
        mes = self.request.GET.get('mes')
        if mes:
            queryset = queryset.filter(mes__icontains=mes)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['familias'] = Abastecimiento.FAMILIA_CHOICES
        context['filtros'] = self.request.GET
        
        # EstadÃ­sticas rÃ¡pidas
        queryset = self.get_queryset()
        context['total_registros'] = queryset.count()
        context['valor_total'] = queryset.aggregate(
            total=models.Sum('total')
        )['total'] or 0
        
        return context

class AbastecimientoCreateView(AdminOrContractFilterMixin, CreateView):
    model = Abastecimiento
    form_class = AbastecimientoForm
    template_name = 'drilling/abastecimiento/form.html'
    success_url = reverse_lazy('abastecimiento-list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filtrar contratos accesibles
        form.fields['contrato'].queryset = self.request.user.get_accessible_contracts()
        
        # Si no es admin, preseleccionar su contrato
        if not self.request.user.can_manage_all_contracts():
            form.fields['contrato'].initial = self.request.user.contrato
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Abastecimiento creado exitosamente')
        return super().form_valid(form)

class AbastecimientoUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = Abastecimiento
    form_class = AbastecimientoForm
    template_name = 'drilling/abastecimiento/form.html'
    success_url = reverse_lazy('abastecimiento-list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Solo permitir editar si no tiene consumos asociados
        return queryset.annotate(
            tiene_consumos=models.Exists(
                ConsumoStock.objects.filter(abastecimiento=models.OuterRef('pk'))
            )
        ).filter(tiene_consumos=False)
    
    def form_valid(self, form):
        messages.success(self.request, 'Abastecimiento actualizado exitosamente')
        return super().form_valid(form)

class AbastecimientoDetailView(AdminOrContractFilterMixin, DetailView):
    model = Abastecimiento
    template_name = 'drilling/abastecimiento/detail.html'
    context_object_name = 'abastecimiento'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener consumos relacionados. Use prefetch for turno.sondajes (M2M)
        context['consumos'] = ConsumoStock.objects.filter(
            abastecimiento=self.object
        ).select_related('turno').prefetch_related('turno__sondajes').order_by('-created_at')
        
        # Calcular stock disponible
        total_consumido = context['consumos'].aggregate(
            total=models.Sum('cantidad_consumida')
        )['total'] or 0
        
        context['stock_disponible'] = self.object.cantidad - total_consumido
        context['total_consumido'] = total_consumido
        
        return context

class AbastecimientoDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = Abastecimiento
    template_name = 'drilling/abastecimiento/confirm_delete.html'
    success_url = reverse_lazy('abastecimiento-list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Solo permitir eliminar si no tiene consumos
        return queryset.annotate(
            tiene_consumos=models.Exists(
                ConsumoStock.objects.filter(abastecimiento=models.OuterRef('pk'))
            )
        ).filter(tiene_consumos=False)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Abastecimiento eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

@login_required
def importar_abastecimiento_excel(request):
    """Vista para importar con borrado previo por mes operativo"""
    
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, 'Debe seleccionar un archivo Excel')
            return redirect('importar-abastecimiento')
        
        excel_file = request.FILES['excel_file']
        delete_existing = request.POST.get('delete_existing', 'on') == 'on'
        
        # Validar extensiÃ³n
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'El archivo debe ser formato Excel (.xlsx o .xls)')
            return redirect('importar-abastecimiento')
        
        # Procesar archivo
        importer = AbastecimientoExcelImporter(request.user)
        result = importer.process_excel(excel_file, delete_existing)
        
        if result['success']:
            mensaje_principal = f"ImportaciÃ³n completada: {result['success_count']} registros creados"
            
            if result['deleted_count'] > 0:
                mensaje_principal += f", {result['deleted_count']} registros anteriores eliminados"
                
            if result['skip_count'] > 0:
                mensaje_principal += f", {result['skip_count']} registros omitidos"
            
            messages.success(request, mensaje_principal)
            
            # Mostrar informaciÃ³n adicional
            if result['meses_procesados']:
                messages.info(
                    request,
                    f"Meses procesados: {', '.join(result['meses_procesados'])}"
                )
            
            if result['contratos_procesados']:
                messages.info(
                    request,
                    f"Contratos afectados: {', '.join(result['contratos_procesados'])}"
                )
            
            # Mostrar errores si los hay
            if result['errors']:
                for error in result['errors'][:10]:  # Mostrar mÃ¡ximo 10 errores
                    messages.warning(request, error)
                    
                if len(result['errors']) > 10:
                    messages.warning(
                        request,
                        f"... y {len(result['errors']) - 10} errores mÃ¡s"
                    )
        else:
            messages.error(request, f"Error en importaciÃ³n: {result['error']}")
            
        return redirect('abastecimiento-list')
    
    # GET - Mostrar formulario de importaciÃ³n
    context = {
        'is_system_admin': request.user.can_manage_all_contracts(),
        'accessible_contracts': request.user.get_accessible_contracts()
    }
    
    return render(request, 'drilling/abastecimiento/importar.html', context)

# ===============================
# CONSUMO STOCK VIEWS - COMPLETO
# ===============================

class ConsumoStockListView(AdminOrContractFilterMixin, ListView):
    model = ConsumoStock
    template_name = 'drilling/consumo/list.html'
    context_object_name = 'consumos'
    paginate_by = 50
    
    def get_queryset(self):
        # Adjust for Turno.sondajes (M2M). Keep select_related for FK fields.
        queryset = ConsumoStock.objects.select_related(
            'turno', 'abastecimiento', 'abastecimiento__unidad_medida'
        ).prefetch_related('turno__sondajes__contrato').order_by('-created_at')
        
        # Filtrar por contrato si no es admin
        if not self.request.user.can_manage_all_contracts():
            queryset = queryset.filter(turno__sondajes__contrato=self.request.user.contrato)
        
        # Filtros adicionales
        contrato_id = self.request.GET.get('contrato')
        if contrato_id and self.request.user.can_manage_all_contracts():
            queryset = queryset.filter(turno__sondajes__contrato_id=contrato_id)
            
        sondaje_id = self.request.GET.get('sondaje')
        if sondaje_id:
            queryset = queryset.filter(turno__sondajes__id=sondaje_id)
            
        fecha_desde = self.request.GET.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(turno__fecha__gte=fecha_desde)
            
        fecha_hasta = self.request.GET.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(turno__fecha__lte=fecha_hasta)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtros'] = self.request.GET
        
        # Sondajes disponibles para filtro
        if self.request.user.can_manage_all_contracts():
            context['sondajes'] = Sondaje.objects.all().order_by('nombre_sondaje')
        else:
            context['sondajes'] = Sondaje.objects.filter(
                contrato=self.request.user.contrato
            ).order_by('nombre_sondaje')
        
        return context

class ConsumoStockCreateView(AdminOrContractFilterMixin, CreateView):
    model = ConsumoStock
    form_class = ConsumoStockForm
    template_name = 'drilling/consumo/form.html'
    success_url = reverse_lazy('consumo-list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        # Filtrar turnos por contrato (use sondajes M2M)
        accessible_contracts = self.request.user.get_accessible_contracts()
        form.fields['turno'].queryset = Turno.objects.filter(
            sondajes__contrato__in=accessible_contracts
        ).prefetch_related('sondajes').order_by('-fecha')
        
        # Filtrar abastecimientos con stock disponible
        form.fields['abastecimiento'].queryset = Abastecimiento.objects.filter(
            contrato__in=accessible_contracts
        ).annotate(
            stock_disponible=models.F('cantidad') - models.Subquery(
                ConsumoStock.objects.filter(
                    abastecimiento=models.OuterRef('pk')
                ).aggregate(
                    total_consumido=models.Sum('cantidad_consumida')
                )['total_consumido'] or 0
            )
        ).filter(stock_disponible__gt=0).order_by('descripcion')
        
        return form
    
    def form_valid(self, form):
        # Validar que hay stock suficiente
        abastecimiento = form.instance.abastecimiento
        cantidad_solicitada = form.instance.cantidad_consumida
        
        stock_actual = abastecimiento.cantidad - (
            ConsumoStock.objects.filter(
                abastecimiento=abastecimiento
            ).aggregate(
                total=models.Sum('cantidad_consumida')
            )['total'] or 0
        )
        
        if cantidad_solicitada > stock_actual:
            form.add_error(
                'cantidad_consumida',
                f'Stock insuficiente. Disponible: {stock_actual}'
            )
            return self.form_invalid(form)
        
        messages.success(self.request, 'Consumo registrado exitosamente')
        return super().form_valid(form)

class ConsumoStockUpdateView(AdminOrContractFilterMixin, UpdateView):
    model = ConsumoStock
    form_class = ConsumoStockForm
    template_name = 'drilling/consumo/form.html'
    success_url = reverse_lazy('consumo-list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por contrato si no es admin
        if not self.request.user.can_manage_all_contracts():
            queryset = queryset.filter(turno__sondajes__contrato=self.request.user.contrato)
        
        return queryset
    
    def form_valid(self, form):
        messages.success(self.request, 'Consumo actualizado exitosamente')
        return super().form_valid(form)

class ConsumoStockDeleteView(AdminOrContractFilterMixin, DeleteView):
    model = ConsumoStock
    template_name = 'drilling/consumo/confirm_delete.html'
    success_url = reverse_lazy('consumo-list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por contrato si no es admin
        if not self.request.user.can_manage_all_contracts():
            queryset = queryset.filter(turno__sondajes__contrato=self.request.user.contrato)
        
        return queryset
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Consumo eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

# ===============================
# STOCK DISPONIBLE VIEW
# ===============================

class StockDisponibleView(AdminOrContractFilterMixin, TemplateView):
    template_name = 'drilling/stock/disponible.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calcular stock disponible por producto
        stock_query = '''
            SELECT 
                a.id,
                a.descripcion,
                a.familia,
                a.serie,
                um.simbolo as unidad,
                SUM(a.cantidad) as abastecido,
                COALESCE(SUM(c.cantidad_consumida), 0) as consumido,
                SUM(a.cantidad) - COALESCE(SUM(c.cantidad_consumida), 0) as disponible,
                a.precio_unitario,
                (SUM(a.cantidad) - COALESCE(SUM(c.cantidad_consumida), 0)) * a.precio_unitario as valor_stock
            FROM abastecimiento a
            LEFT JOIN consumo_stock c ON a.id = c.abastecimiento_id
            LEFT JOIN unidades_medida um ON a.unidad_medida_id = um.id
            WHERE a.contrato_id = %s
            GROUP BY a.id, a.descripcion, a.familia, a.serie, um.simbolo, a.precio_unitario
            HAVING SUM(a.cantidad) - COALESCE(SUM(c.cantidad_consumida), 0) > 0
            ORDER BY a.familia, a.descripcion
        '''
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(stock_query, [self.request.user.contrato.id])
            stock_data = cursor.fetchall()
        
        # Organizar por familia
        stock_por_familia = {}
        total_valor = 0
        
        for row in stock_data:
            familia = row[2]
            if familia not in stock_por_familia:
                stock_por_familia[familia] = []
            
            stock_por_familia[familia].append({
                'id': row[0],
                'descripcion': row[1],
                'serie': row[3],
                'unidad': row[4],
                'abastecido': row[5],
                'consumido': row[6],
                'disponible': row[7],
                'precio_unitario': row[8],
                'valor_stock': row[9] or 0
            })
            
            total_valor += row[9] or 0
        
        context['stock_por_familia'] = stock_por_familia
        context['total_valor_stock'] = total_valor
        
        return context

# ===============================
# API VIEWS
# ===============================

@login_required
def api_abastecimiento_detalle(request, pk):
    """API para obtener detalles de un abastecimiento"""
    try:
        abastecimiento = get_object_or_404(
            Abastecimiento.objects.filter(contrato=request.user.contrato),
            pk=pk
        )
        
        # Calcular stock disponible
        total_consumido = ConsumoStock.objects.filter(
            abastecimiento=abastecimiento
        ).aggregate(
            total=models.Sum('cantidad_consumida')
        )['total'] or 0
        
        stock_disponible = abastecimiento.cantidad - total_consumido
        
        data = {
            'id': abastecimiento.id,
            'descripcion': abastecimiento.descripcion,
            'serie': abastecimiento.serie,
            'familia': abastecimiento.familia,
            'familia_display': abastecimiento.get_familia_display(),
            'cantidad': str(abastecimiento.cantidad),
            'unidad_medida': abastecimiento.unidad_medida.simbolo,
            'precio_unitario': str(abastecimiento.precio_unitario),
            'total': str(abastecimiento.total),
            'stock_disponible': str(stock_disponible),
            'observaciones': abastecimiento.observaciones,
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ===============================
# REPORTE METRAJE PRODUCTOS DIAMANTADOS
# ===============================

@login_required
def reporte_metraje_complementos(request):
    """
    Reporte de metraje acumulado por cada producto diamantado (complemento)
    """
    if not request.user.can_supervise_operations():
        messages.error(request, "No tiene permisos para ver este reporte")
        return redirect('dashboard')
    
    # Obtener parÃ¡metros de filtro
    contrato_id = request.GET.get('contrato')
    tipo_complemento_id = request.GET.get('tipo_complemento')
    codigo_serie = request.GET.get('codigo_serie')
    estado = request.GET.get('estado')
    
    # Query base
    from django.db.models import Sum, Count, Max, Min
    
    complementos_query = TurnoComplemento.objects.select_related(
        'tipo_complemento',
        'turno__contrato',
        'turno__maquina'
    ).all()
    
    # Aplicar filtros
    if not request.user.can_manage_all_contracts():
        complementos_query = complementos_query.filter(turno__contrato=request.user.contrato)
    elif contrato_id:
        complementos_query = complementos_query.filter(turno__contrato_id=contrato_id)
    
    if tipo_complemento_id:
        complementos_query = complementos_query.filter(tipo_complemento_id=tipo_complemento_id)
    
    if codigo_serie:
        complementos_query = complementos_query.filter(codigo_serie__icontains=codigo_serie)
    
    if estado:
        complementos_query = complementos_query.filter(tipo_complemento__estado=estado)
    
    # Agrupar por producto diamantado (tipo + serie)
    resumen_complementos = complementos_query.values(
        'tipo_complemento_id',
        'tipo_complemento__nombre',
        'tipo_complemento__categoria',
        'tipo_complemento__estado',
        'codigo_serie'
    ).annotate(
        total_metros=Sum('metros_turno_calc'),
        cantidad_usos=Count('id'),
        ultimo_uso=Max('turno__fecha'),
        primer_uso=Min('turno__fecha'),
        metros_promedio=models.Avg('metros_turno_calc')
    ).order_by('-total_metros')
    
    # EstadÃ­sticas generales
    totales = complementos_query.aggregate(
        total_metros_general=Sum('metros_turno_calc'),
        total_registros=Count('id'),
        productos_unicos=Count('codigo_serie', distinct=True)
    )
    
    # Datos para filtros
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
    
    tipos_complemento = TipoComplemento.objects.all().order_by('nombre')
    if not request.user.can_manage_all_contracts():
        tipos_complemento = tipos_complemento.filter(contrato=request.user.contrato)
    
    context = {
        'resumen_complementos': resumen_complementos,
        'totales': totales,
        'contratos': contratos,
        'tipos_complemento': tipos_complemento,
        'estados': TipoComplemento.ESTADO_CHOICES,
        'filtros': {
            'contrato_id': contrato_id,
            'tipo_complemento_id': tipo_complemento_id,
            'codigo_serie': codigo_serie,
            'estado': estado,
        }
    }
    
    return render(request, 'drilling/complementos/reporte_metraje.html', context)


# ===============================
# METAS DE MÃQUINAS
# ===============================

@login_required
def metas_maquina_list(request):
    """Lista de metas de mÃ¡quinas con cumplimiento en tiempo real"""
    
    # Filtros
    contrato_id = request.GET.get('contrato')
    maquina_id = request.GET.get('maquina')
    año = request.GET.get('año')
    mes = request.GET.get('mes')
    solo_activas = request.GET.get('activas', '1') == '1'
    
    # Query base
    metas = MetaMaquina.objects.select_related(
        'contrato', 'maquina', 'created_by'
    ).all()
    
    # Aplicar filtros por permisos de usuario
    if not request.user.can_manage_all_contracts():
        metas = metas.filter(contrato=request.user.contrato)
    
    # Aplicar filtros de bÃºsqueda
    if contrato_id:
        metas = metas.filter(contrato_id=contrato_id)
    
    if maquina_id:
        metas = metas.filter(maquina_id=maquina_id)
    
    if año:
        metas = metas.filter(año=año)
    
    if mes:
        metas = metas.filter(mes=mes)
    
    if solo_activas:
        metas = metas.filter(activo=True)
    
    metas = metas.order_by('-año', '-mes', 'contrato__nombre_contrato', 'maquina__nombre')
    
    # Calcular mÃ©tricas de cumplimiento para cada meta
    metas_con_cumplimiento = []
    for meta in metas:
        fecha_inicio = meta.get_fecha_inicio_periodo()
        fecha_fin = meta.get_fecha_fin_periodo()
        
        # Calcular metros reales perforados en el perÃ­odo
        # Nota: el campo 'estado' estÃ¡ en el modelo Turno, no en TurnoAvance
        turnos_en_periodo = TurnoAvance.objects.filter(
            turno__maquina=meta.maquina,
            turno__contrato=meta.contrato,
            turno__fecha__gte=fecha_inicio,
            turno__fecha__lte=fecha_fin,
            turno__estado__in=['COMPLETADO', 'APROBADO']
        )
        
        metros_reales = turnos_en_periodo.aggregate(
            total=Sum('metros_perforados')
        )['total'] or Decimal('0')
        
        # Debug: contar turnos encontrados
        total_turnos = turnos_en_periodo.count()
        
        # Calcular cumplimiento
        porcentaje_cumplimiento = meta.calcular_cumplimiento(metros_reales)
        brecha = meta.meta_metros - metros_reales
        
        # Determinar estado
        if porcentaje_cumplimiento >= 100:
            estado_cumplimiento = 'CUMPLIDO'
            badge_class = 'success'
        elif porcentaje_cumplimiento >= 90:
            estado_cumplimiento = 'CERCA'
            badge_class = 'info'
        elif porcentaje_cumplimiento >= 70:
            estado_cumplimiento = 'REGULAR'
            badge_class = 'warning'
        elif porcentaje_cumplimiento >= 50:
            estado_cumplimiento = 'BAJO'
            badge_class = 'warning'
        else:
            estado_cumplimiento = 'CRÃTICO'
            badge_class = 'danger'
        
        # Determinar si el perÃ­odo estÃ¡ activo
        hoy = date.today()
        if hoy < fecha_inicio:
            estado_periodo = 'FUTURO'
            periodo_badge = 'secondary'
        elif hoy > fecha_fin:
            estado_periodo = 'FINALIZADO'
            periodo_badge = 'dark'
        else:
            estado_periodo = 'EN CURSO'
            periodo_badge = 'primary'
        
        metas_con_cumplimiento.append({
            'meta': meta,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'metros_reales': metros_reales,
            'total_turnos': total_turnos,  # Para debug
            'porcentaje_cumplimiento': porcentaje_cumplimiento,
            'brecha': brecha,
            'estado_cumplimiento': estado_cumplimiento,
            'badge_class': badge_class,
            'estado_periodo': estado_periodo,
            'periodo_badge': periodo_badge,
        })
    
    # Datos para filtros
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
    
    maquinas = Maquina.objects.filter(estado='OPERATIVO').order_by('nombre')
    if not request.user.can_manage_all_contracts():
        maquinas = maquinas.filter(contrato=request.user.contrato)
    
    # años disponibles (desde 2024 hasta año actual + 1)
    año_actual = date.today().year
    años_disponibles = range(2024, año_actual + 2)
    
    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    context = {
        'metas_con_cumplimiento': metas_con_cumplimiento,
        'contratos': contratos,
        'maquinas': maquinas,
        'años_disponibles': años_disponibles,
        'meses': meses,
        'filtros': {
            'contrato_id': contrato_id,
            'maquina_id': maquina_id,
            'año': año,
            'mes': mes,
            'solo_activas': solo_activas,
        }
    }
    
    return render(request, 'drilling/metas/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def metas_maquina_create(request):
    """Crear nueva meta de mÃ¡quina"""
    
    if request.method == 'POST':
        contrato_id = request.POST.get('contrato')
        maquina_id = request.POST.get('maquina')
        año = request.POST.get('año')
        mes = request.POST.get('mes')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        meta_metros = request.POST.get('meta_metros')
        observaciones = request.POST.get('observaciones', '')
        
        try:
            # Crear la meta
            meta = MetaMaquina(
                contrato_id=contrato_id,
                maquina_id=maquina_id,
                año=int(año),
                mes=int(mes),
                meta_metros=Decimal(meta_metros),
                observaciones=observaciones,
                created_by=request.user,
                activo=True
            )
            
            # Fechas personalizadas (opcional)
            if fecha_inicio and fecha_fin:
                from datetime import datetime
                meta.fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                meta.fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            meta.save()
            
            messages.success(request, f'Meta creada exitosamente para {meta.maquina.nombre}')
            return redirect('metas-maquina-list')
            
        except Exception as e:
            messages.error(request, f'Error al crear meta: {str(e)}')
    
    # GET request - mostrar formulario
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
    
    maquinas = Maquina.objects.filter(estado='OPERATIVO').order_by('nombre')
    if not request.user.can_manage_all_contracts():
        maquinas = maquinas.filter(contrato=request.user.contrato)
    
    año_actual = date.today().year
    años_disponibles = range(2024, año_actual + 2)
    
    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    context = {
        'contratos': contratos,
        'maquinas': maquinas,
        'años_disponibles': años_disponibles,
        'meses': meses,
    }
    
    return render(request, 'drilling/metas/form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def metas_maquina_edit(request, pk):
    """Editar meta de mÃ¡quina existente"""
    
    meta = get_object_or_404(MetaMaquina, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if meta.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para editar esta meta')
            return redirect('metas-maquina-list')
    
    if request.method == 'POST':
        contrato_id = request.POST.get('contrato')
        maquina_id = request.POST.get('maquina')
        año = request.POST.get('año')
        mes = request.POST.get('mes')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        meta_metros = request.POST.get('meta_metros')
        observaciones = request.POST.get('observaciones', '')
        activo = request.POST.get('activo') == '1'
        
        try:
            # Actualizar la meta
            meta.contrato_id = contrato_id
            meta.maquina_id = maquina_id
            meta.año = int(año)
            meta.mes = int(mes)
            meta.meta_metros = Decimal(meta_metros)
            meta.observaciones = observaciones
            meta.activo = activo
            
            # Fechas personalizadas (opcional)
            if fecha_inicio and fecha_fin:
                from datetime import datetime
                meta.fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                meta.fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            else:
                meta.fecha_inicio = None
                meta.fecha_fin = None
            
            meta.save()
            
            messages.success(request, f'Meta actualizada exitosamente')
            return redirect('metas-maquina-list')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar meta: {str(e)}')
    
    # GET request - mostrar formulario
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
    
    maquinas = Maquina.objects.filter(estado='OPERATIVO').order_by('nombre')
    if not request.user.can_manage_all_contracts():
        maquinas = maquinas.filter(contrato=request.user.contrato)
    
    año_actual = date.today().year
    años_disponibles = range(2024, año_actual + 2)
    
    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    context = {
        'meta': meta,
        'contratos': contratos,
        'maquinas': maquinas,
        'años_disponibles': años_disponibles,
        'meses': meses,
        'is_edit': True,
    }
    
    return render(request, 'drilling/metas/form.html', context)


@login_required
@require_http_methods(["POST"])
def metas_maquina_delete(request, pk):
    """Eliminar meta de mÃ¡quina"""
    
    meta = get_object_or_404(MetaMaquina, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if meta.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para eliminar esta meta')
            return redirect('metas-maquina-list')
    
    try:
        maquina_nombre = meta.maquina.nombre
        meta.delete()
        messages.success(request, f'Meta de {maquina_nombre} eliminada exitosamente')
    except Exception as e:
        messages.error(request, f'Error al eliminar meta: {str(e)}')
    
    return redirect('metas-maquina-list')


@login_required
@require_http_methods(["GET", "POST"])
def metas_maquina_gestionar(request):
    """Gestionar metas de todas las mÃ¡quinas de un contrato en una sola vista"""
    
    # Obtener contrato seleccionado
    contrato_id = request.GET.get('contrato') or request.POST.get('contrato')
    año = request.GET.get('año') or request.POST.get('año')
    mes = request.GET.get('mes') or request.POST.get('mes')
    
    # Valores por defecto
    if not año:
        año = str(date.today().year)
    if not mes:
        mes = str(date.today().month)
    
    # Filtrar contratos segÃºn permisos
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
        if not contrato_id:
            contrato_id = str(request.user.contrato_id)
    
    # Si no hay contrato seleccionado, usar el primero disponible
    if not contrato_id and contratos.exists():
        contrato_id = str(contratos.first().id)
    
    contrato = None
    maquinas_data = []
    
    if contrato_id:
        contrato = get_object_or_404(Contrato, pk=contrato_id)
        
        # Verificar permisos
        if not request.user.can_manage_all_contracts():
            if contrato != request.user.contrato:
                messages.error(request, 'No tienes permisos para gestionar este contrato')
                return redirect('metas-maquina-list')
        
        # POST - Guardar metas
        if request.method == 'POST':
            try:
                maquinas = Maquina.objects.filter(contrato=contrato, estado='OPERATIVO')
                # Obtener servicio comÃºn (si se especifica)
                servicio_id = request.POST.get('servicio')
                servicio = None
                if servicio_id:
                    servicio = TipoActividad.objects.get(pk=servicio_id)
                
                metas_creadas = 0
                metas_actualizadas = 0
                
                for maquina in maquinas:
                    meta_metros_key = f'meta_metros_{maquina.id}'
                    activo_key = f'activo_{maquina.id}'
                    meta_id_key = f'meta_id_{maquina.id}'
                    
                    meta_metros = request.POST.get(meta_metros_key)
                    activo = request.POST.get(activo_key) == '1'
                    meta_id = request.POST.get(meta_id_key)
                    
                    # Solo procesar si hay un valor de meta
                    if meta_metros and float(meta_metros) > 0:
                        # Verificar si existe una meta para esta mÃ¡quina, año y mes
                        if meta_id:
                            # Actualizar meta existente
                            meta = MetaMaquina.objects.get(pk=meta_id)
                            meta.meta_metros = Decimal(meta_metros)
                            meta.activo = activo
                            if servicio:
                                meta.servicio = servicio
                            meta.save()
                            metas_actualizadas += 1
                        else:
                            # Verificar si ya existe una meta para este perÃ­odo
                            meta_existente = MetaMaquina.objects.filter(
                                contrato=contrato,
                                maquina=maquina,
                                año=int(año),
                                mes=int(mes),
                                fecha_inicio__isnull=True,
                                fecha_fin__isnull=True
                            ).first()
                            
                            if meta_existente:
                                # Actualizar
                                meta_existente.meta_metros = Decimal(meta_metros)
                                meta_existente.activo = activo
                                if servicio:
                                    meta_existente.servicio = servicio
                                meta_existente.save()
                                metas_actualizadas += 1
                            else:
                                # Crear nueva meta
                                MetaMaquina.objects.create(
                                    contrato=contrato,
                                    maquina=maquina,
                                    servicio=servicio,
                                    año=int(año),
                                    mes=int(mes),
                                    meta_metros=Decimal(meta_metros),
                                    activo=activo,
                                    created_by=request.user
                                )
                                metas_creadas += 1
                
                mensaje = []
                if metas_creadas > 0:
                    mensaje.append(f'{metas_creadas} meta(s) creada(s)')
                if metas_actualizadas > 0:
                    mensaje.append(f'{metas_actualizadas} meta(s) actualizada(s)')
                
                if mensaje:
                    messages.success(request, ' y '.join(mensaje))
                else:
                    messages.info(request, 'No se realizaron cambios')
                
                # Redirigir para evitar reenvÃ­o de formulario
                return redirect(f"{request.path}?contrato={contrato_id}&año={año}&mes={mes}")
                
            except Exception as e:
                messages.error(request, f'Error al guardar metas: {str(e)}')
        
        # GET - Mostrar formulario
        # Obtener todas las mÃ¡quinas del contrato
        maquinas = Maquina.objects.filter(
            contrato=contrato,
            estado='OPERATIVO'
        ).order_by('nombre')
        
        # Calcular perÃ­odo
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        año_int = int(año)
        mes_int = int(mes)
        
        primer_dia_mes = datetime(año_int, mes_int, 1).date()
        mes_anterior = primer_dia_mes - relativedelta(months=1)
        fecha_inicio = datetime(mes_anterior.year, mes_anterior.month, 26).date()
        fecha_fin = datetime(año_int, mes_int, 25).date()
        
        # Para cada mÃ¡quina, obtener su meta y metraje real
        for maquina in maquinas:
            # Buscar meta existente
            meta = MetaMaquina.objects.filter(
                contrato=contrato,
                maquina=maquina,
                año=año_int,
                mes=mes_int,
                fecha_inicio__isnull=True,
                fecha_fin__isnull=True
            ).first()
            
            # Calcular metros reales
            turnos_con_avance = TurnoAvance.objects.filter(
                turno__maquina=maquina,
                turno__contrato=contrato,
                turno__fecha__gte=fecha_inicio,
                turno__fecha__lte=fecha_fin,
                turno__estado__in=['COMPLETADO', 'APROBADO']
            )
            
            metros_reales = turnos_con_avance.aggregate(
                total=Sum('metros_perforados')
            )['total'] or Decimal('0')
            
            total_turnos = turnos_con_avance.count()
            
            # Calcular cumplimiento
            porcentaje_cumplimiento = Decimal('0')
            if meta and meta.meta_metros > 0:
                porcentaje_cumplimiento = (metros_reales / meta.meta_metros) * Decimal('100')
            
            # Calcular valorizaciÃ³n si hay meta con servicio
            valorizacion = None
            if meta and meta.servicio:
                valorizacion = meta.calcular_valorizacion_completa(metros_reales, fecha_fin)
            
            maquinas_data.append({
                'maquina': maquina,
                'meta': meta,
                'meta_metros': meta.meta_metros if meta else Decimal('0'),
                'activo': meta.activo if meta else True,
                'servicio': meta.servicio if meta else None,
                'metros_reales': metros_reales,
                'total_turnos': total_turnos,
                'porcentaje_cumplimiento': porcentaje_cumplimiento,
                'valorizacion': valorizacion,
            })
    
    # años disponibles
    año_actual = date.today().year
    años_disponibles = range(2024, año_actual + 2)
    
    # Meses
    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    # Calcular perÃ­odo para mostrar
    periodo_texto = ''
    if año and mes:
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        año_int = int(año)
        mes_int = int(mes)
        primer_dia_mes = datetime(año_int, mes_int, 1).date()
        mes_anterior = primer_dia_mes - relativedelta(months=1)
        fecha_inicio = datetime(mes_anterior.year, mes_anterior.month, 26).date()
        fecha_fin = datetime(año_int, mes_int, 25).date()
        periodo_texto = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
    
    # Obtener servicios disponibles para el contrato
    servicios_disponibles = TipoActividad.objects.filter(
        es_cobrable=True
    ).order_by('nombre')
    
    # Obtener precios unitarios vigentes para el contrato
    precios_unitarios = []
    if contrato:
        precios_unitarios = PrecioUnitarioServicio.objects.filter(
            contrato=contrato,
            activo=True,
            fecha_inicio_vigencia__lte=fecha_fin
        ).filter(
            models.Q(fecha_fin_vigencia__isnull=True) | 
            models.Q(fecha_fin_vigencia__gte=fecha_inicio)
        ).select_related('servicio')
    
    context = {
        'contratos': contratos,
        'contrato': contrato,
        'contrato_id': contrato_id,
        'año': año,
        'mes': mes,
        'años_disponibles': años_disponibles,
        'meses': meses,
        'maquinas_data': maquinas_data,
        'periodo_texto': periodo_texto,
        'servicios_disponibles': servicios_disponibles,
        'precios_unitarios': precios_unitarios,
    }
    
    return render(request, 'drilling/metas/gestionar.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def metas_maquina_dividir(request, pk):
    """Dividir meta existente en dos perÃ­odos con diferentes valores"""
    
    meta_original = get_object_or_404(MetaMaquina, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if meta_original.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para modificar esta meta')
            return redirect('metas-maquina-list')
    
    # Calcular perÃ­odo original
    fecha_inicio_original = meta_original.get_fecha_inicio_periodo()
    fecha_fin_original = meta_original.get_fecha_fin_periodo()
    
    if request.method == 'POST':
        try:
            fecha_division = request.POST.get('fecha_division')
            nueva_meta_metros = request.POST.get('nueva_meta_metros')
            
            if not fecha_division or not nueva_meta_metros:
                messages.error(request, 'Debe ingresar fecha de divisiÃ³n y nueva meta')
                return redirect('metas-maquina-dividir', pk=pk)
            
            from datetime import datetime, timedelta
            fecha_division = datetime.strptime(fecha_division, '%Y-%m-%d').date()
            nueva_meta_metros = Decimal(nueva_meta_metros)
            
            # Validar que la fecha estÃ© dentro del perÃ­odo
            if fecha_division <= fecha_inicio_original or fecha_division > fecha_fin_original:
                messages.error(request, f'La fecha de divisiÃ³n debe estar entre {fecha_inicio_original} y {fecha_fin_original}')
                return redirect('metas-maquina-dividir', pk=pk)
            
            # Calcular metros ya perforados hasta la fecha de divisiÃ³n
            turnos_periodo1 = TurnoAvance.objects.filter(
                turno__maquina=meta_original.maquina,
                turno__contrato=meta_original.contrato,
                turno__fecha__gte=fecha_inicio_original,
                turno__fecha__lt=fecha_division,
                turno__estado__in=['COMPLETADO', 'APROBADO']
            )
            metros_periodo1 = turnos_periodo1.aggregate(total=Sum('metros_perforados'))['total'] or Decimal('0')
            
            # 1. Desactivar meta original y ajustar su perÃ­odo
            meta_original.fecha_fin = fecha_division - timedelta(days=1)
            meta_original.activo = False
            meta_original.observaciones = (meta_original.observaciones or '') + f' [Dividida el {date.today()}. Real: {metros_periodo1}m]'
            meta_original.save()
            
            # 2. Crear nueva meta para el perÃ­odo restante
            nueva_meta = MetaMaquina.objects.create(
                contrato=meta_original.contrato,
                maquina=meta_original.maquina,
                año=meta_original.año,
                mes=meta_original.mes,
                fecha_inicio=fecha_division,
                fecha_fin=meta_original.get_fecha_fin_periodo(),  # Usar el fin del mes operativo
                meta_metros=nueva_meta_metros,
                activo=True,
                observaciones=f'Meta dividida desde {fecha_division}. Meta anterior: {meta_original.meta_metros}m',
                created_by=request.user
            )
            
            messages.success(
                request, 
                f'Meta dividida exitosamente. '
                f'PerÃ­odo 1: {meta_original.get_fecha_inicio_periodo()} a {meta_original.fecha_fin} ({meta_original.meta_metros}m, Real: {metros_periodo1}m). '
                f'PerÃ­odo 2: {fecha_division} a {nueva_meta.fecha_fin} ({nueva_meta_metros}m)'
            )
            return redirect('metas-maquina-list')
            
        except ValueError as e:
            messages.error(request, f'Error en formato de datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al dividir meta: {str(e)}')
    
    # GET - Mostrar formulario
    # Calcular metros reales del perÃ­odo completo
    turnos_periodo = TurnoAvance.objects.filter(
        turno__maquina=meta_original.maquina,
        turno__contrato=meta_original.contrato,
        turno__fecha__gte=fecha_inicio_original,
        turno__fecha__lte=fecha_fin_original,
        turno__estado__in=['COMPLETADO', 'APROBADO']
    )
    
    metros_reales_total = turnos_periodo.aggregate(total=Sum('metros_perforados'))['total'] or Decimal('0')
    total_turnos = turnos_periodo.count()
    
    # Calcular promedio diario
    dias_transcurridos = (date.today() - fecha_inicio_original).days + 1
    if dias_transcurridos > 0:
        promedio_diario = metros_reales_total / dias_transcurridos
    else:
        promedio_diario = Decimal('0')
    
    # ProyecciÃ³n
    dias_totales = (fecha_fin_original - fecha_inicio_original).days + 1
    proyeccion = promedio_diario * dias_totales if promedio_diario > 0 else Decimal('0')
    
    context = {
        'meta': meta_original,
        'fecha_inicio': fecha_inicio_original,
        'fecha_fin': fecha_fin_original,
        'metros_reales_total': metros_reales_total,
        'total_turnos': total_turnos,
        'promedio_diario': promedio_diario,
        'proyeccion': proyeccion,
        'fecha_hoy': date.today(),
    }
    
    return render(request, 'drilling/metas/dividir.html', context)


@login_required
@require_http_methods(["GET"])
def asignaciones_equipos_list(request):
    """Listar todas las asignaciones de equipos del contrato"""
    
    # Obtener contrato del usuario
    if request.user.can_manage_all_contracts():
        contrato = None
        asignaciones = AsignacionEquipo.objects.all()
    else:
        contrato = request.user.contrato
        if not contrato:
            messages.error(request, 'No tienes un contrato asignado.')
            return redirect('home')
        asignaciones = AsignacionEquipo.objects.filter(equipo__contrato=contrato)
    
    # Filtros
    trabajador_id = request.GET.get('trabajador')
    tipo_equipo = request.GET.get('tipo')
    estado_asignacion = request.GET.get('estado')
    
    if trabajador_id:
        asignaciones = asignaciones.filter(trabajador_id=trabajador_id)
    
    if tipo_equipo:
        asignaciones = asignaciones.filter(equipo__tipo=tipo_equipo)
    
    if estado_asignacion:
        asignaciones = asignaciones.filter(estado=estado_asignacion)
    
    # Ordenar por fecha de asignaciÃ³n (mÃ¡s recientes primero)
    asignaciones = asignaciones.select_related(
        'trabajador', 'equipo', 'organigrama_semanal'
    ).order_by('-fecha_asignacion', 'trabajador__apellidos')
    
    # Obtener trabajadores y tipos de equipo para filtros
    if contrato:
        trabajadores = Trabajador.objects.filter(
            contrato=contrato,
            estado='ACTIVO'
        ).order_by('apellidos', 'nombres')
        tipos_equipo = Equipo.objects.filter(
            contrato=contrato
        ).values_list('tipo', flat=True).distinct()
    else:
        trabajadores = Trabajador.objects.filter(estado='ACTIVO').order_by('apellidos', 'nombres')
        tipos_equipo = Equipo.objects.values_list('tipo', flat=True).distinct()
    
    context = {
        'asignaciones': asignaciones,
        'trabajadores': trabajadores,
        'tipos_equipo': tipos_equipo,
        'estados_asignacion': AsignacionEquipo.ESTADO_CHOICES,
        'trabajador_selected': trabajador_id,
        'tipo_selected': tipo_equipo,
        'estado_selected': estado_asignacion,
    }
    
    return render(request, 'drilling/asignaciones_equipos/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def asignacion_equipo_create(request):
    """Crear nueva asignaciÃ³n de equipo"""
    
    # Verificar contrato
    if not request.user.can_manage_all_contracts() and not request.user.contrato:
        messages.error(request, 'No tienes un contrato asignado.')
        return redirect('home')
    
    if request.method == 'POST':
        form = AsignacionEquipoForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                asignacion = form.save(commit=False)
                # No necesita organigrama, es independiente
                asignacion.save()
                
                # Actualizar estado del equipo
                if asignacion.estado == 'ACTIVO':
                    asignacion.equipo.estado = 'ASIGNADO'
                    asignacion.equipo.save()
                
                messages.success(
                    request, 
                    f'Equipo {asignacion.equipo.codigo_interno} asignado exitosamente a {asignacion.trabajador.nombres} {asignacion.trabajador.apellidos}'
                )
                return redirect('asignaciones-equipos-list')
            
            except Exception as e:
                messages.error(request, f'Error al crear asignaciÃ³n: {str(e)}')
    else:
        form = AsignacionEquipoForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Nueva AsignaciÃ³n de Equipo',
    }
    
    return render(request, 'drilling/asignaciones_equipos/form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def asignacion_equipo_update(request, pk):
    """Actualizar asignaciÃ³n de equipo existente"""
    
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if asignacion.equipo.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para modificar esta asignaciÃ³n.')
            return redirect('asignaciones-equipos-list')
    
    estado_anterior = asignacion.estado
    
    if request.method == 'POST':
        form = AsignacionEquipoForm(request.POST, instance=asignacion, user=request.user)
        if form.is_valid():
            try:
                asignacion = form.save()
                
                # Si cambiÃ³ el estado a DEVUELTO, actualizar equipo
                if estado_anterior != 'DEVUELTO' and asignacion.estado == 'DEVUELTO':
                    asignacion.equipo.estado = 'DISPONIBLE'
                    asignacion.equipo.save()
                    messages.info(request, f'Equipo {asignacion.equipo.codigo_interno} marcado como DISPONIBLE')
                
                # Si cambiÃ³ de DEVUELTO a ACTIVO, marcar equipo como ASIGNADO
                elif estado_anterior == 'DEVUELTO' and asignacion.estado == 'ACTIVO':
                    asignacion.equipo.estado = 'ASIGNADO'
                    asignacion.equipo.save()
                    messages.info(request, f'Equipo {asignacion.equipo.codigo_interno} marcado como ASIGNADO')
                
                messages.success(request, 'AsignaciÃ³n actualizada exitosamente')
                return redirect('asignaciones-equipos-list')
            
            except Exception as e:
                messages.error(request, f'Error al actualizar asignaciÃ³n: {str(e)}')
    else:
        form = AsignacionEquipoForm(instance=asignacion, user=request.user)
    
    context = {
        'form': form,
        'asignacion': asignacion,
        'title': 'Editar AsignaciÃ³n de Equipo',
    }
    
    return render(request, 'drilling/asignaciones_equipos/form.html', context)


@login_required
@require_http_methods(["POST"])
def asignacion_equipo_delete(request, pk):
    """Eliminar asignaciÃ³n de equipo"""
    
    asignacion = get_object_or_404(AsignacionEquipo, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if asignacion.equipo.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para eliminar esta asignaciÃ³n.')
            return redirect('asignaciones-equipos-list')
    
    try:
        equipo_codigo = asignacion.equipo.codigo_interno
        trabajador_nombre = f"{asignacion.trabajador.nombres} {asignacion.trabajador.apellidos}"
        
        # Si estaba activo, liberar el equipo
        if asignacion.estado == 'ACTIVO':
            asignacion.equipo.estado = 'DISPONIBLE'
            asignacion.equipo.save()
        
        asignacion.delete()
        
        messages.success(
            request, 
            f'AsignaciÃ³n eliminada: {equipo_codigo} de {trabajador_nombre}'
        )
    except Exception as e:
        messages.error(request, f'Error al eliminar asignaciÃ³n: {str(e)}')
    
    return redirect('asignaciones-equipos-list')


# ===============================
# GESTIÃ“N DE EQUIPOS
# ===============================

@login_required
@require_http_methods(["GET"])
def equipos_dashboard(request):
    """Dashboard de equipos con estadÃ­sticas y acciones rÃ¡pidas"""
    
    # Obtener contrato del usuario
    if request.user.can_manage_all_contracts():
        equipos = Equipo.objects.all()
    else:
        contrato = request.user.contrato
        if not contrato:
            messages.error(request, 'No tienes un contrato asignado.')
            return redirect('home')
        equipos = Equipo.objects.filter(contrato=contrato)
    
    # EstadÃ­sticas generales
    stats = {
        'total': equipos.count(),
        'disponibles': equipos.filter(estado='DISPONIBLE').count(),
        'asignados': equipos.filter(estado='ASIGNADO').count(),
        'mantenimiento': equipos.filter(estado='MANTENIMIENTO').count(),
    }
    
    # Equipos por tipo
    from django.db.models import Count, Q
    equipos_por_tipo = []
    
    tipos = equipos.values_list('tipo', flat=True).distinct()
    for tipo in tipos:
        equipos_tipo = equipos.filter(tipo=tipo)
        tipo_display = dict(Equipo.TIPO_CHOICES).get(tipo, tipo)
        
        equipos_por_tipo.append({
            'tipo': tipo,
            'tipo_display': tipo_display,
            'total': equipos_tipo.count(),
            'disponibles': equipos_tipo.filter(estado='DISPONIBLE').count(),
            'asignados': equipos_tipo.filter(estado='ASIGNADO').count(),
            'mantenimiento': equipos_tipo.filter(estado='MANTENIMIENTO').count(),
        })
    
    # Ordenar por total descendente
    equipos_por_tipo.sort(key=lambda x: x['total'], reverse=True)
    
    context = {
        'stats': stats,
        'equipos_por_tipo': equipos_por_tipo,
    }
    
    return render(request, 'drilling/equipos/dashboard.html', context)


@login_required
def equipos_list(request):
    """Lista de equipos del contrato"""
    if request.user.has_access_to_all_contracts():
        equipos = Equipo.objects.all().select_related('contrato')
    else:
        equipos = Equipo.objects.filter(contrato=request.user.contrato).select_related('contrato')
    
    # Filtros
    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')
    
    if tipo:
        equipos = equipos.filter(tipo=tipo)
    if estado:
        equipos = equipos.filter(estado=estado)
    
    context = {
        'equipos': equipos.order_by('tipo', 'codigo_interno'),
        'tipos_equipo': Equipo.TIPO_CHOICES,
        'estados_equipo': Equipo.ESTADO_CHOICES,
        'filtros': request.GET,
    }
    
    return render(request, 'drilling/equipos/list.html', context)


@login_required
def equipo_create(request):
    """Crear nuevo equipo"""
    if request.method == 'POST':
        try:
            # Obtener contrato
            if request.user.has_access_to_all_contracts():
                contrato_id = request.POST.get('contrato')
                contrato = Contrato.objects.get(id=contrato_id)
            else:
                contrato = request.user.contrato
            
            # Crear equipo
            equipo = Equipo.objects.create(
                contrato=contrato,
                tipo=request.POST.get('tipo'),
                codigo_interno=request.POST.get('codigo_interno'),
                marca=request.POST.get('marca', ''),
                modelo=request.POST.get('modelo', ''),
                numero_serie=request.POST.get('numero_serie', ''),
                numero_telefono=request.POST.get('numero_telefono', ''),
                operador=request.POST.get('operador', ''),
                descripcion=request.POST.get('descripcion', ''),
                fecha_adquisicion=request.POST.get('fecha_adquisicion') or None,
                fecha_garantia_vencimiento=request.POST.get('fecha_garantia_vencimiento') or None,
                estado=request.POST.get('estado', 'DISPONIBLE'),
                observaciones=request.POST.get('observaciones', '')
            )
            
            messages.success(request, f'âœ… Equipo {equipo.codigo_interno} creado exitosamente')
            return redirect('equipos-list')
            
        except Exception as e:
            messages.error(request, f'âŒ Error al crear equipo: {str(e)}')
    
    # GET
    if request.user.has_access_to_all_contracts():
        contratos = Contrato.objects.filter(estado='ACTIVO')
    else:
        contratos = None
    
    context = {
        'contratos': contratos,
        'tipos_equipo': Equipo.TIPO_CHOICES,
        'estados_equipo': Equipo.ESTADO_CHOICES,
    }
    
    return render(request, 'drilling/equipos/form.html', context)


@login_required
def equipo_update(request, pk):
    """Actualizar equipo"""
    equipo = get_object_or_404(Equipo, pk=pk)
    
    # Verificar permisos
    if not request.user.has_access_to_all_contracts():
        if equipo.contrato != request.user.contrato:
            messages.error(request, 'No tiene permisos para editar este equipo')
            return redirect('equipos-list')
    
    if request.method == 'POST':
        try:
            equipo.tipo = request.POST.get('tipo')
            equipo.codigo_interno = request.POST.get('codigo_interno')
            equipo.marca = request.POST.get('marca', '')
            equipo.modelo = request.POST.get('modelo', '')
            equipo.numero_serie = request.POST.get('numero_serie', '')
            equipo.numero_telefono = request.POST.get('numero_telefono', '')
            equipo.operador = request.POST.get('operador', '')
            equipo.descripcion = request.POST.get('descripcion', '')
            equipo.fecha_adquisicion = request.POST.get('fecha_adquisicion') or None
            equipo.fecha_garantia_vencimiento = request.POST.get('fecha_garantia_vencimiento') or None
            equipo.estado = request.POST.get('estado')
            equipo.observaciones = request.POST.get('observaciones', '')
            
            equipo.save()
            
            messages.success(request, f'âœ… Equipo {equipo.codigo_interno} actualizado exitosamente')
            return redirect('equipos-list')
            
        except Exception as e:
            messages.error(request, f'âŒ Error al actualizar equipo: {str(e)}')
    
    context = {
        'equipo': equipo,
        'tipos_equipo': Equipo.TIPO_CHOICES,
        'estados_equipo': Equipo.ESTADO_CHOICES,
        'edit_mode': True,
    }
    
    return render(request, 'drilling/equipos/form.html', context)


@login_required
def equipo_delete(request, pk):
    """Eliminar equipo"""
    equipo = get_object_or_404(Equipo, pk=pk)
    
    # Verificar permisos
    if not request.user.has_access_to_all_contracts():
        if equipo.contrato != request.user.contrato:
            messages.error(request, 'No tiene permisos para eliminar este equipo')
            return redirect('equipos-list')
    
    if request.method == 'POST':
        try:
            codigo = equipo.codigo_interno
            equipo.delete()
            messages.success(request, f'âœ… Equipo {codigo} eliminado exitosamente')
        except Exception as e:
            messages.error(request, f'âŒ Error al eliminar equipo: {str(e)}')
    
    return redirect('equipos-list')


# ====================================
# VISTAS DE PRECIOS UNITARIOS
# ====================================

@login_required
def precios_unitarios_list(request):
    """Listar precios unitarios con filtros"""
    
    # Filtros
    contrato_id = request.GET.get('contrato')
    servicio_id = request.GET.get('servicio')
    solo_vigentes = request.GET.get('solo_vigentes') == '1'
    
    # Query base
    precios = PrecioUnitarioServicio.objects.select_related(
        'contrato', 'servicio', 'created_by'
    ).all()
    
    # Aplicar filtros de permisos
    if not request.user.can_manage_all_contracts():
        precios = precios.filter(contrato=request.user.contrato)
    
    # Aplicar filtros
    if contrato_id:
        precios = precios.filter(contrato_id=contrato_id)
    
    if servicio_id:
        precios = precios.filter(servicio_id=servicio_id)
    
    if solo_vigentes:
        hoy = date.today()
        precios = precios.filter(
            activo=True,
            fecha_inicio_vigencia__lte=hoy
        ).filter(
            models.Q(fecha_fin_vigencia__isnull=True) | 
            models.Q(fecha_fin_vigencia__gte=hoy)
        )
    
    precios = precios.order_by('-fecha_inicio_vigencia', 'contrato', 'servicio')
    
    # Para el filtro
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
    
    servicios = TipoActividad.objects.filter(es_cobrable=True).order_by('nombre')
    
    # AÃ±adir estado de vigencia a cada precio
    hoy = date.today()
    precios_data = []
    for precio in precios:
        precios_data.append({
            'precio': precio,
            'esta_vigente': precio.esta_vigente(hoy)
        })
    
    context = {
        'precios_data': precios_data,
        'contratos': contratos,
        'servicios': servicios,
        'contrato_seleccionado': contrato_id,
        'servicio_seleccionado': servicio_id,
        'solo_vigentes': solo_vigentes,
    }
    
    return render(request, 'drilling/precios/list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def precios_unitarios_create(request):
    """Crear nuevo precio unitario"""
    
    if request.method == 'POST':
        try:
            contrato_id = request.POST.get('contrato')
            servicio_id = request.POST.get('servicio')
            precio_unitario = request.POST.get('precio_unitario')
            moneda = request.POST.get('moneda')
            fecha_inicio = request.POST.get('fecha_inicio_vigencia')
            fecha_fin = request.POST.get('fecha_fin_vigencia')
            activo = request.POST.get('activo') == '1'
            observaciones = request.POST.get('observaciones', '')
            
            # Validar campos requeridos
            if not all([contrato_id, servicio_id, precio_unitario, moneda, fecha_inicio]):
                messages.error(request, 'Todos los campos marcados son obligatorios')
                return redirect('precios-unitarios-create')
            
            # Obtener objetos
            contrato = get_object_or_404(Contrato, pk=contrato_id)
            servicio = get_object_or_404(TipoActividad, pk=servicio_id)
            
            # Verificar permisos
            if not request.user.can_manage_all_contracts():
                if contrato != request.user.contrato:
                    messages.error(request, 'No tienes permisos para crear precios en este contrato')
                    return redirect('precios-unitarios-list')
            
            # Convertir fechas
            from datetime import datetime
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = None
            if fecha_fin:
                fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            # Crear precio
            PrecioUnitarioServicio.objects.create(
                contrato=contrato,
                servicio=servicio,
                precio_unitario=Decimal(precio_unitario),
                moneda=moneda,
                fecha_inicio_vigencia=fecha_inicio,
                fecha_fin_vigencia=fecha_fin_obj,
                activo=activo,
                observaciones=observaciones,
                created_by=request.user
            )
            
            messages.success(request, f'Precio unitario creado: {servicio.nombre} - {moneda} {precio_unitario}/m')
            return redirect('precios-unitarios-list')
            
        except Exception as e:
            messages.error(request, f'Error al crear precio: {str(e)}')
    
    # GET
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
    
    servicios = TipoActividad.objects.filter(es_cobrable=True).order_by('nombre')
    
    context = {
        'contratos': contratos,
        'servicios': servicios,
    }
    
    return render(request, 'drilling/precios/form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def precios_unitarios_edit(request, pk):
    """Editar precio unitario existente"""
    
    precio = get_object_or_404(PrecioUnitarioServicio, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if precio.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para editar este precio')
            return redirect('precios-unitarios-list')
    
    if request.method == 'POST':
        try:
            precio.precio_unitario = Decimal(request.POST.get('precio_unitario'))
            precio.moneda = request.POST.get('moneda')
            
            from datetime import datetime
            precio.fecha_inicio_vigencia = datetime.strptime(
                request.POST.get('fecha_inicio_vigencia'), '%Y-%m-%d'
            ).date()
            
            fecha_fin = request.POST.get('fecha_fin_vigencia')
            if fecha_fin:
                precio.fecha_fin_vigencia = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            else:
                precio.fecha_fin_vigencia = None
            
            precio.activo = request.POST.get('activo') == '1'
            precio.observaciones = request.POST.get('observaciones', '')
            
            precio.save()
            
            messages.success(request, 'Precio unitario actualizado exitosamente')
            return redirect('precios-unitarios-list')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar precio: {str(e)}')
    
    # GET
    context = {
        'precio': precio,
        'editing': True,
    }
    
    return render(request, 'drilling/precios/form.html', context)


@login_required
@require_http_methods(["POST"])
def precios_unitarios_delete(request, pk):
    """Eliminar precio unitario"""
    
    precio = get_object_or_404(PrecioUnitarioServicio, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if precio.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para eliminar este precio')
            return redirect('precios-unitarios-list')
    
    try:
        servicio_nombre = precio.servicio.nombre
        precio.delete()
        messages.success(request, f'Precio de {servicio_nombre} eliminado exitosamente')
    except Exception as e:
        messages.error(request, f'Error al eliminar precio: {str(e)}')
    
    return redirect('precios-unitarios-list')


@login_required
def metas_valorizacion_reporte(request):
    """Reporte consolidado de valorizaciÃ³n de metas"""
    
    # Filtros
    contrato_id = request.GET.get('contrato')
    año = request.GET.get('año') or str(date.today().year)
    mes = request.GET.get('mes') or str(date.today().month)
    
    # Filtrar contratos segÃºn permisos
    contratos = Contrato.objects.filter(estado='ACTIVO').order_by('nombre_contrato')
    if not request.user.can_manage_all_contracts():
        contratos = contratos.filter(id=request.user.contrato_id)
        if not contrato_id:
            contrato_id = str(request.user.contrato_id)
    
    if not contrato_id and contratos.exists():
        contrato_id = str(contratos.first().id)
    
    contrato = None
    valorizacion_data = []
    resumen = {
        'total_meta_metros': Decimal('0'),
        'total_real_metros': Decimal('0'),
        'total_meta_monto': Decimal('0'),
        'total_real_monto': Decimal('0'),
        'moneda': None,
    }
    
    if contrato_id:
        contrato = get_object_or_404(Contrato, pk=contrato_id)
        
        # Verificar permisos
        if not request.user.can_manage_all_contracts():
            if contrato != request.user.contrato:
                messages.error(request, 'No tienes permisos para ver este contrato')
                return redirect('metas-valorizacion-reporte')
        
        # Obtener metas del perÃ­odo
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        año_int = int(año)
        mes_int = int(mes)
        
        primer_dia_mes = datetime(año_int, mes_int, 1).date()
        mes_anterior = primer_dia_mes - relativedelta(months=1)
        fecha_inicio = datetime(mes_anterior.year, mes_anterior.month, 26).date()
        fecha_fin = datetime(año_int, mes_int, 25).date()
        
        metas = MetaMaquina.objects.filter(
            contrato=contrato,
            año=año_int,
            mes=mes_int,
            activo=True
        ).select_related('maquina', 'servicio')
        
        for meta in metas:
            # Calcular metros reales
            turnos_con_avance = TurnoAvance.objects.filter(
                turno__maquina=meta.maquina,
                turno__contrato=contrato,
                turno__fecha__gte=fecha_inicio,
                turno__fecha__lte=fecha_fin,
                turno__estado__in=['COMPLETADO', 'APROBADO']
            )
            
            metros_reales = turnos_con_avance.aggregate(
                total=Sum('metros_perforados')
            )['total'] or Decimal('0')
            
            # Calcular valorizaciÃ³n
            valorizacion = meta.calcular_valorizacion_completa(metros_reales, fecha_fin)
            
            if valorizacion['tiene_precio']:
                valorizacion_data.append({
                    'maquina': meta.maquina,
                    'servicio': meta.servicio,
                    'meta': meta,
                    'valorizacion': valorizacion,
                })
                
                # Acumular totales
                resumen['total_meta_metros'] += valorizacion['meta_metros']
                resumen['total_real_metros'] += valorizacion['real_metros']
                resumen['total_meta_monto'] += valorizacion['meta_monto']
                resumen['total_real_monto'] += valorizacion['real_monto']
                resumen['moneda'] = valorizacion['moneda']
        
        # Calcular porcentajes del resumen
        if resumen['total_meta_metros'] > 0:
            resumen['porcentaje_cumplimiento'] = (
                resumen['total_real_metros'] / resumen['total_meta_metros']
            ) * Decimal('100')
        else:
            resumen['porcentaje_cumplimiento'] = Decimal('0')
        
        if resumen['total_meta_monto'] > 0:
            resumen['porcentaje_valor'] = (
                resumen['total_real_monto'] / resumen['total_meta_monto']
            ) * Decimal('100')
        else:
            resumen['porcentaje_valor'] = Decimal('0')
        
        resumen['diferencia_monto'] = resumen['total_real_monto'] - resumen['total_meta_monto']
    
    # años y meses
    año_actual = date.today().year
    años_disponibles = range(2024, año_actual + 2)
    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    context = {
        'contratos': contratos,
        'contrato': contrato,
        'contrato_id': contrato_id,
        'año': año,
        'mes': mes,
        'años_disponibles': años_disponibles,
        'meses': meses,
        'valorizacion_data': valorizacion_data,
        'resumen': resumen,
    }
    
    return render(request, 'drilling/metas/valorizacion_reporte.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def metas_maquina_dividir(request, pk):
    """Dividir meta existente en dos perÃ­odos con diferentes valores"""
    
    meta_original = get_object_or_404(MetaMaquina, pk=pk)
    
    # Verificar permisos
    if not request.user.can_manage_all_contracts():
        if meta_original.contrato != request.user.contrato:
            messages.error(request, 'No tienes permisos para modificar esta meta')
            return redirect('metas-maquina-list')
    
    # Calcular perÃ­odo original
    fecha_inicio_original = meta_original.get_fecha_inicio_periodo()
    fecha_fin_original = meta_original.get_fecha_fin_periodo()
    
    if request.method == 'POST':
        try:
            fecha_division = request.POST.get('fecha_division')
            nueva_meta_metros = request.POST.get('nueva_meta_metros')
            
            if not fecha_division or not nueva_meta_metros:
                messages.error(request, 'Debe ingresar fecha de divisiÃ³n y nueva meta')
                return redirect('metas-maquina-dividir', pk=pk)
            
            fecha_division = datetime.strptime(fecha_division, '%Y-%m-%d').date()
            nueva_meta_metros = Decimal(nueva_meta_metros)
            
            # Validar que la fecha estÃ© dentro del perÃ­odo
            if fecha_division <= fecha_inicio_original or fecha_division > fecha_fin_original:
                messages.error(request, f'La fecha de divisiÃ³n debe estar entre {fecha_inicio_original} y {fecha_fin_original}')
                return redirect('metas-maquina-dividir', pk=pk)
            
            # Calcular metros ya perforados hasta la fecha de divisiÃ³n
            turnos_periodo1 = TurnoAvance.objects.filter(
                turno__maquina=meta_original.maquina,
                turno__contrato=meta_original.contrato,
                turno__fecha__gte=fecha_inicio_original,
                turno__fecha__lt=fecha_division,
                turno__estado__in=['COMPLETADO', 'APROBADO']
            )
            metros_periodo1 = turnos_periodo1.aggregate(total=Sum('metros_perforados'))['total'] or Decimal('0')
            
            # 1. Desactivar meta original y ajustar su perÃ­odo
            meta_original.fecha_fin = fecha_division - timedelta(days=1)
            meta_original.activo = False
            meta_original.observaciones = (meta_original.observaciones or '') + f' [Dividida el {date.today()}. Real: {metros_periodo1}m]'
            meta_original.save()
            
            # 2. Crear nueva meta para el perÃ­odo restante
            nueva_meta = MetaMaquina.objects.create(
                contrato=meta_original.contrato,
                maquina=meta_original.maquina,
                año=meta_original.año,
                mes=meta_original.mes,
                fecha_inicio=fecha_division,
                fecha_fin=meta_original.get_fecha_fin_periodo(),  # Usar el fin del mes operativo
                meta_metros=nueva_meta_metros,
                activo=True,
                observaciones=f'Meta dividida desde {fecha_division}. Meta anterior: {meta_original.meta_metros}m',
                created_by=request.user
            )
            
            messages.success(
                request, 
                f'Meta dividida exitosamente. '
                f'PerÃ­odo 1: {meta_original.get_fecha_inicio_periodo()} a {meta_original.fecha_fin} ({meta_original.meta_metros}m, Real: {metros_periodo1}m). '
                f'PerÃ­odo 2: {fecha_division} a {nueva_meta.fecha_fin} ({nueva_meta_metros}m)'
            )
            return redirect('metas-maquina-list')
            
        except ValueError as e:
            messages.error(request, f'Error en formato de datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al dividir meta: {str(e)}')
    
    # GET - Mostrar formulario
    # Calcular metros reales del perÃ­odo completo
    turnos_periodo = TurnoAvance.objects.filter(
        turno__maquina=meta_original.maquina,
        turno__contrato=meta_original.contrato,
        turno__fecha__gte=fecha_inicio_original,
        turno__fecha__lte=fecha_fin_original,
        turno__estado__in=['COMPLETADO', 'APROBADO']
    )
    
    metros_reales_total = turnos_periodo.aggregate(total=Sum('metros_perforados'))['total'] or Decimal('0')
    total_turnos = turnos_periodo.count()
    
    # Calcular promedio diario
    dias_transcurridos = (date.today() - fecha_inicio_original).days + 1
    if dias_transcurridos > 0:
        promedio_diario = metros_reales_total / dias_transcurridos
    else:
        promedio_diario = Decimal('0')
    
    # ProyecciÃ³n
    dias_totales = (fecha_fin_original - fecha_inicio_original).days + 1
    proyeccion = promedio_diario * dias_totales if promedio_diario > 0 else Decimal('0')
    
    context = {
        'meta': meta_original,
        'fecha_inicio': fecha_inicio_original,
        'fecha_fin': fecha_fin_original,
        'metros_reales_total': metros_reales_total,
        'total_turnos': total_turnos,
        'promedio_diario': promedio_diario,
        'proyeccion': proyeccion,
        'fecha_hoy': date.today(),
    }
    
    return render(request, 'drilling/metas/dividir.html', context)
