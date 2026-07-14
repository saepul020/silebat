from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.middleware import PortalCacheMiddleware


@override_settings(
    APP_CACHE_VERSION="uji-cache-v2",
    APP_CACHE_COOKIE="silebat_cache_version",
    APP_CACHE_COOKIE_AGE=31536000,
    SESSION_COOKIE_SECURE=False,
)
class PortalCacheMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_html_tidak_disimpan_dan_versi_baru_membersihkan_cache(self):
        request = self.factory.get("/")
        request.COOKIES.update(
            {
                settings.SESSION_COOKIE_NAME: "session-aman",
                settings.CSRF_COOKIE_NAME: "csrf-aman",
                "preferensi_lama": "1",
                "silebat_cache_version": "uji-cache-v1",
            }
        )
        middleware = PortalCacheMiddleware(
            lambda _request: HttpResponse("Portal")
        )

        response = middleware(request)

        self.assertEqual(
            response.headers["Cache-Control"],
            "no-store, no-cache, max-age=0, must-revalidate, private",
        )
        self.assertEqual(response.headers["Pragma"], "no-cache")
        self.assertEqual(response.headers["Expires"], "0")
        self.assertEqual(response.headers["Clear-Site-Data"], '"cache"')
        self.assertEqual(
            response.cookies["silebat_cache_version"].value,
            "uji-cache-v2",
        )
        self.assertEqual(response.cookies["preferensi_lama"]["max-age"], 0)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertNotIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_versi_yang_sama_tidak_mengulang_pembersihan(self):
        request = self.factory.get("/")
        request.COOKIES["silebat_cache_version"] = "uji-cache-v2"
        middleware = PortalCacheMiddleware(
            lambda _request: HttpResponse("Portal")
        )

        response = middleware(request)

        self.assertNotIn("Clear-Site-Data", response.headers)
        self.assertNotIn("silebat_cache_version", response.cookies)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_response_non_html_tidak_diubah(self):
        request = self.factory.get("/api/data/")
        middleware = PortalCacheMiddleware(
            lambda _request: JsonResponse({"ok": True})
        )

        response = middleware(request)

        self.assertNotIn("Clear-Site-Data", response.headers)
        self.assertNotIn("Cache-Control", response.headers)


class PortalCacheConfigTests(SimpleTestCase):
    shell_templates = [
        "templates/base.html",
        "templates/registration/login.html",
        "apps/landing/templates/landing/index.html",
        "apps/dashboard/templates/dashboard/display.html",
    ]

    def test_semua_shell_memuat_bootstrap_versi_cache(self):
        base_dir = Path(settings.BASE_DIR)

        for relative_path in self.shell_templates:
            content = (base_dir / relative_path).read_text(encoding="utf-8")
            with self.subTest(template=relative_path):
                self.assertIn('name="silebat-cache-version"', content)
                self.assertIn("js/cache.js", content)
                self.assertIn("app_cache_version", content)

    def test_bootstrap_membersihkan_storage_dan_worker_lama(self):
        content = (
            Path(settings.BASE_DIR) / "static/js/cache.js"
        ).read_text(encoding="utf-8")

        self.assertIn("window.caches.delete", content)
        self.assertIn("registration.unregister", content)
        self.assertIn("window.sessionStorage.clear", content)
        self.assertIn("window.localStorage.clear", content)

    def test_nginx_memvalidasi_ulang_static(self):
        content = (
            Path(settings.BASE_DIR) / "nginx/default.conf"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'Cache-Control "no-cache, max-age=0, must-revalidate"',
            content,
        )
        self.assertNotIn("max-age=31536000, immutable", content)
