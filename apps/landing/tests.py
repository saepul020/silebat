import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from PIL import Image

from apps.master_data.models import KategoriBarangLaboratoriumChoices
from apps.pengguna.models import Role, User

from .forms import LandingPeralatanCardForm
from .models import MAX_EQUIPMENT_PHOTOS, LandingPeralatanCard, LandingPeralatanFoto
from .services import invalidate_public_landing_cache


def image_upload(name):
    output = BytesIO()
    Image.new("RGB", (160, 120), color=(16, 62, 111)).save(output, format="PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


def card_form_data(**overrides):
    data = {
        "kategori_barang": [KategoriBarangLaboratoriumChoices.DRONE],
        "nama_barang": ["Drone Uji"],
        "jenis_barang": ["Pesawat tanpa awak"],
        "merek_tipe_alat": ["Tipe A"],
        "fungsi_alat": ["Pemetaan"],
        "spesifikasi_alat": ["Kamera resolusi tinggi"],
        "ringkasan_alat": ["Peralatan survei udara"],
        "urutan": ["1"],
        "is_active": ["on"],
    }
    for key, value in overrides.items():
        data[key] = value if isinstance(value, list) else [value]
    return MultiValueDict(data)


class LandingSeoRouteTests(SimpleTestCase):
    @patch("apps.landing.views.get_public_landing_context")
    def test_homepage_renders_core_seo_and_lcp_markup(self, get_context):
        get_context.return_value = {
            "landing_stats": {"current_year": 2026},
            "landing_charts": {},
            "inventory_cards": [],
            "equipment_cards": [],
        }

        response = self.client.get(reverse("landing:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta name="description"')
        self.assertContains(response, '<link rel="canonical" href="http://testserver/"')
        self.assertContains(response, "foto-kegiatan-gl-mobile.webp")
        self.assertContains(response, 'fetchpriority="high"')
        self.assertContains(response, "vendor/chartjs/chart.umd.min.js")
        self.assertNotContains(response, "fonts.googleapis.com")

    def test_robots_txt_points_to_sitemap(self):
        response = self.client.get(reverse("landing:robots_txt"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertContains(response, "User-agent: *")
        self.assertContains(response, "/sitemap.xml")

    def test_sitemap_contains_homepage(self):
        response = self.client.get(reverse("landing:sitemap_xml"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        self.assertContains(response, "<loc>http://testserver/</loc>")


class LandingEquipmentGalleryTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)
        invalidate_public_landing_cache()
        self.addCleanup(invalidate_public_landing_cache)

    def test_form_saves_up_to_five_photos(self):
        files = MultiValueDict(
            {"foto_barang": [image_upload(f"foto-{index}.png") for index in range(5)]}
        )
        form = LandingPeralatanCardForm(card_form_data(), files)

        self.assertTrue(form.is_valid(), form.errors)
        card = form.save()

        self.assertEqual(card.fotos.count(), MAX_EQUIPMENT_PHOTOS)
        self.assertEqual(
            list(card.fotos.values_list("urutan", flat=True)),
            [1, 2, 3, 4, 5],
        )
        self.assertTrue(
            all(photo.foto.storage.exists(photo.foto.name) for photo in card.fotos.all())
        )

    def test_form_rejects_more_than_five_photos(self):
        files = MultiValueDict(
            {"foto_barang": [image_upload(f"foto-{index}.png") for index in range(6)]}
        )
        form = LandingPeralatanCardForm(card_form_data(), files)

        self.assertFalse(form.is_valid())
        self.assertIn("Maksimal 5 foto", form.errors["foto_barang"][0])

    def test_form_rejects_total_above_five_when_editing(self):
        card = LandingPeralatanCard.objects.create(
            kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
            nama_barang="Drone Lama",
            jenis_barang="Drone",
            merek_tipe_alat="Tipe Lama",
            fungsi_alat="Pemetaan",
            spesifikasi_alat="Spesifikasi",
            ringkasan_alat="Ringkasan",
            urutan=1,
        )
        for index in range(4):
            LandingPeralatanFoto.objects.create(
                card=card,
                foto=image_upload(f"lama-{index}.png"),
                urutan=index + 1,
            )
        files = MultiValueDict(
            {"foto_barang": [image_upload("baru-1.png"), image_upload("baru-2.png")]}
        )
        form = LandingPeralatanCardForm(card_form_data(), files, instance=card)

        self.assertFalse(form.is_valid())
        self.assertIn("Total foto maksimal 5", form.errors["foto_barang"][0])

    def test_edit_can_delete_and_add_gallery_photos(self):
        card = LandingPeralatanCard.objects.create(
            kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
            nama_barang="Drone Lama",
            jenis_barang="Drone",
            merek_tipe_alat="Tipe Lama",
            fungsi_alat="Pemetaan",
            spesifikasi_alat="Spesifikasi",
            ringkasan_alat="Ringkasan",
            urutan=1,
        )
        first = LandingPeralatanFoto.objects.create(card=card, foto=image_upload("lama-1.png"), urutan=1)
        second = LandingPeralatanFoto.objects.create(card=card, foto=image_upload("lama-2.png"), urutan=2)
        files = MultiValueDict({"foto_barang": [image_upload("baru.png")]})
        form = LandingPeralatanCardForm(
            card_form_data(hapus_foto_ids=[str(first.pk)]),
            files,
            instance=card,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.assertFalse(LandingPeralatanFoto.objects.filter(pk=first.pk).exists())
        self.assertTrue(LandingPeralatanFoto.objects.filter(pk=second.pk).exists())
        self.assertEqual(card.fotos.count(), 2)
        self.assertEqual(list(card.fotos.values_list("urutan", flat=True)), [1, 2])

    def test_invalid_edit_keeps_selected_photo_delete_state(self):
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        user = User.objects.create_user(username="landing-invalid-edit", password="test-pass-123")
        user.safe_profile.role = role
        user.safe_profile.save(update_fields=["role"])
        card = LandingPeralatanCard.objects.create(
            kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
            nama_barang="Drone Lama",
            jenis_barang="Drone",
            merek_tipe_alat="Tipe Lama",
            fungsi_alat="Pemetaan",
            spesifikasi_alat="Spesifikasi",
            ringkasan_alat="Ringkasan",
            urutan=1,
        )
        photo = LandingPeralatanFoto.objects.create(card=card, foto=image_upload("lama.png"))
        self.client.force_login(user)

        response = self.client.post(
            reverse("landing:equipment_update", args=[card.pk]),
            card_form_data(nama_barang="", hapus_foto_ids=[str(photo.pk)]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].deleted_photo_ids, {str(photo.pk)})
        self.assertTrue(LandingPeralatanFoto.objects.filter(pk=photo.pk).exists())

    def test_deleting_card_cleans_gallery_files(self):
        card = LandingPeralatanCard.objects.create(
            kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
            nama_barang="Drone Hapus",
            jenis_barang="Drone",
            merek_tipe_alat="Tipe Hapus",
            fungsi_alat="Pemetaan",
            spesifikasi_alat="Spesifikasi",
            ringkasan_alat="Ringkasan",
            urutan=1,
        )
        photo = LandingPeralatanFoto.objects.create(card=card, foto=image_upload("hapus.png"))
        storage = photo.foto.storage
        name = photo.foto.name
        self.assertTrue(storage.exists(name))

        card.delete()

        self.assertFalse(storage.exists(name))

    def test_public_landing_renders_slider_and_lightbox(self):
        card = LandingPeralatanCard.objects.create(
            kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
            nama_barang="Drone Galeri",
            jenis_barang="Drone",
            merek_tipe_alat="Tipe Galeri",
            fungsi_alat="Pemetaan",
            spesifikasi_alat="Spesifikasi",
            ringkasan_alat="Ringkasan",
            urutan=1,
        )
        LandingPeralatanFoto.objects.create(card=card, foto=image_upload("galeri-1.png"), urutan=1)
        LandingPeralatanFoto.objects.create(card=card, foto=image_upload("galeri-2.png"), urutan=2)

        response = self.client.get(reverse("landing:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-equipment-gallery", count=1)
        self.assertContains(response, "data-gallery-slide", count=2)
        self.assertContains(response, "data-equipment-lightbox", count=1)

    def test_super_admin_edit_page_uses_multiple_gallery_input(self):
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        user = User.objects.create_user(username="landing-admin", password="test-pass-123")
        user.safe_profile.role = role
        user.safe_profile.save(update_fields=["role"])
        card = LandingPeralatanCard.objects.create(
            kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
            nama_barang="Drone Edit",
            jenis_barang="Drone",
            merek_tipe_alat="Tipe Edit",
            fungsi_alat="Pemetaan",
            spesifikasi_alat="Spesifikasi",
            ringkasan_alat="Ringkasan",
            urutan=1,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("landing:equipment_update", args=[card.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-gallery-upload")
        self.assertContains(response, "data-gallery-trigger")
        self.assertContains(response, "data-gallery-strip")
        self.assertContains(response, 'multiple="multiple"')
        self.assertContains(response, "Maksimal 5 foto")
