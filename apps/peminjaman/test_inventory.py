import shutil
import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from apps.master_data.models import (
    BarangLaboratorium,
    KetersediaanChoices,
    PeralatanLaboratorium,
    StatusBarangChoices,
)
from apps.pengguna.models import Role, User

from .inventory import sync_active_inventory
from .models import (
    PeminjamanBarangLaboratorium,
    PeminjamanPeralatanLaboratorium,
    PeminjamanRequest,
    ReturnStepChoices,
    StepChoices,
)
from .views import _build_inventory_context


class InventoryAvailabilitySyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="test")

    def _create_request(self, **kwargs):
        defaults = {
            "peminjam": self.user,
            "nama_peminjam": "User",
            "tanggal_mulai": date(2026, 1, 1),
            "tanggal_selesai": date(2026, 1, 2),
            "aset_sudah_dialokasikan": True,
        }
        defaults.update(kwargs)
        return PeminjamanRequest.objects.create(**defaults)

    def _create_peralatan_lab(self):
        return PeralatanLaboratorium.objects.create(
            nama_barang="Peralatan Lab",
            tipe_merek_barang="Tipe A",
            jenis_barang="Alat",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="PL-001",
            volume=1,
            lokasi_barang="Lab",
        )

    def test_completed_allocation_does_not_block_peralatan_lab_selection(self):
        item = self._create_peralatan_lab()
        completed = self._create_request(
            current_step=StepChoices.APPROVED,
            return_current_step=ReturnStepChoices.COMPLETED,
        )
        PeminjamanPeralatanLaboratorium.objects.create(
            pengajuan=completed,
            barang=item,
            volume=1,
        )
        PeralatanLaboratorium.objects.filter(pk=item.pk).update(
            volume_dipinjam=1,
            ketersediaan=KetersediaanChoices.TIDAK_TERSEDIA,
        )

        context = _build_inventory_context()
        item.refresh_from_db()
        row = next(row for row in context["peralatan_lab_items"] if row.pk == item.pk)

        self.assertEqual(item.volume_dipinjam, 0)
        self.assertEqual(item.ketersediaan, KetersediaanChoices.TERSEDIA)
        self.assertEqual(row.available_stock, 1)
        self.assertTrue(row.is_available_for_selection)
        self.assertEqual(row.selection_ketersediaan, KetersediaanChoices.TERSEDIA)

    def test_active_allocation_keeps_peralatan_lab_unavailable(self):
        item = self._create_peralatan_lab()
        active = self._create_request(current_step=StepChoices.ADMIN_LAB)
        PeminjamanPeralatanLaboratorium.objects.create(
            pengajuan=active,
            barang=item,
            volume=1,
        )

        sync_active_inventory(peralatan_lab_ids=[item.pk])
        item.refresh_from_db()

        self.assertEqual(item.volume_dipinjam, 1)
        self.assertEqual(item.ketersediaan, KetersediaanChoices.TIDAK_TERSEDIA)

    def test_completed_allocation_clears_lab_borrowed_flag(self):
        item = BarangLaboratorium.objects.create(
            nama_barang="Alat Survei",
            tipe_merek_barang="Tipe B",
            jenis_barang="Alat",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="LAB-001",
            lokasi_barang="Lab",
        )
        completed = self._create_request(
            current_step=StepChoices.APPROVED,
            return_current_step=ReturnStepChoices.COMPLETED,
        )
        PeminjamanBarangLaboratorium.objects.create(pengajuan=completed, barang=item)
        BarangLaboratorium.objects.filter(pk=item.pk).update(
            sedang_dipinjam=True,
            ketersediaan=KetersediaanChoices.TIDAK_TERSEDIA,
        )

        sync_active_inventory(lab_ids=[item.pk])
        item.refresh_from_db()

        self.assertFalse(item.sedang_dipinjam)
        self.assertEqual(item.ketersediaan, KetersediaanChoices.TERSEDIA)


class PeminjamanPhotoFormTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)

        role, _ = Role.objects.get_or_create(nama="User")
        self.user = User.objects.create_user(
            username="peminjaman-foto-user",
            password="test-pass-123",
        )
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])

        self.item_foto = BarangLaboratorium.objects.create(
            nama_barang="Drone dengan Foto",
            tipe_merek_barang="DJI Foto",
            jenis_barang="Drone",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="LAB-FOTO-001",
            lokasi_barang="Gudang",
            foto_barang=SimpleUploadedFile(
                "drone.jpg",
                b"test-image-content",
                content_type="image/jpeg",
            ),
        )
        BarangLaboratorium.objects.create(
            nama_barang="Drone tanpa Foto",
            tipe_merek_barang="DJI Kosong",
            jenis_barang="Drone",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="LAB-FOTO-002",
            lokasi_barang="Gudang",
        )
        self.client.force_login(self.user)

    def test_form_tambah_menampilkan_thumbnail_dan_modal_preview_foto(self):
        response = self.client.get(reverse("peminjaman:tambah"))

        self.assertEqual(response.status_code, 200)
        response_html = response.content.decode()
        survey_start = response_html.index('id="inventorySectionSurvey"')
        name_header = response_html.index(">Nama Barang</th>", survey_start)
        photo_header = response_html.index(">Foto Barang</th>", survey_start)
        type_header = response_html.index(">Tipe / Merek</th>", survey_start)
        code_header = response_html.index(">Kode Laboratorium</th>", survey_start)
        self.assertLess(name_header, photo_header)
        self.assertLess(photo_header, type_header)
        self.assertLess(type_header, code_header)
        self.assertContains(response, 'class="inventory-col inventory-col--fit"')
        self.assertContains(response, 'class="col-photo"')
        self.assertContains(response, 'colspan="9"')
        self.assertContains(response, "data-inventory-photo-open", count=1)
        self.assertContains(
            response,
            f'data-photo-src="{self.item_foto.foto_barang.url}"',
        )
        self.assertContains(response, 'class="inventory-photo__thumb"')
        self.assertContains(response, 'class="inventory-photo__empty"')
        self.assertContains(response, 'id="inventoryPhotoModal"', count=1)
        self.assertContains(response, "Preview Foto Barang")
