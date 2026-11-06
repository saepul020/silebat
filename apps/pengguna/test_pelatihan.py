import re
import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from apps.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from apps.pengguna.forms import PesertaAdminForm
from apps.pengguna.models import Pelatihan, PesertaPelatihan, Role, User


def upload(name="sertifikat.pdf", content=b"%PDF-1.4 sertifikat"):
    return SimpleUploadedFile(name, content)


class PelatihanTests(TestCase):
    def setUp(self):
        media_root = tempfile.mkdtemp()
        self.media_root = Path(media_root)
        self.addCleanup(shutil.rmtree, media_root, True)
        settings = override_settings(MEDIA_ROOT=media_root)
        settings.enable()
        self.addCleanup(settings.disable)
        self.actor = User.objects.create_user(username="penginput", first_name="Penginput")
        self.other = User.objects.create_user(username="peserta", first_name="Peserta Kedua")
        self.outsider = User.objects.create_user(username="lain")
        self.admin = User.objects.create_user(username="admin")
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        self.admin.safe_profile.role = role
        self.admin.safe_profile.save(update_fields=["role"])
        self.client.force_login(self.actor)

    def payload(self, **changes):
        data = {
            "tipe_pelatihan": Pelatihan.TIPE_INTERNAL,
            "jenis_pelatihan": Pelatihan.JENIS_LABORATORIUM,
            "nama_pelatihan": "Pelatihan Bersama",
            "tanggal_mulai": "05 Nov 2026",
            "tanggal_selesai": "06 Nov 2026",
            "lokasi_pelatihan": "Bandung",
            "uraian_pelatihan": "Praktik laboratorium",
            "peserta-TOTAL_FORMS": "2",
            "peserta-INITIAL_FORMS": "1",
            "peserta-1-user": str(self.other.pk),
        }
        data.update(changes)
        return data

    def create_training(self, **changes):
        response = self.client.post(reverse("pengguna:pelatihan_tambah"), self.payload(**changes))
        self.assertEqual(response.status_code, 302)
        return Pelatihan.objects.get()

    def test_create_locks_actor_and_shares_list_dashboard_and_detail(self):
        obj = self.create_training(**{
            "peserta-0-user": self.outsider.pk,
            "peserta-0-file_sertifikat": upload("penginput.pdf"),
            "peserta-1-file_sertifikat": upload("peserta.pdf"),
        })
        self.assertEqual(set(obj.peserta.values_list("user_id", flat=True)), {self.actor.pk, self.other.pk})
        self.assertTrue(obj.peserta.get(user=self.actor).file_sertifikat.name.endswith("penginput.pdf"))
        self.assertTrue(obj.peserta.get(user=self.other).file_sertifikat.name.endswith("peserta.pdf"))
        for user in (self.actor, self.other):
            self.client.force_login(user)
            response = self.client.get(reverse("pengguna:pelatihan_daftar"))
            self.assertContains(response, obj.nama_pelatihan)
            response = self.client.get(reverse("pengguna:dashboard_sdm"))
            self.assertEqual(response.context["total_pelatihan"], 1)
            response = self.client.get(reverse("pengguna:pelatihan_detail", args=[obj.pk]))
            self.assertContains(response, "Peserta Kedua")
            self.assertContains(response, "peserta-list")
            self.assertEqual(response.context["keikutsertaan"].user_id, user.pk)

    def test_form_starts_with_actor_only_and_certificate_in_peserta_fieldset(self):
        response = self.client.get(reverse("pengguna:pelatihan_tambah"))
        forms = response.context["peserta"].forms
        self.assertEqual(len(forms), 1)
        self.assertTrue(forms[0].fields["user"].disabled)
        self.assertEqual(forms[0].initial["user"], self.actor.pk)
        empty_form = response.context["peserta"].empty_form
        self.assertFalse(empty_form.fields["user"].disabled)
        self.assertEqual(response.context["peserta"].management_form.initial["TOTAL_FORMS"], 1)
        html = response.content.decode()
        self.assertLess(html.index("<legend>Detail Pelatihan"), html.index("<legend>Peserta Pelatihan"))
        documents = html.split("<legend>Dokumen Pelatihan</legend>")[1]
        self.assertNotIn("file_sertifikat", documents)
        self.assertNotIn(self.admin.pk, empty_form.fields["user"].queryset.values_list("pk", flat=True))

    def test_admin_detail_renders_creator_and_optional_participant_certificates(self):
        obj = self.create_training(**{"peserta-0-file_sertifikat": upload("penginput.pdf")})
        certificate = obj.peserta.get(user=self.actor).file_sertifikat
        self.client.force_login(self.admin)
        response = self.client.get(reverse("pengguna:pelatihan_detail", args=[obj.pk]))
        self.assertContains(response, "Penginput: Penginput")
        self.assertContains(response, "Peserta Kedua")
        self.assertContains(response, 'href="' + certificate.url + '"', count=1)
        self.assertNotContains(response, "{{")
        self.assertNotContains(response, "{%")

    def test_optional_other_participant(self):
        obj = self.create_training(**{"peserta-TOTAL_FORMS": "1", "peserta-1-user": ""})
        self.assertEqual(obj.peserta.count(), 1)

    def test_rejects_duplicate_unknown_and_admin_participants(self):
        for user_id in (self.actor.pk, self.admin.pk, 99999999):
            with self.subTest(user_id=user_id):
                response = self.client.post(reverse("pengguna:pelatihan_tambah"), self.payload(**{"peserta-1-user": user_id}))
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context["peserta"].is_valid())
                self.assertFalse(Pelatihan.objects.exists())

    def test_rejects_invalid_certificate_without_partial_save(self):
        for file in (upload("virus.exe"), upload(content=b"a" * (MAX_UPLOAD_SIZE_BYTES + 1))):
            response = self.client.post(reverse("pengguna:pelatihan_tambah"), self.payload(**{"peserta-1-file_sertifikat": file}))
            self.assertEqual(response.status_code, 200)
            self.assertIn("file_sertifikat", response.context["peserta"].forms[1].errors)
            self.assertFalse(Pelatihan.objects.exists())
            self.assertFalse(PesertaPelatihan.objects.exists())

    def test_rejects_certificate_without_selected_user(self):
        response = self.client.post(reverse("pengguna:pelatihan_tambah"), self.payload(**{
            "peserta-1-user": "", "peserta-1-file_sertifikat": upload(),
        }))
        self.assertEqual(response.status_code, 200)
        self.assertIn("user", response.context["peserta"].forms[1].errors)
        self.assertFalse(Pelatihan.objects.exists())

    def test_rejects_missing_or_tampered_management_data(self):
        for changes in (
            {"peserta-TOTAL_FORMS": "0"},
            {"peserta-INITIAL_FORMS": "0"},
            {"peserta-INITIAL_FORMS": "3"},
        ):
            response = self.client.post(reverse("pengguna:pelatihan_tambah"), self.payload(**changes))
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["peserta"].is_valid())
            self.assertFalse(Pelatihan.objects.exists())

    def test_nonparticipant_cannot_read_edit_or_delete(self):
        obj = self.create_training()
        self.client.force_login(self.outsider)
        for route in ("pelatihan_detail", "pelatihan_edit", "pelatihan_hapus"):
            self.assertEqual(self.client.get(reverse("pengguna:" + route, args=[obj.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse("pengguna:" + route, args=[obj.pk]), {}).status_code, 404)
        self.assertEqual(obj.peserta.count(), 2)

    def test_creator_edit_preserves_participants_and_adds_new_participant(self):
        obj = self.create_training(**{"peserta-1-file_sertifikat": upload()})
        old_name = obj.peserta.get(user=self.other).file_sertifikat.name
        response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
            "nama_pelatihan": "Judul Baru",
            "peserta-INITIAL_FORMS": "2", "peserta-TOTAL_FORMS": "3",
            "peserta-0-user": self.outsider.pk,
            "peserta-1-user": self.outsider.pk,
            "peserta-2-user": self.outsider.pk,
        }))
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.nama_pelatihan, "Judul Baru")
        self.assertEqual(obj.peserta.count(), 3)
        self.assertEqual(obj.peserta.get(user=self.other).file_sertifikat.name, old_name)

    def test_participant_can_edit_all_training_fields_and_certificates(self):
        obj = self.create_training(**{
            "file_materi": upload("materi-lama.pdf"),
            "peserta-0-file_sertifikat": upload("penginput.pdf"),
            "peserta-1-file_sertifikat": upload("peserta.pdf"),
        })
        old_files = [obj.file_materi, *(row.file_sertifikat for row in obj.peserta.all())]
        peserta_ids = set(obj.peserta.values_list("pk", flat=True))
        self.client.force_login(self.other)
        response = self.client.get(reverse("pengguna:pelatihan_edit", args=[obj.pk]))
        self.assertTrue(all(not field.disabled for field in response.context["form"].fields.values()))
        self.assertFalse(response.context["peserta"].can_delete)
        for form in response.context["peserta"].forms:
            self.assertTrue(form.fields["user"].disabled)
            self.assertFalse(form.fields["file_sertifikat"].disabled)
            self.assertFalse(form.removable)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
                "nama_pelatihan": "Diperbarui Peserta",
                "tipe_pelatihan": Pelatihan.TIPE_EKSTERNAL,
                "jenis_pelatihan": Pelatihan.JENIS_NON_LABORATORIUM,
                "tanggal_mulai": "07 Nov 2026", "tanggal_selesai": "08 Nov 2026",
                "lokasi_pelatihan": "Jakarta", "uraian_pelatihan": "Uraian terbaru",
                "file_materi": upload("materi-baru.pdf"),
                "peserta-INITIAL_FORMS": "2", "peserta-TOTAL_FORMS": "2",
                "peserta-0-file_sertifikat": upload("milik-sendiri.pdf"),
                "peserta-1-file_sertifikat": upload("revisi-penginput.pdf"),
            }))
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.nama_pelatihan, "Diperbarui Peserta")
        self.assertEqual(obj.tipe_pelatihan, Pelatihan.TIPE_EKSTERNAL)
        self.assertEqual(obj.jenis_pelatihan, Pelatihan.JENIS_NON_LABORATORIUM)
        self.assertEqual(obj.tanggal_mulai.isoformat(), "2026-11-07")
        self.assertEqual(obj.tanggal_selesai.isoformat(), "2026-11-08")
        self.assertEqual(obj.lokasi_pelatihan, "Jakarta")
        self.assertEqual(obj.uraian_pelatihan, "Uraian terbaru")
        self.assertTrue(obj.file_materi.name.endswith("materi-baru.pdf"))
        self.assertTrue(obj.peserta.get(user=self.other).file_sertifikat.name.endswith("milik-sendiri.pdf"))
        self.assertTrue(obj.peserta.get(user=self.actor).file_sertifikat.name.endswith("revisi-penginput.pdf"))
        self.assertEqual(set(obj.peserta.values_list("pk", flat=True)), peserta_ids)
        self.assertEqual(obj.user_id, self.actor.pk)
        for file in old_files:
            self.assertFalse(file.storage.exists(file.name))
        self.client.force_login(self.actor)
        self.assertContains(self.client.get(reverse("pengguna:pelatihan_detail", args=[obj.pk])), "Diperbarui Peserta")

    def test_participant_edit_still_validates_dates_and_uploads(self):
        obj = self.create_training()
        self.client.force_login(self.other)
        for changes in (
            {"tanggal_mulai": "08 Nov 2026", "tanggal_selesai": "07 Nov 2026"},
            {"file_materi": upload("invalid.exe")},
            {"peserta-1-file_sertifikat": upload("invalid.exe")},
        ):
            response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
                "peserta-INITIAL_FORMS": "2", "nama_pelatihan": "Belum valid", **changes,
            }))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors or any(response.context["peserta"].errors))
            obj.refresh_from_db()
            self.assertEqual(obj.nama_pelatihan, "Pelatihan Bersama")
            self.assertEqual(obj.peserta.count(), 2)

    def test_participant_can_add_others_without_changing_existing_participants(self):
        obj = self.create_training(**{"peserta-0-file_sertifikat": upload("penginput.pdf")})
        original = obj.peserta.get(user=self.actor)
        self.client.force_login(self.other)
        response = self.client.get(reverse("pengguna:pelatihan_edit", args=[obj.pk]))
        self.assertContains(response, "data-peserta-add")
        self.assertTrue(all(not form.removable for form in response.context["peserta"].forms))
        response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
            "nama_pelatihan": "Diperbarui Peserta",
            "peserta-INITIAL_FORMS": "2", "peserta-TOTAL_FORMS": "3",
            "peserta-1-user": self.outsider.pk,
            "peserta-1-DELETE": "on",
            "peserta-1-file_sertifikat": upload("revisi-penginput.pdf"),
            "peserta-2-user": self.outsider.pk,
            "peserta-2-file_sertifikat": upload("peserta-baru.pdf"),
        }))
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        original.refresh_from_db()
        self.assertEqual(obj.nama_pelatihan, "Diperbarui Peserta")
        self.assertEqual(obj.peserta.count(), 3)
        self.assertTrue(original.file_sertifikat.name.endswith("revisi-penginput.pdf"))
        self.assertTrue(obj.peserta.filter(user=self.other).exists())
        self.assertTrue(obj.peserta.get(user=self.outsider).file_sertifikat.name.endswith("peserta-baru.pdf"))
        self.client.force_login(self.outsider)
        self.assertContains(self.client.get(reverse("pengguna:pelatihan_daftar")), obj.nama_pelatihan)

    def test_creator_cannot_delete_participants_with_forged_delete_flags(self):
        obj = self.create_training()
        response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
            "peserta-INITIAL_FORMS": "2", "peserta-0-DELETE": "on", "peserta-1-DELETE": "on",
        }))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(obj.peserta.count(), 2)

    def test_super_admin_create_selects_first_participant_without_joining(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("pengguna:pelatihan_tambah"))
        forms = response.context["peserta"].forms
        self.assertEqual(len(forms), 1)
        self.assertFalse(forms[0].fields["user"].disabled)
        self.assertIsNone(forms[0]["user"].value())
        self.assertNotIn(self.admin.pk, forms[0].fields["user"].queryset.values_list("pk", flat=True))
        obj = self.create_training(**{
            "peserta-TOTAL_FORMS": "1", "peserta-0-user": self.other.pk,
            "peserta-0-file_sertifikat": upload("peserta.pdf"),
        })
        self.assertEqual(obj.user_id, self.admin.pk)
        self.assertEqual(list(obj.peserta.values_list("user_id", flat=True)), [self.other.pk])

    def test_super_admin_create_requires_valid_non_admin_first_participant(self):
        self.client.force_login(self.admin)
        for user_id in ("", self.admin.pk, 99999999):
            with self.subTest(user_id=user_id):
                response = self.client.post(reverse("pengguna:pelatihan_tambah"), self.payload(**{
                    "peserta-TOTAL_FORMS": "1", "peserta-0-user": user_id,
                }))
                self.assertEqual(response.status_code, 200)
                self.assertIn("user", response.context["peserta"].forms[0].errors)
                self.assertFalse(Pelatihan.objects.exists())

    def test_super_admin_can_remove_one_saved_participant_and_keep_shared_material(self):
        obj = self.create_training(**{
            "file_materi": upload("materi.pdf"),
            "peserta-0-file_sertifikat": upload("penginput.pdf"),
            "peserta-1-file_sertifikat": upload("peserta.pdf"),
        })
        removed_file = obj.peserta.get(user=self.actor).file_sertifikat
        retained_file = obj.peserta.get(user=self.other).file_sertifikat
        self.client.force_login(self.admin)
        response = self.client.get(reverse("pengguna:pelatihan_edit", args=[obj.pk]))
        self.assertTrue(response.context["peserta"].can_delete)
        self.assertTrue(all(form.removable for form in response.context["peserta"].forms))
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
                "peserta-INITIAL_FORMS": "2", "peserta-0-DELETE": "on",
            }))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(obj.peserta.values_list("user_id", flat=True)), [self.other.pk])
        self.assertFalse(removed_file.storage.exists(removed_file.name))
        self.assertTrue(retained_file.storage.exists(retained_file.name))
        self.assertTrue(obj.file_materi.storage.exists(obj.file_materi.name))

    def test_super_admin_edit_requires_at_least_one_remaining_participant(self):
        obj = self.create_training()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
            "peserta-INITIAL_FORMS": "2", "peserta-0-DELETE": "on", "peserta-1-DELETE": "on",
        }))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Minimal satu peserta", str(response.context["peserta"].non_form_errors()))
        self.assertEqual(obj.peserta.count(), 2)

    def test_super_admin_can_readd_removed_user_without_duplicate_constraint_error(self):
        obj = self.create_training()
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
            "peserta-INITIAL_FORMS": "2", "peserta-TOTAL_FORMS": "3",
            "peserta-0-DELETE": "on", "peserta-2-user": self.actor.pk,
        }))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(set(obj.peserta.values_list("user_id", flat=True)), {self.actor.pk, self.other.pk})

    def test_creator_cannot_drop_saved_participant_via_form(self):
        obj = self.create_training()
        response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
            "peserta-INITIAL_FORMS": "2", "peserta-TOTAL_FORMS": "1",
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(obj.peserta.count(), 2)

    def test_replacing_certificate_removes_only_old_file_after_commit(self):
        obj = self.create_training(**{"peserta-0-file_sertifikat": upload("lama.pdf")})
        old_file = obj.peserta.get(user=self.actor).file_sertifikat
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
                "peserta-INITIAL_FORMS": "2", "peserta-0-file_sertifikat": upload("baru.pdf"),
            }))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(old_file.storage.exists(old_file.name))
        new_file = obj.peserta.get(user=self.actor).file_sertifikat
        self.assertTrue(new_file.storage.exists(new_file.name))

    def test_shared_certificate_file_is_kept_for_remaining_participant(self):
        obj = self.create_training(**{"peserta-0-file_sertifikat": upload("bersama.pdf")})
        shared = obj.peserta.get(user=self.actor).file_sertifikat
        other = obj.peserta.get(user=self.other)
        other.file_sertifikat = shared.name
        other.save(update_fields=["file_sertifikat"])
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("pengguna:pelatihan_hapus", args=[obj.pk]))
        self.assertTrue(shared.storage.exists(shared.name))

    def test_repeated_replacement_with_same_filenames_leaves_only_current_files(self):
        obj = self.create_training(**{
            "file_materi": upload("materi.pdf"),
            "peserta-0-file_sertifikat": upload("sertifikat.pdf"),
            "peserta-1-file_sertifikat": upload("sertifikat.pdf"),
        })
        for _ in range(3):
            old_files = [obj.file_materi, *(row.file_sertifikat for row in obj.peserta.all())]
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
                    "peserta-INITIAL_FORMS": "2", "file_materi": upload("materi.pdf"),
                    "peserta-0-file_sertifikat": upload("sertifikat.pdf"),
                    "peserta-1-file_sertifikat": upload("sertifikat.pdf"),
                }))
            self.assertEqual(response.status_code, 302)
            obj.refresh_from_db()
            for file in old_files:
                self.assertFalse(file.storage.exists(file.name), file.name)
            expected = {obj.file_materi.name, *obj.peserta.values_list("file_sertifikat", flat=True)}
            stored = {path.relative_to(self.media_root).as_posix() for path in self.media_root.rglob("*") if path.is_file()}
            self.assertEqual(stored, expected)

    def test_invalid_replacement_keeps_old_files_and_does_not_store_new_uploads(self):
        obj = self.create_training(**{
            "file_materi": upload("materi.pdf"),
            "peserta-0-file_sertifikat": upload("penginput.pdf"),
            "peserta-1-file_sertifikat": upload("peserta.pdf"),
        })
        expected = {obj.file_materi.name, *obj.peserta.values_list("file_sertifikat", flat=True)}
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
                "peserta-INITIAL_FORMS": "2", "file_materi": upload("materi-baru.pdf"),
                "peserta-0-file_sertifikat": upload("penginput-baru.pdf"),
                "peserta-1-file_sertifikat": upload("invalid.exe"),
            }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(callbacks, [])
        obj.refresh_from_db()
        self.assertEqual({obj.file_materi.name, *obj.peserta.values_list("file_sertifikat", flat=True)}, expected)
        stored = {path.relative_to(self.media_root).as_posix() for path in self.media_root.rglob("*") if path.is_file()}
        self.assertEqual(stored, expected)

    def test_replacing_shared_certificate_keeps_file_referenced_by_other_participant(self):
        obj = self.create_training(**{"peserta-0-file_sertifikat": upload("bersama.pdf")})
        shared = obj.peserta.get(user=self.actor).file_sertifikat
        other = obj.peserta.get(user=self.other)
        other.file_sertifikat = shared.name
        other.save(update_fields=["file_sertifikat"])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
                "peserta-INITIAL_FORMS": "2", "peserta-0-file_sertifikat": upload("baru.pdf"),
            }))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(shared.storage.exists(shared.name))
        self.assertEqual(obj.peserta.get(user=self.other).file_sertifikat.name, shared.name)
        self.assertNotEqual(obj.peserta.get(user=self.actor).file_sertifikat.name, shared.name)

    def test_admin_inline_rejects_invalid_certificate(self):
        form = PesertaAdminForm(data={"user": self.actor.pk}, files={"file_sertifikat": upload("invalid.exe")})
        self.assertFalse(form.is_valid())
        self.assertIn("file_sertifikat", form.errors)

    def test_deleting_creator_membership_preserves_other_participants_and_material(self):
        obj = self.create_training(**{
            "file_materi": upload("materi.pdf"),
            "peserta-0-file_sertifikat": upload("penginput.pdf"),
            "peserta-1-file_sertifikat": upload("peserta.pdf"),
        })
        own = obj.peserta.get(user=self.actor).file_sertifikat
        other_file = obj.peserta.get(user=self.other).file_sertifikat
        self.assertEqual(self.client.get(reverse("pengguna:pelatihan_hapus", args=[obj.pk])).status_code, 302)
        self.assertEqual(obj.peserta.count(), 2)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("pengguna:pelatihan_hapus", args=[obj.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Pelatihan.objects.filter(pk=obj.pk).exists())
        self.assertFalse(obj.peserta.filter(user=self.actor).exists())
        self.assertTrue(obj.peserta.filter(user=self.other).exists())
        self.assertFalse(own.storage.exists(own.name))
        self.assertTrue(other_file.storage.exists(other_file.name))
        self.assertTrue(obj.file_materi.storage.exists(obj.file_materi.name))
        response = self.client.get(reverse("pengguna:pelatihan_daftar"))
        self.assertEqual(len(response.context["items"]), 0)
        self.assertEqual(self.client.get(reverse("pengguna:dashboard_sdm")).context["total_pelatihan"], 0)
        self.client.force_login(self.other)
        self.assertContains(self.client.get(reverse("pengguna:pelatihan_detail", args=[obj.pk])), obj.nama_pelatihan)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("pengguna:pelatihan_hapus", args=[obj.pk]))
        self.assertFalse(Pelatihan.objects.filter(pk=obj.pk).exists())
        self.assertFalse(other_file.storage.exists(other_file.name))
        self.assertFalse(obj.file_materi.storage.exists(obj.file_materi.name))

    def test_super_admin_can_delete_training_and_all_participants_and_files(self):
        obj = self.create_training(**{
            "file_materi": upload("materi.pdf"),
            "peserta-0-file_sertifikat": upload("penginput.pdf"),
            "peserta-1-file_sertifikat": upload("peserta.pdf"),
        })
        files = [obj.file_materi, *(row.file_sertifikat for row in obj.peserta.all())]
        self.client.force_login(self.admin)
        response = self.client.get(reverse("pengguna:pelatihan_daftar"))
        self.assertContains(response, 'data-delete-url="' + reverse("pengguna:pelatihan_hapus", args=[obj.pk]) + '"')
        self.assertContains(response, "seluruh data pelatihan")
        self.client.get(reverse("pengguna:pelatihan_hapus", args=[obj.pk]))
        self.assertTrue(Pelatihan.objects.filter(pk=obj.pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("pengguna:pelatihan_hapus", args=[obj.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Pelatihan.objects.filter(pk=obj.pk).exists())
        self.assertFalse(PesertaPelatihan.objects.filter(pelatihan_id=obj.pk).exists())
        for file in files:
            self.assertFalse(file.storage.exists(file.name))

    def test_super_admin_participant_also_deletes_entire_training(self):
        obj = self.create_training()
        PesertaPelatihan.objects.create(pelatihan=obj, user=self.admin)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pengguna:pelatihan_hapus", args=[obj.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Pelatihan.objects.filter(pk=obj.pk).exists())

    def test_super_admin_can_edit_training_without_being_participant(self):
        obj = self.create_training()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("pengguna:pelatihan_edit", args=[obj.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].fields["nama_pelatihan"].disabled)
        response = self.client.post(reverse("pengguna:pelatihan_edit", args=[obj.pk]), self.payload(**{
            "nama_pelatihan": "Diperbarui Super Admin", "peserta-INITIAL_FORMS": "2",
            "peserta-TOTAL_FORMS": "3", "peserta-2-user": self.outsider.pk,
            "peserta-1-file_sertifikat": upload("revisi.pdf"),
        }))
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.nama_pelatihan, "Diperbarui Super Admin")
        self.assertEqual(obj.peserta.count(), 3)
        self.assertTrue(obj.peserta.get(user=self.other).file_sertifikat.name.endswith("revisi.pdf"))
        self.assertEqual(obj.user_id, self.actor.pk)

    def test_sdm_monitor_filter_uses_membership_and_counts_shared_training_once(self):
        obj = self.create_training()
        self.client.force_login(self.admin)
        dashboard = reverse("pengguna:dashboard_sdm")
        self.assertEqual(self.client.get(dashboard).context["total_pelatihan"], 1)
        response = self.client.get(dashboard, {"user": self.other.pk})
        self.assertEqual(response.context["total_pelatihan"], 1)
        self.assertEqual(sum(row["total"] for row in response.context["sdm_tipe_chart"]["rows"]), 1)
        self.assertEqual(self.client.get(dashboard, {"user": self.outsider.pk}).context["total_pelatihan"], 0)

    def test_deleting_creator_account_does_not_cascade_shared_training(self):
        obj = self.create_training()
        self.actor.delete()
        obj.refresh_from_db()
        self.assertIsNone(obj.user_id)
        self.assertEqual(list(obj.peserta.values_list("user_id", flat=True)), [self.other.pk])
        self.client.force_login(self.admin)
        response = self.client.get(reverse("pengguna:pelatihan_daftar"))
        self.assertContains(response, obj.nama_pelatihan)
        response = self.client.get(reverse("pengguna:pelatihan_detail", args=[obj.pk]))
        self.assertContains(response, "Penginput: -")
        self.assertContains(response, obj.nama_pelatihan)


class TemplateTests(SimpleTestCase):
    def test_pengguna_templates_compile_without_split_django_tokens(self):
        root = Path(__file__).parent / "templates"
        for path in sorted(root.rglob("*.html")):
            with self.subTest(template=path.name):
                get_template(path.relative_to(root).as_posix())
                source = path.read_text(encoding="utf-8")
                for token in re.finditer(r"{{.*?}}|{%.*?%}", source, re.DOTALL):
                    self.assertNotIn("\n", token.group(), f"Tag Django terpotong dalam {path.name}")


class PelatihanMigrationTests(TransactionTestCase):
    def test_existing_owner_and_certificate_become_participant(self):
        previous = [("pengguna", "0010_alter_pelatihan_uraian_required")]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        executor.migrate(previous)
        apps = executor.loader.project_state(previous).apps
        user = apps.get_model("pengguna", "User").objects.create(username="legacy")
        old = apps.get_model("pengguna", "Pelatihan").objects.create(
            user_id=user.pk, nama_pelatihan="Pelatihan Lama",
            tipe_pelatihan=Pelatihan.TIPE_INTERNAL, jenis_pelatihan=Pelatihan.JENIS_LABORATORIUM,
            tanggal_mulai="2026-11-05", tanggal_selesai="2026-11-05",
            lokasi_pelatihan="Bandung", uraian_pelatihan="Data lama",
            file_sertifikat="pengguna/pelatihan/sertifikat/legacy.pdf",
            file_materi="pengguna/pelatihan/materi/legacy.zip",
        )
        MigrationExecutor(connection).migrate(latest)
        migrated = Pelatihan.objects.get(pk=old.pk)
        peserta = migrated.peserta.get()
        self.assertEqual(peserta.user_id, user.pk)
        self.assertEqual(peserta.file_sertifikat.name, "pengguna/pelatihan/sertifikat/legacy.pdf")
        self.assertEqual(migrated.file_materi.name, "pengguna/pelatihan/materi/legacy.zip")
