from copy import deepcopy
from datetime import date
from importlib import import_module
from io import BytesIO
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from apps.pengguna.models import Role, User

from apps.operasional.forms import InstansiKlienForm
from apps.operasional.views import IMPORT_INSTANSI_HEADERS, _validate_instansi_import


class OrganisasiTests(TestCase):
    def test_form_menerima_sda_dan_bat_menolak_pu(self):
        for organisasi in ("Internal SDA", "Eksternal SDA", "Internal BAT", "Internal PU", "Eksternal PU"):
            with self.subTest(organisasi=organisasi):
                form = InstansiKlienForm(data={
                    "nama_instansi": "Instansi Uji",
                    "alamat_instansi": "Alamat Uji",
                    "organisasi": organisasi,
                })
                self.assertEqual(form.is_valid(), "PU" not in organisasi, form.errors)
                if "PU" in organisasi:
                    self.assertIn("organisasi", form.errors)

    def test_import_instansi_memvalidasi_kategori_baru(self):
        for organisasi in ("Internal SDA", "Eksternal SDA", "Internal BAT", "Internal PU", "Eksternal PU"):
            with self.subTest(organisasi=organisasi):
                workbook = Workbook()
                workbook.active.append(IMPORT_INSTANSI_HEADERS)
                workbook.active.append(["Instansi Uji", "Alamat Uji", organisasi])
                upload = BytesIO()
                workbook.save(upload)
                rows, errors = _validate_instansi_import(
                    SimpleUploadedFile("instansi.xlsx", upload.getvalue())
                )
                if "PU" in organisasi:
                    self.assertEqual(rows, [])
                    self.assertTrue(any("Organisasi tidak sesuai" in error for error in errors))
                else:
                    self.assertEqual(errors, [])
                    self.assertEqual(rows[0]["organisasi"], organisasi)

    def test_format_excel_instansi_dan_riwayat_memakai_sda(self):
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        user = User.objects.create_user(username="uji-organisasi")
        user.safe_profile.role = role
        user.safe_profile.save(update_fields=["role"])
        self.client.force_login(user)

        for url, sheet_name, header in (
            ("operasional:download_format_import_instansi", "Format Import Instansi", "Organisasi"),
            ("peminjaman:download_format_import_riwayat_peminjaman", "Peminjaman", "Organisasi Instansi"),
        ):
            with self.subTest(url=url):
                response = self.client.get(reverse(url))
                self.assertEqual(response.status_code, 200)
                workbook = load_workbook(BytesIO(response.content))
                worksheet = workbook[sheet_name]
                column = next(cell.column for cell in worksheet[1] if cell.value == header)
                self.assertEqual(worksheet.cell(row=2, column=column).value, "Eksternal SDA")
                validator = next(
                    rule for rule in worksheet.data_validations.dataValidation
                    if worksheet.cell(row=2, column=column).coordinate in rule.sqref
                )
                self.assertEqual(validator.formula1, '"Internal SDA,Eksternal SDA,Internal BAT"')

    def test_migrasi_menjaga_relasi_snapshot_dan_dapat_diulang(self):
        migration = import_module("apps.operasional.migrations.0005_organisasi_sda")
        state = MigrationLoader(connection).project_state([
            ("operasional", "0005_organisasi_sda"),
        ])
        Instansi = state.apps.get_model("operasional", "InstansiKlien")
        Request = state.apps.get_model("peminjaman", "PeminjamanRequest")
        user = User.objects.create_user(username="uji-migrasi-organisasi")
        records = []
        for index, organisasi in enumerate((
            "Internal PU", "Eksternal PU", "Internal BAT", "Internal SDA", "Eksternal SDA",
        )):
            instansi = Instansi.objects.create(
                nama_instansi=f"Instansi {index}", alamat_instansi="Alamat Uji", organisasi=organisasi,
            )
            snapshot = {
                "kegiatan": {"organisasi_instansi": organisasi, "instansi_tujuan": instansi.nama_instansi},
                "peminjam": {"nama": "Pengguna Historis"},
                "items": {"lab": [{"nama_barang": "Alat Historis"}]},
            }
            obj = Request.objects.create(
                nomor_pengajuan=f"PMJ-260714-{index + 1:03d}",
                peminjam_id=user.pk, instansi_tujuan_id=instansi.pk,
                tanggal_mulai=date(2026, 7, 14), tanggal_selesai=date(2026, 7, 15),
                report_snapshot=snapshot,
            )
            records.append((instansi, obj, deepcopy(snapshot), obj.updated_at))

        editor = SimpleNamespace(connection=connection)
        migration.forwards(state.apps, editor)
        migration.forwards(state.apps, editor)
        for instansi, obj, snapshot, updated_at in records:
            instansi.refresh_from_db()
            obj.refresh_from_db()
            old_value = snapshot["kegiatan"]["organisasi_instansi"]
            expected = migration.RENAMES.get(old_value, old_value)
            snapshot["kegiatan"]["organisasi_instansi"] = expected
            self.assertEqual(instansi.organisasi, expected)
            self.assertEqual(obj.instansi_tujuan_id, instansi.pk)
            self.assertEqual(obj.report_snapshot, snapshot)
            self.assertEqual(obj.updated_at, updated_at)

        migration.backwards(state.apps, editor)
        for instansi, obj, _snapshot, _updated_at in records:
            instansi.refresh_from_db()
            obj.refresh_from_db()
            self.assertNotIn(instansi.organisasi, migration.RENAMES.values())
            self.assertEqual(obj.report_snapshot["kegiatan"]["organisasi_instansi"], instansi.organisasi)
