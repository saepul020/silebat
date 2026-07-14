from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook

from apps.master_data.models import KondisiBarangChoices
from apps.master_data.views import (
    IMPORT_FASILITAS_RUANGAN_HEADERS,
    _validate_fasilitas_ruangan_import,
)


class AssetVolumeImportTests(TestCase):
    def _file(self, values):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(IMPORT_FASILITAS_RUANGAN_HEADERS)
        worksheet.append([values.get(header, "") for header in IMPORT_FASILITAS_RUANGAN_HEADERS])
        output = BytesIO()
        workbook.save(output)
        return SimpleUploadedFile(
            "fasilitas.xlsx",
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_non_bmn_bervolume_mengikuti_volume_input(self):
        rows, errors = _validate_fasilitas_ruangan_import(self._file({
            "Status Barang": "Non BMN",
            "Barang Ber-volume": "Ya",
            "Nama Barang": "Kursi Uji",
            "Tipe / Merek Barang": "Tipe A",
            "Jenis Barang": "Kursi",
            "Volume Baik": 8,
            "Volume Rusak": 2,
            "Satuan": "Buah",
            "Kategori Barang": "Fasilitas Ruangan",
        }))

        self.assertEqual(errors, [])
        self.assertTrue(rows[0]["bervolume"])
        self.assertEqual(rows[0]["volume"], 8)
        self.assertEqual(rows[0]["volume_rusak"], 2)

    def test_non_bmn_tidak_bervolume_mengikuti_kondisi(self):
        rows, errors = _validate_fasilitas_ruangan_import(self._file({
            "Status Barang": "Non BMN",
            "Barang Ber-volume": "Tidak",
            "Nama Barang": "Meja Uji",
            "Tipe / Merek Barang": "Tipe B",
            "Jenis Barang": "Meja",
            "Satuan": "Unit",
            "Kategori Barang": "Fasilitas Ruangan",
            "Kondisi Barang": KondisiBarangChoices.RUSAK,
        }))

        self.assertEqual(errors, [])
        self.assertFalse(rows[0]["bervolume"])
        self.assertEqual(rows[0]["volume"], 0)
        self.assertEqual(rows[0]["volume_rusak"], 1)
