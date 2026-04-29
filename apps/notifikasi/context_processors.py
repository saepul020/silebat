from django.db.utils import OperationalError, ProgrammingError

from .services import get_navbar_notifications


def navbar_notifications(request):
    try:
        return get_navbar_notifications(getattr(request, "user", None))
    except (OperationalError, ProgrammingError):
        return {
            "notification_unread_count": 0,
            "notification_recent_items": [],
        }
