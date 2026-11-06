from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.master_data.forms import BarangLaboratoriumForm, FasilitasRuanganForm, PeralatanLaboratoriumForm
from apps.master_data.models import BarangLaboratorium, FasilitasRuangan, PeralatanLaboratorium
from apps.master_data.views import (
    _save_import_objects,
    _validate_barang_laboratorium_import,
    _validate_fasilitas_ruangan_import,
    _validate_peralatan_laboratorium_import,
)
from apps.pengguna.models import Role, User


CASES = (
    (BarangLaboratoriumForm, BarangLaboratorium, "barang_laboratorium", _validate_barang_laboratorium_import),
    (FasilitasRuanganForm, FasilitasRuangan, "fasilitas_ruangan", _validate_fasilitas_ruangan_import),
    (PeralatanLaboratoriumForm, PeralatanLaboratorium, "peralatan_laboratorium", _validate_peralatan_laboratorium_import),
)


class AsalPerolehanTests(TestCase):
    def setUp(self):
        for target in (
            "apps.master_data.signals.ensure_master_qr_code",
            "apps.master_data.views.ensure_master_qr_code",
            "apps.master_data.qr_utils.ensure_master_qr_code",
        ):
            qr_patch = patch(target)
            qr_patch.start()
            self.addCleanup(qr_patch.stop)
        self.counter = 0
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        self.user = User.objects.create_user(username="uji-asal-perolehan")
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])
        self.client.force_login(self.user)

    def _data(self, form_class, **overrides):
        self.counter += 1
        data = {
            "status_barang": "BMN", "bervolume": "false",
            "nama_barang": f"Barang Asal {self.counter}", "tipe_merek_barang": "Tipe A",
            "jenis_barang": "Alat Uji", "kode_aset_bmn": f"BMN-ASAL-{self.counter}",
            "kode_laboratorium": f"LAB-ASAL-{self.counter}", "satuan": "Unit",
            "tahun_perolehan": 2026, "asal_perolehan": " Pengadaan APBN ",
            "kondisi_barang": "Baik", "lokasi_barang": "Gudang",
            "komponen_pemeliharaan": ["Pemeriksaan rutin"],
        }
        if form_class is BarangLaboratoriumForm:
            data["kategori_barang"] = "Borehole Camera"
        elif form_class is FasilitasRuanganForm:
            data["kategori_barang"] = "Fasilitas Ruangan"
        data.update(overrides)
        return data

    def _upload(self, workbook):
        output = BytesIO()
        workbook.save(output)
        return SimpleUploadedFile("asal.xlsx", output.getvalue())

    def test_tambah_dan_edit_bmn_non_bmn_tanpa_volume(self):
        for form_class, model, _key, _validate in CASES:
            for status in ("BMN", "Non BMN"):
                with self.subTest(model=model.__name__, status=status):
                    data = self._data(form_class, status_barang=status)
                    form = form_class(data=data)
                    self.assertTrue(form.is_valid(), form.errors)
                    obj = form.save()
                    obj.refresh_from_db()
                    self.assertEqual(obj.asal_perolehan, "Pengadaan APBN")
                    data["asal_perolehan"] = "Hibah"
                    edit = form_class(data=data, instance=obj)
                    self.assertTrue(edit.is_valid(), edit.errors)
                    edit.save()
                    obj.refresh_from_db()
                    self.assertEqual(obj.asal_perolehan, "Hibah")

    def test_opsional_dan_batas_panjang_divalidasi_backend(self):
        for form_class, _model, _key, _validate in CASES:
            with self.subTest(form=form_class.__name__):
                form = form_class(data=self._data(form_class, asal_perolehan=""))
                self.assertTrue(form.is_valid(), form.errors)
                form = form_class(data=self._data(form_class, asal_perolehan="A" * 201))
                self.assertFalse(form.is_valid())
                self.assertIn("asal_perolehan", form.errors)

    def test_input_manual_bervolume_diabaikan_termasuk_request_tampering(self):
        for form_class, _model, _key, _validate in CASES[1:]:
            with self.subTest(form=form_class.__name__):
                form = form_class(data=self._data(
                    form_class, status_barang="Non BMN", bervolume="true",
                    volume=8, volume_rusak=2, asal_perolehan="A" * 201,
                ))
                self.assertTrue(form.fields["asal_perolehan"].disabled)
                self.assertTrue(form.is_valid(), form.errors)
                obj = form.save()
                obj.refresh_from_db()
                self.assertEqual(obj.asal_perolehan, "")
                self.assertEqual(obj.volume, 8)

    def test_model_clean_dan_partial_save_mengosongkan_asal_bervolume(self):
        for form_class, _model, _key, _validate in CASES[1:]:
            with self.subTest(form=form_class.__name__):
                form = form_class(data=self._data(form_class, status_barang="Non BMN"))
                self.assertTrue(form.is_valid(), form.errors)
                obj = form.save()
                obj.bervolume = True
                obj.clean()
                self.assertEqual(obj.asal_perolehan, "")
                obj.asal_perolehan = "Isian tersembunyi"
                obj.save(update_fields=["bervolume"])
                obj.refresh_from_db()
                self.assertEqual(obj.asal_perolehan, "")

    def test_form_detail_dan_qr_menampilkan_asal(self):
        for form_class, _model, key, _validate in CASES:
            with self.subTest(key=key):
                form = form_class(data=self._data(form_class))
                self.assertTrue(form.is_valid(), form.errors)
                obj = form.save()
                response = self.client.get(reverse(f"master_data:edit_{key}", args=[obj.pk]))
                self.assertContains(response, 'name="asal_perolehan"')
                self.assertContains(response, 'value="Pengadaan APBN"')
                groups = response.context["field_groups"]
                self.assertTrue(any(
                    ["tahun_perolehan", "asal_perolehan", "kondisi_barang"] in rows
                    for _title, rows in groups
                ))
                for url in (
                    reverse(f"master_data:detail_{key}", args=[obj.pk]),
                    reverse(f"master_data:public_{key}", args=[obj.qr_token]),
                ):
                    self.assertContains(self.client.get(url), "Pengadaan APBN")

    def test_export_dan_import_menjaga_asal_perolehan(self):
        for form_class, model, key, validate in CASES:
            with self.subTest(key=key):
                form = form_class(data=self._data(form_class, status_barang="Non BMN"))
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                response = self.client.get(reverse(f"master_data:export_{key}"))
                self.assertEqual(response.status_code, 200)
                workbook = load_workbook(BytesIO(response.content))
                sheet = workbook.active
                columns = {cell.value: cell.column for cell in sheet[1]}
                self.assertEqual(sheet.cell(2, columns["Asal Perolehan"]).value, "Pengadaan APBN")
                sheet.cell(2, columns["Kode Laboratorium"]).value = f"IMP-{key}"
                sheet.cell(2, columns["Kode Aset BMN"]).value = f"BMN-IMP-{key}"
                rows, errors = validate(self._upload(workbook))
                self.assertEqual(errors, [])
                self.assertEqual(rows[0]["asal_perolehan"], "Pengadaan APBN")
                count, errors = _save_import_objects(rows, model)
                self.assertEqual((count, errors), (1, []))
                self.assertEqual(model.objects.get(kode_laboratorium=f"IMP-{key}").asal_perolehan, "Pengadaan APBN")

    def test_format_baru_dan_format_lama_tanpa_kolom_asal(self):
        for _form, _model, key, validate in CASES:
            with self.subTest(key=key):
                response = self.client.get(reverse(f"master_data:download_format_import_{key}"))
                self.assertEqual(response.status_code, 200)
                workbook = load_workbook(BytesIO(response.content))
                sheet = workbook.active
                columns = {cell.value: cell.column for cell in sheet[1]}
                column = columns["Asal Perolehan"]
                self.assertEqual(column, columns["Tahun Perolehan"] + 1)
                self.assertEqual(sheet.cell(2, column).value, "Pengadaan")
                sheet.cell(2, column).value = "A" * 201
                _rows, errors = validate(self._upload(workbook))
                self.assertTrue(any("Asal Perolehan maksimal" in error for error in errors))
                sheet.delete_cols(column)
                rows, errors = validate(self._upload(workbook))
                self.assertEqual(errors, [])
                self.assertEqual(rows[0]["asal_perolehan"], "")
