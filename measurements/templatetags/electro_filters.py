from django import template

register = template.Library()

@register.filter
def scientific(value):
    try:
        # Formatuje np. 0.000005 na 5.00e-06
        return "{:.2e}".format(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def microamps(value):
    try:
        # Zamienia Ampery na Mikroampery dla czytelności
        return "{:.2f} µA".format(float(value) * 1_000_000)
    except (ValueError, TypeError):
        return value