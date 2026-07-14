from datetime import date
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps as django_apps
from django.db import connection
from django.test import TestCase

from apps.operasional.forms import SurveiKegiatanForm
from apps.operasional.models import SurveiKegiatan
from apps.peminjaman.import_riwayat import _find_survei
from apps.peminjaman.models import PeminjamanRequest
from apps.pengguna.models import User


class MergeBoreholeSurveiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="uji-borehole",
            password="test-password",
        )
        self.migration = import_module(
            "apps.peminjaman.migrations.0019_merge_borehole_survei"
        )
        self.schema_editor = SimpleNamespace(connection=connection)

    def _pengajuan(self, suffix, snapshot_items):
        return PeminjamanRequest.objects.create(
            nomor_pengajuan=f"PMJ-260714-{suffix}",
            peminjam=self.user,
            nama_peminjam="Pengguna Uji",
            tanggal_mulai=date(2026, 7, 14),
            tanggal_selesai=date(2026, 7, 15),
            report_snapshot={
                "kegiatan": {"kegiatan_survei": snapshot_items}
            },
        )

    def test_merge_memindahkan_relasi_dan_snapshot_tanpa_duplikasi(self):
        source = SurveiKegiatan.objects.create(jenis_survei="Borehole")
        target = SurveiKegiatan.objects.create(jenis_survei="Borehole Camera")
        source_only = self._pengajuan("001", ["Borehole", "Drone"])
        target_only = self._pengajuan("002", ["Borehole Camera"])
        both = self._pengajuan(
            "003",
            ["Borehole", "Borehole Camera", "Logging"],
        )
        source_only.kegiatan_survei.add(source)
        target_only.kegiatan_survei.add(target)
        both.kegiatan_survei.add(source, target)

        self.migration.merge_borehole_survei(
            django_apps,
            self.schema_editor,
        )

        self.assertFalse(
            SurveiKegiatan.objects.filter(jenis_survei="Borehole").exists()
        )
        for obj in (source_only, target_only, both):
            self.assertEqual(
                list(obj.kegiatan_survei.values_list("jenis_survei", flat=True)),
                ["Borehole Camera"],
            )

        source_only.refresh_from_db()
        target_only.refresh_from_db()
        both.refresh_from_db()
        self.assertEqual(
            source_only.report_snapshot["kegiatan"]["kegiatan_survei"],
            ["Borehole Camera", "Drone"],
        )
        self.assertEqual(
            target_only.report_snapshot["kegiatan"]["kegiatan_survei"],
            ["Borehole Camera"],
        )
        self.assertEqual(
            both.report_snapshot["kegiatan"]["kegiatan_survei"],
            ["Borehole Camera", "Logging"],
        )

    def test_merge_mengganti_nama_jika_target_belum_ada(self):
        source = SurveiKegiatan.objects.create(jenis_survei="Borehole")
        obj = self._pengajuan("004", ["Borehole"])
        obj.kegiatan_survei.add(source)

        self.migration.merge_borehole_survei(
            django_apps,
            self.schema_editor,
        )

        source.refresh_from_db()
        obj.refresh_from_db()
        self.assertEqual(source.jenis_survei, "Borehole Camera")
        self.assertEqual(
            list(obj.kegiatan_survei.values_list("jenis_survei", flat=True)),
            ["Borehole Camera"],
        )
        self.assertEqual(
            obj.report_snapshot["kegiatan"]["kegiatan_survei"],
            ["Borehole Camera"],
        )

    def test_form_menormalkan_alias_borehole(self):
        form = SurveiKegiatanForm(data={"jenis_survei": "Borehole"})

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["jenis_survei"], "Borehole Camera")

    def test_form_menolak_alias_jika_target_sudah_ada(self):
        SurveiKegiatan.objects.create(jenis_survei="Borehole Camera")
        form = SurveiKegiatanForm(data={"jenis_survei": "Borehole"})

        self.assertFalse(form.is_valid())
        self.assertIn("jenis_survei", form.errors)

    def test_import_riwayat_memakai_nama_kanonis(self):
        target = SurveiKegiatan.objects.create(
            jenis_survei="Borehole Camera"
        )

        result = _find_survei(["Borehole"])

        self.assertEqual(result, [target])
        self.assertEqual(SurveiKegiatan.objects.count(), 1)
