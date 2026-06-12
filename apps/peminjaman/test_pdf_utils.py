from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import cm, mm
from reportlab.platypus import Table
from PIL import Image

from apps.peminjaman.pdf_utils import (
    BOTTOM_MARGIN,
    CONTENT_WIDTH,
    KOP_TOP_MARGIN,
    LEFT_MARGIN,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    PAIR_SIGN_COL_WIDTHS,
    PAIR_SIGN_GAP,
    PAIR_SIGN_WIDTH,
    RIGHT_MARGIN,
    SIGN_GAP,
    SIGN_WIDTH,
    SignName,
    TOP_MARGIN,
    _PdfDoc,
    _signature_cell,
    _dokumen_rows,
    _peminjam_rows,
    data_table,
    render_berita_acara_pdf,
    photo_grid,
    signature_block,
    signature_list,
    title_block,
)


class PdfLayoutTests(SimpleTestCase):
    def test_document_uses_requested_margins(self):
        doc = _PdfDoc(BytesIO(), "Uji PDF", has_kop=True)
        first = doc.pageTemplates[0].frames[0]
        later = doc.pageTemplates[1].frames[0]

        self.assertEqual(doc.pageTemplates[0].autoNextPageTemplate, "Later")
        self.assertAlmostEqual(LEFT_MARGIN, 1.5 * cm)
        self.assertAlmostEqual(RIGHT_MARGIN, 1.5 * cm)
        self.assertAlmostEqual(TOP_MARGIN, 1.5 * cm)
        self.assertAlmostEqual(BOTTOM_MARGIN, 1.5 * cm)
        self.assertAlmostEqual(KOP_TOP_MARGIN, 1 * cm)

        self.assertAlmostEqual(first._x1, LEFT_MARGIN)
        self.assertAlmostEqual(first._y1, BOTTOM_MARGIN)
        self.assertAlmostEqual(PAGE_WIDTH - first._x2, RIGHT_MARGIN)
        self.assertAlmostEqual(PAGE_HEIGHT - first._y2, KOP_TOP_MARGIN)

        self.assertAlmostEqual(later._x1, LEFT_MARGIN)
        self.assertAlmostEqual(later._y1, BOTTOM_MARGIN)
        self.assertAlmostEqual(PAGE_WIDTH - later._x2, RIGHT_MARGIN)
        self.assertAlmostEqual(PAGE_HEIGHT - later._y2, TOP_MARGIN)

    def test_document_without_kop_uses_normal_top_margin(self):
        doc = _PdfDoc(BytesIO(), "Uji PDF", has_kop=False)
        first = doc.pageTemplates[0].frames[0]

        self.assertAlmostEqual(PAGE_HEIGHT - first._y2, TOP_MARGIN)

    def test_data_table_repeats_header_row(self):
        table = data_table(["No.", "Nama"], [[1, "Barang"]])

        self.assertEqual(table.repeatRows, 1)
        self.assertEqual(table._ncols, 2)
        self.assertEqual(len(table._cellvalues[1]), 2)

    def test_data_table_centers_selected_columns_and_replaces_zero(self):
        center_headers = [
            "No.",
            "Status Barang",
            "Kode Aset BMN",
            "Kode Laboratorium",
            "Volume",
            "Satuan",
            "Kondisi Barang",
            "Tahun Perolehan",
            "Volume Dipinjam",
            "Dikembalikan",
            "Rusak",
            "Hilang",
            "Transfer",
            "Sisa",
        ]
        headers = [*center_headers, "Nama Barang"]
        table = data_table(headers, [[1, *["Baik"] * 3, 0, "unit", "Baik", 2025, 2, 1, 0, "0.000", 0, 0, "Pompa Uji"]])
        header = table._cellvalues[0]
        row = table._cellvalues[1]

        self.assertTrue(all(cell.style.alignment == TA_CENTER for cell in header))
        self.assertEqual(table._cellStyles[0][0].valign, "MIDDLE")
        self.assertTrue(all(cell.style.alignment == TA_CENTER for cell in row[:-1]))
        self.assertEqual(row[-1].style.alignment, TA_LEFT)
        self.assertEqual(row[4].getPlainText(), "-")
        self.assertEqual(row[10].getPlainText(), "-")
        self.assertEqual(row[11].getPlainText(), "-")
        self.assertEqual(row[12].getPlainText(), "-")
        self.assertEqual(row[13].getPlainText(), "-")

    def test_title_block_uses_two_column_grid_without_table(self):
        left = _peminjam_rows("Pengguna", "123", "0812", "user@example.com", "Bandung")
        right = _dokumen_rows("PJM-001", "Tanggal Peminjaman", "01 Januari 2026", "-", "-")
        story = title_block("DOKUMEN", left, right)
        grid = story[1]

        self.assertNotIsInstance(grid, Table)
        self.assertEqual(grid.left_rows, left)
        self.assertEqual(grid.right_rows, right)
        width, height = grid.wrap(500, 700)
        self.assertEqual(width, 500)
        self.assertGreater(height, 0)
        left_col, right_col = grid._cols
        self.assertLess(left_col[1], right_col[1])
        self.assertTrue(all(label_width < 38 * cm / 10 for _, label_width in grid._cols))
        for column, _ in grid._cols:
            self.assertTrue(all(item[2].getPlainText() == ":" for item in column))

        output = BytesIO()
        _PdfDoc(output, "Uji Grid", has_kop=False).build(story)
        self.assertTrue(output.getvalue().startswith(b"%PDF"))

        self.assertEqual(
            [label for label, _ in left],
            ["Nama", "NIP / NIK", "Nomor Telepon", "Email", "Alamat"],
        )
        self.assertEqual(
            [label for label, _ in right],
            [
                "Nomor Pengajuan",
                "Tanggal Peminjaman",
                "Tanggal Pengembalian",
                "Pengembalian Selesai",
            ],
        )

    def test_signature_block_uses_compact_right_aligned_grid_without_lines(self):
        date = "Bandung, 01 Januari 2026"
        block = signature_block(
            date,
            [("Peminjam,", None), ("Teknisi Laboratorium,", None)],
            [("Kepala Laboratorium,", None), ("Ketua Tim Layanan Teknis,", None)],
        )[0]
        date_table = block._content[1]
        date_gap = block._content[2]
        first_table = block._content[3]
        heading = block._content[5]
        knowing_table = block._content[6]

        self.assertLess(SIGN_WIDTH, CONTENT_WIDTH / 2)
        self.assertGreater(SIGN_WIDTH + SIGN_GAP, CONTENT_WIDTH / 2)
        self.assertEqual(first_table._argW, [SIGN_WIDTH, SIGN_GAP, SIGN_WIDTH])
        self.assertEqual(date_table._argW, first_table._argW)
        self.assertEqual(first_table._argW, knowing_table._argW)
        self.assertEqual(date_table._cellvalues[0][2].getPlainText(), date)
        self.assertAlmostEqual(date_gap.height, 1 * mm)
        self.assertEqual(heading.getPlainText(), "Mengetahui:")
        self.assertEqual(heading.style.textColor, colors.black)

        cells = [
            first_table._cellvalues[0][0],
            first_table._cellvalues[0][2],
            knowing_table._cellvalues[0][0],
            knowing_table._cellvalues[0][2],
        ]
        for cell in cells:
            self.assertFalse(any(item.__class__.__name__ == "HRFlowable" for item in cell))
            self.assertEqual(cell[-2].style.spaceBefore, 0)
            self.assertEqual(cell[-2].style.spaceAfter, 0)
            self.assertEqual(cell[-1].style.spaceBefore, 0)
            self.assertEqual(cell[-1].style.spaceAfter, 0)

        output = BytesIO()
        _PdfDoc(output, "Uji Tanda Tangan", has_kop=False).build([block])
        self.assertTrue(output.getvalue().startswith(b"%PDF"))

    def test_signature_name_stays_on_one_line_and_scales_to_column(self):
        name = "Nama Penanda Tangan Sangat Panjang Dengan Banyak Gelar Tambahan"
        user = SimpleNamespace(get_full_name=lambda: name, nip="123456789")
        cell = _signature_cell("Peminjam,", user)
        name_flow = cell[-2]

        self.assertIsInstance(name_flow, SignName)
        width, height = name_flow.wrap(SIGN_WIDTH, PAGE_HEIGHT)
        self.assertEqual(name_flow.getPlainText(), name)
        self.assertLessEqual(width, SIGN_WIDTH)
        self.assertLess(name_flow.font_size, name_flow.style.fontSize)
        self.assertLessEqual(height, name_flow.style.leading)

        output = BytesIO()
        block = signature_block(
            "Bandung, 01 Januari 2026",
            [("Peminjam,", user), ("Teknisi Laboratorium,", user)],
            [("Kepala Laboratorium,", user), ("Ketua Tim Layanan Teknis,", user)],
        )[0]
        _PdfDoc(output, "Uji Nama Tanda Tangan", has_kop=False).build([block])
        self.assertTrue(output.getvalue().startswith(b"%PDF"))

    def test_signature_list_supports_only_users_involved_in_process(self):
        user = SimpleNamespace(get_full_name=lambda: "Pelaksana", nip="123")
        block = signature_list(
            "Bandung, 01 Januari 2026",
            [
                ("Pelaksana Pemeliharaan,", user),
                ("Kepala Laboratorium,", user),
                ("Ketua Tim Layanan Teknis,", user),
            ],
        )[0]

        self.assertEqual(len(block._content), 7)
        first_signers = block._content[3]
        last_signer = block._content[5]
        self.assertEqual(first_signers._cellvalues[0][0][-2].getPlainText(), "Pelaksana")
        self.assertEqual(first_signers._cellvalues[0][2][-2].getPlainText(), "Pelaksana")
        self.assertEqual(last_signer._cellvalues[0][0][-2].getPlainText(), "Pelaksana")
        self.assertEqual(last_signer._cellvalues[0][2], "")

    def test_signature_list_centers_content_and_last_signer_on_canvas(self):
        pelaksana = SimpleNamespace(
            get_full_name=lambda: "Pelaksana",
            username="pelaksana",
            nip="111",
        )
        kepala = SimpleNamespace(
            get_full_name=lambda: "Kepala Lab",
            username="kepala",
            nip="222",
        )
        ketua = SimpleNamespace(
            get_full_name=lambda: "Ketua Tim",
            username="ketua",
            nip="333",
        )
        block = signature_list(
            "Bandung, 01 Januari 2026",
            [
                ("Pelaksana Pemeliharaan,", pelaksana),
                ("Kepala Laboratorium,", kepala),
                ("Ketua Tim Layanan Teknis,", ketua),
            ],
            centered=True,
            approval_label="Menyetujui:",
        )[0]

        date_table = block._content[1]
        first_signers = block._content[3]
        approval_heading = block._content[5]
        last_signer = block._content[6]
        self.assertEqual(date_table._cellvalues[0][0], "")
        self.assertEqual(date_table._cellvalues[0][1], "")
        self.assertEqual(
            date_table._cellvalues[0][2].getPlainText(),
            "Bandung, 01 Januari 2026",
        )
        self.assertEqual(date_table._cellvalues[0][2].style.alignment, TA_CENTER)
        self.assertEqual(first_signers._argW, PAIR_SIGN_COL_WIDTHS)
        self.assertEqual(date_table._argW, first_signers._argW)
        self.assertEqual(PAIR_SIGN_GAP, 30 * mm)
        self.assertEqual(first_signers._cellvalues[0][0][0].style.alignment, TA_CENTER)
        self.assertEqual(first_signers._cellvalues[0][1], "")
        self.assertEqual(first_signers._cellvalues[0][2][0].style.alignment, TA_CENTER)
        self.assertEqual(first_signers._cellvalues[0][0][-2].getPlainText(), "Pelaksana")
        self.assertEqual(first_signers._cellvalues[0][0][-1].getPlainText(), "NIP/NIK: 111")
        self.assertEqual(first_signers._cellvalues[0][2][-2].getPlainText(), "Kepala Lab")
        self.assertEqual(first_signers._cellvalues[0][2][-1].getPlainText(), "NIP/NIK: 222")
        self.assertEqual(
            approval_heading._cellvalues[0][1].getPlainText(),
            "Menyetujui:",
        )
        self.assertEqual(
            approval_heading._cellvalues[0][1].style.fontName,
            "Helvetica-Bold",
        )
        self.assertEqual(last_signer._cellvalues[0][0], "")
        self.assertEqual(
            last_signer._cellvalues[0][1][0].getPlainText(),
            "Ketua Tim Layanan Teknis,",
        )
        self.assertEqual(last_signer._cellvalues[0][2], "")
        self.assertEqual(last_signer._cellvalues[0][1][-2].getPlainText(), "Ketua Tim")
        self.assertEqual(last_signer._cellvalues[0][1][-1].getPlainText(), "NIP/NIK: 333")
        self.assertTrue(last_signer._cellvalues[0][1][-2].centered)
        self.assertEqual(
            first_signers._cellvalues[0][0][-2].wrap(PAIR_SIGN_WIDTH, PAGE_HEIGHT)[0],
            PAIR_SIGN_WIDTH,
        )
        self.assertEqual(
            first_signers._cellvalues[0][2][-2].wrap(PAIR_SIGN_WIDTH, PAGE_HEIGHT)[0],
            PAIR_SIGN_WIDTH,
        )

        output = BytesIO()
        _PdfDoc(output, "Uji Tanda Tangan Tengah", has_kop=False).build([block])
        self.assertTrue(output.getvalue().startswith(b"%PDF"))

    def test_photo_grid_builds_three_photos_in_one_row(self):
        with TemporaryDirectory() as directory:
            paths = []
            for index in range(3):
                path = Path(directory) / f"foto-{index}.png"
                Image.new("RGB", (120, 80), "white").save(path, format="PNG")
                paths.append(SimpleNamespace(name=path.name, path=str(path)))

            story = photo_grid(paths, header="Dokumentasi Pemeriksaan")

            table = story[0]
            self.assertEqual(table._ncols, 3)
            self.assertEqual(table._nrows, 2)
            self.assertEqual(
                table._cellvalues[0][0].getPlainText(),
                "Dokumentasi Pemeriksaan",
            )
            self.assertTrue(all(table._cellvalues[1]))
            self.assertTrue(
                all(cell.__class__.__name__ == "Image" for cell in table._cellvalues[1])
            )
            self.assertTrue(all(cell.drawHeight <= 18 * mm for cell in table._cellvalues[1]))

    def test_photo_grid_uses_automatic_uniform_header_height(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "foto.png"
            Image.new("RGB", (120, 80), "white").save(path, format="PNG")
            field = SimpleNamespace(name=path.name, path=str(path))

            table = photo_grid([field], header="Dokumentasi Pemeriksaan")[0]

        self.assertIsNone(table._argH[0])

    def test_berita_acara_uses_borrow_and_completed_dates(self):
        submitted = object()
        return_started = object()
        return_completed = object()
        obj = SimpleNamespace(
            kegiatan_survei=SimpleNamespace(all=lambda: []),
            survei_lainnya="",
            nama_peminjam="Pengguna",
            nip_peminjam="123",
            no_hp_peminjam="0812",
            email_peminjam="user@example.com",
            alamat_peminjam="Bandung",
            nomor_pengajuan="PJM-001",
            submitted_at=submitted,
            return_started_at=return_started,
            return_completed_at=return_completed,
            layanan_kegiatan_label="-",
            tim_kegiatan=None,
            instansi_tujuan=None,
            instansi_tujuan_lainnya="",
            tanggal_mulai=None,
            tanggal_selesai=None,
            total_hari=1,
            peminjam=None,
            get_kepala_lab_signer=lambda: None,
            get_return_pimpinan_signer=lambda: None,
        )
        formatted = {
            submitted: "01 Maret 2026",
            return_started: "12 Maret 2026",
            return_completed: "13 Maret 2026",
            None: "-",
        }

        with (
            patch("apps.peminjaman.pdf_utils.title_block", return_value=[]) as title_mock,
            patch("apps.peminjaman.pdf_utils.section", return_value=None),
            patch("apps.peminjaman.pdf_utils.info_table", return_value=None),
            patch("apps.peminjaman.pdf_utils._append_table"),
            patch("apps.peminjaman.pdf_utils.signature_block", return_value=[]) as sign_mock,
            patch("apps.peminjaman.pdf_utils.build_pdf"),
        ):
            render_berita_acara_pdf(
                BytesIO(),
                obj,
                {"rusak": [], "hilang": []},
                formatted.get,
                None,
            )

        document_rows = title_mock.call_args.args[2]
        self.assertEqual(
            document_rows,
            [
                ("Nomor Pengajuan", "PJM-001"),
                ("Tanggal Peminjaman", "01 Maret 2026"),
                ("Tanggal Pengembalian", "12 Maret 2026"),
                ("Pengembalian Selesai", "13 Maret 2026"),
            ],
        )
        self.assertEqual(sign_mock.call_args.args[0], "Bandung, 13 Maret 2026")
