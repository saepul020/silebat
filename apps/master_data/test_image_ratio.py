import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ImageRatioStyleTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base_dir = Path(settings.BASE_DIR)
        cls.base_css = (base_dir / "static/css/base.css").read_text(encoding="utf-8")
        cls.maintenance_css = (
            base_dir / "static/css/pemeliharaan.css"
        ).read_text(encoding="utf-8")

    def _rule(self, css, selector):
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            selectors = [item.strip() for item in match.group(1).split(",")]
            if selector in selectors:
                return match.group(2)
        self.fail(f"Selector CSS tidak ditemukan: {selector}")

    def assert_ratio_frame(self, css, selector):
        rule = self._rule(css, selector)
        self.assertIn("aspect-ratio: 4 / 3", rule)

    def assert_contained_image(self, css, selector):
        rule = self._rule(css, selector)
        self.assertIn("object-fit: contain", rule)
        self.assertNotIn("object-fit: cover", rule)

    def test_master_data_preview_memakai_rasio_empat_banding_tiga(self):
        self.assert_ratio_frame(self.base_css, ".upload-preview-card--master")
        self.assert_contained_image(
            self.base_css,
            ".upload-preview-frame--master img",
        )
        self.assert_ratio_frame(self.base_css, ".detail-asset-avatar")
        self.assert_contained_image(self.base_css, ".detail-asset-avatar img")

    def test_peminjaman_preview_memakai_rasio_empat_banding_tiga(self):
        self.assert_ratio_frame(self.base_css, ".inventory-photo__trigger")
        self.assert_contained_image(self.base_css, ".inventory-photo__thumb")
        self.assert_ratio_frame(self.base_css, ".inventory-photo__stage")
        self.assert_contained_image(
            self.base_css,
            ".inventory-photo__stage img",
        )

    def test_pemeliharaan_preview_memakai_rasio_empat_banding_tiga(self):
        self.assert_ratio_frame(
            self.maintenance_css,
            ".pemeliharaan-form-card .landing-gallery-thumb",
        )
        self.assert_contained_image(
            self.maintenance_css,
            ".pemeliharaan-form-card .landing-gallery-thumb img",
        )
        self.assert_ratio_frame(
            self.maintenance_css,
            ".pemeliharaan-photo-strip a",
        )
        self.assert_contained_image(
            self.maintenance_css,
            ".pemeliharaan-photo-strip img",
        )
        self.assert_ratio_frame(
            self.maintenance_css,
            ".pemeliharaan-photo-modal__stage",
        )
        self.assert_contained_image(
            self.maintenance_css,
            ".pemeliharaan-photo-modal__stage img",
        )

    def test_spasi_preview_pemeliharaan_dan_fieldset_pelatihan_seragam(self):
        gallery_rule = self._rule(
            self.maintenance_css,
            ".pemeliharaan-form-card .landing-gallery-strip",
        )
        self.assertIn("min-height: 0", gallery_rule)

        fieldset_rule = self._rule(
            self.base_css,
            ".pelatihan-form-card .master-fieldset-stack > fieldset",
        )
        self.assertIn("margin-bottom: 0", fieldset_rule)
        stack_rule = self._rule(
            self.base_css,
            ".master-fieldset-stack",
        )
        self.assertIn("gap: 18px", stack_rule)
