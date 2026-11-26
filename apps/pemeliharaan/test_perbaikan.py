from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from openpyxl import load_workbook

from apps.master_data.models import BarangLaboratorium, KondisiBarangChoices
from apps.notifikasi.models import Notification, NotificationCategory
from apps.pengguna.models import Role, User
from .forms import PemeliharaanForm
from .views import _can_send_pengajuan, _get_pengajuan_queryset, _get_report_queryset
from .models import (
    JenisFotoPemeliharaanChoices as Foto,
    KondisiPemeliharaanChoices as Kondisi,
    MetodePerbaikanChoices as Metode,
    PemeliharaanFoto,
    PemeliharaanItem,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices as Step,
    TindakanPerbaikanChoices as Tindakan,
)


class PerbaikanFlowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        media = cls.enterClassContext(TemporaryDirectory())
        cls.enterClassContext(override_settings(MEDIA_ROOT=media))
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for key, role in (("owner", "Admin Lab"), ("other", "Admin Lab"), ("head", "Kepala Lab"), ("super", "Super Admin")):
            user = User.objects.create_user(username=f"repair-{key}")
            user.safe_profile.role, _ = Role.objects.get_or_create(nama=role)
            user.safe_profile.save(update_fields=["role"])
            cls.users[key] = user
        with patch("apps.master_data.signals.ensure_master_qr_code"):
            cls.alat = BarangLaboratorium.objects.create(
                nama_barang="Alat Perbaikan", kode_laboratorium="REPAIR-01",
                komponen_pemeliharaan=["Sensor", "Baterai"],
            )

    def image(self, name="foto.png"):
        output = BytesIO()
        Image.new("RGB", (10, 10), "white").save(output, "PNG")
        return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")

    def draft(self, action=Tindakan.LANJUTAN, mixed=False):
        obj = PemeliharaanPengajuan.objects.create(pemohon=self.users["owner"], alat=self.alat)
        for index, component in enumerate(self.alat.komponen_pemeliharaan):
            selected = Tindakan.LANGSUNG if mixed and index == 1 else action
            item = PemeliharaanItem.objects.create(
                pengajuan=obj, komponen=component, kondisi=Kondisi.PERLU_PERBAIKAN,
                tindakan_perbaikan=selected,
                uraian_perbaikan="Perbaikan langsung selesai" if selected == Tindakan.LANGSUNG else "",
                uraian_kerusakan="Sensor rusak" if selected == Tindakan.LANJUTAN else "",
                tanggal_mulai_perbaikan=obj.tanggal_pemeriksaan if selected == Tindakan.LANGSUNG else None,
                tanggal_selesai_perbaikan=obj.tanggal_pemeriksaan + timedelta(hours=1) if selected == Tindakan.LANGSUNG else None,
            )
            for kind in (Foto.PEMERIKSAAN, Foto.PERBAIKAN if selected == Tindakan.LANGSUNG else Foto.KERUSAKAN):
                if kind != Foto.PEMERIKSAAN or index == 0:
                    PemeliharaanFoto.objects.create(item=item, jenis=kind, foto=self.image())
        obj.tandai_alat_dalam_pemeliharaan()
        return obj

    def send(self, obj):
        self.client.force_login(self.users["owner"])
        response = self.client.post(reverse("pemeliharaan:kirim", args=[obj.pk]))
        self.assertRedirects(response, reverse("pemeliharaan:list"), fetch_redirect_response=False)
        obj.refresh_from_db()

    def approve(self, obj, method=Metode.MANDIRI):
        self.client.force_login(self.users["head"])
        response = self.client.post(reverse("verifikasi:detail_pemeliharaan", args=[obj.pk]), {
            "aksi": "setujui", "metode_perbaikan": method,
        })
        self.assertRedirects(response, reverse("verifikasi:index"), fetch_redirect_response=False)
        obj.refresh_from_db()

    def repair_data(self, count=2):
        data = {}
        for index in range(count):
            data.update({
                f"uraian_perbaikan_{index}": "Sensor diperbaiki dan diuji.",
                f"tanggal_selesai_perbaikan_{index}": timezone.localdate().isoformat(),
                f"dokumentasi_perbaikan_{index}": self.image(),
            })
        return data

    def test_initial_choices_and_old_values_are_rejected(self):
        self.client.force_login(self.users["owner"])
        response = self.client.get(reverse("pemeliharaan:tambah"))
        self.assertNotContains(response, '<option value="Perbaikan Mandiri"')
        form = PemeliharaanForm({
            "pilih_alat": self.alat.pk, "tanggal_pemeriksaan": timezone.localdate().isoformat(),
            "kondisi_0": Kondisi.PERLU_PERBAIKAN, "tindakan_0": Metode.MANDIRI,
            "kondisi_1": Kondisi.BAIK, "dokumentasi_pemeriksaan": self.image(),
        }, actor=self.users["owner"])
        self.assertFalse(form.is_valid())
        self.assertIn("Tindakan perbaikan wajib dipilih", str(form.component_errors))

    def test_direct_finishes_on_send_and_updates_equipment(self):
        obj = self.draft(Tindakan.LANGSUNG)
        self.send(obj)
        self.assertEqual(obj.current_step, Step.SELESAI)
        self.assertEqual(obj.metode_perbaikan, "")
        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, KondisiBarangChoices.BAIK)
        self.assertEqual(self.alat.tanggal_perbaikan, timezone.localdate())
        self.assertFalse(Notification.objects.filter(source_pemeliharaan=obj, category=NotificationCategory.VERIFICATION).exists())

    def test_incomplete_draft_cannot_skip_validation_by_posting_send(self):
        obj = self.draft(Tindakan.LANGSUNG)
        obj.items.filter(komponen="Sensor").update(uraian_perbaikan="")
        self.client.force_login(self.users["owner"])
        response = self.client.post(reverse("pemeliharaan:kirim", args=[obj.pk]))
        self.assertRedirects(response, reverse("pemeliharaan:edit", args=[obj.pk]), fetch_redirect_response=False)
        obj.refresh_from_db()
        self.assertEqual(obj.current_step, Step.DRAFT)

    def test_head_must_select_valid_method_and_repeated_approval_is_blocked(self):
        obj = self.draft()
        self.send(obj)
        self.client.force_login(self.users["head"])
        before = obj.timeline_entries.count()
        for method in ("", Tindakan.LANGSUNG, "invalid"):
            response = self.client.post(reverse("verifikasi:detail_pemeliharaan", args=[obj.pk]), {
                "aksi": "setujui", "metode_perbaikan": method,
            })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors.get("metode_perbaikan"))
            self.assertTrue(response.context["open_action_modal"])
            self.assertContains(response, '<div class="form-group has-error">')
            self.assertContains(response, 'class="input-error-text verify-note-error"')
            obj.refresh_from_db()
            self.assertEqual(obj.current_step, Step.KEPALA_LAB)
            self.assertEqual(obj.timeline_entries.count(), before)
        self.approve(obj)
        after = obj.timeline_entries.count()
        self.client.post(reverse("verifikasi:detail_pemeliharaan", args=[obj.pk]), {"aksi": "setujui", "metode_perbaikan": Metode.EKSTERNAL})
        self.assertEqual(obj.timeline_entries.count(), after)

    def test_manual_lifecycle_preserves_direct_repair_and_damage_documents(self):
        obj = self.draft(mixed=True)
        direct = obj.items.get(komponen="Baterai")
        damage_ids = set(PemeliharaanFoto.objects.filter(item__pengajuan=obj, jenis=Foto.KERUSAKAN).values_list("pk", flat=True))
        self.send(obj)
        self.approve(obj)
        self.assertEqual(obj.current_step, Step.PERBAIKAN_MANDIRI)
        obj.kepala_lab_at = timezone.now() - timedelta(days=400)
        obj.save(update_fields=["kepala_lab_at"])
        pending = Notification.objects.get(source_pemeliharaan=obj, recipient=self.users["owner"], category=NotificationCategory.VERIFICATION, is_read=False)
        self.assertEqual(pending.link_url, reverse("pemeliharaan:perbaikan", args=[obj.pk]))
        self.client.force_login(self.users["owner"])
        response = self.client.get(reverse("pemeliharaan:perbaikan", args=[obj.pk]))
        self.assertContains(response, "Uraian Perbaikan")
        self.assertContains(response, '<button type="submit" class="btn btn-primary">Simpan</button>', html=True)
        self.assertNotContains(response, '<button type="submit" class="btn btn-primary">Kirim</button>', html=True)
        self.assertNotContains(response, 'name="tindakan_0"')
        listing = self.client.get(reverse("pemeliharaan:list"))
        self.assertContains(listing, "Input Perbaikan Mandiri")
        self.assertFalse(next(row for row in listing.context["items"] if row.pk == obj.pk).can_kirim)
        self.assertContains(listing, 'disabled title="Lengkapi dan simpan data perbaikan mandiri sebelum mengirim pengajuan"')
        detail = self.client.get(reverse("pemeliharaan:detail", args=[obj.pk]))
        self.assertTrue(detail.context["show_submit_pengajuan"])
        self.assertFalse(detail.context["can_submit_pengajuan"])
        self.assertContains(detail, 'disabled title="Lengkapi dan simpan data perbaikan mandiri sebelum mengirim pengajuan"')
        response = self.client.post(reverse("pemeliharaan:perbaikan", args=[obj.pk]), self.repair_data(1))
        if response.status_code == 200:
            self.fail((response.context["form"].errors, response.context["form"].component_errors))
        self.assertRedirects(response, reverse("pemeliharaan:detail", args=[obj.pk]), fetch_redirect_response=False)
        obj.refresh_from_db()
        self.assertEqual(obj.current_step, Step.PERBAIKAN_MANDIRI)
        self.assertTrue(obj.perbaikan_lengkap)
        pending.refresh_from_db()
        self.assertFalse(pending.is_read)
        self.assertFalse(Notification.objects.filter(source_pemeliharaan=obj, category=NotificationCategory.STATUS).exists())
        self.alat.refresh_from_db()
        self.assertEqual(self.alat.kondisi_barang, KondisiBarangChoices.DALAM_PEMELIHARAAN)
        listing = self.client.get(reverse("pemeliharaan:list"))
        self.assertTrue(next(row for row in listing.context["items"] if row.pk == obj.pk).can_kirim)
        self.assertContains(listing, 'data-send-url="%s"' % reverse("pemeliharaan:kirim", args=[obj.pk]))
        detail = self.client.get(reverse("pemeliharaan:detail", args=[obj.pk]))
        self.assertTrue(detail.context["can_submit_pengajuan"])
        self.assertContains(detail, 'data-send-url="%s"' % reverse("pemeliharaan:kirim", args=[obj.pk]))
        self.send(obj)
        obj.refresh_from_db()
        self.assertEqual(obj.current_step, Step.SELESAI)
        self.assertEqual(obj.kepala_lab_by, self.users["head"])
        self.assertEqual(obj.kepala_lab_status, "approved")
        self.assertEqual(obj.items.get(komponen="Sensor").tanggal_mulai_perbaikan, obj.tanggal_pemeriksaan)
        direct.refresh_from_db()
        self.assertEqual(direct.uraian_perbaikan, "Perbaikan langsung selesai")
        self.assertEqual(PemeliharaanFoto.objects.filter(pk__in=damage_ids).count(), len(damage_ids))
        pending.refresh_from_db()
        self.assertTrue(pending.is_read)
        self.assertEqual(self.client.get(reverse("pemeliharaan:download_pdf", args=[obj.pk])).status_code, 200)
        dashboard = self.client.get(reverse("dashboard:index"))
        self.assertNotIn(obj.pk, {item.pk for item in dashboard.context["active_pemeliharaan"]})
        report = _get_report_queryset(self.users["super"]).get(pk=obj.pk)
        self.assertEqual(report.report_at, obj.updated_at)
        self.client.force_login(self.users["super"])
        exported = self.client.get(reverse("pemeliharaan:laporan_export"))
        self.assertEqual(exported.status_code, 200)
        workbook = load_workbook(BytesIO(exported.content), data_only=True)
        for title in ("Laporan Pemeliharaan", "Detail Komponen"):
            sheet = workbook[title]
            self.assertEqual(sheet.cell(1, sheet.max_column).value, "Metode Perbaikan")
            self.assertEqual(sheet.cell(2, sheet.max_column).value, Metode.MANDIRI)

    def test_manual_requires_complete_data_and_valid_dates_photos(self):
        obj = self.draft()
        self.send(obj)
        self.approve(obj)
        self.client.force_login(self.users["owner"])
        for field, value, message in (
            ("uraian_perbaikan_0", "", "Uraian Perbaikan wajib diisi"),
            ("tanggal_selesai_perbaikan_0", "01 Jan 2000", "tidak boleh lebih awal"),
            ("dokumentasi_perbaikan_0", [self.image(f"{i}.png") for i in range(4)], "maksimal 3 foto"),
        ):
            data = self.repair_data()
            data[field] = value
            response = self.client.post(reverse("pemeliharaan:perbaikan", args=[obj.pk]), data)
            self.assertEqual(response.status_code, 200)
            self.assertIn(message, str(response.context["form"].component_errors[0]["perbaikan"]))
            obj.refresh_from_db()
            self.assertEqual(obj.current_step, Step.PERBAIKAN_MANDIRI)
            self.assertFalse(obj.items.exclude(uraian_perbaikan="").exists())
        response = self.client.post(reverse("pemeliharaan:kirim", args=[obj.pk]))
        self.assertRedirects(response, reverse("pemeliharaan:perbaikan", args=[obj.pk]), fetch_redirect_response=False)

    def test_manual_ownership_and_immutable_fields(self):
        obj = self.draft()
        self.send(obj)
        self.approve(obj)
        self.client.force_login(self.users["other"])
        response = self.client.post(reverse("pemeliharaan:perbaikan", args=[obj.pk]), self.repair_data())
        self.assertRedirects(response, reverse("dashboard:index"), fetch_redirect_response=False)
        self.client.force_login(self.users["owner"])
        response = self.client.get(reverse("pemeliharaan:edit", args=[obj.pk]))
        self.assertRedirects(response, reverse("dashboard:index"), fetch_redirect_response=False)
        data = self.repair_data()
        data.update(pilih_alat="999999", tanggal_pemeriksaan="01 Jan 2000", kondisi_0=Kondisi.BAIK, tindakan_0=Tindakan.LANGSUNG)
        response = self.client.post(reverse("pemeliharaan:perbaikan", args=[obj.pk]), data)
        if response.status_code == 200:
            self.fail((response.context["form"].errors, response.context["form"].component_errors))
        obj.refresh_from_db()
        self.assertEqual(obj.current_step, Step.PERBAIKAN_MANDIRI)
        self.assertEqual(obj.alat_id, self.alat.pk)
        self.assertEqual(obj.items.get(komponen="Sensor").tindakan_perbaikan, Tindakan.LANJUTAN)
        self.assertEqual(timezone.localdate(obj.tanggal_pemeriksaan), timezone.localdate())

    def test_manual_readiness_rechecks_all_saved_fields_before_send(self):
        obj = self.draft()
        self.send(obj)
        self.approve(obj)
        self.client.force_login(self.users["owner"])
        self.client.post(reverse("pemeliharaan:perbaikan", args=[obj.pk]), self.repair_data())
        obj.refresh_from_db()
        self.assertTrue(_can_send_pengajuan(self.users["owner"], obj))
        self.assertFalse(_can_send_pengajuan(self.users["other"], obj))
        item = obj.items.get(komponen="Baterai")
        for field, value in (
            ("uraian_perbaikan", "   "),
            ("tanggal_mulai_perbaikan", None),
            ("tanggal_selesai_perbaikan", None),
            ("tanggal_selesai_perbaikan", obj.tanggal_pemeriksaan - timedelta(days=1)),
        ):
            with self.subTest(field=field, value=value):
                PemeliharaanItem.objects.filter(pk=item.pk).update(**{field: value})
                self.assertFalse(_can_send_pengajuan(self.users["owner"], obj))
                response = self.client.post(reverse("pemeliharaan:kirim", args=[obj.pk]))
                self.assertRedirects(response, reverse("pemeliharaan:perbaikan", args=[obj.pk]), fetch_redirect_response=False)
                obj.refresh_from_db()
                self.assertEqual(obj.current_step, Step.PERBAIKAN_MANDIRI)
                PemeliharaanItem.objects.filter(pk=item.pk).update(**{field: getattr(item, field)})
        item.fotos.filter(jenis=Foto.PERBAIKAN).delete()
        self.assertFalse(_can_send_pengajuan(self.users["owner"], obj))
        self.client.post(reverse("pemeliharaan:kirim", args=[obj.pk]))
        obj.refresh_from_db()
        self.assertEqual(obj.current_step, Step.PERBAIKAN_MANDIRI)

    def test_send_readiness_uses_prefetched_rows_without_queries_per_request(self):
        obj = self.draft()
        self.send(obj)
        self.approve(obj)
        self.client.force_login(self.users["owner"])
        self.client.post(reverse("pemeliharaan:perbaikan", args=[obj.pk]), self.repair_data())

        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                rows = list(_get_pengajuan_queryset())
                self.assertTrue(all(_can_send_pengajuan(self.users["owner"], row) for row in rows))
            return len(queries)

        initial = count_queries()
        for _ in range(3):
            extra = PemeliharaanPengajuan.objects.create(
                pemohon=self.users["owner"], current_step=Step.PERBAIKAN_MANDIRI, metode_perbaikan=Metode.MANDIRI,
            )
            item = PemeliharaanItem.objects.create(
                pengajuan=extra, komponen="Sensor", kondisi=Kondisi.PERLU_PERBAIKAN,
                tindakan_perbaikan=Tindakan.LANJUTAN, uraian_perbaikan="Selesai diperbaiki",
                tanggal_mulai_perbaikan=extra.tanggal_pemeriksaan, tanggal_selesai_perbaikan=extra.tanggal_pemeriksaan,
            )
            PemeliharaanFoto.objects.create(item=item, jenis=Foto.PERBAIKAN, foto=self.image())
        self.assertEqual(count_queries(), initial)

    def test_reject_and_revision_ignore_repair_method_and_render_it_hidden(self):
        obj = self.draft()
        self.send(obj)
        self.client.force_login(self.users["head"])
        for action, step in (("tolak", Step.DITOLAK), ("perbaiki", Step.DIKEMBALIKAN)):
            with self.subTest(action=action):
                obj.current_step = Step.KEPALA_LAB
                obj.save(update_fields=["current_step"])
                response = self.client.post(reverse("verifikasi:detail_pemeliharaan", args=[obj.pk]), {"aksi": action})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<div data-repair-method hidden>', html=False)
                self.assertNotContains(response, "Metode Perbaikan (Wajib)")
                self.assertNotIn("metode_perbaikan", response.context["form"].errors)
                response = self.client.post(reverse("verifikasi:detail_pemeliharaan", args=[obj.pk]), {
                    "aksi": action, "catatan": "Catatan tindak lanjut", "metode_perbaikan": "irrelevant-value",
                })
                self.assertRedirects(response, reverse("verifikasi:index"), fetch_redirect_response=False)
                obj.refresh_from_db()
                self.assertEqual(obj.current_step, step)

    def test_manual_cannot_delete_examination_photos_and_remains_active(self):
        obj = self.draft()
        self.send(obj)
        self.approve(obj)
        self.client.force_login(self.users["owner"])
        data = self.repair_data()
        photo = PemeliharaanFoto.objects.filter(item__pengajuan=obj, jenis=Foto.PEMERIKSAAN).get()
        data["hapus_foto_ids"] = [str(photo.pk)]
        response = self.client.post(reverse("pemeliharaan:perbaikan", args=[obj.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("hapus_foto_ids", response.context["form"].errors)
        self.assertTrue(PemeliharaanFoto.objects.filter(pk=photo.pk).exists())
        with self.assertRaises(IntegrityError), transaction.atomic():
            PemeliharaanPengajuan.objects.create(pemohon=self.users["other"], alat=self.alat)

    def test_external_method_continues_to_existing_pimpinan_flow(self):
        obj = self.draft()
        self.send(obj)
        self.approve(obj, Metode.EKSTERNAL)
        self.assertEqual(obj.current_step, Step.PIMPINAN)
        self.assertTrue(obj.perlu_pimpinan)
        self.client.force_login(self.users["owner"])
        response = self.client.get(reverse("pemeliharaan:perbaikan", args=[obj.pk]))
        self.assertRedirects(response, reverse("dashboard:index"), fetch_redirect_response=False)


class PerbaikanMigrationTests(TransactionTestCase):
    def test_existing_actions_documents_and_approved_external_route_are_preserved(self):
        before = [("pemeliharaan", "0007_pemeliharaanvendor_and_more")]
        after = [("pemeliharaan", "0008_alur_perbaikan")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            old = executor.loader.project_state(before).apps
            user = old.get_model("pengguna", "User").objects.create(username="repair-migration", password="")
            Request = old.get_model("pemeliharaan", "PemeliharaanPengajuan")
            Item = old.get_model("pemeliharaan", "PemeliharaanItem")
            Photo = old.get_model("pemeliharaan", "PemeliharaanFoto")
            direct = Request.objects.create(pemohon_id=user.pk, nomor_pengajuan="OLD-DIRECT", current_step="selesai")
            item = Item.objects.create(pengajuan_id=direct.pk, komponen="Sensor", tindakan_perbaikan="Perbaikan Mandiri", uraian_perbaikan="Riwayat tetap", tanggal_selesai_perbaikan=timezone.now())
            photo = Photo.objects.create(item_id=item.pk, jenis="perbaikan", foto="pemeliharaan/history.png")
            for stage in ("kepala_lab", "vendor_draft", "selesai"):
                obj = Request.objects.create(pemohon_id=user.pk, nomor_pengajuan=f"OLD-{stage}", current_step=stage)
                Item.objects.create(pengajuan_id=obj.pk, komponen="Sensor", tindakan_perbaikan="Perbaikan Eksternal", uraian_kerusakan="Data lama")
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            NewItem = current.get_model("pemeliharaan", "PemeliharaanItem")
            NewRequest = current.get_model("pemeliharaan", "PemeliharaanPengajuan")
            converted = NewItem.objects.get(pk=item.pk)
            self.assertEqual(converted.tindakan_perbaikan, Tindakan.LANGSUNG)
            self.assertEqual(converted.uraian_perbaikan, "Riwayat tetap")
            self.assertEqual(current.get_model("pemeliharaan", "PemeliharaanFoto").objects.get(pk=photo.pk).foto.name, "pemeliharaan/history.png")
            self.assertEqual(NewRequest.objects.get(nomor_pengajuan="OLD-kepala_lab").metode_perbaikan, "")
            for stage in ("vendor_draft", "selesai"):
                self.assertEqual(NewRequest.objects.get(nomor_pengajuan=f"OLD-{stage}").metode_perbaikan, Metode.EKSTERNAL)
                self.assertEqual(NewItem.objects.get(pengajuan__nomor_pengajuan=f"OLD-{stage}").tindakan_perbaikan, Tindakan.LANJUTAN)
        finally:
            MigrationExecutor(connection).migrate(after)
