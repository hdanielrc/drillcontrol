from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.core.cache import cache

class ContractSecurityMiddleware:
    """Middleware para seguridad por contrato"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Actualizar última actividad del usuario (solo cada 5 minutos para evitar writes constantes)
        if request.user.is_authenticated:
            try:
                cache_key = f'last_activity_{request.user.id}'
                last_update = cache.get(cache_key)
                now = timezone.now()
                
                # Solo actualizar en BD cada 5 minutos
                if not last_update or (now - last_update).total_seconds() > 300:
                    request.user.last_activity = now
                    request.user.save(update_fields=['last_activity'])
                    cache.set(cache_key, now, 600)  # Cache por 10 minutos
            except Exception as e:
                # Silenciar errores del middleware para no romper el request
                pass
        
        response = self.get_response(request)
        return response

class RoleBasedTemplateMiddleware:
    """Middleware para asignar template base según rol del usuario"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Asignar template base según el rol
            if request.user.role in ['GERENCIA', 'CONTROL_PROYECTOS']:
                request.base_template = 'drilling/base_admin.html'
            elif request.user.role == 'ADMINISTRADOR':
                request.base_template = 'drilling/base_manager.html'
            elif request.user.role in ['RESIDENTE', 'LOGISTICO']:
                request.base_template = 'drilling/base_supervisor.html'
            elif request.user.role == 'OPERADOR':
                request.base_template = 'drilling/base_operador.html'
            else:
                request.base_template = 'drilling/base.html'
        else:
            request.base_template = 'drilling/base.html'
        
        response = self.get_response(request)
        return response

class LoginRequiredMiddleware:
    """Middleware para requerir login en todas las URLs excepto login"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            reverse('login'),
        ]

    def __call__(self, request):
        if not request.user.is_authenticated and request.path not in self.exempt_urls:
            return redirect('login')
        
        response = self.get_response(request)
        return response