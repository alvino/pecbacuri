# ControleRebanho/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter(name='addcss')
def addcss(field, css):
   return field.as_widget(attrs={"class": css})

@register.filter
def sub(value, arg):
    """Subtrai o argumento do valor."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def mul(value, arg):
    """Multiplica o valor pelo argumento."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''