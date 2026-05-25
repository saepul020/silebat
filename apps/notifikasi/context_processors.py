from django.db import DatabaseError
from django.db.utils import InterfaceError, OperationalError, ProgrammingError

from .services import get_navbar_notifications


def navbar_notifications(request):
    try:
        return get_navbar_notifications(getattr(request, "user", None))
    except (DatabaseError, InterfaceError, OperationalError, ProgrammingError):
        return {
            "notification_unread_count": 0,
            "notification_recent_items": [],
        }
