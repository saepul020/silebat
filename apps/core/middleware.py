from django.conf import settings


class PortalCacheMiddleware:
    """Mencegah shell HTML lama dan membersihkan cache saat versi deploy berubah."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method not in {"GET", "HEAD"}:
            return response

        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith(("text/html", "application/xhtml+xml")):
            return response

        response.headers["Cache-Control"] = (
            "no-store, no-cache, max-age=0, must-revalidate, private"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        version = settings.APP_CACHE_VERSION
        cookie_name = settings.APP_CACHE_COOKIE
        if not version or request.COOKIES.get(cookie_name) == version:
            return response

        response.headers["Clear-Site-Data"] = '"cache"'
        protected = {
            settings.SESSION_COOKIE_NAME,
            settings.CSRF_COOKIE_NAME,
            cookie_name,
        }
        for name in request.COOKIES:
            if name in protected:
                continue
            response.delete_cookie(
                name,
                path="/",
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite="Lax",
            )

        response.set_cookie(
            cookie_name,
            version,
            max_age=settings.APP_CACHE_COOKIE_AGE,
            path="/",
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,
            samesite="Lax",
        )
        return response
