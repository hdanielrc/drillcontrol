from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

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