import html
import re
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.html import escape

from .templatetags.tv_tags import tv_lines


def lines(markup):
    return [html.unescape(value) for value in re.findall(r'<span class="tv-wrap__line">(.*?)</span>', markup)]


class TvTextTests(SimpleTestCase):
    def test_word_boundaries_and_character_limits_include_spaces(self):
        self.assertEqual(lines(tv_lines("Verifikasi Peminjaman - Ketua Tim", 22)), ["Verifikasi Peminjaman", "- Ketua Tim"])
        self.assertEqual(lines(tv_lines("TKTM - Direktorat BINTEK SDA", 18)), ["TKTM - Direktorat", "BINTEK SDA"])
        self.assertEqual(lines(tv_lines("Belum Diproses", 22)), ["Belum Diproses"])
        self.assertEqual(lines(tv_lines("  TKTM\n -  Direktorat   BINTEK SDA ", 18)), ["TKTM - Direktorat", "BINTEK SDA"])

    def test_long_words_unicode_and_empty_fields_preserve_content(self):
        for width in (18, 22):
            for text in ("A" * width, "B" * (width + 1), "Perolehan " + "É" * 60, "Direktorat 😀 SDA"):
                result = lines(tv_lines(text, width))
                self.assertTrue(all(len(line) <= width for line in result))
                self.assertEqual("".join(result).replace(" ", ""), text.replace(" ", ""))
        self.assertEqual(tv_lines(None, 22), "")
        self.assertEqual(tv_lines("", 18), "")

    def test_wrapping_escapes_html_without_losing_text(self):
        text = '<script>alert("asal")</script> & <img src=x onerror=alert(1)>'
        markup = tv_lines(text, 18)
        self.assertNotIn("<script>", markup)
        self.assertNotIn("<img", markup)
        self.assertEqual("".join(lines(markup)).replace(" ", ""), text.replace(" ", ""))

    def test_tv_partials_wrap_only_status_and_origin_fields(self):
        row = render_to_string("dashboard/partials/active_rows.html", {"active_peminjaman": [{
            "nomor_pengajuan": "PMJ-1", "nama_peminjam": "Nama Peminjam Panjang",
            "instansi_tujuan_lainnya": "Direktorat SDA",
            "proses_peminjaman_label": "Verifikasi Peminjaman - Ketua Tim",
            "proses_pengembalian_label": "Belum Diproses",
        }]})
        self.assertIn("Nama Peminjam Panjang", row)
        self.assertEqual(lines(row), ["Verifikasi Peminjaman", "- Ketua Tim", "Belum Diproses"])
        equipment = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": [{
            "nomor": 1, "judul_barang": "Borehole TV Camera",
            "alat": SimpleNamespace(asal_perolehan="TKTM - Direktorat BINTEK SDA", kode_aset_bmn="3080149020-1", kode_laboratorium=""),
        }]})
        self.assertIn("3080149020-1", equipment)
        self.assertEqual(lines(equipment), ["TKTM - Direktorat", "BINTEK SDA"])

    def test_documentation_omits_empty_slots_for_every_photo_count(self):
        for count in range(7):
            with self.subTest(count=count):
                markup = render_to_string("dashboard/partials/tv_documentation.html", {"tv_documentation": {
                    "slots": [{"nomor": i + 1, "foto": SimpleNamespace(url=f"/photo-{i}.png") if i < count else None} for i in range(6)],
                }})
                self.assertEqual(markup.count('<figure class="tv-documentation__item">'), count)
                self.assertNotIn("belum diunggah", markup)

    def test_table_preserves_escaped_full_text_for_two_line_display(self):
        text = '<img src=x onerror="alert(1)"> & Direktorat ' * 12
        row = render_to_string("dashboard/partials/active_rows.html", {"active_peminjaman": [{
            "nomor_pengajuan": text, "nama_peminjam": text,
            "layanan_kegiatan_label": text, "instansi_tujuan_lainnya": text,
            "proses_peminjaman_label": text, "proses_pengembalian_label": text,
        }]})
        self.assertEqual(row.count('class="tv-table__text"'), 7)
        self.assertEqual(row.count(f'title="{escape(text)}"'), 6)
        self.assertNotIn("<img", row)
        self.assertTrue(all(len(line) <= 22 for line in lines(row)))
