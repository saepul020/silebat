from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter
def get_item(form, field_name):
    try:
        return form[field_name]
    except Exception:
        return None


@register.filter
def display_dash(value):
    """Tampilkan strip untuk nilai kosong atau nol pada tabel list master_data."""
    if value is None:
        return "-"

    if isinstance(value, str):
        normalized_value = value.strip()
        if not normalized_value:
            return "-"
        try:
            if Decimal(normalized_value.replace(",", ".")) == 0:
                return "-"
        except (InvalidOperation, ValueError):
            pass
        return normalized_value

    if value == 0:
        return "-"
    return value
