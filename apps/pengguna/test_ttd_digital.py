from io import BytesIO
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import UserProfileForm
from .models import Role, User


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

    def test_profile_photo_remains_square_cropped(self):
        profile = self.user.safe_profile
        form = UserProfileForm(
            data={},
            files={"foto_profil": image_upload("profile.png", (320, 100))},
            instance=profile,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        profile.refresh_from_db()
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
        self.assertContains(response, "Auto crop 1:1", count=1)
