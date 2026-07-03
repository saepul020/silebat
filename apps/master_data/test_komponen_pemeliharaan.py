from unittest.mock import patch

from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.pengguna.models import Role, User

from apps.master_data.forms import BarangLaboratoriumForm
from apps.master_data.models import (
    BarangLaboratorium,
    KategoriBarangLaboratoriumChoices,
    KondisiBarangChoices,
    StatusBarangChoices,
)
from apps.peminjaman.models import PeminjamanBarangLaboratorium, PeminjamanRequest
from apps.pemeliharaan.models import PemeliharaanPengajuan


class KomponenPemeliharaanRutinTests(TestCase):
    def setUp(self):
        role, _ = Role.objects.get_or_create(nama="Admin Lab")
        self.user = User.objects.create_user(
            username="admin-komponen",
            password="test-pass-123",
        )
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])

    def _form_data(self, components):
        data = QueryDict(mutable=True)
        data.update(
            {
                "status_barang": StatusBarangChoices.NON_BMN,
                "nama_barang": "Drone Uji Komponen",
                "tipe_merek_barang": "DJI Uji",
                "jenis_barang": "Drone",
                "kode_laboratorium": "LAB-KOMP-001",
                "satuan": "Unit",
                "tahun_perolehan": "2026",
                "kondisi_barang": "Baik",
                "lokasi_barang": "Gudang Uji",
                "kategori_barang": KategoriBarangLaboratoriumChoices.DRONE,
                "catatan": "",
            }
        )
        data.setlist("komponen_pemeliharaan", components)
        return data

    def test_form_menampilkan_satu_input_di_bawah_catatan(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("master_data:tambah_barang_laboratorium"))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-komponen")
        self.assertContains(response, "data-file-source-modal")
        self.assertContains(response, "data-file-source-open")
        self.assertContains(response, 'data-file-source-select="upload"')
        self.assertContains(response, 'data-file-source-select="camera"')
        self.assertEqual(content.count("data-komponen-input"), 1)
        self.assertLess(
            content.index("<legend>Catatan</legend>"),
            content.index("<legend>Komponen Pemeliharaan Rutin</legend>"),
        )

    def test_form_menyimpan_komponen_sebagai_list_bersih(self):
        form = BarangLaboratoriumForm(
            data=self._form_data(
                [
                    " Kalibrasi alat ",
                    "",
                    "Pembersihan sensor",
                    "Pemeriksaan baterai",
                ]
            )
        )

        self.assertTrue(form.is_valid(), form.errors)
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            obj = form.save()

        obj.refresh_from_db()
        self.assertEqual(
            obj.komponen_pemeliharaan,
            ["Kalibrasi alat", "Pembersihan sensor", "Pemeriksaan baterai"],
        )
        self.assertTrue(BarangLaboratorium.objects.filter(pk=obj.pk).exists())

    def test_form_menolak_komponen_lebih_dari_seratus_karakter(self):
        form = BarangLaboratoriumForm(data=self._form_data(["A" * 101]))

        self.assertFalse(form.is_valid())
        self.assertIn("komponen_pemeliharaan", form.errors)
        self.assertIn("maksimal 100 karakter", str(form.errors["komponen_pemeliharaan"]))

    def test_detail_alat_tidak_menampilkan_komponen(self):
        self.client.force_login(self.user)
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            obj = BarangLaboratorium.objects.create(
                nama_barang="Drone Detail Bug",
                tipe_merek_barang="DJI Uji Detail",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-KOMP-DETAIL",
                satuan="Unit",
                tahun_perolehan=2026,
                kondisi_barang="Baik",
                lokasi_barang="Gudang Detail",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kalibrasi kamera"],
            )

        with patch("apps.master_data.views.ensure_master_qr_code"):
            response = self.client.get(
                reverse("master_data:detail_barang_laboratorium", args=[obj.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Drone Detail Bug")
        self.assertNotContains(response, "Komponen Pemeliharaan Rutin")
        self.assertNotContains(response, "Kalibrasi kamera")
        self.assertNotContains(response, "(&#x27;label&#x27;,")
        self.assertNotContains(response, "(&#x27;value&#x27;,")

    def test_detail_publik_alat_tidak_menampilkan_komponen(self):
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            obj = BarangLaboratorium.objects.create(
                nama_barang="Drone Public Bug",
                tipe_merek_barang="DJI Uji Public",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-KOMP-PUBLIC",
                satuan="Unit",
                tahun_perolehan=2026,
                kondisi_barang="Baik",
                lokasi_barang="Gudang Public",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Cek baling-baling"],
            )

        response = self.client.get(
            reverse("master_data:public_barang_laboratorium", args=[obj.qr_token])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Drone Public Bug")
        self.assertNotContains(response, "Komponen Pemeliharaan Rutin")
        self.assertNotContains(response, "Cek baling-baling")
        self.assertNotContains(response, "(&#x27;label&#x27;,")
        self.assertNotContains(response, "(&#x27;value&#x27;,")

    def test_komponen_dan_tombol_tambah_terkunci_saat_pemeliharaan_aktif(self):
        self.client.force_login(self.user)
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            obj = BarangLaboratorium.objects.create(
                nama_barang="Drone Lock Komponen",
                tipe_merek_barang="DJI Lock",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-KOMP-LOCK",
                satuan="Unit",
                tahun_perolehan=2026,
                kondisi_barang=KondisiBarangChoices.BAIK,
                lokasi_barang="Gudang Lock",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kamera", "Baterai"],
            )
        PemeliharaanPengajuan.objects.create(pemohon=self.user, alat=obj)

        response = self.client.get(
            reverse("master_data:edit_barang_laboratorium", args=[obj.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-komponen-locked-all="true"')
        self.assertContains(response, "btn btn-secondary komponen-rutin__add btn-disabled")
        self.assertContains(response, "disabled title=")

    def test_komponen_locked_mempertahankan_data_lama_dari_post_manual(self):
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            obj = BarangLaboratorium.objects.create(
                nama_barang="Drone Preserve Komponen",
                tipe_merek_barang="DJI Preserve",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-KOMP-PRESERVE",
                satuan="Unit",
                tahun_perolehan=2026,
                kondisi_barang=KondisiBarangChoices.BAIK,
                lokasi_barang="Gudang Preserve",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kamera", "Baterai"],
            )
        PemeliharaanPengajuan.objects.create(pemohon=self.user, alat=obj)

        form = BarangLaboratoriumForm(
            data=self._form_data(["Komponen Baru"]),
            instance=obj,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["komponen_pemeliharaan"], ["Kamera", "Baterai"])

    def test_kondisi_barang_terkunci_saat_pemeliharaan_aktif(self):
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            obj = BarangLaboratorium.objects.create(
                nama_barang="Drone Lock Kondisi Pemeliharaan",
                tipe_merek_barang="DJI Kondisi",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-KOND-PEM",
                satuan="Unit",
                tahun_perolehan=2026,
                kondisi_barang=KondisiBarangChoices.DALAM_PEMELIHARAAN,
                lokasi_barang="Gudang Kondisi",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kamera"],
            )
        PemeliharaanPengajuan.objects.create(pemohon=self.user, alat=obj)
        data = self._form_data(["Kamera"])
        data["kondisi_barang"] = KondisiBarangChoices.HILANG

        form = BarangLaboratoriumForm(data=data, instance=obj)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.fields["kondisi_barang"].disabled)
        self.assertEqual(
            form.cleaned_data["kondisi_barang"],
            KondisiBarangChoices.DALAM_PEMELIHARAAN,
        )

    def test_kondisi_barang_terkunci_saat_peminjaman_aktif(self):
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            obj = BarangLaboratorium.objects.create(
                nama_barang="Drone Lock Kondisi Peminjaman",
                tipe_merek_barang="DJI Peminjaman",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-KOND-PMJ",
                satuan="Unit",
                tahun_perolehan=2026,
                kondisi_barang=KondisiBarangChoices.BAIK,
                lokasi_barang="Gudang Pinjam",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kamera"],
            )
        today = timezone.localdate()
        pengajuan = PeminjamanRequest.objects.create(
            peminjam=self.user,
            nama_peminjam="Admin Komponen",
            tanggal_mulai=today,
            tanggal_selesai=today,
        )
        PeminjamanBarangLaboratorium.objects.create(pengajuan=pengajuan, barang=obj)
        data = self._form_data(["Kamera"])
        data["kondisi_barang"] = KondisiBarangChoices.HILANG

        form = BarangLaboratoriumForm(data=data, instance=obj)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.fields["kondisi_barang"].disabled)
        self.assertEqual(form.cleaned_data["kondisi_barang"], KondisiBarangChoices.BAIK)
