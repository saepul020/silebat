import re
import tempfile
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from apps.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from apps.pengguna.models import Role, User

from .forms import DokumentasiTVForm
from .models import DokumentasiTV, SlideDokumentasi
from .services import get_tv_documentation


def photo(name="kegiatan.png", image_format="PNG"):
    output = BytesIO()
    Image.new("RGB", (160, 90), (16, 62, 111)).save(output, format=image_format)
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/" + image_format.lower())


class DokumentasiTVTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory(prefix="silebat-tv-doc-")
        self.addCleanup(media.cleanup)
        settings_override = override_settings(MEDIA_ROOT=media.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.user = User.objects.create_user(username="admin-dokumentasi-tv")
        self.set_role("Super Admin")
        self.slide = SlideDokumentasi.objects.first() or SlideDokumentasi.objects.create()
        self.url = reverse("landing:dokumentasi_tv")
        self.edit_url = f"{self.url}#slide-{self.slide.pk}"
        self.display = reverse("dashboard:display", args=[settings.DASHBOARD_TV_SLUG])
        self.refresh = reverse("dashboard:display_active_data", args=[settings.DASHBOARD_TV_SLUG])

    def set_role(self, name):
        role, _ = Role.objects.get_or_create(nama=name)
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])

    def post_slide(self, data=None, slide=None):
        slide = slide or self.slide
        payload = {"action": "simpan", "slide_id": slide.pk}
        payload.update({f"slide-{slide.pk}-{key}": value for key, value in (data or {}).items()})
        return self.client.post(self.url, payload)

    def response_form(self, response, slide=None):
        slide = slide or self.slide
        return next(item["form"] for item in response.context["slides"] if item["slide"].pk == slide.pk)

    def test_six_uploads_save_in_order_and_keep_images_when_not_replaced(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'type="file"', count=6)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'href="' + self.url + '"')
        self.assertEqual(DokumentasiTV.objects.count(), 0)
        self.assertRedirects(self.post_slide({f"foto_{i}": photo(f"{i}.png") for i in range(1, 7)}), self.edit_url)
        original = list(DokumentasiTV.objects.values_list("nomor", "foto"))
        self.assertEqual([nomor for nomor, _ in original], list(range(1, 7)))
        self.assertRedirects(self.post_slide({}), self.edit_url)
        self.assertEqual(list(DokumentasiTV.objects.values_list("nomor", "foto")), original)
        response = self.client.get(self.url)
        self.assertContains(response, 'data-tv-photo-clear', count=6)
        for _, name in original:
            self.assertContains(response, name)

    def test_only_super_admin_can_read_or_write(self):
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(self.url).status_code, 302)
        self.client.force_login(self.user)
        for role in ("User", "Admin Lab", "Teknisi Lab", "Kepala Lab", "Pimpinan"):
            self.set_role(role)
            for method in (self.client.get, self.client.post):
                self.assertRedirects(method(self.url), reverse("dashboard:index"), fetch_redirect_response=False)
        self.assertFalse(DokumentasiTV.objects.exists())

    def test_invalid_image_extension_and_size_do_not_save_any_slot(self):
        self.client.force_login(self.user)
        original = DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo("old.png"))
        oversized = SimpleUploadedFile(
            "large.png", photo().read() + b"0" * MAX_UPLOAD_SIZE_BYTES, content_type="image/png",
        )
        for invalid in (photo("invalid.gif", "GIF"), SimpleUploadedFile("fake.png", b"not an image"), oversized):
            with self.subTest(name=invalid.name):
                response = self.post_slide({"foto_1": photo("new.png"), "foto_6": invalid})
                self.assertEqual(response.status_code, 200)
                self.assertIn("foto_6", self.response_form(response).errors)
                self.assertEqual(list(DokumentasiTV.objects.values_list("nomor", "foto")), [(1, original.foto.name)])
                with self.assertRaises(ValueError):
                    self.response_form(response).save()

    def test_remove_replace_and_file_cleanup_run_after_commit(self):
        first = DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo("old.png"))
        second = DokumentasiTV.objects.create(slide=self.slide, nomor=2, foto=photo("keep.png"))
        old_name, storage = first.foto.name, first.foto.storage
        form = DokumentasiTVForm(slide=self.slide, data={}, files={"foto_1": photo("new.png")})
        self.assertTrue(form.is_valid(), form.errors)
        with self.captureOnCommitCallbacks(execute=True):
            form.save()
            self.assertTrue(storage.exists(old_name))
        self.assertFalse(storage.exists(old_name))
        replacement = DokumentasiTV.objects.get(nomor=1)
        self.assertTrue(storage.exists(replacement.foto.name))
        self.assertTrue(storage.exists(second.foto.name))
        form = DokumentasiTVForm(slide=self.slide, data={"hapus_1": "on"})
        with self.captureOnCommitCallbacks(execute=True):
            form.save()
        self.assertFalse(DokumentasiTV.objects.filter(nomor=1).exists())
        self.assertFalse(storage.exists(replacement.foto.name))
        self.assertTrue(storage.exists(second.foto.name))

    def test_saved_replace_and_x_removal_clean_database_references_and_files(self):
        original = DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo("original.png"))
        kept = DokumentasiTV.objects.create(slide=self.slide, nomor=2, foto=photo("kept.png"))
        old_name, storage = original.foto.name, original.foto.storage
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        form = self.response_form(response)
        self.assertEqual(form.fields["hapus_1"].widget.input_type, "hidden")
        self.assertContains(response, 'data-tv-photo-remove', count=6)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertRedirects(self.post_slide({"foto_1": photo("replacement.png"), "hapus_1": "False"}), self.edit_url)
        self.assertFalse(storage.exists(old_name))
        self.assertFalse(DokumentasiTV.objects.filter(foto=old_name).exists())
        replacement = self.slide.fotos.get(nomor=1)
        self.assertEqual(self.slide.fotos.count(), 2)
        new_name = replacement.foto.name
        self.assertTrue(storage.exists(new_name))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertRedirects(self.post_slide({"hapus_1": "True"}), self.edit_url)
        self.assertFalse(storage.exists(new_name))
        self.assertFalse(DokumentasiTV.objects.filter(foto=new_name).exists())
        self.assertEqual(list(self.slide.fotos.values_list("pk", flat=True)), [kept.pk])
        self.assertTrue(storage.exists(kept.foto.name))

    def test_deleting_slide_removes_all_six_photo_records_and_files(self):
        self.client.force_login(self.user)
        self.post_slide({f"foto_{i}": photo(f"slide-{i}.png") for i in range(1, 7)})
        photos = list(self.slide.fotos.all())
        self.assertEqual(len(photos), 6)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertRedirects(self.client.post(reverse("landing:dokumentasi_delete", args=[self.slide.pk])), self.url)
        self.assertFalse(SlideDokumentasi.objects.filter(pk=self.slide.pk).exists())
        self.assertFalse(DokumentasiTV.objects.filter(slide_id=self.slide.pk).exists())
        self.assertTrue(all(not item.foto.storage.exists(item.foto.name) for item in photos))

    def test_shared_file_and_rolled_back_removal_are_not_cleaned(self):
        first = DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo())
        DokumentasiTV.objects.create(slide=self.slide, nomor=2, foto=first.foto.name)
        name, storage = first.foto.name, first.foto.storage
        with self.captureOnCommitCallbacks(execute=True):
            first.delete()
        self.assertTrue(storage.exists(name))
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                DokumentasiTV.objects.filter(nomor=2).delete()
                raise RuntimeError("rollback")
        self.assertTrue(DokumentasiTV.objects.filter(nomor=2).exists())
        self.assertTrue(storage.exists(name))

    def test_conflicting_replace_and_clear_are_rejected(self):
        form = DokumentasiTVForm(slide=self.slide, data={"hapus_1": "on"}, files={"foto_1": photo()})
        self.assertFalse(form.is_valid())
        self.assertIn("foto_1", form.errors)
        self.assertFalse(DokumentasiTV.objects.exists())

    def test_slot_range_is_enforced_by_model_and_database(self):
        for nomor in (0, 7):
            with self.subTest(nomor=nomor):
                with self.assertRaises(ValidationError):
                    DokumentasiTV(slide=self.slide, nomor=nomor, foto="sample.png").full_clean()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    DokumentasiTV.objects.create(slide=self.slide, nomor=nomor, foto="sample.png")

    def test_display_and_polling_show_six_slots_and_hide_empty_documentation(self):
        with self.assertNumQueries(1):
            data = get_tv_documentation()
        self.assertEqual(data, [])
        response = self.client.get(self.display)
        self.assertNotContains(response, 'data-tv-documentation-slide=')
        first = DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo("one.png"))
        last = DokumentasiTV.objects.create(slide=self.slide, nomor=6, foto=photo("six.png"))
        with self.assertNumQueries(1):
            data = get_tv_documentation()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["slots"][5]["foto"].name, last.foto.name)
        for mode in ("", "?tv=1"):
            response = self.client.get(self.display + mode)
            self.assertContains(response, f'data-tv-documentation-slide="{self.slide.pk}"')
            self.assertContains(response, 'class="tv-documentation__item"', count=2)
            self.assertContains(response, first.foto.url)
            self.assertContains(response, last.foto.url)
        response = self.client.get(self.refresh)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response.json()["documentationSlides"][0]["html"].count('<img '), 2)
        with self.captureOnCommitCallbacks(execute=True):
            DokumentasiTV.objects.all().delete()
        self.assertEqual(self.client.get(self.refresh).json()["documentationSlides"], [])
        self.assertEqual(self.client.get(reverse("dashboard:display_active_data", args=["wrong-slug"])).status_code, 404)

    def test_add_slide_and_save_twelve_images_independently(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.post_slide({f"foto_{i}": photo(f"first-{i}.png") for i in range(1, 7)}), self.edit_url)
        original = list(self.slide.fotos.values_list("nomor", "foto"))
        response = self.client.post(self.url, {"action": "tambah"})
        second = SlideDokumentasi.objects.latest("pk")
        second_url = f"{self.url}#slide-{second.pk}"
        self.assertRedirects(response, second_url)
        self.assertNotEqual(second.pk, self.slide.pk)
        response = self.client.get(second_url)
        self.assertContains(response, 'type="file"', count=12)
        self.assertContains(response, 'Tambah Slide')
        self.assertContains(response, f'id="slide-{self.slide.pk}"')
        self.assertContains(response, f'id="slide-{second.pk}"')
        self.assertNotContains(response, 'id="tv-doc-slide"')
        self.assertFalse(second.fotos.exists())
        self.assertRedirects(self.post_slide({f"foto_{i}": photo(f"second-{i}.png") for i in range(1, 7)}, slide=second), second_url)
        self.assertEqual(DokumentasiTV.objects.count(), 12)
        self.assertEqual(list(self.slide.fotos.values_list("nomor", "foto")), original)
        with self.assertNumQueries(1):
            data = get_tv_documentation()
        self.assertEqual([slide["id"] for slide in data], [self.slide.pk, second.pk])
        self.assertTrue(all(len(slide["slots"]) == 6 for slide in data))
        response = self.client.get(self.display + "?tv=1")
        self.assertContains(response, 'data-tv-documentation-slide=', count=2)
        self.assertContains(response, 'class="tv-documentation__item"', count=12)
        payload = self.client.get(self.refresh).json()["documentationSlides"]
        self.assertEqual([slide["id"] for slide in payload], [self.slide.pk, second.pk])
        self.assertTrue(all(slide["html"].count('<img ') == 6 for slide in payload))
        with self.captureOnCommitCallbacks(execute=True):
            self.post_slide({f"hapus_{i}": "on" for i in range(1, 7)}, slide=second)
        self.assertTrue(SlideDokumentasi.objects.filter(pk=second.pk).exists())
        self.assertEqual([slide["id"] for slide in self.client.get(self.refresh).json()["documentationSlides"]], [self.slide.pk])
        self.assertEqual(list(self.slide.fotos.values_list("nomor", "foto")), original)

    def test_invalid_second_slide_upload_keeps_both_slides_unchanged(self):
        second = SlideDokumentasi.objects.create()
        first = DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo("first.png"))
        old = DokumentasiTV.objects.create(slide=second, nomor=1, foto=photo("second.png"))
        self.client.force_login(self.user)
        response = self.post_slide({
            "foto_1": photo("new.png"), "foto_6": SimpleUploadedFile("bad.png", b"bad image"),
        }, slide=second)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foto_6", self.response_form(response, second).errors)
        self.assertFalse(self.response_form(response).is_bound)
        self.assertEqual(list(DokumentasiTV.objects.values_list("foto", flat=True)), [first.foto.name, old.foto.name])

    def test_save_target_actions_and_addition_permissions_are_checked(self):
        self.client.force_login(self.user)
        before = SlideDokumentasi.objects.count()
        for query, status in (("abc", 400), ("-1", 400), ("999999999", 404)):
            self.assertEqual(self.client.post(self.url, {"action": "simpan", "slide_id": query}).status_code, status)
        self.assertEqual(self.client.post(self.url, {"action": "invalid"}).status_code, 400)
        self.set_role("Admin Lab")
        self.assertRedirects(self.client.post(self.url, {"action": "tambah"}), reverse("dashboard:index"), fetch_redirect_response=False)
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {"action": "tambah"}).status_code, 302)
        self.assertEqual(SlideDokumentasi.objects.count(), before)

    def test_same_slot_number_is_allowed_across_slides_but_not_within_one_slide(self):
        DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo())
        second = SlideDokumentasi.objects.create()
        DokumentasiTV.objects.create(slide=second, nomor=1, foto=photo())
        with self.assertRaises(IntegrityError), transaction.atomic():
            DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto="duplicate.png")

    def test_listing_renders_all_slides_with_unique_upload_fields_and_one_photo_query(self):
        for _ in range(3):
            SlideDokumentasi.objects.create()
        self.client.force_login(self.user)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="file"', count=24)
        self.assertContains(response, 'data-delete-modal="master"', count=4)
        self.assertNotContains(response, 'tv-doc-slide')
        self.assertNotContains(response, 'tv-photo-toolbar__picker')
        ids = re.findall(r'<input[^>]+type="file"[^>]+id="([^"]+)"', response.content.decode())
        self.assertEqual(len(ids), 24)
        self.assertEqual(len(set(ids)), 24)
        photo_queries = [q for q in queries if 'FROM "landing_dokumentasitv"' in q["sql"]]
        self.assertEqual(len(photo_queries), 1)

    def test_slide_labels_stay_sequential_after_deleting_and_adding(self):
        second = SlideDokumentasi.objects.create()
        third = SlideDokumentasi.objects.create()
        kept = DokumentasiTV.objects.create(slide=third, nomor=1, foto=photo("keep.png"))
        self.client.force_login(self.user)
        self.client.post(reverse("landing:dokumentasi_delete", args=[second.pk]))
        self.client.post(self.url, {"action": "tambah"})
        fourth = SlideDokumentasi.objects.latest("pk")
        response = self.client.get(self.url)
        items = response.context["slides"]
        self.assertEqual([item["nomor"] for item in items], [1, 2, 3])
        self.assertEqual([item["slide"].pk for item in items], [self.slide.pk, third.pk, fourth.pk])
        titles = re.findall(r'<h3 class="table-title"[^>]*>(.*?)</h3>', response.content.decode())
        self.assertEqual(titles, [f"Slide {i} - Konten Kegiatan TV" for i in range(1, 4)])
        self.assertContains(response, f'data-delete-url="{reverse("landing:dokumentasi_delete", args=[third.pk])}" data-item-name="Slide 2"')
        self.assertContains(response, "Simpan Slide 3")
        kept.refresh_from_db()
        self.assertEqual(kept.slide_id, third.pk)
        self.assertTrue(kept.foto.storage.exists(kept.foto.name))
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("landing:dokumentasi_delete", args=[third.pk]), follow=True)
        self.assertContains(response, "Slide 2 dokumentasi berhasil dihapus.")
        self.assertTrue(SlideDokumentasi.objects.filter(pk=fourth.pk).exists())
        self.assertEqual([item["nomor"] for item in response.context["slides"]], [1, 2])

    def test_numbering_restarts_at_one_after_all_slides_are_removed(self):
        old_id = self.slide.pk
        self.client.force_login(self.user)
        self.client.post(reverse("landing:dokumentasi_delete", args=[old_id]))
        self.client.post(self.url, {"action": "tambah"})
        response = self.client.get(self.url)
        item = response.context["slides"][0]
        self.assertGreater(item["slide"].pk, old_id)
        self.assertEqual(item["nomor"], 1)
        self.assertContains(response, "Slide 1 - Konten Kegiatan TV")
        self.assertContains(response, 'data-item-name="Slide 1"')

    def test_delete_empty_slide_and_last_slide_then_add_again(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"action": "tambah"})
        second = SlideDokumentasi.objects.latest("pk")
        self.assertRedirects(response, f"{self.url}#slide-{second.pk}")
        self.assertRedirects(self.client.post(reverse("landing:dokumentasi_delete", args=[second.pk])), self.url)
        self.assertFalse(SlideDokumentasi.objects.filter(pk=second.pk).exists())
        self.assertTrue(SlideDokumentasi.objects.filter(pk=self.slide.pk).exists())
        self.client.post(reverse("landing:dokumentasi_delete", args=[self.slide.pk]))
        self.assertFalse(SlideDokumentasi.objects.exists())
        response = self.client.get(self.url)
        self.assertContains(response, "Belum ada slide dokumentasi")
        self.assertNotContains(response, 'type="file"')
        self.assertFalse(SlideDokumentasi.objects.exists())
        self.client.post(self.url, {"action": "tambah"})
        self.assertEqual(SlideDokumentasi.objects.count(), 1)

    def test_delete_slide_cleans_its_files_after_commit_and_keeps_other_slides(self):
        first = DokumentasiTV.objects.create(slide=self.slide, nomor=1, foto=photo("shared.png"))
        second = SlideDokumentasi.objects.create()
        DokumentasiTV.objects.create(slide=second, nomor=1, foto=first.foto.name)
        removed = DokumentasiTV.objects.create(slide=second, nomor=2, foto=photo("removed.png"))
        storage, name = removed.foto.storage, removed.foto.name
        self.client.force_login(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertRedirects(self.client.post(reverse("landing:dokumentasi_delete", args=[second.pk])), self.url)
            self.assertTrue(storage.exists(name))
        self.assertFalse(SlideDokumentasi.objects.filter(pk=second.pk).exists())
        self.assertFalse(DokumentasiTV.objects.filter(slide_id=second.pk).exists())
        self.assertFalse(storage.exists(name))
        self.assertTrue(storage.exists(first.foto.name))
        self.assertTrue(self.slide.fotos.filter(pk=first.pk).exists())
        self.assertEqual([s["id"] for s in self.client.get(self.refresh).json()["documentationSlides"]], [self.slide.pk])

    def test_delete_requires_super_admin_post_csrf_and_existing_slide(self):
        url = reverse("landing:dokumentasi_delete", args=[self.slide.pk])
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(url).status_code, 302)
        self.client.force_login(self.user)
        for name in ("User", "Admin Lab", "Teknisi Lab", "Kepala Lab", "Pimpinan"):
            self.set_role(name)
            for method in (self.client.get, self.client.post):
                self.assertRedirects(method(url), reverse("dashboard:index"), fetch_redirect_response=False)
        self.set_role("Super Admin")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(reverse("landing:dokumentasi_delete", args=[99999999])).status_code, 404)
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(self.user)
        self.assertEqual(secure_client.post(url).status_code, 403)
        self.assertTrue(SlideDokumentasi.objects.filter(pk=self.slide.pk).exists())


class DocumentationMigrationTests(TransactionTestCase):
    def test_existing_six_photos_become_first_slide_without_changing_files(self):
        old_target = [("landing", "0009_dokumentasi_tv")]
        new_target = [("landing", "0010_dokumentasi_slide")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(new_target))
        old_apps = executor.loader.project_state(old_target).apps
        OldPhoto = old_apps.get_model("landing", "DokumentasiTV")
        for i in range(1, 7):
            OldPhoto.objects.create(nomor=i, foto=f"landing/dokumentasi/original-{i}.png")
        executor = MigrationExecutor(connection)
        executor.migrate(new_target)
        new_apps = executor.loader.project_state(new_target).apps
        Slide = new_apps.get_model("landing", "SlideDokumentasi")
        Photo = new_apps.get_model("landing", "DokumentasiTV")
        first = Slide.objects.get()
        self.assertEqual(list(Photo.objects.values_list("slide_id", "nomor", "foto")), [
            (first.pk, i, f"landing/dokumentasi/original-{i}.png") for i in range(1, 7)
        ])
        second = Slide.objects.create()
        added = Photo.objects.create(slide_id=second.pk, nomor=1, foto="landing/dokumentasi/new.png")
        self.assertGreater(added.pk, 6)
