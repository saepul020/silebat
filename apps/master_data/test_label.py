import shutil
import tempfile
from io import BytesIO
from pathlib import Path
import re

from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from reportlab.lib.units import mm

from apps.pengguna.models import Role, User

from apps.master_data.models import (
    BarangLaboratorium,
    FasilitasRuangan,
    KategoriBarangLaboratoriumChoices,
    KategoriSaranaPrasaranaChoices,
    PeralatanLaboratorium,
    StatusBarangChoices,
)
from apps.master_data.label_utils import (
    LEFT_WIDTH,
    PDF_LABEL_HEIGHT_MM,
    PDF_LABEL_WIDTH_MM,
    PX_PER_MM,
    QR_SIZE,
    build_label_pdf,
)


class MasterLabelTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
            PUBLIC_BASE_URL="http://testserver",
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        admin_role, _ = Role.objects.get_or_create(nama="Admin Lab")
        user_role, _ = Role.objects.get_or_create(nama="User")
        self.admin = User.objects.create_user(
            username="master-label-admin",
            password="test-pass-123",
        )
        self.admin.safe_profile.role = admin_role
        self.admin.safe_profile.save(update_fields=["role"])
        self.user = User.objects.create_user(
            username="master-label-user",
            password="test-pass-123",
        )
        self.user.safe_profile.role = user_role
        self.user.safe_profile.save(update_fields=["role"])

        self.survei = BarangLaboratorium.objects.create(
            nama_barang="Multiparameter Kualitas Air Kecil",
            tipe_merek_barang="TSD&EC Meter Hold",
            jenis_barang="Kualitas Air",
            status_barang=StatusBarangChoices.NON_BMN,
            kode_laboratorium="LAB-PSL-002",
            kategori_barang=KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN,
        )
        self.fasilitas = FasilitasRuangan.objects.create(
            nama_barang="Meja Preparasi",
            tipe_merek_barang="Stainless",
            jenis_barang="Furniture Lab",
            status_barang=StatusBarangChoices.BMN,
            kode_aset_bmn="BMN-FAS-001",
            kode_laboratorium="LAB-FAS-001",
            kategori_barang=KategoriSaranaPrasaranaChoices.FASILITAS_RUANGAN,
        )
        self.peralatan = PeralatanLaboratorium.objects.create(
            nama_barang="Oven Laboratorium",
            tipe_merek_barang="Memmert",
            jenis_barang="Pemanas",
            status_barang=StatusBarangChoices.BMN,
            kode_aset_bmn="BMN-LAB-001",
            kode_laboratorium="LAB-PRL-001",
        )

    def test_label_download_rendered_as_png_for_allowed_asset_categories(self):
        self.client.force_login(self.admin)
        cases = (
            ("label_barang_laboratorium", self.survei),
            ("label_fasilitas_ruangan", self.fasilitas),
            ("label_peralatan_laboratorium", self.peralatan),
        )

        for url_name, obj in cases:
            with self.subTest(url=url_name):
                response = self.client.get(reverse(f"master_data:{url_name}", args=[obj.pk]))

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "image/png")
                self.assertIn("attachment;", response["Content-Disposition"])
                self.assertIn(".png", response["Content-Disposition"])
                self.assertEqual(response.content[:8], b"\x89PNG\r\n\x1a\n")
                image = Image.open(BytesIO(response.content))
                self.assertEqual(image.size, (600, 240))
                self.assertEqual(LEFT_WIDTH, 30 * PX_PER_MM)
                self.assertEqual(QR_SIZE, 19 * PX_PER_MM)
                obj.refresh_from_db()
                self.assertTrue(obj.qr_code)

    def test_label_actions_visible_on_target_list_and_detail_pages(self):
        self.client.force_login(self.admin)
        cases = (
            (
                "data_barang_laboratorium",
                "detail_barang_laboratorium",
                "label_barang_laboratorium",
                "bulk_label_barang_laboratorium",
                self.survei,
            ),
            (
                "data_fasilitas_ruangan",
                "detail_fasilitas_ruangan",
                "label_fasilitas_ruangan",
                "bulk_label_fasilitas_ruangan",
                self.fasilitas,
            ),
            (
                "data_peralatan_laboratorium",
                "detail_peralatan_laboratorium",
                "label_peralatan_laboratorium",
                "bulk_label_peralatan_laboratorium",
                self.peralatan,
            ),
        )

        for list_name, detail_name, label_name, bulk_name, obj in cases:
            label_url = reverse(f"master_data:{label_name}", args=[obj.pk])
            bulk_url = reverse(f"master_data:{bulk_name}")
            with self.subTest(list=list_name):
                list_response = self.client.get(reverse(f"master_data:{list_name}"))
                detail_response = self.client.get(reverse(f"master_data:{detail_name}", args=[obj.pk]))

                self.assertContains(list_response, label_url)
                self.assertContains(list_response, bulk_url)
                self.assertContains(list_response, "Download Label")
                self.assertNotContains(list_response, "Download PDF")
                self.assertContains(list_response, 'name="label_items"')
                self.assertContains(list_response, 'value="kecil"')
                self.assertContains(list_response, obj.nama_barang)
                self.assertContains(list_response, 'id="masterPreviewModal"')
                self.assertContains(list_response, 'data-master-preview-open="label"')
                self.assertContains(list_response, 'data-master-preview-qr-download')
                self.assertContains(list_response, "Download QR")
                self.assertNotContains(list_response, 'data-master-preview-open="qr"')
                self.assertNotContains(list_response, "Lihat QR-Code")
                self.assertNotContains(list_response, f'{label_url}?download=1')
                self.assertContains(detail_response, label_url)
                self.assertContains(detail_response, "Label Barang")
                self.assertContains(detail_response, "Download Label")
                self.assertContains(detail_response, "Download QR")
                self.assertNotContains(detail_response, "QR-Code Barang")
                self.assertNotContains(detail_response, "&nbsp;Preview Label")

    def test_label_layout_does_not_use_silebat_logo(self):
        checked_files = (
            Path("apps/master_data/label_utils.py"),
            Path("apps/master_data/templates/master_data/label_preview.html"),
            Path("apps/master_data/templates/master_data/preview_modal.html"),
        )

        for path in checked_files:
            with self.subTest(path=path):
                self.assertNotIn("silebat-logo.png", path.read_text())

    def test_label_css_uses_new_print_scale(self):
        css = Path("static/css/label.css").read_text()

        self.assertIn("width: 50mm", css)
        self.assertIn("height: 20mm", css)
        self.assertIn("grid-template-columns: 30mm 20mm", css)
        self.assertIn("grid-template-rows: 6mm 14mm", css)
        self.assertIn("grid-template-columns: 5.2mm minmax(0, 1fr)", css)
        self.assertIn("grid-template-columns: 10mm 1mm minmax(0, 1fr)", css)
        self.assertIn("text-overflow: clip", css)
        self.assertIn("font-size: 3.5pt", css)
        self.assertIn("font-size: 5pt", css)
        self.assertIn("height: 19mm", css)
        self.assertIn("width: 19mm", css)
        self.assertIn(".bulk-label-table th,", css)
        self.assertIn("padding: 9px 12px", css)
        self.assertIn(".bulk-label-table .cell-wrap", css)
        self.assertIn("vertical-align: middle", css)
        self.assertIn("min-height: 38px", css)
        self.assertNotIn(".master-preview__qr", css)

    def test_bulk_label_download_rendered_as_pdf(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("master_data:bulk_label_barang_laboratorium"),
            data={
                "label_items": [str(self.survei.pk)],
                f"label_size_{self.survei.pk}": "kecil",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn(".pdf", response["Content-Disposition"])
        self.assertEqual(response.content[:4], b"%PDF")
        self.assertIn(b"/MediaBox", response.content)

    def test_bulk_label_pdf_uses_forty_labels_per_page(self):
        image = Image.new("RGB", (600, 240), "white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        content = build_label_pdf(
            [
                {"image": buffer.getvalue(), "size": "normal"}
                for _ in range(41)
            ]
        )

        page_counts = re.findall(rb"/Count\s+(\d+)", content)

        self.assertIn(b"2", page_counts)

    def test_bulk_label_pdf_normal_size_uses_exact_label_scale(self):
        image = Image.new("RGB", (600, 240), "white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        content = build_label_pdf([{"image": buffer.getvalue(), "size": "normal"}])

        width = f"{PDF_LABEL_WIDTH_MM * mm:.4f}".encode()
        height = f"{PDF_LABEL_HEIGHT_MM * mm:.5f}".encode()

        self.assertIn(width + b" 0 0 " + height, content)

    def test_bulk_label_requires_selected_item(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("master_data:bulk_label_barang_laboratorium"))

        self.assertRedirects(response, reverse("master_data:data_barang_laboratorium"))

    def test_user_role_cannot_open_label_preview(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("master_data:label_barang_laboratorium", args=[self.survei.pk])
        )

        self.assertRedirects(
            response,
            reverse("dashboard:index"),
            fetch_redirect_response=False,
        )
