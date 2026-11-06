from datetime import date, datetime
from io import BytesIO
import json
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.master_data.models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    KategoriBahanOperasionalChoices,
    KategoriBarangPenunjangChoices,
    StatusBarangChoices,
)
from apps.peminjaman.models import (
    PeminjamanBarangLaboratorium,
    PeminjamanRequest,
    ReturnStepChoices,
    StepChoices,
)
from apps.pengguna.models import Role, User
from apps.operasional.models import InstansiKlien

from apps.dashboard.views import (
    build_dashboard_context,
    build_inventory_chart_context,
    build_instansi_charts,
    build_survey_equipment_chart,
    get_approved_peminjaman_queryset,
)


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
        self.assertContains(response, 'data-chart-picker="bahan"')
        self.assertContains(response, 'data-chart-picker="penunjang"')
        self.assertContains(response, 'value="%s" checked' % BahanOperasional.objects.get(nama_barang="Alpha Bahan").pk)
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
        self.assertNotContains(response, 'data-chart-picker=')


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


class DashboardPeminjamanStatsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboard-stats-user",
            password="test-pass-123",
        )

    def _approved_request(self, *, year, return_step=ReturnStepChoices.NONE):
        approved_at = timezone.make_aware(datetime(year, 6, 1, 10, 0))
        return PeminjamanRequest.objects.create(
            peminjam=self.user,
            nama_peminjam=f"Stats User {year}",
            tanggal_mulai=date(year, 6, 1),
            tanggal_selesai=date(year, 6, 2),
            current_step=StepChoices.APPROVED,
            pimpinan_at=approved_at,
            return_current_step=return_step,
        )

    def test_dashboard_stats_hanya_menghitung_peminjaman_tahun_berjalan(self):
        current_year = timezone.localtime().year
        previous_year = current_year - 1

        self._approved_request(
            year=current_year,
            return_step=ReturnStepChoices.COMPLETED,
        )
        self._approved_request(year=current_year)
        self._approved_request(
            year=previous_year,
            return_step=ReturnStepChoices.COMPLETED,
        )
        self._approved_request(year=previous_year)

        context = build_dashboard_context()

        self.assertEqual(context["dashboard_stats"]["completed_count"], 1)
        self.assertEqual(context["dashboard_stats"]["ongoing_count"], 1)
        self.assertEqual(context["dashboard_stats"]["total_count"], 2)


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
        self.assertEqual(response.content.count(b'data-chart-download="xlsx"'), 10)
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


class DashboardInstansiChartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="dashboard-instansi-user")
        role, _ = Role.objects.get_or_create(nama="Admin Lab")
        cls.user.safe_profile.role = role
        cls.user.safe_profile.save(update_fields=["role"])
        cls.internal = InstansiKlien.objects.create(
            nama_instansi="Instansi Internal", alamat_instansi="Alamat Internal",
            organisasi=InstansiKlien.OrganisasiChoices.INTERNAL_SDA,
        )
        cls.eksternal = InstansiKlien.objects.create(
            nama_instansi="Instansi Eksternal", alamat_instansi="Alamat Eksternal",
            organisasi=InstansiKlien.OrganisasiChoices.EKSTERNAL_SDA,
        )
        cls.bat = InstansiKlien.objects.create(
            nama_instansi="Instansi BAT", alamat_instansi="Alamat BAT",
            organisasi=InstansiKlien.OrganisasiChoices.INTERNAL_BAT,
        )

    def _pengajuan(self, year, instansi=None, lainnya="", step=StepChoices.APPROVED):
        return PeminjamanRequest.objects.create(
            peminjam=self.user, nama_peminjam="Pengguna Uji",
            instansi_tujuan=instansi, instansi_tujuan_lainnya=lainnya,
            tanggal_mulai=date(year, 6, 1), tanggal_selesai=date(year, 6, 2),
            current_step=step,
            pimpinan_at=timezone.make_aware(datetime(year, 6, 1, 10, 0)),
        )

    def _charts(self):
        return build_instansi_charts(get_approved_peminjaman_queryset(), 2026)

    def test_kategori_terpisah_dan_input_manual_masuk_gabungan(self):
        self._pengajuan(2025, self.internal)
        self._pengajuan(2025, self.internal)
        self._pengajuan(2026, self.eksternal)
        self._pengajuan(2026, self.bat)
        self._pengajuan(2026, lainnya="Instansi Manual A")
        self._pengajuan(2026, lainnya="Instansi Manual B")

        with self.assertNumQueries(3):
            internal, gabungan = self._charts()

        self.assertEqual([item["id"] for item in internal["categories"]], [self.internal.pk])
        self.assertEqual(
            {item["id"] for item in gabungan["categories"]},
            {self.eksternal.pk, self.bat.pk, "lainnya"},
        )
        self.assertEqual(internal["rows"], [
            {"year": 2025, "instansiId": self.internal.pk, "total": 2},
        ])
        self.assertEqual({row["instansiId"]: row["total"] for row in gabungan["rows"]}, {
            self.eksternal.pk: 1, self.bat.pk: 1, "lainnya": 2,
        })
        self.assertEqual(internal["availableYears"], [2025, 2026])
        self.assertEqual(gabungan["availableYears"], [2026])
        self.assertEqual(internal["defaultYear"], 2026)
        self.assertEqual(gabungan["defaultYear"], 2026)

    def test_status_tidak_disetujui_dan_input_kosong_tidak_dihitung(self):
        self._pengajuan(2024, self.internal, step=StepChoices.ADMIN_LAB)
        self._pengajuan(2024, self.eksternal, step=StepChoices.REJECTED)
        self._pengajuan(2024, lainnya="Instansi Ditolak", step=StepChoices.REJECTED)
        self._pengajuan(2023, lainnya="   ")
        self._pengajuan(2023)

        for chart in self._charts():
            self.assertEqual(chart["rows"], [])
            self.assertEqual(chart["availableYears"], [2026])
            self.assertNotIn("lainnya", [item["id"] for item in chart["categories"]])

    def test_data_lama_dengan_relasi_dan_manual_tidak_dihitung_ganda(self):
        self._pengajuan(2026, self.internal, lainnya="Sisa Isian Manual")
        internal, gabungan = self._charts()
        self.assertEqual(sum(row["total"] for row in internal["rows"]), 1)
        self.assertEqual(gabungan["rows"], [])

    def test_tahun_memakai_updated_at_jika_tanggal_persetujuan_kosong(self):
        pengajuan = self._pengajuan(2022, self.bat)
        PeminjamanRequest.objects.filter(pk=pengajuan.pk).update(
            pimpinan_at=None, updated_at=timezone.make_aware(datetime(2023, 1, 1, 10, 0)),
        )
        _internal, gabungan = self._charts()
        self.assertEqual(gabungan["rows"], [
            {"year": 2023, "instansiId": self.bat.pk, "total": 1},
        ])
        self.assertEqual(gabungan["availableYears"], [2023, 2026])

    def test_dashboard_dan_tv_memuat_kedua_chart_dengan_data_terpisah(self):
        self._pengajuan(2026, self.internal)
        self._pengajuan(2026, lainnya="Instansi Manual")
        self.client.force_login(self.user)

        dashboard = self.client.get(reverse("dashboard:index"))
        display = self.client.get(reverse("dashboard:display", args=[settings.DASHBOARD_TV_SLUG]))
        for response, prefix in ((dashboard, "grafik"), (display, "tv")):
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f'id="{prefix}-instansi-internal"')
            self.assertContains(response, f'id="{prefix}-instansi-gabungan"')
            self.assertContains(response, 'id="data-instansi-internal"')
            self.assertContains(response, 'id="data-instansi-gabungan"')
            self.assertNotIn("instansi_chart", response.context)
            self.assertEqual(len(response.context["instansi_charts"]), 2)
        self.assertContains(dashboard, 'id="tahun-instansi-internal"')
        self.assertContains(dashboard, 'id="tahun-instansi-gabungan"')
        self.assertContains(dashboard, 'data-chart-target="grafik-instansi-internal"', count=2)
        self.assertContains(dashboard, 'data-chart-target="grafik-instansi-gabungan"', count=2)
        self.assertEqual(display.content.count(b" data-tv-slide "), 10)
        self.assertContains(display, 'data-tv-dots')

    def test_export_excel_masing_masing_kelompok(self):
        self._pengajuan(2026, self.internal)
        self._pengajuan(2026, self.eksternal)
        self._pengajuan(2026, lainnya="Instansi Manual")
        self.client.force_login(self.user)
        for chart in self._charts():
            with self.subTest(chart=chart["key"]):
                totals = {row["instansiId"]: row["total"] for row in chart["rows"]}
                labels = [item["label"] for item in chart["categories"]]
                data = [totals.get(item["id"], 0) for item in chart["categories"]]
                response = self.client.post(
                    reverse("dashboard:export_chart"),
                    data=json.dumps({
                        "title": chart["title"], "labels": labels,
                        "datasets": [{"label": "Total Peminjaman", "data": data}],
                    }),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                workbook = load_workbook(BytesIO(response.content))
                self.assertEqual(list(workbook["Data Grafik"].values)[1:], list(zip(labels, data)))
