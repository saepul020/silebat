from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from apps.master_data.forms import BarangLaboratoriumForm
from apps.master_data.models import (
    BarangLaboratorium,
    KategoriBarangLaboratoriumChoices,
    KondisiBarangChoices,
    StatusBarangChoices,
)
from apps.pengguna.models import Role, User

from apps.pemeliharaan.forms import PemeliharaanForm
from apps.pemeliharaan.models import (
    KondisiPemeliharaanChoices,
    PemeliharaanItem,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices,
    TindakanPerbaikanChoices,
)


class PemeliharaanVerifikasiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role_name in ("Admin Lab", "Kepala Lab", "Pimpinan"):
            role, _ = Role.objects.get_or_create(nama=role_name)
            user = User.objects.create_user(
                username=f"pemeliharaan-{role_name.lower().replace(' ', '-')}",
                password="test-pass-123",
            )
            user.safe_profile.role = role
            user.safe_profile.save(update_fields=["role"])
            cls.users[role_name] = user

        with patch("apps.master_data.signals.ensure_master_qr_code"):
            cls.alat = BarangLaboratorium.objects.create(
                nama_barang="Drone Verifikasi Pemeliharaan",
                tipe_merek_barang="DJI Uji",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-PEM-VER-001",
                lokasi_barang="Gudang Uji",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kamera"],
            )

    def _login(self, role_name):
        self.client.force_login(self.users[role_name])

    def _create_pengajuan(self, tindakan):
        pengajuan = PemeliharaanPengajuan.objects.create(
            pemohon=self.users["Admin Lab"],
            alat=self.alat,
        )
        PemeliharaanItem.objects.create(
            pengajuan=pengajuan,
            komponen="Kamera",
            kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
            tindakan_perbaikan=tindakan,
        )
        pengajuan.tandai_alat_dalam_pemeliharaan()
        return pengajuan

    def _master_form_data(self, alat, components):
        data = QueryDict(mutable=True)
        data.update(
            {
                "status_barang": alat.status_barang,
                "nama_barang": alat.nama_barang,
                "tipe_merek_barang": alat.tipe_merek_barang,
                "jenis_barang": alat.jenis_barang,
                "kode_laboratorium": alat.kode_laboratorium,
                "satuan": alat.satuan,
                "tahun_perolehan": alat.tahun_perolehan or "",
                "kondisi_barang": alat.kondisi_barang or KondisiBarangChoices.BAIK,
                "lokasi_barang": alat.lokasi_barang,
                "kategori_barang": alat.kategori_barang,
                "catatan": alat.catatan,
            }
        )
        data.setlist("komponen_pemeliharaan", components)
        return data

    def test_simpan_pengajuan_menandai_alat_dalam_pemeliharaan_dan_filter_dropdown(self):
        self._login("Admin Lab")
        response = self.client.post(
            reverse("pemeliharaan:tambah"),
            {
                "pilih_alat": str(self.alat.pk),
                "komponen_0": "Kamera",
                "kondisi_0": KondisiPemeliharaanChoices.BAIK,
                "dokumentasi_pemeriksaan": SimpleUploadedFile(
                    "pemeriksaan.png",
                    b"fake-image",
                    content_type="image/png",
                ),
            },
        )
        self.assertEqual(response.status_code, 302)

        self.alat.refresh_from_db()
        self.assertEqual(
            self.alat.kondisi_barang,
            KondisiBarangChoices.DALAM_PEMELIHARAAN,
        )

        response = self.client.get(reverse("pemeliharaan:tambah"))
        self.assertNotContains(response, self.alat.nama_barang)

    def test_alat_sedang_dipinjam_tidak_muncul_di_dropdown_pengajuan(self):
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            alat_dipinjam = BarangLaboratorium.objects.create(
                nama_barang="Drone Sedang Dipinjam",
                tipe_merek_barang="DJI Dipinjam",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-PEM-DIPINJAM",
                lokasi_barang="Gudang Uji",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kamera"],
                sedang_dipinjam=True,
            )

        self._login("Admin Lab")
        response = self.client.get(reverse("pemeliharaan:tambah"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, alat_dipinjam.nama_barang)
        self.assertNotContains(response, f'"{alat_dipinjam.pk}":')

    def test_form_menolak_post_manual_alat_sedang_dipinjam(self):
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            alat_dipinjam = BarangLaboratorium.objects.create(
                nama_barang="Drone Manual Dipinjam",
                tipe_merek_barang="DJI Manual",
                jenis_barang="Drone",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-PEM-MANUAL-DIPINJAM",
                lokasi_barang="Gudang Uji",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
                komponen_pemeliharaan=["Kamera"],
                sedang_dipinjam=True,
            )

        form = PemeliharaanForm(
            data={"pilih_alat": str(alat_dipinjam.pk)},
            actor=self.users["Admin Lab"],
        )

        self.assertFalse(form.is_valid())
        self.assertIn("pilih_alat", form.errors)

    def test_master_data_menolak_hapus_komponen_dan_barang_aktif(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        pengajuan.tandai_alat_dalam_pemeliharaan()

        form = BarangLaboratoriumForm(
            data=self._master_form_data(self.alat, []),
            instance=self.alat,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["komponen_pemeliharaan"], ["Kamera"])

        self._login("Admin Lab")
        response = self.client.post(
            reverse("master_data:hapus_barang_laboratorium", args=[self.alat.pk])
        )
        self.assertRedirects(
            response,
            reverse("master_data:data_barang_laboratorium"),
            fetch_redirect_response=False,
        )
        self.assertTrue(BarangLaboratorium.objects.filter(pk=self.alat.pk).exists())

    def test_alur_eksternal_melewati_kepala_lab_lalu_pimpinan(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.EKSTERNAL)

        self._login("Admin Lab")
        response = self.client.post(reverse("pemeliharaan:kirim", args=[pengajuan.pk]))
        self.assertRedirects(
            response,
            reverse("pemeliharaan:detail", args=[pengajuan.pk]),
            fetch_redirect_response=False,
        )
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.KEPALA_LAB)

        self._login("Kepala Lab")
        response = self.client.get(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ringkasan Pengajuan")

        response = self.client.post(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk]),
            {"aksi": "setujui", "catatan": ""},
        )
        self.assertRedirects(response, reverse("verifikasi:index"))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.PIMPINAN)

        self._login("Pimpinan")
        response = self.client.post(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk]),
            {"aksi": "setujui", "catatan": ""},
        )
        self.assertRedirects(response, reverse("verifikasi:index"))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.SELESAI)
        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, KondisiBarangChoices.BAIK)

    def test_alur_mandiri_selesai_di_kepala_lab(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)

        self._login("Admin Lab")
        self.client.post(reverse("pemeliharaan:kirim", args=[pengajuan.pk]))

        self._login("Kepala Lab")
        response = self.client.post(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk]),
            {"aksi": "setujui", "catatan": ""},
        )
        self.assertRedirects(response, reverse("verifikasi:index"))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.SELESAI)

    def test_tidak_setuju_mengembalikan_ke_pemohon(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        self._login("Admin Lab")
        self.client.post(reverse("pemeliharaan:kirim", args=[pengajuan.pk]))

        self._login("Kepala Lab")
        response = self.client.post(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk]),
            {"aksi": "kembalikan", "catatan": "Lengkapi dokumentasi."},
        )
        self.assertRedirects(response, reverse("verifikasi:index"))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.DIKEMBALIKAN)
