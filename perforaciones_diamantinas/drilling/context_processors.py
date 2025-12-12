def base_template(request):
    """
    Context processor para hacer disponible el template base según rol
    """
    return {
        'base_template': getattr(request, 'base_template', 'drilling/base.html')
    }
