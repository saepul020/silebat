from textwrap import wrap

from django import template
from django.utils.html import format_html_join

register = template.Library()


@register.filter
def tv_lines(value, width):
    """Wrap TV text at word boundaries, splitting long words without truncation."""
    lines = wrap(" ".join(str(value or "").split()), width=int(width), break_on_hyphens=False)
    return format_html_join("", '<span class="tv-wrap__line">{}</span>', ((line,) for line in lines))
