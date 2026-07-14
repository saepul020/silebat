from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.master_data.models import (
    BarangLaboratorium,
    KategoriBarangLaboratoriumChoices,
    StatusBarangChoices,
)
from apps.pemeliharaan.models import (
    KondisiPemeliharaanChoices,
    PemeliharaanItem,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices,
    TindakanPerbaikanChoices,
)
from apps.peminjaman.models import (
    PeminjamanBarangLaboratorium,
    PeminjamanRequest,
    StepChoices,
)
from apps.pengguna.models import Role, User


class DetailRiwayatAlatTests(TestCase):
    def setUp(self):
        role, _ = Role.objects.get_or_create(nama="Admin Lab")
        self.user = User.objects.create_user(
            username="admin-grafik-alat",
            password="test-pass-123",
        )
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])
        self.client.force_login(self.user)

        qr_patch = patch("apps.master_data.signals.ensure_master_qr_code")
        qr_patch.start()
        self.addCleanup(qr_patch.stop)
        self.alat = BarangLaboratorium.objects.create(
            nama_barang="Borehole Camera Grafik",
            tipe_merek_barang="BC-01",
            jenis_barang="Borehole Camera",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="LAB-GRAFIK-001",
            satuan="Unit",
            tahun_perolehan=2024,
            kondisi_barang="Baik",
            lokasi_barang="Gudang Uji",
            kategori_barang=KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA,
        )
        self.current_year = timezone.localdate().year
        self.previous_year = self.current_year - 1

    def _at(self, year, month):
        return timezone.make_aware(
            datetime(year, month, 10, 9, 0),
            timezone.get_current_timezone(),
        )

    def _pemeliharaan(self, year, month, *, repair=False, alat=True):
        obj = PemeliharaanPengajuan.objects.create(
            pemohon=self.user,
            alat=self.alat if alat else None,
            tanggal_pemeriksaan=self._at(year, month),
            snapshot_nama_barang=self.alat.nama_barang if not alat else "",
            snapshot_kode_laboratorium=(
                self.alat.kode_laboratorium if not alat else ""
            ),
            snapshot_tipe_merek_barang=(
                self.alat.tipe_merek_barang if not alat else ""
            ),
            current_step=StepPemeliharaanChoices.SELESAI,
        )
        if repair:
            for component in ("Kamera", "Kabel"):
                PemeliharaanItem.objects.create(
                    pengajuan=obj,
                    komponen=component,
                    kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
                    tindakan_perbaikan=TindakanPerbaikanChoices.MANDIRI,
                )
        return obj

    def _chart_map(self, response):
        charts = response.context["asset_charts"]["items"]
        return {chart["key"]: chart for chart in charts}

    def test_detail_menampilkan_tiga_grafik_dalam_satu_card(self):
        pengajuan = PeminjamanRequest.objects.create(
            peminjam=self.user,
            nama_peminjam="Admin Grafik",
            tanggal_mulai=timezone.localdate(),
            tanggal_selesai=timezone.localdate(),
            current_step=StepChoices.APPROVED,
            pimpinan_at=self._at(self.current_year, 2),
        )
        PeminjamanBarangLaboratorium.objects.create(
            pengajuan=pengajuan,
            barang=self.alat,
        )
        self._pemeliharaan(self.current_year, 3)
        self._pemeliharaan(self.current_year, 4, repair=True)
        self._pemeliharaan(self.previous_year, 5, alat=False)
        PemeliharaanPengajuan.objects.create(
            pemohon=self.user,
            alat=self.alat,
            tanggal_pemeriksaan=self._at(self.current_year, 6),
            current_step=StepPemeliharaanChoices.DRAFT,
        )

        with patch("apps.master_data.views.ensure_master_qr_code"):
            response = self.client.get(
                reverse(
                    "master_data:detail_barang_laboratorium",
                    args=[self.alat.pk],
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riwayat Peminjaman Alat")
        self.assertNotContains(
            response,
            "Riwayat Peminjaman Peralatan Survei Lapangan",
        )
        self.assertContains(response, 'data-asset-chart-switch="pinjam"')
        self.assertContains(response, 'data-asset-chart-switch="pemeliharaan"')
        self.assertContains(response, 'data-asset-chart-switch="perbaikan"')
        self.assertEqual(
            response.content.count(b"data-asset-chart-card"),
            1,
        )

        charts = self._chart_map(response)
        self.assertEqual(set(charts), {"pinjam", "pemeliharaan", "perbaikan"})
        self.assertTrue(
            all(
                chart["selectedYear"] == self.current_year
                for chart in charts.values()
            )
        )
        self.assertIn(
            {"year": self.current_year, "month": 2, "total": 1},
            charts["pinjam"]["rows"],
        )
        self.assertIn(
            {"year": self.current_year, "month": 3, "total": 1},
            charts["pemeliharaan"]["rows"],
        )
        self.assertIn(
            {"year": self.current_year, "month": 4, "total": 1},
            charts["perbaikan"]["rows"],
        )
        self.assertIn(
            {"year": self.previous_year, "month": 5, "total": 1},
            charts["pemeliharaan"]["rows"],
        )

    def test_filter_tahun_tersimpan_per_grafik(self):
        self._pemeliharaan(self.previous_year, 5)
        self._pemeliharaan(self.previous_year, 6, repair=True)
        url = reverse(
            "master_data:detail_barang_laboratorium",
            args=[self.alat.pk],
        )

        with patch("apps.master_data.views.ensure_master_qr_code"):
            response = self.client.get(
                url,
                {
                    "tahun_pemeliharaan": str(self.previous_year),
                    "tahun_perbaikan": "all",
                },
            )

        charts = self._chart_map(response)
        self.assertEqual(
            charts["pemeliharaan"]["selectedYear"],
            self.previous_year,
        )
        self.assertEqual(charts["perbaikan"]["selectedYear"], "all")
        self.assertEqual(charts["pinjam"]["selectedYear"], self.current_year)
