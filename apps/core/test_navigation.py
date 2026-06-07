from django.test import RequestFactory, SimpleTestCase

from apps.core.navigation import get_next_url


class SafeNextUrlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_internal_next_url_preserves_query(self):
        next_url = "/master-data/barang-laboratorium/?entries=10&page=3&q=pompa"
        request = self.factory.get("/master-data/barang-laboratorium/1/edit/", {"next": next_url})

        self.assertEqual(get_next_url(request), next_url)

    def test_post_next_url_is_used_after_form_submission(self):
        next_url = "/operasional/layanan/?page=3"
        request = self.factory.post("/operasional/layanan/1/edit/", {"next": next_url})

        self.assertEqual(get_next_url(request), next_url)

    def test_external_next_url_is_rejected(self):
        request = self.factory.post(
            "/operasional/layanan/1/edit/",
            {"next": "https://example.org/ambil-alih"},
        )

        self.assertEqual(get_next_url(request), "")

    def test_protocol_relative_next_url_is_rejected(self):
        request = self.factory.get(
            "/operasional/layanan/1/edit/",
            {"next": "//example.org/ambil-alih"},
        )

        self.assertEqual(get_next_url(request), "")
