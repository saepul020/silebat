from django.conf import settings

from .permissions import build_role_access


def app_cache(request):
    return {
        "app_cache_version": settings.APP_CACHE_VERSION,
    }


def role_access(request):
    return {
        "role_access": build_role_access(getattr(request, "user", None)),
    }
