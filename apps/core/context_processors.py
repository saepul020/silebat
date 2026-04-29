from .permissions import build_role_access


def role_access(request):
    return {
        "role_access": build_role_access(getattr(request, "user", None)),
    }
