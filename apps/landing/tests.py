from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse


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
