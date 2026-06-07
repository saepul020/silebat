from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.pengguna.models import Role, User

from apps.master_data.models import BahanOperasional


class MasterEditReturnNavigationTests(TestCase):
    def setUp(self):
        self.qr_patcher = patch("apps.master_data.signals.ensure_master_qr_code")
        self.qr_patcher.start()
        self.addCleanup(self.qr_patcher.stop)

        role, _ = Role.objects.get_or_create(nama="Admin Lab")
        self.user = User.objects.create_user(username="admin-lab", password="test-pass-123")
        self.user.profile.role = role
        self.user.profile.save(update_fields=["role"])
        self.client.force_login(self.user)
        self.obj = BahanOperasional.objects.create(
            nama_barang="Bahan Awal",
            kategori_barang="Bahan Lapangan",
            volume=10,
            satuan="Buah",
            stok_minimum=2,
        )

    def test_master_update_returns_to_source_page(self):
        next_url = f"{reverse('master_data:data_bahan_operasional')}?entries=10&page=3&q=bahan"
        response = self.client.post(
            reverse("master_data:edit_bahan_operasional", args=[self.obj.pk]),
            {
                "nama_barang": "Bahan Diperbarui",
                "kategori_barang": "Bahan Lapangan",
                "volume": 12,
                "satuan": "Buah",
                "stok_minimum": 2,
                "next": next_url,
            },
        )

        self.assertRedirects(response, next_url, fetch_redirect_response=False)
