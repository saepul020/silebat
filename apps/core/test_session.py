from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.pengguna.models import User


class SessionConfigTests(TestCase):
    def test_idle_session_timeout_configured_for_two_hours(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 2 * 60 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertEqual(settings.LOGIN_URL, "/login/")
        self.assertEqual(settings.LOGIN_REDIRECT_URL, "/dashboard/")
        self.assertEqual(settings.LOGOUT_REDIRECT_URL, "/")

    def test_protected_pages_redirect_to_login_with_next(self):
        cases = (
            reverse("dashboard:index"),
            reverse("master_data:data_barang_laboratorium"),
            reverse("master_data:data_peralatan_laboratorium"),
            reverse("master_data:data_fasilitas_ruangan"),
            reverse("master_data:label_barang_laboratorium", args=[1]),
        )

        for url in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{settings.LOGIN_URL}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_login_with_next_redirects_to_requested_page(self):
        User.objects.create_user(username="session-user", password="test-pass-123")
        target_url = reverse("dashboard:index")

        response = self.client.post(
            f"{settings.LOGIN_URL}?next={target_url}",
            {"username": "session-user", "password": "test-pass-123"},
        )

        self.assertRedirects(response, target_url, fetch_redirect_response=False)
