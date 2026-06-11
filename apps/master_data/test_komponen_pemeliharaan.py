from unittest.mock import patch

from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from apps.pengguna.models import Role, User

from apps.master_data.forms import BarangLaboratoriumForm
from apps.master_data.models import (
    BarangLaboratorium,
    KategoriBarangLaboratoriumChoices,
    StatusBarangChoices,
)


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
