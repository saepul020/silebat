from copy import deepcopy
from datetime import date, datetime
import json
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import load_workbook
from io import BytesIO

from apps.dashboard.views import build_dashboard_context, build_survey_equipment_chart
from apps.master_data.models import BarangLaboratorium, StatusBarangChoices
from apps.operasional.models import InstansiKlien, LayananKegiatan, SurveiKegiatan, TimKegiatan
from apps.pengguna.models import Role, User

from .models import (
    PeminjamanBarangLaboratorium, PeminjamanRequest, PengembalianBarangLaboratorium,
    ReturnItemStatusChoices, ReturnStepChoices, StepChoices,
)
from .views import _get_report_snapshot


class KoreksiLaporanTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory(prefix="silebat-koreksi-")
        self.addCleanup(media.cleanup)
        self.media_root = media.name
        settings = self.settings(MEDIA_ROOT=self.media_root)
        settings.enable()
        self.addCleanup(settings.disable)
        qr = patch("apps.master_data.signals.ensure_master_qr_code")
        qr.start()
        self.addCleanup(qr.stop)
        self.admin = self._user("super", "Super Admin")
        self.user = self._user("peminjam", "User")
        self.teknisi = self._user("teknisi", "Teknisi Lab")
        self.layanan = LayananKegiatan.objects.create(jenis_layanan="Air Baku")
        self.tim = TimKegiatan.objects.create(nama_tim="Tim Layanan Teknis")
        self.survei = SurveiKegiatan.objects.create(jenis_survei="Borehole Camera")
        self.instansi = InstansiKlien.objects.create(nama_instansi="Instansi A", organisasi="Internal SDA")
        self.obj = self._request()
        self.alat = self._alat("Alat A", "ALAT-A")
        self.alat_b = self._alat("Alat B", "ALAT-B")
        self.borrowed, self.returned = self._item(self.alat)
        self.obj.ensure_report_snapshot()
        # Unrelated imported content must survive correction without rebuilding it.
        self.obj.report_snapshot["items"]["bahan"] = [{"nama_barang": "Bahan historis", "qty_sisa": 3}]
        self.obj.save(update_fields=["report_snapshot", "updated_at"])
        self.url = reverse("peminjaman:laporan_koreksi", args=[self.obj.pk])
        self.client.force_login(self.admin)

    def _user(self, username, role):
        user = User.objects.create_user(username=username, first_name=username, email=f"{username}@example.com")
        user.safe_profile.role = Role.objects.get_or_create(nama=role)[0]
        user.safe_profile.save(update_fields=["role"])
        return user

    def _request(self):
        moment = timezone.make_aware(datetime(2026, 1, 3, 10))
        obj = PeminjamanRequest.objects.create(
            peminjam=self.user, nama_peminjam="Peminjam Lama", email_peminjam="lama@example.com",
            tanggal_mulai=date(2026, 1, 1), tanggal_selesai=date(2026, 1, 2),
            layanan_kegiatan=self.layanan, tim_kegiatan=self.tim, instansi_tujuan=self.instansi,
            current_step=StepChoices.APPROVED, return_current_step=ReturnStepChoices.COMPLETED,
            pimpinan_at=moment, return_started_at=moment, return_completed_at=moment,
            return_inventory_applied=True,
        )
        obj.kegiatan_survei.add(self.survei)
        return obj

    def _alat(self, nama, kode):
        return BarangLaboratorium.objects.create(
            nama_barang=nama, tipe_merek_barang="Tipe A", jenis_barang="Alat",
            status_barang=StatusBarangChoices.NON_BMN, kode_laboratorium=kode, tahun_perolehan=2020,
        )

    def _item(self, alat, obj=None):
        obj = obj or self.obj
        return (
            PeminjamanBarangLaboratorium.objects.create(pengajuan=obj, barang=alat),
            PengembalianBarangLaboratorium.objects.create(pengajuan=obj, barang=alat, note=f"Catatan {alat.nama_barang}"),
        )

    def _payload(self, filled=True):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = {}
        form = response.context["form"]
        for field in form:
            value = field.value()
            if filled and field.name not in ("versi", "berkas_pendukung"):
                value = form.previous[field.name]
                if hasattr(value, "values_list"):
                    value = list(value.values_list("pk", flat=True))
                elif hasattr(value, "pk"):
                    value = value.pk
            data[field.html_name] = value if isinstance(value, list) else str(value) if value is not None else ""
            if field.name == "kegiatan_survei" and not value:
                data[field.html_name] = []
        formset = response.context["formset"]
        data.update({f"alat-{key}": str(formset.management_form[key].value()) for key in (
            "TOTAL_FORMS", "INITIAL_FORMS", "MIN_NUM_FORMS", "MAX_NUM_FORMS",
        )})
        for alat_form in formset:
            for field in alat_form:
                if field.name == "DELETE":
                    continue
                value = alat_form.old_barang_id if filled and field.name == "barang" else field.value()
                data[field.html_name] = str(value) if value is not None else ""
        return data

    def _submit(self, data):
        response = self.client.post(self.url, data)
        if response.status_code != 302:
            self.fail(f"{response.context['form'].errors}; {response.context['formset'].errors}; {response.context['formset'].non_form_errors()}")
        self.obj.refresh_from_db()
        return response

    def test_correction_updates_transaction_snapshot_export_and_charts_without_inventory(self):
        old_stock = list(BarangLaboratorium.objects.order_by("pk").values())
        other_items = deepcopy(self.obj.report_snapshot["items"]["bahan"])
        data = self._payload()
        data.update({
            "peminjam": str(self.teknisi.pk), "nama_peminjam": "teknisi", "email_peminjam": "benar@example.com",
            "tanggal_mulai": "01 Jan 2025", "tanggal_selesai": "02 Jan 2025",
            "tanggal_persetujuan": "01 Jan 2025", "tanggal_pengembalian": "03 Jan 2025",
            "tanggal_selesai_pengembalian": "03 Jan 2025", "titik_borehole": "7",
            "alat-0-barang": str(self.alat_b.pk), "alat-0-snapshot_nama_barang": "Nilai palsu dari request",
        })
        self._submit(data)
        self.borrowed.refresh_from_db()
        self.returned.refresh_from_db()
        self.assertEqual(self.obj.peminjam_id, self.teknisi.pk)
        self.assertEqual(self.obj.total_hari, 2)
        self.assertEqual(self.obj.current_step, StepChoices.APPROVED)
        self.assertEqual(self.obj.return_current_step, ReturnStepChoices.COMPLETED)
        self.assertTrue(self.obj.return_inventory_applied)
        self.assertEqual(self.borrowed.barang_id, self.alat_b.pk)
        self.assertEqual(self.returned.barang_id, self.alat_b.pk)
        self.assertEqual(self.borrowed.snapshot_nama_barang, "Alat B")
        report = _get_report_snapshot(self.obj)
        self.assertEqual(report["peminjam"]["nama"], "teknisi")
        self.assertEqual(report["items"]["lab"][0]["nama_barang"], "Alat B")
        self.assertEqual(report["items"]["lab"][0]["catatan_pengembalian"], "Catatan Alat A")
        self.assertEqual(report["items"]["bahan"], other_items)
        self.assertEqual(next(x for x in report["pengukuran"] if x["key"] == "titik_borehole")["value"], 7)
        self.assertEqual(list(BarangLaboratorium.objects.order_by("pk").values()), old_stock)
        chart = build_survey_equipment_chart(2026)
        self.assertIn({"year": 2025, "barangId": self.alat_b.pk, "total": 1}, chart["rows"])
        ctx = build_dashboard_context()
        self.assertIn({"year": 2025, "pengukuranKey": "titik_borehole", "total": 7}, ctx["pengukuran_chart"]["yearRows"])
        audit = json.loads(self.obj.timeline_entries.get(stage="Koreksi Laporan").note)
        self.assertEqual(audit["sebelum"]["nama_peminjam"], "Peminjam Lama")
        self.assertEqual(audit["sesudah"]["nama_peminjam"], "teknisi")
        self.teknisi.refresh_from_db()
        self.assertEqual(self.teknisi.first_name, "teknisi")
        detail = self.client.get(reverse("peminjaman:laporan_detail", args=[self.obj.pk]))
        self.assertContains(detail, "Alat B")
        export = self.client.get(reverse("peminjaman:export_laporan_peminjaman"), {"tahun": "2025"})
        book = load_workbook(BytesIO(export.content), read_only=True)
        values = [value for sheet in book for row in sheet.values for value in row]
        self.assertIn("teknisi", values)
        self.assertIn("Alat B", values)
        book.close()
        with patch("apps.peminjaman.views.render_laporan_pdf") as render_pdf:
            self.client.get(reverse("peminjaman:download_laporan_pdf", args=[self.obj.pk]))
            self.assertEqual(render_pdf.call_args.args[2]["peminjam"]["nama"], "teknisi")

    def test_roles_status_and_anonymous_are_restricted(self):
        for actor in (self.user, self.teknisi):
            self.client.force_login(actor)
            for method in (self.client.get, self.client.post):
                self.assertRedirects(method(self.url), reverse("dashboard:index"), fetch_redirect_response=False)
            detail = self.client.get(reverse("peminjaman:laporan_detail", args=[self.obj.pk]))
            self.assertNotContains(detail, "Koreksi Data")
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.admin)
        self.obj.return_current_step = ReturnStepChoices.NONE
        self.obj.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {}).status_code, 404)

    def test_admin_entry_point_and_history_with_deleted_actor(self):
        detail = self.client.get(reverse("peminjaman:laporan_detail", args=[self.obj.pk]))
        self.assertContains(detail, self.url)
        self.obj.add_timeline("Koreksi Laporan", "Koreksi terdahulu", None, "Catatan historis")
        self.assertContains(self.client.get(self.url), "Pengguna dihapus")

    def test_form_count_limit_and_orphan_return_are_rejected(self):
        data = self._payload()
        data["alat-TOTAL_FORMS"] = "401"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["formset"].non_form_errors())
        PengembalianBarangLaboratorium.objects.create(pengajuan=self.obj, barang=self.alat_b)
        response = self.client.post(self.url, self._payload())
        self.assertContains(response, "tidak cocok dengan daftar pinjaman")
        self.assertFalse(self.obj.timeline_entries.filter(stage="Koreksi Laporan").exists())

    def test_invalid_fields_and_duplicate_master_leave_everything_unchanged(self):
        original = deepcopy(self.obj.report_snapshot)
        for changes in (
            {"peminjam": "999999999"}, {"titik_borehole": "-1"},
            {"tanggal_selesai": "31 Dec 2025"}, {"tanggal_persetujuan": "31 Dec 2025"},
            {"tanggal_selesai_pengembalian": "01 Jan 2026"},
            {"alat-INITIAL_FORMS": "0", "alat-TOTAL_FORMS": "0"},
        ):
            with self.subTest(changes=changes):
                data = self._payload()
                data.update(changes)
                response = self.client.post(self.url, data)
                self.assertEqual(response.status_code, 200)
                self.obj.refresh_from_db()
                self.assertEqual(self.obj.report_snapshot, original)
                self.assertFalse(self.obj.timeline_entries.filter(stage="Koreksi Laporan").exists())

    def test_stale_page_is_rejected(self):
        data = self._payload()
        self.obj.nama_peminjam = "Perubahan admin lain"
        self.obj.save()
        response = self.client.post(self.url, data)
        self.assertContains(response, "Data laporan sudah berubah")
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.nama_peminjam, "Perubahan admin lain")

    def test_date_limits_reject_each_invalid_sequence_without_saving(self):
        original = deepcopy(self.obj.report_snapshot)
        cases = (
            ({"tanggal_selesai": "31 Dec 2025"}, "tanggal_selesai"),
            ({"tanggal_persetujuan": "31 Dec 2025"}, "tanggal_persetujuan"),
            ({"tanggal_pengembalian": "01 Jan 2026"}, "tanggal_pengembalian"),
            ({"tanggal_selesai_pengembalian": "01 Jan 2026"}, "tanggal_selesai_pengembalian"),
            ({"tanggal_selesai_pengembalian": "02 Jan 2026"}, "tanggal_selesai_pengembalian"),
            ({"tanggal_selesai": "04 Jan 2026"}, "tanggal_pengembalian"),
            ({"tanggal_persetujuan": "04 Jan 2026"}, "tanggal_persetujuan"),
        )
        for changes, field in cases:
            with self.subTest(changes=changes):
                data = self._payload()
                data.update(changes)
                response = self.client.post(self.url, data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.obj.refresh_from_db()
                self.assertEqual(self.obj.report_snapshot, original)
                self.assertFalse(self.obj.timeline_entries.filter(stage="Koreksi Laporan").exists())

    def test_equal_dates_are_allowed_and_reason_is_no_longer_required(self):
        data = self._payload()
        for name in ("tanggal_mulai", "tanggal_selesai", "tanggal_persetujuan", "tanggal_pengembalian", "tanggal_selesai_pengembalian"):
            data[name] = "01 Jan 2026"
        response = self.client.get(self.url)
        for text in ("Alasan Koreksi", "Menentukan periode grafik tim", "Menentukan periode grafik pengukuran"):
            self.assertNotContains(response, text)
        self._submit(data)
        self.assertEqual(self.obj.total_hari, 1)
        entry = self.obj.timeline_entries.get(stage="Koreksi Laporan")
        self.assertEqual(entry.actor_id, self.admin.pk)
        self.assertIsNotNone(entry.created_at)
        self.assertEqual(set(json.loads(entry.note)), {"sebelum", "sesudah"})

    def test_master_or_other_rejects_double_and_switches_existing_selection(self):
        original = deepcopy(self.obj.report_snapshot)
        for selected, manual, pk in (("layanan_kegiatan", "layanan_kegiatan_lainnya", self.layanan.pk), ("instansi_tujuan", "instansi_tujuan_lainnya", self.instansi.pk)):
            data = self._payload(filled=False)
            data.update({selected: str(pk), manual: "Manual duplikat"})
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, 200)
            self.assertIn(selected, response.context["form"].errors)
            self.assertIn(manual, response.context["form"].errors)
            self.obj.refresh_from_db()
            self.assertEqual(self.obj.report_snapshot, original)
        data = self._payload(filled=False)
        data.update({"layanan_kegiatan_lainnya": "Layanan manual", "instansi_tujuan_lainnya": "Instansi manual"})
        self._submit(data)
        self.assertIsNone(self.obj.layanan_kegiatan_id)
        self.assertIsNone(self.obj.instansi_tujuan_id)
        self.assertEqual(self.obj.report_snapshot["kegiatan"]["layanan_kegiatan"], "Layanan manual")
        self.assertEqual(self.obj.report_snapshot["kegiatan"]["instansi_tujuan"], "Instansi manual")

    def test_foreign_item_id_is_rejected(self):
        other = self._request()
        borrowed, _ = self._item(self.alat, other)
        data = self._payload()
        data["alat-0-id"] = str(borrowed.pk)
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.obj.barang_laboratorium_items.filter(pk=self.borrowed.pk).exists())
        self.assertTrue(other.barang_laboratorium_items.filter(pk=borrowed.pk).exists())

    def test_normal_return_allows_delete_and_add_historical_tool(self):
        data = self._payload()
        data.update({"alat-0-DELETE": "on", "alat-TOTAL_FORMS": "2", "alat-1-barang": str(self.alat_b.pk)})
        self._submit(data)
        self.assertFalse(PeminjamanBarangLaboratorium.objects.filter(pk=self.borrowed.pk).exists())
        self.assertEqual(self.obj.barang_laboratorium_items.get().barang_id, self.alat_b.pk)
        self.assertEqual(self.obj.pengembalian_lab_items.get().barang_id, self.alat_b.pk)
        self.assertEqual(self.obj.report_snapshot["items"]["lab"][0]["nama_barang"], "Alat B")

    def test_two_links_can_be_swapped_and_duplicates_are_rejected(self):
        second, _ = self._item(self.alat_b)
        self.obj.ensure_report_snapshot()
        data = self._payload()
        data["alat-1-barang"] = str(self.alat.pk)
        self.assertContains(self.client.post(self.url, data), "Master alat yang sama")
        data["alat-0-barang"] = str(self.alat_b.pk)
        self._submit(data)
        self.borrowed.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.borrowed.barang_id, self.alat_b.pk)
        self.assertEqual(second.barang_id, self.alat.pk)

    def test_special_returns_keep_links_and_refresh_selected_master_snapshot(self):
        for status in (ReturnItemStatusChoices.RUSAK, ReturnItemStatusChoices.HILANG, ReturnItemStatusChoices.TRANSFER):
            PengembalianBarangLaboratorium.objects.filter(pk=self.returned.pk).update(status=status)
            data = self._payload()
            data["alat-0-barang"] = str(self.alat_b.pk)
            self.assertContains(self.client.post(self.url, data), "memerlukan rekonsiliasi")
            data = self._payload()
            data["alat-0-DELETE"] = "on"
            self.assertContains(self.client.post(self.url, data), "memerlukan rekonsiliasi")
        data = self._payload()
        data["alat-0-snapshot_nama_barang"] = "Nilai palsu"
        self._submit(data)
        self.assertEqual(self.obj.report_snapshot["items"]["lab"][0]["nama_barang"], self.alat.nama_barang)

    def test_incoming_transfer_blocks_relink(self):
        other = self._request()
        PengembalianBarangLaboratorium.objects.create(
            pengajuan=other, barang=self.alat, status=ReturnItemStatusChoices.TRANSFER, transfer_target=self.obj,
        )
        data = self._payload()
        data["alat-0-barang"] = str(self.alat_b.pk)
        self.assertContains(self.client.post(self.url, data), "memerlukan rekonsiliasi")

    def test_detached_import_rows_keep_distinct_return_notes(self):
        second, second_return = self._item(self.alat_b)
        self.obj.ensure_report_snapshot()
        PeminjamanBarangLaboratorium.objects.filter(pengajuan=self.obj).update(barang=None)
        PengembalianBarangLaboratorium.objects.filter(pengajuan=self.obj).update(barang=None)
        data = self._payload()
        data["alat-0-barang"] = str(self.alat.pk)
        self._submit(data)
        rows = self.obj.report_snapshot["items"]["lab"]
        self.assertEqual([row["catatan_pengembalian"] for row in rows], ["Catatan Alat A", "Catatan Alat B"])
        self.assertEqual([row["nama_barang"] for row in rows], ["Alat A", "Alat B"])

    def test_unmapped_imported_categories_are_preserved_on_partial_update(self):
        self.obj.layanan_kegiatan = None
        self.obj.instansi_tujuan = None
        self.obj.tim_kegiatan = None
        self.obj.kegiatan_survei.clear()
        self.obj.save()
        data = self._payload(filled=False)
        data["titik_borehole"] = "1"
        self._submit(data)
        kegiatan = self.obj.report_snapshot["kegiatan"]
        self.assertEqual(kegiatan["layanan_kegiatan"], "Air Baku")
        self.assertEqual(kegiatan["tim_kegiatan"], "Tim Layanan Teknis")
        self.assertEqual(kegiatan["kegiatan_survei"], ["Borehole Camera"])

    def test_changed_categories_update_snapshot_and_dashboard(self):
        layanan = LayananKegiatan.objects.create(jenis_layanan="Layanan Baru")
        tim = TimKegiatan.objects.create(nama_tim="Tim Baru")
        instansi = InstansiKlien.objects.create(nama_instansi="Eksternal", organisasi="Eksternal SDA")
        survei = SurveiKegiatan.objects.create(jenis_survei="Survei Baru")
        data = self._payload()
        data.update({"layanan_kegiatan": str(layanan.pk), "tim_kegiatan": str(tim.pk),
                     "instansi_tujuan": str(instansi.pk), "kegiatan_survei": [str(survei.pk)]})
        self._submit(data)
        kegiatan = self.obj.report_snapshot["kegiatan"]
        self.assertEqual(kegiatan["layanan_kegiatan"], layanan.jenis_layanan)
        self.assertEqual(kegiatan["tim_kegiatan"], tim.nama_tim)
        self.assertEqual(kegiatan["instansi_tujuan"], instansi.nama_instansi)
        self.assertEqual(kegiatan["kegiatan_survei"], [survei.jenis_survei])
        context = build_dashboard_context()
        self.assertEqual(context["layanan_chart"]["rows"][0]["layananId"], layanan.pk)
        self.assertEqual(context["tim_chart"]["rows"][0]["timId"], tim.pk)
        self.assertEqual(context["survei_chart"]["rows"][0]["surveiId"], survei.pk)
        gabungan = next(c for c in context["instansi_charts"] if c["key"] == "instansi-gabungan")
        self.assertEqual(gabungan["rows"][0]["instansiId"], instansi.pk)

    def test_upload_validation_commit_cleanup_and_rollback(self):
        data = self._payload()
        data["berkas_pendukung"] = SimpleUploadedFile("wrong.exe", b"wrong")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("berkas_pendukung", response.context["form"].errors)
        self.assertEqual(list(Path(self.media_root).rglob("*.exe")), [])
        data = self._payload()
        data["berkas_pendukung"] = SimpleUploadedFile("awal.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self._submit(data)
        old_path = self.obj.berkas_pendukung.path
        self.assertTrue(Path(old_path).exists())
        data = self._payload()
        data["berkas_pendukung"] = SimpleUploadedFile("baru.pdf", b"%PDF-1.4 new", content_type="application/pdf")
        with self.captureOnCommitCallbacks(execute=True):
            self._submit(data)
        self.assertFalse(Path(old_path).exists())
        current_file = self.obj.berkas_pendukung.name
        self.assertEqual(self.obj.report_snapshot["kegiatan"]["berkas_pendukung"], current_file)
        data = self._payload()
        data["berkas_pendukung"] = SimpleUploadedFile("gagal.pdf", b"%PDF-1.4 rollback", content_type="application/pdf")
        with patch.object(PeminjamanRequest, "add_timeline", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, data)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.berkas_pendukung.name, current_file)
        self.assertEqual(list(Path(self.media_root).rglob("gagal*.pdf")), [])

    def test_existing_missing_file_does_not_block_unrelated_correction(self):
        self.obj.berkas_pendukung = "peminjaman/arsip_lama.pdf"
        self.obj.save()
        data = self._payload()
        data["peminjam"] = str(self.teknisi.pk)
        self._submit(data)
        self.assertEqual(self.obj.berkas_pendukung.name, "peminjaman/arsip_lama.pdf")
        self.assertEqual(self.obj.nama_peminjam, self.teknisi.get_full_name())

    def test_comparison_keeps_original_data_on_invalid_post(self):
        data = self._payload()
        data.update({"peminjam": str(self.teknisi.pk), "titik_borehole": "-1"})
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        identitas = response.context["sections"][0]
        self.assertEqual(identitas["rows"][0]["previous"]["value"], "Peminjam Lama")
        self.assertEqual(response.context["form"]["peminjam"].value(), str(self.teknisi.pk))
        self.assertContains(response, "Data Sebelumnya", count=4)
        self.assertNotContains(response, 'name="alat-0-snapshot_nama_barang"')
        self.assertContains(response, 'class="file-input-proxy"')
        self.assertContains(response, 'class="survey-choice-card"')
        self.assertEqual(len(identitas["rows"]), 1)
        for name in ("nama_peminjam", "no_hp_peminjam", "email_peminjam", "nip_peminjam", "alamat_peminjam"):
            self.assertNotContains(response, f'name="{name}"')

    def test_borrower_snapshot_comes_from_selected_account_ignoring_manual_values(self):
        data = self._payload()
        self.teknisi.first_name = "Nama Terbaru"
        self.teknisi.last_name = "Akun"
        self.teknisi.no_hp = "081234567890"
        self.teknisi.nip = "NIP-123456"
        self.teknisi.save()
        profile = self.teknisi.safe_profile
        profile.alamat = "Alamat akun terbaru"
        profile.save(update_fields=["alamat"])
        data.update({
            "peminjam": str(self.teknisi.pk), "nama_peminjam": "Nama palsu", "email_peminjam": "palsu@example.com",
            "no_hp_peminjam": "000", "nip_peminjam": "PALSU", "alamat_peminjam": "Alamat palsu",
        })
        self._submit(data)
        self.assertEqual(self.obj.nama_peminjam, "Nama Terbaru Akun")
        self.assertEqual(self.obj.no_hp_peminjam, self.teknisi.no_hp)
        self.assertEqual(self.obj.email_peminjam, self.teknisi.email)
        self.assertEqual(self.obj.nip_peminjam, self.teknisi.nip)
        self.assertEqual(self.obj.alamat_peminjam, profile.alamat)
        self.assertEqual(self.obj.report_snapshot["peminjam"], {
            "nama": "Nama Terbaru Akun", "nomor_telepon": self.teknisi.no_hp,
            "email": self.teknisi.email, "nip": self.teknisi.nip, "alamat": profile.alamat,
        })

    def test_previous_tool_is_one_locked_label_from_snapshot(self):
        PeminjamanBarangLaboratorium.objects.filter(pk=self.borrowed.pk).update(
            snapshot_nama_barang="Borehole TV Camera", snapshot_tipe_merek_barang="TUBK Lite 200",
            snapshot_kode_aset_bmn="3080149020-1",
        )
        self.obj.ensure_report_snapshot()
        response = self.client.get(self.url)
        expected = "Borehole TV Camera - TUBK Lite 200 (3080149020-1)"
        self.assertEqual(response.context["previous_alat"][0]["label"], expected)
        self.assertContains(response, f'value="{expected}"')
        self.assertContains(response, "koreksi__locked-control")
        self.assertNotContains(response, "Kondisi Barang saat Dipinjam")

    def test_previous_tools_follow_the_same_row_order_as_editable_choices(self):
        self.alat_b.nama_barang = "Aardvark"
        self.alat_b.save()
        self._item(self.alat_b)
        self.obj.ensure_report_snapshot()
        response = self.client.get(self.url)
        self.assertEqual([row["nama_barang"] for row in response.context["previous_alat"]], ["Alat A", "Aardvark"])
        self.assertEqual([f.old_barang_id for f in response.context["formset"]], [self.alat.pk, self.alat_b.pk])

    def test_selected_master_is_refreshed_at_save_and_old_comparison_is_frozen(self):
        data = self._payload()
        self.alat.nama_barang = "Nama master terbaru"
        self.alat.tipe_merek_barang = "Merk terbaru"
        self.alat.tahun_perolehan = 2024
        self.alat.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context["previous_alat"][0]["nama_barang"], "Alat A")
        self.assertContains(response, "Nama master terbaru - Merk terbaru")
        self._submit(data)
        self.borrowed.refresh_from_db()
        self.returned.refresh_from_db()
        row = self.obj.report_snapshot["items"]["lab"][0]
        self.assertEqual(row["nama_barang"], "Nama master terbaru")
        self.assertEqual(row["tipe_merek_barang"], "Merk terbaru")
        self.assertEqual(row["tahun_perolehan"], 2024)
        self.assertEqual(self.borrowed.snapshot_nama_barang, "Nama master terbaru")
        self.assertEqual(self.returned.snapshot_nama_barang, "Nama master terbaru")

    def test_unknown_master_is_rejected(self):
        for value in ("999999999",):
            data = self._payload()
            data["alat-0-barang"] = value
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, 200)
            self.assertIn("barang", response.context["formset"].forms[0].errors)
            self.borrowed.refresh_from_db()
            self.assertEqual(self.borrowed.barang_id, self.alat.pk)

    def test_file_clear_uses_shared_upload_control_and_cleans_up_after_commit(self):
        data = self._payload()
        data["berkas_pendukung"] = SimpleUploadedFile("hapus.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self._submit(data)
        old_path = self.obj.berkas_pendukung.path
        data = self._payload()
        data["berkas_pendukung-clear"] = "on"
        with self.captureOnCommitCallbacks(execute=True):
            self._submit(data)
        self.assertFalse(self.obj.berkas_pendukung)
        self.assertFalse(Path(old_path).exists())
        self.assertEqual(self.obj.report_snapshot["kegiatan"]["berkas_pendukung"], "")

    def test_failure_rolls_back_transaction_items_snapshot_and_audit(self):
        data = self._payload()
        data.update({"nama_peminjam": "Tidak boleh tersimpan", "alat-0-barang": str(self.alat_b.pk)})
        original = deepcopy(self.obj.report_snapshot)
        with patch.object(PeminjamanRequest, "add_timeline", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, data)
        self.obj.refresh_from_db()
        self.borrowed.refresh_from_db()
        self.assertEqual(self.obj.nama_peminjam, "Peminjam Lama")
        self.assertEqual(self.obj.report_snapshot, original)
        self.assertEqual(self.borrowed.barang_id, self.alat.pk)

    def test_all_visible_edits_start_empty_and_noop_does_not_save(self):
        response = self.client.get(self.url)
        for field in response.context["form"].visible_fields():
            self.assertIn(field.value(), (None, "", [], False))
        for f in response.context["formset"]:
            self.assertIsNone(f["barang"].value())
            self.assertFalse(f["DELETE"].value())
        self.assertNotContains(response, "Pilih kegiatan survei yang sesuai.")
        self.assertNotContains(response, "Data lama belum terhubung ke master.")
        snapshot = deepcopy(self.obj.report_snapshot)
        updated_at = self.obj.updated_at
        result = self.client.post(self.url, self._payload(filled=False))
        self.assertContains(result, "Isi minimal satu kolom perubahan")
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.report_snapshot, snapshot)
        self.assertEqual(self.obj.updated_at, updated_at)
        self.assertFalse(self.obj.timeline_entries.filter(stage="Koreksi Laporan").exists())

    def test_only_filled_values_change_and_zero_is_an_explicit_correction(self):
        original = deepcopy(self.obj.report_snapshot)
        self.user.first_name = "Profil sudah berubah"
        self.user.save()
        self.alat.nama_barang = "Master sudah berubah"
        self.alat.save()
        data = self._payload(filled=False)
        data.update({"titik_borehole": "0", "layanan_kegiatan_lainnya": "   "})
        self._submit(data)
        self.borrowed.refresh_from_db()
        self.returned.refresh_from_db()
        self.assertEqual(self.obj.titik_borehole, 0)
        self.assertEqual(self.obj.nama_peminjam, "Peminjam Lama")
        self.assertEqual(self.obj.report_snapshot["peminjam"], original["peminjam"])
        self.assertEqual(self.obj.report_snapshot["kegiatan"], original["kegiatan"])
        self.assertEqual(self.obj.report_snapshot["items"], original["items"])
        self.assertEqual(self.borrowed.snapshot_nama_barang, "Alat A")
        self.assertEqual(self.returned.snapshot_nama_barang, "Alat A")
        self.assertEqual(self.obj.layanan_kegiatan_id, self.layanan.pk)

    def test_partial_dates_validate_against_unchanged_dates(self):
        data = self._payload(filled=False)
        data["tanggal_selesai"] = "04 Jan 2026"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("tanggal_pengembalian", response.context["form"].errors)
        data.update({"tanggal_pengembalian": "04 Jan 2026", "tanggal_selesai_pengembalian": "04 Jan 2026"})
        self._submit(data)
        self.assertEqual(self.obj.tanggal_mulai, date(2026, 1, 1))
        self.assertEqual(self.obj.tanggal_selesai, date(2026, 1, 4))
        self.assertEqual(self.obj.total_hari, 4)

    def test_blank_existing_tool_still_participates_in_duplicate_validation(self):
        data = self._payload(filled=False)
        data.update({"alat-TOTAL_FORMS": "2", "alat-1-barang": str(self.alat.pk)})
        self.assertContains(self.client.post(self.url, data), "Master alat yang sama")
        data["alat-1-barang"] = str(self.alat_b.pk)
        self._submit(data)
        self.assertEqual(self.obj.barang_laboratorium_items.count(), 2)
        self.assertEqual(self.obj.barang_laboratorium_items.get(pk=self.borrowed.pk).barang_id, self.alat.pk)
