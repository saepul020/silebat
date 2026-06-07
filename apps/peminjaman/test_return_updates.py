from datetime import date
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.master_data.models import (
    BarangLaboratorium,
    StatusBarangChoices,
)
from apps.pengguna.models import Role, User

from .models import (
    PeminjamanBarangLaboratorium,
    PeminjamanRequest,
    PengembalianBarangLaboratorium,
    ReturnItemStatusChoices,
    ReturnStepChoices,
    StepChoices,
)
from .pengembalian_views import (
    RETURN_ITEM_NOTE_MAX_LENGTH,
    _classify_row_field_errors,
    _parse_pengembalian_data,
    _save_pengembalian_data,
)
from .views import _build_berita_acara_sections, _get_latest_return_teknisi_actor


class ReturnUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="peminjam",
            password="test-password",
            first_name="Pengguna",
        )
        self.teknisi = User.objects.create_user(
            username="teknisi",
            password="test-password",
            first_name="Teknisi",
            nip="198765",
        )
        self.obj = PeminjamanRequest.objects.create(
            peminjam=self.user,
            nama_peminjam="Pengguna",
            tanggal_mulai=date(2026, 1, 1),
            tanggal_selesai=date(2026, 1, 2),
            current_step=StepChoices.APPROVED,
        )
        self.barang = BarangLaboratorium.objects.create(
            nama_barang="Alat Uji",
            tipe_merek_barang="Tipe A",
            jenis_barang="Alat",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="LAB-001",
            lokasi_barang="Laboratorium",
        )
        self.borrowed = PeminjamanBarangLaboratorium.objects.create(
            pengajuan=self.obj,
            barang=self.barang,
        )

    def test_optional_item_note_is_saved_and_reported(self):
        parsed = _parse_pengembalian_data(
            self.obj,
            {
                f"lab_status_{self.barang.pk}": ReturnItemStatusChoices.DIKEMBALIKAN,
                f"lab_note_{self.barang.pk}": "  Kondisi lengkap dan bersih.  ",
            },
        )

        parsed_lab, parsed_penunjang, parsed_peralatan, parsed_bahan, errors = parsed
        self.assertFalse(errors["lab"])

        _save_pengembalian_data(
            self.obj,
            parsed_lab,
            parsed_penunjang,
            parsed_peralatan,
            parsed_bahan,
        )

        returned = self.obj.pengembalian_lab_items.get(barang=self.barang)
        self.assertEqual(returned.note, "Kondisi lengkap dan bersih.")
        self.assertEqual(
            self.obj.build_report_snapshot()["items"]["lab"][0]["catatan_pengembalian"],
            "Kondisi lengkap dan bersih.",
        )

    def test_item_note_length_is_validated_on_server(self):
        self.assertEqual(RETURN_ITEM_NOTE_MAX_LENGTH, 100)
        parsed = _parse_pengembalian_data(
            self.obj,
            {
                f"lab_status_{self.barang.pk}": ReturnItemStatusChoices.DIKEMBALIKAN,
                f"lab_note_{self.barang.pk}": "x" * (RETURN_ITEM_NOTE_MAX_LENGTH + 1),
            },
        )

        self.assertFalse(parsed[0])
        messages = parsed[-1]["lab"][self.barang.pk]
        fields = _classify_row_field_errors("lab", {}, messages)
        self.assertIn("note", fields)
        self.assertIn(str(RETURN_ITEM_NOTE_MAX_LENGTH), fields["note"][0])

    def test_return_item_note_uses_single_line_input(self):
        role, _ = Role.objects.get_or_create(nama="User")
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("peminjaman:pengembalian", args=[self.obj.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'name="lab_note_{self.barang.pk}"')
        self.assertContains(response, 'type="text"')
        self.assertContains(response, 'maxlength="100"')
        self.assertNotContains(response, f'<textarea name="lab_note_{self.barang.pk}"')

    def test_return_item_note_is_shown_on_verification_detail(self):
        note = "Kabel daya perlu diganti."
        PengembalianBarangLaboratorium.objects.create(
            pengajuan=self.obj,
            barang=self.barang,
            status=ReturnItemStatusChoices.RUSAK,
            note=note,
        )
        self.obj.return_current_step = ReturnStepChoices.TEKNISI_VERIFICATION
        self.obj.save(update_fields=["return_current_step", "updated_at"])
        role, _ = Role.objects.get_or_create(nama="Teknisi Lab")
        self.teknisi.safe_profile.role = role
        self.teknisi.safe_profile.save(update_fields=["role"])
        self.client.force_login(self.teknisi)

        response = self.client.get(reverse("verifikasi:detail", args=[self.obj.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Verifikasi Pengembalian")
        self.assertContains(response, "Catatan Pengembalian")
        self.assertContains(response, note)

    def test_latest_return_teknisi_uses_current_verification_action(self):
        self.obj.add_timeline(
            "Pengembalian",
            "Verifikasi pengembalian disetujui Teknisi Lab dan diteruskan ke Kepala Lab",
            self.teknisi,
        )
        self.obj.add_timeline(
            "Pengembalian",
            "Pengembalian disetujui Kepala Lab",
            self.user,
        )

        self.assertEqual(_get_latest_return_teknisi_actor(self.obj), self.teknisi)

    def test_berita_acara_separates_code_and_return_note(self):
        PengembalianBarangLaboratorium.objects.create(
            pengajuan=self.obj,
            barang=self.barang,
            status=ReturnItemStatusChoices.RUSAK,
            note="Layar retak.",
        )

        row = _build_berita_acara_sections(self.obj)["rusak"][0]

        self.assertEqual(row["kode_laboratorium"], "LAB-001")
        self.assertEqual(row["catatan_pengembalian"], "Layar retak.")
        self.assertNotIn("keterangan", row)

    def test_login_has_password_visibility_toggle(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-password-toggle")
        self.assertContains(response, 'data-password-target="id_password"')

    def test_summary_submit_clears_unsaved_guard_before_native_submit(self):
        source = Path(settings.BASE_DIR, "static", "js", "apps.js").read_text(encoding="utf-8")
        handler_start = source.index("if (confirmSummaryButton) {")
        handler_end = source.index("document.addEventListener('keydown'", handler_start)
        handler = source[handler_start:handler_end]

        self.assertLess(
            handler.index("form.dispatchEvent(new CustomEvent('unsaved:submitted'))"),
            handler.index("HTMLFormElement.prototype.submit.call(form)"),
        )
        self.assertIn("confirmSummaryButton.disabled = true", handler)
