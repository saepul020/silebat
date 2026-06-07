from urllib.parse import quote

from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from apps.pengguna.models import Role, User

from apps.operasional.models import LayananKegiatan


class EditReturnNavigationTests(TestCase):
    def setUp(self):
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        self.user = User.objects.create_user(username="admin", password="test-pass-123")
        self.user.profile.role = role
        self.user.profile.save(update_fields=["role"])
        self.client.force_login(self.user)
        self.obj = LayananKegiatan.objects.create(jenis_layanan="Layanan Awal")

    def test_update_returns_to_source_page(self):
        next_url = f"{reverse('operasional:data_layanan')}?entries=10&page=3&q=air"
        response = self.client.post(
            reverse("operasional:edit_layanan", args=[self.obj.pk]),
            {
                "jenis_layanan": "Layanan Diperbarui",
                "next": next_url,
            },
        )

        self.assertRedirects(response, next_url, fetch_redirect_response=False)

    def test_list_edit_link_carries_current_page(self):
        items = [
            LayananKegiatan.objects.create(jenis_layanan=f"Layanan {index:02d}")
            for index in range(25)
        ]
        source_url = f"{reverse('operasional:data_layanan')}?entries=10&page=3"
        edit_url = reverse("operasional:edit_layanan", args=[items[20].pk])

        response = self.client.get(source_url)

        self.assertContains(response, f"{edit_url}?next={quote(source_url, safe='/')}")

    def test_invalid_form_keeps_source_page(self):
        next_url = f"{reverse('operasional:data_layanan')}?entries=10&page=3"

        response = self.client.post(
            reverse("operasional:edit_layanan", args=[self.obj.pk]),
            {
                "jenis_layanan": "",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'name="next" value="{escape(next_url)}"')

    def test_external_next_falls_back_to_list(self):
        response = self.client.post(
            reverse("operasional:edit_layanan", args=[self.obj.pk]),
            {
                "jenis_layanan": "Layanan Diperbarui",
                "next": "https://example.org/ambil-alih",
            },
        )

        self.assertRedirects(
            response,
            reverse("operasional:data_layanan"),
            fetch_redirect_response=False,
        )
