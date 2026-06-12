from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class GlobalLoadingTests(SimpleTestCase):
    shell_templates = [
        "templates/base.html",
        "templates/registration/login.html",
        "apps/landing/templates/landing/index.html",
        "apps/dashboard/templates/dashboard/display.html",
    ]

    def test_all_html_shells_include_global_loading_assets(self):
        base_dir = Path(settings.BASE_DIR)

        for relative_path in self.shell_templates:
            content = (base_dir / relative_path).read_text(encoding="utf-8")
            with self.subTest(template=relative_path):
                self.assertIn("css/loading.css", content)
                self.assertIn("partials/loading.html", content)
                self.assertIn("js/loading.js", content)

    def test_loading_component_has_accessible_status(self):
        content = (
            Path(settings.BASE_DIR) / "templates/partials/loading.html"
        ).read_text(encoding="utf-8")

        self.assertIn('role="status"', content)
        self.assertIn('aria-live="polite"', content)
        self.assertIn("data-app-loader-text", content)
