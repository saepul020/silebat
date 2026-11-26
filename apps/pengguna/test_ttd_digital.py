from io import BytesIO
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.pengguna.forms import UserProfileForm
from apps.pengguna.models import Role, User


def image_upload(name, size):
    output = BytesIO()
    Image.new("RGBA", size, (255, 255, 255, 0)).save(output, format="PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class TtdDigitalTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)
        self.user = User.objects.create_user(username="ttd-user", password="test-password")

    def test_ttd_digital_preserves_uploaded_ratio(self):
        profile = self.user.safe_profile
        form = UserProfileForm(
            data={},
            files={"ttd_digital": image_upload("ttd.png", (320, 100))},
            instance=profile,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        profile.refresh_from_db()
        with Image.open(profile.ttd_digital.path) as stored:
            self.assertEqual(stored.size, (320, 100))

    def test_profile_photo_is_cropped_to_portrait(self):
        for size in ((320, 100), (100, 320), (100, 100), (200, 300), (1, 1)):
            with self.subTest(size=size):
                form = UserProfileForm(
                    data={},
                    files={"foto_profil": image_upload("profile.png", size)},
                    instance=self.user.safe_profile,
                )
                self.assertTrue(form.is_valid(), form.errors)
                profile = form.save()
                profile.refresh_from_db()
                with Image.open(profile.foto_profil.path) as stored:
                    self.assertEqual(stored.width * 3, stored.height * 2)
                    if size == (200, 300):
                        self.assertEqual(stored.size, size)

    def test_profile_photo_is_preserved_without_new_upload(self):
        profile = self.user.safe_profile
        profile.foto_profil.save("old.png", image_upload("old.png", (100, 100)))
        old_name = profile.foto_profil.name
        form = UserProfileForm(data={}, instance=profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        profile.refresh_from_db()
        self.assertEqual(profile.foto_profil.name, old_name)
        with Image.open(profile.foto_profil.path) as stored:
            self.assertEqual(stored.size, (100, 100))

    def test_ttd_upload_card_uses_proportional_preview_mode(self):
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("pengguna:edit", args=[self.user.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "upload-card--signature", count=1)
        self.assertNotContains(response, "Rasio gambar asli")
        self.assertContains(response, 'class="upload-card__hint"', count=1)
        self.assertContains(response, "Auto crop 2:3", count=1)
        self.assertNotContains(response, "Auto crop 1:1")

        response = self.client.get(reverse("pengguna:tambah"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auto crop 2:3", count=1)
        self.assertNotContains(response, "Auto crop 1:1")
