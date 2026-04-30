from functools import wraps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect


def rol_requerido(*roles):
    """
    Decorador de vista que verifica que el usuario tenga uno de los roles indicados.
    Uso: @rol_requerido('GERENCIA', 'ADMINISTRADOR')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            # is_system_admin o ADMINISTRADOR_GENERAL tienen acceso total
            if getattr(request.user, 'is_system_admin', False) or request.user.role == 'ADMINISTRADOR_GENERAL':
                return view_func(request, *args, **kwargs)
            if request.user.role not in roles:
                messages.error(
                    request,
                    f'No tiene permisos para esta acción. Se requiere uno de: {", ".join(roles)}.'
                )
                return redirect('planilla-hub')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class AdminOrContractFilterMixin(LoginRequiredMixin):
    """Mixin para filtrar datos por contrato o permitir acceso completo a admins"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Si es admin del sistema, puede ver todo
        if self.request.user.can_manage_all_contracts():
            return queryset
        
        # Si no es admin, solo ve datos de su contrato
        if hasattr(queryset.model, 'contrato'):
            return queryset.filter(contrato=self.request.user.contrato)
        
        return queryset

class SystemAdminRequiredMixin(LoginRequiredMixin):
    """Mixin que requiere permisos de administrador del sistema"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.can_manage_all_contracts():
            raise PermissionDenied("Necesita permisos de administrador del sistema")
        return super().dispatch(request, *args, **kwargs)