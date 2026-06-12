from datetime import date, datetime
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from django.utils import timezone
from PIL import Image

from apps.master_data.forms import BarangLaboratoriumForm
from apps.master_data.models import (
    BarangLaboratorium,
    KategoriBarangLaboratoriumChoices,
    KondisiBarangChoices,
    StatusBarangChoices,
)
from apps.operasional.models import TIM_LAYANAN_TEKNIS_NAME, TimKegiatan
from apps.pengguna.models import Role, User

from apps.pemeliharaan.forms import PemeliharaanForm
from apps.pemeliharaan.models import (
    JenisFotoPemeliharaanChoices,
    KondisiPemeliharaanChoices,
    PemeliharaanFoto,
    PemeliharaanItem,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices,
    TindakanPerbaikanChoices,
)
from apps.pemeliharaan.pdf_utils import (
    TABLE_GAP,
    _repair_table,
    _signers,
    render_pemeliharaan_pdf,
)


class PemeliharaanVerifikasiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role_name in ("Super Admin", "Admin Lab", "Kepala Lab", "Pimpinan"):
            role, _ = Role.objects.get_or_create(nama=role_name)
            user = User.objects.create_user(
                username=f"pemeliharaan-{role_name.lower().replace(' ', '-')}",
                password="test-pass-123",
            )
            user.safe_profile.role = role
            profile_fields = ["role"]
            if role_name == "Pimpinan":
                user.safe_profile.jabatan = "Ketua Tim Layanan Teknis"
                profile_fields.append("jabatan")
            user.safe_profile.save(update_fields=profile_fields)
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
        self.alat.refresh_from_db()
        pengajuan = PemeliharaanPengajuan.objects.create(
            pemohon=self.users["Admin Lab"],
            alat=self.alat,
        )
        PemeliharaanItem.objects.create(
            pengajuan=pengajuan,
            komponen="Kamera",
            kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
            tindakan_perbaikan=tindakan,
            tanggal_selesai_perbaikan=timezone.now()
            if tindakan == TindakanPerbaikanChoices.MANDIRI
            else None,
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

    def _image_upload(self, name):
        output = BytesIO()
        Image.new("RGB", (120, 80), "white").save(output, format="PNG")
        return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")

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
        self.assertIsNone(self.alat.tanggal_pemeliharaan)
        self.assertIsNone(self.alat.tanggal_perbaikan)

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

    def test_form_menerima_tanggal_perbaikan_format_picker(self):
        tanggal_pemeriksaan = timezone.make_aware(datetime(2026, 6, 12, 9, 0))
        form = PemeliharaanForm(
            data={
                "pilih_alat": str(self.alat.pk),
                "komponen_0": "Kamera",
                "kondisi_0": KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
                "tindakan_0": TindakanPerbaikanChoices.MANDIRI,
                "uraian_perbaikan_0": "Kalibrasi ulang kamera.",
                "tanggal_selesai_perbaikan_0": "12 Jun 2026",
            },
            files=MultiValueDict(
                {
                    "dokumentasi_pemeriksaan": [
                        SimpleUploadedFile(
                            "pemeriksaan.png",
                            b"fake-image",
                            content_type="image/png",
                        )
                    ],
                    "dokumentasi_perbaikan_0": [
                        SimpleUploadedFile(
                            "perbaikan.png",
                            b"fake-image",
                            content_type="image/png",
                        )
                    ],
                }
            ),
            actor=self.users["Admin Lab"],
            tanggal_pemeriksaan=tanggal_pemeriksaan,
        )

        self.assertTrue(form.is_valid(), form.errors)
        selesai = form.cleaned_items[0]["tanggal_selesai_perbaikan"]
        self.assertEqual(selesai.hour, 23)
        self.assertEqual(selesai.minute, 59)

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
            reverse("pemeliharaan:list"),
            fetch_redirect_response=False,
        )
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.KEPALA_LAB)
        self.alat.refresh_from_db()
        self.assertIsNone(self.alat.tanggal_pemeliharaan)
        self.assertIsNone(self.alat.tanggal_perbaikan)

        self._login("Kepala Lab")
        response = self.client.get(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pemeriksaan")
        self.assertContains(response, "Perbaikan")
        self.assertContains(response, "Tolak")
        self.assertContains(response, "Perbaiki")
        self.assertContains(response, "Setujui")
        self.assertContains(response, 'data-action="setujui"')
        self.assertContains(response, 'class="btn btn-primary js-verify-action"')
        self.assertContains(response, "btn-warning")

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
        self.assertIsNotNone(self.alat.tanggal_pemeliharaan)
        self.assertIsNotNone(self.alat.tanggal_perbaikan)

    def test_alur_mandiri_selesai_di_kepala_lab(self):
        self.alat.kondisi_barang = KondisiBarangChoices.RUSAK
        self.alat.save(update_fields=["kondisi_barang", "updated_at"])
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
        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, KondisiBarangChoices.BAIK)
        self.assertIsNotNone(self.alat.tanggal_pemeliharaan)
        self.assertIsNotNone(self.alat.tanggal_perbaikan)

    def test_edit_detail_terkunci_setelah_dikirim_dan_aktif_saat_dikembalikan(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        self._login("Admin Lab")

        self.client.post(reverse("pemeliharaan:kirim", args=[pengajuan.pk]))
        response = self.client.get(reverse("pemeliharaan:detail", args=[pengajuan.pk]))

        self.assertContains(
            response,
            'title="Pengajuan tidak dapat diedit pada tahap ini" disabled>Edit</button>',
            html=False,
        )
        self.assertNotContains(response, reverse("pemeliharaan:edit", args=[pengajuan.pk]))

        pengajuan.current_step = StepPemeliharaanChoices.DIKEMBALIKAN
        pengajuan.save(update_fields=["current_step", "updated_at"])
        response = self.client.get(reverse("pemeliharaan:detail", args=[pengajuan.pk]))

        self.assertContains(response, reverse("pemeliharaan:edit", args=[pengajuan.pk]))
        self.assertNotContains(response, 'disabled>Edit</button>')

    def test_perbaiki_mengembalikan_ke_pemohon(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        self._login("Admin Lab")
        self.client.post(reverse("pemeliharaan:kirim", args=[pengajuan.pk]))

        self._login("Kepala Lab")
        response = self.client.post(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk]),
            {"aksi": "perbaiki", "catatan": "Lengkapi dokumentasi."},
        )
        self.assertRedirects(response, reverse("verifikasi:index"))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.DIKEMBALIKAN)

    def test_tolak_kepala_lab_selesai_dan_memulihkan_kondisi_awal(self):
        self.alat.kondisi_barang = KondisiBarangChoices.RUSAK
        self.alat.tanggal_pemeliharaan = date(2025, 1, 10)
        self.alat.tanggal_perbaikan = date(2025, 1, 11)
        self.alat.save(
            update_fields=[
                "kondisi_barang",
                "tanggal_pemeliharaan",
                "tanggal_perbaikan",
                "updated_at",
            ]
        )
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        self._login("Admin Lab")
        self.client.post(reverse("pemeliharaan:kirim", args=[pengajuan.pk]))

        self._login("Kepala Lab")
        response = self.client.post(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk]),
            {"aksi": "tolak", "catatan": "Tidak layak diproses."},
        )

        self.assertRedirects(response, reverse("verifikasi:index"))
        pengajuan.refresh_from_db()
        self.assertEqual(pengajuan.current_step, StepPemeliharaanChoices.DITOLAK)
        self.assertEqual(pengajuan.kepala_lab_status, "rejected")
        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, KondisiBarangChoices.RUSAK)
        self.assertEqual(self.alat.tanggal_pemeliharaan, date(2025, 1, 10))
        self.assertEqual(self.alat.tanggal_perbaikan, date(2025, 1, 11))

    def test_hapus_pengajuan_memulihkan_seluruh_data_master_awal(self):
        self.alat.kondisi_barang = KondisiBarangChoices.RUSAK
        self.alat.tanggal_pemeliharaan = date(2025, 1, 10)
        self.alat.tanggal_perbaikan = date(2025, 1, 11)
        self.alat.save(
            update_fields=[
                "kondisi_barang",
                "tanggal_pemeliharaan",
                "tanggal_perbaikan",
                "updated_at",
            ]
        )
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        pengajuan.add_timeline("Pelaksana Pemeliharaan", "Data uji dibuat")

        self._login("Admin Lab")
        self.client.post(reverse("pemeliharaan:kirim", args=[pengajuan.pk]))
        self._login("Kepala Lab")
        self.client.post(
            reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk]),
            {"aksi": "setujui", "catatan": ""},
        )
        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, KondisiBarangChoices.BAIK)
        self.assertNotEqual(self.alat.tanggal_pemeliharaan, date(2025, 1, 10))

        self._login("Super Admin")
        response = self.client.post(reverse("pemeliharaan:hapus", args=[pengajuan.pk]))

        self.assertRedirects(
            response,
            reverse("pemeliharaan:list"),
            fetch_redirect_response=False,
        )
        self.assertFalse(PemeliharaanPengajuan.objects.filter(pk=pengajuan.pk).exists())
        self.assertFalse(PemeliharaanItem.objects.filter(pengajuan_id=pengajuan.pk).exists())
        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, KondisiBarangChoices.RUSAK)
        self.assertEqual(self.alat.tanggal_pemeliharaan, date(2025, 1, 10))
        self.assertEqual(self.alat.tanggal_perbaikan, date(2025, 1, 11))

    def test_hapus_pengajuan_lama_tidak_mengubah_hasil_pengajuan_lebih_baru(self):
        pengajuan_lama = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        pengajuan_lama.current_step = StepPemeliharaanChoices.SELESAI
        pengajuan_lama.save(update_fields=["current_step", "updated_at"])

        pengajuan_baru = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        pengajuan_baru.current_step = StepPemeliharaanChoices.SELESAI
        pengajuan_baru.save(update_fields=["current_step", "updated_at"])
        pengajuan_baru.catat_riwayat_alat_disetujui()
        pengajuan_baru.tandai_alat_baik_jika_selesai()
        self.alat.refresh_from_db()
        kondisi_terbaru = self.alat.kondisi_barang
        pemeliharaan_terbaru = self.alat.tanggal_pemeliharaan
        perbaikan_terbaru = self.alat.tanggal_perbaikan

        self._login("Super Admin")
        self.client.post(reverse("pemeliharaan:hapus", args=[pengajuan_lama.pk]))

        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, kondisi_terbaru)
        self.assertEqual(self.alat.tanggal_pemeliharaan, pemeliharaan_terbaru)
        self.assertEqual(self.alat.tanggal_perbaikan, perbaikan_terbaru)

    def test_hapus_laporan_hanya_super_admin_dan_kembali_ke_laporan(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        pengajuan.current_step = StepPemeliharaanChoices.SELESAI
        pengajuan.save(update_fields=["current_step", "updated_at"])
        delete_url = reverse("pemeliharaan:hapus", args=[pengajuan.pk])

        self._login("Admin Lab")
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PemeliharaanPengajuan.objects.filter(pk=pengajuan.pk).exists())

        self._login("Super Admin")
        response = self.client.post(
            delete_url,
            HTTP_REFERER=f"http://testserver{reverse('pemeliharaan:laporan')}",
        )
        self.assertRedirects(
            response,
            reverse("pemeliharaan:laporan"),
            fetch_redirect_response=False,
        )
        self.assertFalse(PemeliharaanPengajuan.objects.filter(pk=pengajuan.pk).exists())

    def test_kondisi_dalam_perbaikan_tidak_lagi_muncul_di_pilihan_master_data(self):
        values = [value for value, _label in KondisiBarangChoices.choices]
        self.assertNotIn("Dalam Perbaikan", values)
        self.assertIn(KondisiBarangChoices.DALAM_PEMELIHARAAN, values)

    def test_pengajuan_final_masuk_laporan_dan_tidak_masuk_daftar_berjalan(self):
        selesai = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        selesai.current_step = StepPemeliharaanChoices.SELESAI
        selesai.kepala_lab_by = self.users["Kepala Lab"]
        selesai.kepala_lab_at = timezone.now()
        selesai.save(
            update_fields=[
                "current_step",
                "kepala_lab_by",
                "kepala_lab_at",
                "updated_at",
            ]
        )
        ditolak = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        ditolak.current_step = StepPemeliharaanChoices.DITOLAK
        ditolak.kepala_lab_by = self.users["Kepala Lab"]
        ditolak.kepala_lab_at = timezone.now()
        ditolak.save(
            update_fields=[
                "current_step",
                "kepala_lab_by",
                "kepala_lab_at",
                "updated_at",
            ]
        )
        berjalan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)

        self._login("Admin Lab")
        response = self.client.get(reverse("pemeliharaan:list"))
        self.assertContains(response, berjalan.nomor_pengajuan)
        self.assertNotContains(response, selesai.nomor_pengajuan)
        self.assertNotContains(response, ditolak.nomor_pengajuan)

        response = self.client.get(reverse("pemeliharaan:laporan"))
        self.assertContains(response, selesai.nomor_pengajuan)
        self.assertContains(response, ditolak.nomor_pengajuan)
        self.assertContains(response, "Disetujui")
        self.assertContains(response, "Ditolak")
        self.assertNotContains(response, berjalan.nomor_pengajuan)
        self.assertNotContains(
            response,
            reverse("pemeliharaan:hapus", args=[selesai.pk]),
        )

        self._login("Super Admin")
        response = self.client.get(reverse("pemeliharaan:laporan"))
        self.assertContains(
            response,
            reverse("pemeliharaan:hapus", args=[selesai.pk]),
        )
        self.assertContains(response, 'title="Hapus laporan"', html=False)

    def test_pdf_laporan_hanya_tersedia_setelah_proses_final(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        self._login("Admin Lab")

        response = self.client.get(reverse("pemeliharaan:download_pdf", args=[pengajuan.pk]))
        self.assertEqual(response.status_code, 404)

        pengajuan.current_step = StepPemeliharaanChoices.SELESAI
        pengajuan.kepala_lab_by = self.users["Kepala Lab"]
        pengajuan.kepala_lab_at = timezone.now()
        pengajuan.add_timeline(
            "Kepala Lab",
            "Pengajuan pemeliharaan disetujui Kepala Lab dan dinyatakan selesai",
            self.users["Kepala Lab"],
        )
        item = pengajuan.items.get()
        PemeliharaanFoto.objects.create(
            item=item,
            jenis=JenisFotoPemeliharaanChoices.PEMERIKSAAN,
            foto=self._image_upload("pdf-pemeriksaan.png"),
        )
        PemeliharaanFoto.objects.create(
            item=item,
            jenis=JenisFotoPemeliharaanChoices.PERBAIKAN,
            foto=self._image_upload("pdf-perbaikan.png"),
        )
        pengajuan.save(
            update_fields=[
                "current_step",
                "kepala_lab_by",
                "kepala_lab_at",
                "updated_at",
            ]
        )

        response = self.client.get(reverse("pemeliharaan:download_pdf", args=[pengajuan.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(
            f"laporan-pemeliharaan-{pengajuan.nomor_pengajuan}.pdf",
            response["Content-Disposition"],
        )
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_pdf_memakai_penanda_tangan_dari_data_master(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.EKSTERNAL)
        pengajuan.current_step = StepPemeliharaanChoices.SELESAI
        pengajuan.kepala_lab_by = self.users["Admin Lab"]
        pengajuan.pimpinan_by = self.users["Admin Lab"]
        pengajuan.save(
            update_fields=[
                "current_step",
                "kepala_lab_by",
                "pimpinan_by",
                "updated_at",
            ]
        )
        TimKegiatan.objects.update_or_create(
            nama_tim=TIM_LAYANAN_TEKNIS_NAME,
            defaults={"ketua_tim": self.users["Pimpinan"]},
        )

        signers = _signers(pengajuan)

        self.assertEqual(
            [user for _title, user in signers],
            [
                self.users["Admin Lab"],
                self.users["Kepala Lab"],
                self.users["Pimpinan"],
            ],
        )
        self.assertEqual(
            [title for title, _user in signers],
            [
                "Pelaksana Pemeliharaan,",
                "Kepala Laboratorium,",
                "Ketua Tim Layanan Teknis,",
            ],
        )

    def test_laporan_memakai_snapshot_status_barang(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.MANDIRI)
        self.assertEqual(pengajuan.snapshot_status_barang, StatusBarangChoices.NON_BMN)

        BarangLaboratorium.objects.filter(pk=self.alat.pk).update(
            status_barang=StatusBarangChoices.BMN
        )
        pengajuan.refresh_from_db()

        self.assertEqual(pengajuan.status_barang_label, StatusBarangChoices.NON_BMN)

    def test_pdf_tanpa_riwayat_proses_dan_foto_sesuai_bagian(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.EKSTERNAL)
        item = pengajuan.items.get()
        mandiri = PemeliharaanItem.objects.create(
            pengajuan=pengajuan,
            komponen="Baterai",
            kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
            tindakan_perbaikan=TindakanPerbaikanChoices.MANDIRI,
            uraian_perbaikan="Kalibrasi baterai.",
            tanggal_selesai_perbaikan=timezone.now(),
        )
        PemeliharaanFoto.objects.create(
            item=item,
            jenis=JenisFotoPemeliharaanChoices.PEMERIKSAAN,
            foto=self._image_upload("pemeriksaan.png"),
        )
        PemeliharaanFoto.objects.create(
            item=item,
            jenis=JenisFotoPemeliharaanChoices.KERUSAKAN,
            foto=self._image_upload("kerusakan.png"),
        )
        PemeliharaanFoto.objects.create(
            item=mandiri,
            jenis=JenisFotoPemeliharaanChoices.PERBAIKAN,
            foto=self._image_upload("perbaikan.png"),
        )

        with (
            patch("apps.pemeliharaan.pdf_utils.section") as section_mock,
            patch("apps.pemeliharaan.pdf_utils.info_table", return_value="") as info_mock,
            patch("apps.pemeliharaan.pdf_utils.data_table", return_value="") as data_mock,
            patch("apps.pemeliharaan.pdf_utils.photo_grid", return_value=[]) as photo_mock,
            patch("apps.pemeliharaan.pdf_utils._repair_table", return_value=[]) as repair_mock,
            patch("apps.pemeliharaan.pdf_utils.signature_list", return_value=[]) as sign_mock,
            patch("apps.pemeliharaan.pdf_utils.build_pdf"),
        ):
            render_pemeliharaan_pdf(BytesIO(), pengajuan, lambda value: "-")

        section_titles = [call.args[0] for call in section_mock.call_args_list]
        self.assertNotIn("D. Riwayat Proses", section_titles)
        self.assertNotIn("Dokumentasi Pemeriksaan", section_titles)
        self.assertIn("C. Tindak Lanjut Perbaikan", section_titles)
        self.assertEqual(photo_mock.call_count, 1)
        self.assertEqual(photo_mock.call_args.kwargs["header"], "Dokumentasi Pemeriksaan")
        self.assertEqual(info_mock.call_args.kwargs["valign"], "MIDDLE")
        self.assertEqual(data_mock.call_args.kwargs["valign"], "MIDDLE")
        self.assertEqual(
            [call.args[0] for call in repair_mock.call_args_list],
            ["Perbaikan Mandiri", "Perbaikan Eksternal"],
        )
        self.assertTrue(sign_mock.call_args.kwargs["centered"])
        self.assertEqual(sign_mock.call_args.kwargs["approval_label"], "Menyetujui:")

    def test_pdf_memberi_jarak_antar_tabel(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.EKSTERNAL)
        item = pengajuan.items.get()
        PemeliharaanItem.objects.create(
            pengajuan=pengajuan,
            komponen="Baterai",
            kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
            tindakan_perbaikan=TindakanPerbaikanChoices.MANDIRI,
            uraian_perbaikan="Kalibrasi baterai.",
            tanggal_selesai_perbaikan=timezone.now(),
        )
        PemeliharaanFoto.objects.create(
            item=item,
            jenis=JenisFotoPemeliharaanChoices.PEMERIKSAAN,
            foto=self._image_upload("pemeriksaan-gap.png"),
        )
        foto_table = object()
        mandiri_table = object()
        eksternal_table = object()

        with (
            patch("apps.pemeliharaan.pdf_utils.info_table", return_value=object()),
            patch("apps.pemeliharaan.pdf_utils.data_table", return_value=object()),
            patch(
                "apps.pemeliharaan.pdf_utils.photo_grid",
                return_value=[foto_table],
            ),
            patch(
                "apps.pemeliharaan.pdf_utils._repair_table",
                side_effect=[[mandiri_table], [eksternal_table]],
            ),
            patch("apps.pemeliharaan.pdf_utils.signature_list", return_value=[]),
            patch("apps.pemeliharaan.pdf_utils.build_pdf") as build_mock,
        ):
            render_pemeliharaan_pdf(BytesIO(), pengajuan, lambda value: "-")

        story = build_mock.call_args.args[2]
        foto_index = story.index(foto_table)
        mandiri_index = story.index(mandiri_table)
        eksternal_index = story.index(eksternal_table)
        self.assertEqual(story[foto_index - 1].height, TABLE_GAP)
        self.assertEqual(story[mandiri_index + 1].height, TABLE_GAP)
        self.assertEqual(eksternal_index, mandiri_index + 2)

    def test_tabel_perbaikan_terpisah_tanpa_kolom_tindakan(self):
        pengajuan = self._create_pengajuan(TindakanPerbaikanChoices.EKSTERNAL)
        eksternal = pengajuan.items.get()
        mandiri = PemeliharaanItem.objects.create(
            pengajuan=pengajuan,
            komponen="Baterai",
            kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN,
            tindakan_perbaikan=TindakanPerbaikanChoices.MANDIRI,
            uraian_perbaikan="Kalibrasi baterai.",
            tanggal_selesai_perbaikan=timezone.now(),
        )

        with patch("apps.pemeliharaan.pdf_utils.photo_cell", return_value="-"):
            tabel_mandiri = _repair_table(
                "Perbaikan Mandiri",
                [mandiri],
                JenisFotoPemeliharaanChoices.PERBAIKAN,
                lambda value: "-",
            )[0]
            tabel_eksternal = _repair_table(
                "Perbaikan Eksternal",
                [eksternal],
                JenisFotoPemeliharaanChoices.KERUSAKAN,
                lambda value: "-",
            )[0]

        judul_mandiri = tabel_mandiri._cellvalues[0][0].getPlainText()
        judul_eksternal = tabel_eksternal._cellvalues[0][0].getPlainText()
        header_mandiri = [cell.getPlainText() for cell in tabel_mandiri._cellvalues[1]]
        header_eksternal = [cell.getPlainText() for cell in tabel_eksternal._cellvalues[1]]
        self.assertEqual(judul_mandiri, "Perbaikan Mandiri")
        self.assertEqual(judul_eksternal, "Perbaikan Eksternal")
        self.assertNotIn("Tindakan", header_mandiri)
        self.assertNotIn("Tindakan", header_eksternal)
        self.assertIn("Dokumentasi Perbaikan", header_mandiri)
        self.assertIn("Dokumentasi Kerusakan", header_eksternal)
        self.assertEqual(tabel_mandiri.repeatRows, 2)
        self.assertEqual(tabel_eksternal.repeatRows, 2)
        self.assertIsNone(tabel_mandiri._argH[0])
        self.assertIsNone(tabel_mandiri._argH[1])
        self.assertIsNone(tabel_eksternal._argH[0])
        self.assertIsNone(tabel_eksternal._argH[1])
        self.assertTrue(
            all(
                cell.valign == "MIDDLE"
                for row in tabel_mandiri._cellStyles
                for cell in row
            )
        )
        self.assertTrue(
            all(
                cell.valign == "MIDDLE"
                for row in tabel_eksternal._cellStyles
                for cell in row
            )
        )
