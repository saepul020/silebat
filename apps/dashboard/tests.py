from datetime import date
from io import BytesIO
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.master_data.models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    KategoriBahanOperasionalChoices,
    KategoriBarangPenunjangChoices,
    StatusBarangChoices,
)
from apps.peminjaman.models import PeminjamanBarangLaboratorium, PeminjamanRequest, StepChoices
from apps.pengguna.models import Role, User

from apps.dashboard.views import build_inventory_chart_context, build_survey_equipment_chart


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


class DashboardSurveyEquipmentChartTests(TestCase):
    def setUp(self):
        qr_patcher = patch("apps.master_data.signals.ensure_master_qr_code")
        qr_patcher.start()
        self.addCleanup(qr_patcher.stop)

        self.user = User.objects.create_user(
            username="survey-equipment-chart-user",
            password="test-pass-123",
        )
        admin_role, _ = Role.objects.get_or_create(nama="Admin Lab")
        self.user.safe_profile.role = admin_role
        self.user.safe_profile.save(update_fields=["role"])
        self.equipment = BarangLaboratorium.objects.create(
            nama_barang="Resistivity Meter",
            tipe_merek_barang="Geo X",
            jenis_barang="Geolistrik",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="SUR-001",
            lokasi_barang="Gudang Survei",
        )
        approved_request = PeminjamanRequest.objects.create(
            peminjam=self.user,
            nama_peminjam="Survey Equipment User",
            tanggal_mulai=date(2026, 6, 1),
            tanggal_selesai=date(2026, 6, 2),
            current_step=StepChoices.APPROVED,
        )
        PeminjamanBarangLaboratorium.objects.create(
            pengajuan=approved_request,
            barang=self.equipment,
        )

    def test_survey_equipment_chart_counts_approved_transactions_by_year(self):
        chart = build_survey_equipment_chart(2026)

        self.assertEqual(chart["availableYears"], [2026])
        self.assertEqual(chart["categories"][0]["label"], "Resistivity Meter")
        self.assertEqual(
            chart["rows"],
            [
                {
                    "year": 2026,
                    "barangId": self.equipment.pk,
                    "total": 1,
                },
            ],
        )

    def test_dashboard_renders_survey_equipment_chart(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="grafikPeralatanSurvei"')
        self.assertEqual(response.context["survey_equipment_chart"]["rows"][0]["total"], 1)


class DashboardChartExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboard-export-user",
            password="test-pass-123",
        )
        role, _ = Role.objects.get_or_create(nama="Admin Lab")
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])
        self.payload = {
            "title": "Rekap Peminjaman",
            "type": "bar",
            "labels": ["Jan", "Feb"],
            "datasets": [
                {"label": "Selesai", "data": [3, 5]},
                {"label": "Berjalan", "data": [2, 1]},
            ],
        }

    def test_dashboard_menampilkan_pilihan_download_excel(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count(b'data-chart-download="xlsx"'), 9)
        self.assertContains(response, "Download Excel")

    def test_export_excel_berisi_data_dan_chart(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("dashboard:export_chart"),
            data=json.dumps(self.payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml.sheet", response["Content-Type"])
        self.assertIn("rekap-peminjaman", response["Content-Disposition"])
        workbook = load_workbook(BytesIO(response.content))
        worksheet = workbook["Data Grafik"]
        self.assertEqual(
            list(worksheet.values)[:3],
            [
                ("Kategori", "Selesai", "Berjalan"),
                ("Jan", 3, 2),
                ("Feb", 5, 1),
            ],
        )
        self.assertEqual(len(worksheet._charts), 1)

    def test_export_excel_membutuhkan_login_dan_data_valid(self):
        login_response = self.client.post(
            reverse("dashboard:export_chart"),
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 302)

        self.client.force_login(self.user)
        invalid_response = self.client.post(
            reverse("dashboard:export_chart"),
            data=json.dumps({**self.payload, "datasets": [{"label": "A", "data": [1]}]}),
            content_type="application/json",
        )
        self.assertEqual(invalid_response.status_code, 400)
