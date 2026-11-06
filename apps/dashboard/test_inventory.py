from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from apps.landing.services import get_inventory_category_cards, get_tv_inventory_cards
from apps.master_data.models import BarangLaboratorium, KategoriBarangLaboratoriumChoices, KondisiBarangChoices


class TvInventoryTests(TestCase):
    labels = ["Borehole Camera", "Drone", "Geolistrik", "Infiltrasi", "Instrumen Keairan", "Logging"]

    def setUp(self):
        qr_patch = patch("apps.master_data.signals.ensure_master_qr_code")
        qr_patch.start()
        self.addCleanup(qr_patch.stop)
        self.sequence = 0

    def create_equipment(self, category, condition=KondisiBarangChoices.BAIK):
        self.sequence += 1
        return BarangLaboratorium.objects.create(
            nama_barang=f"Alat Rekap {self.sequence}", tipe_merek_barang="Merek Uji",
            jenis_barang="Alat Survei", status_barang="BMN",
            kode_aset_bmn=f"BMN-REKAP-{self.sequence}", kode_laboratorium=f"LAB-REKAP-{self.sequence}",
            kategori_barang=category, tahun_perolehan=2026, kondisi_barang=condition,
        )

    def test_empty_inventory_still_has_six_ordered_cards_and_existing_photos(self):
        with self.assertNumQueries(1):
            cards = get_tv_inventory_cards()
        self.assertEqual([card["label"] for card in cards], self.labels)
        self.assertTrue(all(card["total"] == 0 for card in cards))
        self.assertTrue(all(card["baik"] == 0 and card["rusak"] == 0 for card in cards))
        for card in cards:
            self.assertTrue((Path(settings.BASE_DIR) / "static" / card["img"]).is_file())
        with self.assertNumQueries(0):
            html = render_to_string("dashboard/partials/tv_inventory.html", {"tv_inventory_cards": cards})
        self.assertEqual(html.count('class="tv-equipment__card tv-summary"'), 6)
        self.assertNotIn("Pendukung Survei Lapangan", html)
        self.assertNotIn("Topografi (TS)", html)
        self.assertEqual(html.count('<dt>Rusak</dt><dd>0 unit</dd>'), 6)
        self.assertEqual(html.count('<dt>Baik</dt><dd>0 unit</dd>'), 6)

    def test_totals_match_landing_and_include_all_conditions_without_excluded_categories(self):
        categories = KategoriBarangLaboratoriumChoices
        for category in categories:
            self.create_equipment(category)
        for condition in (KondisiBarangChoices.RUSAK, KondisiBarangChoices.DALAM_PEMELIHARAAN, KondisiBarangChoices.HILANG):
            self.create_equipment(categories.BOREHOLE_CAMERA, condition)

        with self.assertNumQueries(1):
            cards = get_tv_inventory_cards()
        landing = {card["label"]: card for card in get_inventory_category_cards()}
        self.assertEqual(len(landing), 8)
        self.assertEqual(cards[0]["total"], 4)
        self.assertEqual(cards[0]["baik"], 1)
        self.assertEqual(cards[0]["rusak"], 1)
        self.assertEqual([card["label"] for card in cards], self.labels)
        for card in cards:
            self.assertEqual({field: card[field] for field in ("label", "total", "img")}, landing[card["label"]])
            self.assertNotIn("baik", landing[card["label"]])
            self.assertNotIn("rusak", landing[card["label"]])
        self.assertTrue(all(card["baik"] == 1 and card["rusak"] == 0 for card in cards[1:]))

    def test_page_includes_one_summary_slide_and_keeps_both_selected_equipment_slides(self):
        url = reverse("dashboard:display", args=[settings.DASHBOARD_TV_SLUG])
        for query in ("", "?tv=1"):
            response = self.client.get(url + query)
            self.assertContains(response, 'data-title="Rekapitulasi Keberfungsian Alat Survei Utama"', count=1)
            self.assertContains(response, "data-tv-inventory", count=1)
            self.assertContains(response, 'class="tv-equipment__card tv-summary"', count=6)
            self.assertEqual(response.content.count(b" data-tv-slide "), 10)
            for slide in (1, 2):
                self.assertContains(response, f'data-tv-equipment="{slide}"', count=1)

    def test_realtime_summary_reflects_master_changes_and_preserves_existing_payload(self):
        url = reverse("dashboard:display_active_data", args=[settings.DASHBOARD_TV_SLUG])
        response = self.client.get(url)
        self.assertIn('aria-label="Borehole Camera: 0 unit"', response.json()["inventoryHtml"])

        item = self.create_equipment(KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA)
        self.create_equipment(KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA, KondisiBarangChoices.RUSAK)
        response = self.client.get(url)
        payload = response.json()
        self.assertIn('aria-label="Borehole Camera: 2 unit"', payload["inventoryHtml"])
        first_card = payload["inventoryHtml"].split("</article>")[0]
        self.assertIn('<dt>Rusak</dt><dd>1 unit</dd>', first_card)
        self.assertIn('<dt>Baik</dt><dd>1 unit</dd>', first_card)
        self.assertEqual(payload["inventoryHtml"].count('class="tv-equipment__card tv-summary"'), 6)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("html", payload)
        self.assertIn("updatedAt", payload)
        self.assertEqual([slide["nomor"] for slide in payload["equipmentSlides"]], [1, 2])

        BarangLaboratorium.objects.filter(pk=item.pk).update(kondisi_barang=KondisiBarangChoices.RUSAK)
        first_card = self.client.get(url).json()["inventoryHtml"].split("</article>")[0]
        self.assertIn('<dt>Rusak</dt><dd>2 unit</dd>', first_card)
        self.assertIn('<dt>Baik</dt><dd>0 unit</dd>', first_card)

        BarangLaboratorium.objects.filter(pk=item.pk).update(kategori_barang=KategoriBarangLaboratoriumChoices.DRONE)
        html = self.client.get(url).json()["inventoryHtml"]
        self.assertIn('aria-label="Borehole Camera: 1 unit"', html)
        self.assertIn('aria-label="Drone: 1 unit"', html)
