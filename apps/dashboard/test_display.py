import json
from unittest.mock import patch

from django.conf import settings
from django.http import Http404
from django.test import RequestFactory, SimpleTestCase
from django.utils import timezone

from apps.dashboard.views import display, display_active_data


class DisplayModeTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.slides = [
            {"nomor": slide, "slots": [{"nomor": column, "alat": None} for column in range(1, 7)]}
            for slide in (1, 2)
        ]
        self.context = {
            "display_generated_at": timezone.localtime(),
            "dashboard_stats": {"completed_count": 12, "ongoing_count": 4},
            "active_peminjaman": [],
            "instansi_charts": [],
        }

    def render_display(self, query="", **headers):
        request = self.factory.get("/display/" + query, **headers)
        with (
            patch("apps.dashboard.views.build_dashboard_context", return_value=self.context.copy()),
            patch("apps.dashboard.views.get_tv_slides", return_value=self.slides),
            patch("apps.dashboard.views.get_tv_inventory_cards", return_value=[]),
            patch("apps.dashboard.views.get_tv_documentation", return_value=[]),
        ):
            return display(request, settings.DASHBOARD_TV_SLUG)

    def test_explicit_tv_mode_keeps_both_slides_and_the_viewport(self):
        for query in ("", "?tv=1"):
            with self.subTest(query=query):
                response = self.render_display(query)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'content="width=device-width, initial-scale=1.0"')
                self.assertContains(response, 'class="tv-equipment__card', count=12)
                self.assertContains(response, 'data-tv-equipment="1"')
                self.assertContains(response, 'data-tv-equipment="2"')
                self.assertContains(response, 'data-tv-active-url=')
                self.assertContains(response, 'data-tv-active-body')
                self.assertContains(response, 'data-tv-clock')
                self.assertContains(response, 'data-tv-dots')
                self.assertContains(response, 'js/tv_layout.js')
                if query:
                    self.assertContains(response, '<html lang="id" class="tv-screen">')
                    self.assertContains(response, 'css/tv_screen.css')
                    self.assertContains(response, 'js/tv_layout.js')
                    self.assertNotContains(response, 'class="tv-mode-link"')
                else:
                    self.assertNotContains(response, 'class="tv-screen"')
                    self.assertNotContains(response, 'css/tv_screen.css')
                    self.assertContains(response, 'href="?tv=1">Aktifkan Mode TV</a>')

    def test_only_tv_equals_one_enables_the_mode(self):
        for query in ("?tv=0", "?tv=true", "?tv=", ""):
            with self.subTest(query=query):
                response = self.render_display(query, HTTP_USER_AGENT="BrowseHere Android TV TCL V8-R51AT01")
                self.assertNotContains(response, 'class="tv-screen"')

    def test_tv_mode_preserves_the_display_access_check(self):
        with self.assertRaises(Http404):
            display(self.factory.get("/display/?tv=1"), "invalid-slug")

    def test_initial_render_and_polling_keep_more_than_eight_activities(self):
        activities = [
            {
                "nomor_pengajuan": f"AKTIF-{index:02}",
                "nama_peminjam": "Fajar Muhamad Tawakal, S.T.",
                "instansi_tujuan_lainnya": "Direktorat Air Tanah dan Air Baku",
                "tanggal_mulai": timezone.localdate(),
                "tanggal_selesai": timezone.localdate(),
                "proses_peminjaman_label": "Verifikasi Peminjaman - Ketua Tim",
            }
            for index in range(11)
        ]
        self.context["active_peminjaman"] = activities
        for query in ("", "?tv=1"):
            response = self.render_display(query)
            for activity in activities:
                self.assertContains(response, activity["nomor_pengajuan"])
            self.assertNotContains(response, "<br>")

        with (
            patch("apps.dashboard.views.get_active_peminjaman_queryset", return_value=activities),
            patch("apps.dashboard.views.get_tv_slides", return_value=[]),
            patch("apps.dashboard.views.get_tv_inventory_cards", return_value=[]),
            patch("apps.dashboard.views.get_tv_documentation", return_value=[]),
        ):
            response = display_active_data(self.factory.get("/active-data/"), settings.DASHBOARD_TV_SLUG)
        html = json.loads(response.content)["html"]
        self.assertEqual(html.count("<tr>"), 11)
        self.assertIn("AKTIF-10", html)
        self.assertNotIn("<br>", html)
        self.assertIn("no-store", response["Cache-Control"])
