from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Filtro para acceder a elementos de un diccionario usando una clave variable
    Uso: {{ diccionario|get_item:clave }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter(name='replace')
def replace(value, args):
    """
    Filtro para reemplazar caracteres en un string
    Uso: {{ texto|replace:"_:-" }}  (reemplaza _ por -)
    """
    if not value or not args:
        return value
    
    try:
        old, new = args.split(':')
        return str(value).replace(old, new)
    except ValueError:
        return value


@register.filter(name='get_icon_equipo')
def get_icon_equipo(tipo_equipo):
    """
    Retorna el icono de Font Awesome apropiado según el tipo de equipo
    """
    iconos = {
        'LAPTOP': 'laptop',
        'CELULAR': 'mobile-alt',
        'MODEM': 'wifi',
        'IMPRESORA': 'print',
        'DETECTOR_TORMENTAS': 'bolt',
        'ENMICADORA': 'microphone',
        'RADIO': 'broadcast-tower',
        'TABLET': 'tablet-alt',
        'GPS': 'map-marked-alt',
        'OTRO': 'box',
    }
    return iconos.get(tipo_equipo, 'box')
