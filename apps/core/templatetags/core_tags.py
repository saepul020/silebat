from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def dash_if_zero(value):
    if value is None:
        return "-"

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return "-"
        try:
            numeric_value = Decimal(stripped)
        except (InvalidOperation, ValueError):
            return value
        return "-" if numeric_value == 0 else value

    if isinstance(value, (int, float, Decimal)):
        return "-" if Decimal(str(value)) == 0 else value

    return value
