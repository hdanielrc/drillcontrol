from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse

class ContractSecurityMiddleware:
    """Middleware para seguridad por contrato"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Actualizar última actividad del usuario
        if request.user.is_authenticated:
            request.user.last_activity = timezone.now()
            request.user.save(update_fields=['last_activity'])
        
        response = self.get_response(request)
        return response

class RoleBasedTemplateMiddleware:
    """Middleware para asignar template base según rol del usuario"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Asignar template base según el rol
            if request.user.role == 'ADMIN_SISTEMA':
                request.base_template = 'drilling/base_admin.html'
            elif request.user.role == 'MANAGER_CONTRATO':
                request.base_template = 'drilling/base_manager.html'
            elif request.user.role == 'SUPERVISOR':
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