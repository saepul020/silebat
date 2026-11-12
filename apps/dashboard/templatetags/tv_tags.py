from textwrap import wrap

from django import template
from django.utils.html import format_html_join

register = template.Library()


def tv_wrap(value, width):
    """Wrap plain TV text, including long words, without truncation."""
    lines = wrap(" ".join(str(value or "").split()), width=int(width), break_on_hyphens=False)
    return "\n".join(lines)


@register.filter
def tv_lines(value, width):
    """Render escaped line spans for TV metadata and status labels."""
    text = " ".join(str(value or "").split())
    parts = []
    offset = 0
    for line in tv_wrap(text, width).splitlines():
        # Preserve word boundaries when the same spans are inline in normal mode.
        separator = " " if text[offset:offset + 1] == " " else ""
        offset += len(separator) + len(line)
        parts.append((separator, line))
    return format_html_join("", '{}<span class="tv-wrap__line">{}</span>', parts)
