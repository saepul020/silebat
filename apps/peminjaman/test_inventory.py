from datetime import date

from django.test import TestCase

from apps.master_data.models import (
    BarangLaboratorium,
    KetersediaanChoices,
    PeralatanLaboratorium,
    StatusBarangChoices,
)
from apps.pengguna.models import User

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
