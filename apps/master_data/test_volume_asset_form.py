from unittest.mock import patch

from django.test import TestCase

from apps.master_data.forms import (
    BarangLaboratoriumForm,
    FasilitasRuanganForm,
    PeralatanLaboratoriumForm,
)
from apps.master_data.models import (
    FasilitasRuangan,
    KondisiBarangChoices,
    PeralatanLaboratorium,
    StatusBarangChoices,
)


class VolumeAssetFormTests(TestCase):
    def setUp(self):
        self.qr_patcher = patch("apps.master_data.signals.ensure_master_qr_code")
        self.qr_patcher.start()
        self.addCleanup(self.qr_patcher.stop)

    def _base_data(self, **overrides):
        data = {
            "status_barang": StatusBarangChoices.NON_BMN,
            "nama_barang": "Alat Uji",
            "tipe_merek_barang": "Merek A",
            "jenis_barang": "Alat",
            "satuan": "Unit",
            "catatan": "",
        }
        data.update(overrides)
        return data

    def test_non_bmn_bervolume_uses_manual_volume_and_clears_metadata(self):
        form = PeralatanLaboratoriumForm(
            data=self._base_data(
                bervolume="true",
                volume=8,
                volume_rusak=2,
                komponen_pemeliharaan=["Komponen yang harus diabaikan"],
            )
        )

        self.assertFalse(form.komponen_visible)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertTrue(obj.bervolume)
        self.assertEqual(obj.volume, 8)
        self.assertEqual(obj.volume_rusak, 2)
        self.assertIsNone(obj.kode_laboratorium)
        self.assertIsNone(obj.tahun_perolehan)
        self.assertEqual(obj.lokasi_barang, "")
        self.assertEqual(obj.komponen_pemeliharaan, [])

    def test_non_bmn_tanpa_volume_uses_condition_automatic_volume(self):
        form = FasilitasRuanganForm(
            data=self._base_data(
                bervolume="false",
                kode_laboratorium="FAS-001",
                tahun_perolehan=2026,
                kondisi_barang=KondisiBarangChoices.RUSAK,
                lokasi_barang="Ruang Uji",
                kategori_barang="Fasilitas Ruangan",
                komponen_pemeliharaan=["Pembersihan", "Pemeriksaan baut"],
            )
        )

        self.assertTrue(form.komponen_visible)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertFalse(obj.bervolume)
        self.assertEqual(obj.volume, 0)
        self.assertEqual(obj.volume_rusak, 1)
        self.assertEqual(obj.kondisi_barang, KondisiBarangChoices.RUSAK)
        self.assertEqual(
            obj.komponen_pemeliharaan,
            ["Pembersihan", "Pemeriksaan baut"],
        )

    def test_edit_peralatan_lab_non_bmn_tidak_saves_without_manual_metadata(self):
        obj = PeralatanLaboratorium.objects.create(
            status_barang=StatusBarangChoices.NON_BMN,
            bervolume=True,
            nama_barang="Alat Manual Lama",
            tipe_merek_barang="Merek Lama",
            jenis_barang="Alat",
            satuan="Unit",
            volume=8,
            volume_rusak=2,
        )

        form = PeralatanLaboratoriumForm(
            data=self._base_data(
                bervolume="false",
                nama_barang=obj.nama_barang,
                tipe_merek_barang=obj.tipe_merek_barang,
                jenis_barang=obj.jenis_barang,
                satuan=obj.satuan,
                kondisi_barang=KondisiBarangChoices.RUSAK,
                komponen_pemeliharaan=["Pemeriksaan"],
            ),
            instance=obj,
        )

        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertFalse(saved.bervolume)
        self.assertEqual(saved.volume, 0)
        self.assertEqual(saved.volume_rusak, 1)
        self.assertEqual(saved.kondisi_barang, KondisiBarangChoices.RUSAK)
        self.assertEqual(saved.kode_laboratorium, "")
        self.assertEqual(saved.lokasi_barang, "")
        self.assertEqual(saved.komponen_pemeliharaan, ["Pemeriksaan"])

    def test_bmn_menyimpan_komponen_pemeliharaan(self):
        form = PeralatanLaboratoriumForm(
            data=self._base_data(
                status_barang=StatusBarangChoices.BMN,
                kode_aset_bmn="BMN-KOMP-001",
                kode_laboratorium="LAB-KOMP-001",
                tahun_perolehan=2026,
                kondisi_barang=KondisiBarangChoices.BAIK,
                lokasi_barang="Ruang Uji",
                komponen_pemeliharaan=[" Kalibrasi ", "Pembersihan sensor"],
            )
        )

        self.assertTrue(form.komponen_visible)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(
            obj.komponen_pemeliharaan,
            ["Kalibrasi", "Pembersihan sensor"],
        )

    def test_komponen_pemeliharaan_maksimal_seratus_karakter(self):
        form = PeralatanLaboratoriumForm(
            data=self._base_data(
                bervolume="false",
                kode_laboratorium="LAB-KOMP-PANJANG",
                tahun_perolehan=2026,
                kondisi_barang=KondisiBarangChoices.BAIK,
                lokasi_barang="Ruang Uji",
                komponen_pemeliharaan=["A" * 101],
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn("maksimal 100 karakter", str(form.errors["komponen_pemeliharaan"]))

    def test_non_bmn_requires_explicit_volume_choice(self):
        for form_class in (FasilitasRuanganForm, PeralatanLaboratoriumForm):
            with self.subTest(form_class=form_class.__name__):
                data = self._base_data()
                if form_class is FasilitasRuanganForm:
                    data["kategori_barang"] = "Fasilitas Ruangan"
                form = form_class(data=data)

                self.assertTrue(form.dependent_fields_locked)
                self.assertFalse(form.is_valid())
                self.assertEqual(
                    form.errors["bervolume"],
                    ["Pilih Ya atau Tidak untuk status barang ber-volume."],
                )

    def test_volume_choice_uses_yes_no_radio_buttons(self):
        form = PeralatanLaboratoriumForm(
            data=self._base_data(bervolume="false")
        )

        field = form.fields["bervolume"]
        self.assertFalse(form.dependent_fields_locked)
        self.assertTrue(field.required)
        self.assertEqual(
            list(field.choices),
            [("true", "Ya"), ("false", "Tidak")],
        )

    def test_kode_laboratorium_initial_increments_last_trailing_number(self):
        PeralatanLaboratorium.objects.create(
            status_barang=StatusBarangChoices.NON_BMN,
            bervolume=False,
            nama_barang="Alat Lama",
            tipe_merek_barang="Merek Lama",
            jenis_barang="Alat",
            kode_laboratorium="LAB-009",
            satuan="Unit",
            kondisi_barang=KondisiBarangChoices.BAIK,
            lokasi_barang="Gudang",
        )

        form = PeralatanLaboratoriumForm()

        self.assertEqual(form.fields["kode_laboratorium"].initial, "LAB-010")

    def test_foto_barang_tidak_memaksa_kamera_otomatis(self):
        form = PeralatanLaboratoriumForm()

        attrs = form.fields["foto_barang"].widget.attrs
        self.assertNotIn("capture", attrs)
        self.assertIn("image/*", attrs["accept"])
        self.assertEqual(attrs["data-inline-file-placeholder"], "Pilih gambar")

    def test_form_survei_tidak_memiliki_pilihan_barang_bervolume(self):
        form = BarangLaboratoriumForm(
            data={
                "status_barang": StatusBarangChoices.NON_BMN,
                "nama_barang": "Drone Survei",
                "tipe_merek_barang": "DJI",
                "jenis_barang": "Drone",
                "kode_laboratorium": "SUR-001",
                "satuan": "Unit",
                "tahun_perolehan": 2026,
                "kondisi_barang": KondisiBarangChoices.BAIK,
                "lokasi_barang": "Gudang",
                "kategori_barang": "Drone",
                "catatan": "",
                "komponen_pemeliharaan": ["Kamera"],
            }
        )

        self.assertNotIn("bervolume", form.fields)
        self.assertFalse(form.dependent_fields_locked)
        self.assertTrue(form.is_valid(), form.errors)
