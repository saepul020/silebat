from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.master_data.models import (
    BahanOperasional,
    BarangPenunjangOperasional,
    KategoriBahanOperasionalChoices,
    KategoriBarangPenunjangChoices,
)
from apps.pengguna.models import Role, User

from apps.dashboard.views import build_inventory_chart_context


class DashboardInventoryChartTests(TestCase):
    def setUp(self):
        qr_patcher = patch("apps.master_data.signals.ensure_master_qr_code")
        qr_patcher.start()
        self.addCleanup(qr_patcher.stop)

        self.user = User.objects.create_user(
            username="dashboard-chart-user",
            password="test-pass-123",
        )
        admin_role, _ = Role.objects.get_or_create(nama="Admin Lab")
        self.user.safe_profile.role = admin_role
        self.user.safe_profile.save(update_fields=["role"])
        self.restricted_user = User.objects.create_user(
            username="dashboard-restricted-user",
            password="test-pass-123",
        )
        user_role, _ = Role.objects.get_or_create(nama="User")
        self.restricted_user.safe_profile.role = user_role
        self.restricted_user.safe_profile.save(update_fields=["role"])
        BahanOperasional.objects.create(
            nama_barang="Zeta Bahan",
            kategori_barang=KategoriBahanOperasionalChoices.BAHAN_LAPANGAN,
            volume=4,
            satuan="Botol",
            stok_minimum=1,
        )
        BahanOperasional.objects.create(
            nama_barang="Alpha Bahan",
            kategori_barang=KategoriBahanOperasionalChoices.BAHAN_LABORATORIUM,
            volume=12,
            satuan="Buah",
            stok_minimum=2,
        )
        BarangPenunjangOperasional.objects.create(
            nama_barang="Tripod",
            tipe_merek_barang="Tipe A",
            volume=7,
            volume_rusak=3,
            satuan="Unit",
            kategori_barang=KategoriBarangPenunjangChoices.LAPANGAN,
        )

    def test_inventory_chart_context_contains_ordered_stock_values(self):
        context = build_inventory_chart_context()

        self.assertEqual(
            context["bahan_chart"]["items"],
            [
                {
                    "id": BahanOperasional.objects.get(nama_barang="Alpha Bahan").pk,
                    "label": "Alpha Bahan",
                    "stock": 12,
                    "unit": "Buah",
                },
                {
                    "id": BahanOperasional.objects.get(nama_barang="Zeta Bahan").pk,
                    "label": "Zeta Bahan",
                    "stock": 4,
                    "unit": "Botol",
                },
            ],
        )
        self.assertEqual(
            context["penunjang_chart"]["items"][0],
            {
                "id": BarangPenunjangOperasional.objects.get(nama_barang="Tripod").pk,
                "label": "Tripod",
                "baik": 7,
                "rusak": 3,
                "unit": "Unit",
            },
        )

    def test_dashboard_renders_inventory_charts_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="grafikBahan"')
        self.assertContains(response, 'id="grafikPenunjang"')
        self.assertEqual(response.context["bahan_chart"]["items"][0]["label"], "Alpha Bahan")
        self.assertEqual(response.context["penunjang_chart"]["items"][0]["rusak"], 3)

    def test_user_role_does_not_receive_master_inventory_charts(self):
        self.client.force_login(self.restricted_user)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("bahan_chart", response.context)
        self.assertNotIn("penunjang_chart", response.context)
        self.assertNotContains(response, 'id="grafikBahan"')
        self.assertNotContains(response, 'id="grafikPenunjang"')
