"""
Custom Template Tags y Filters para Tareo V2
"""
from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite acceder a items de un diccionario en templates
    
    Uso: {{ mi_dict|get_item:clave }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter(name='default_if_none')
def default_if_none(value, default):
    """
    Retorna un valor por defecto si el valor es None
    
    Uso: {{ valor|default_if_none:dict }}
    """
    if value is None:
        return default
    return value
