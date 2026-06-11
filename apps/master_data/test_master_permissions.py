from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.pengguna.models import Role, User

from apps.master_data.models import (
    BahanOperasional,
    BarangLaboratorium,
    KategoriBarangLaboratoriumChoices,
    StatusBarangChoices,
)


class MasterDataRoleAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for index, role_name in enumerate(
            ("Super Admin", "Admin Lab", "Teknisi Lab", "Kepala Lab", "Pimpinan", "User")
        ):
            role, _ = Role.objects.get_or_create(nama=role_name)
            user = User.objects.create_user(
                username=f"master-role-{index}",
                password="test-pass-123",
            )
            user.safe_profile.role = role
            user.safe_profile.save(update_fields=["role"])
            cls.users[role_name] = user

        with patch("apps.master_data.signals.ensure_master_qr_code"):
            cls.bahan = BahanOperasional.objects.create(
                nama_barang="Bahan Uji Permission",
                kategori_barang="Bahan Lapangan",
                volume=10,
                satuan="Buah",
                stok_minimum=2,
            )
            cls.barang = BarangLaboratorium.objects.create(
                nama_barang="Peralatan Uji Permission",
                tipe_merek_barang="Tipe Uji",
                jenis_barang="Jenis Uji",
                status_barang=StatusBarangChoices.NON_BMN,
                kode_laboratorium="LAB-PERMISSION-001",
                lokasi_barang="Gudang Uji",
                kategori_barang=KategoriBarangLaboratoriumChoices.DRONE,
            )

    def setUp(self):
        self.qr_list_patcher = patch("apps.master_data.views.ensure_master_qr_codes")
        self.qr_detail_patcher = patch("apps.master_data.views.ensure_master_qr_code")
        self.qr_list_patcher.start()
        self.qr_detail_patcher.start()
        self.addCleanup(self.qr_list_patcher.stop)
        self.addCleanup(self.qr_detail_patcher.stop)

    def login(self, role_name):
        self.client.force_login(self.users[role_name])

    def test_kepala_and_pimpinan_can_open_all_master_lists(self):
        list_urls = (
            "data_barang_laboratorium",
            "data_barang_penunjang",
            "data_bahan_operasional",
            "data_fasilitas_ruangan",
            "data_peralatan_laboratorium",
        )

        for role_name in ("Kepala Lab", "Pimpinan"):
            self.login(role_name)
            for url_name in list_urls:
                with self.subTest(role=role_name, url=url_name):
                    response = self.client.get(reverse(f"master_data:{url_name}"))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, "Data Master")

    def test_read_only_roles_cannot_call_manage_or_import_endpoints(self):
        denied_urls = (
            ("get", reverse("master_data:tambah_barang_laboratorium")),
            ("get", reverse("master_data:edit_barang_laboratorium", args=[self.barang.pk])),
            ("post", reverse("master_data:hapus_barang_laboratorium", args=[self.barang.pk])),
            ("post", reverse("master_data:import_barang_laboratorium")),
            ("get", reverse("master_data:download_format_import_barang_laboratorium")),
            ("get", reverse("master_data:tambah_barang_penunjang")),
            ("get", reverse("master_data:edit_barang_penunjang", args=[999999])),
            ("post", reverse("master_data:hapus_barang_penunjang", args=[999999])),
            ("post", reverse("master_data:import_barang_penunjang")),
            ("get", reverse("master_data:download_format_import_barang_penunjang")),
            ("get", reverse("master_data:tambah_bahan_operasional")),
            ("get", reverse("master_data:edit_bahan_operasional", args=[self.bahan.pk])),
            ("post", reverse("master_data:hapus_bahan_operasional", args=[self.bahan.pk])),
            ("post", reverse("master_data:import_bahan_operasional")),
            ("get", reverse("master_data:download_format_import_bahan_operasional")),
            ("get", reverse("master_data:tambah_fasilitas_ruangan")),
            ("get", reverse("master_data:edit_fasilitas_ruangan", args=[999999])),
            ("post", reverse("master_data:hapus_fasilitas_ruangan", args=[999999])),
            ("post", reverse("master_data:import_fasilitas_ruangan")),
            ("get", reverse("master_data:download_format_import_fasilitas_ruangan")),
            ("get", reverse("master_data:tambah_peralatan_laboratorium")),
            ("get", reverse("master_data:edit_peralatan_laboratorium", args=[999999])),
            ("post", reverse("master_data:hapus_peralatan_laboratorium", args=[999999])),
            ("post", reverse("master_data:import_peralatan_laboratorium")),
            ("get", reverse("master_data:download_format_import_peralatan_laboratorium")),
        )
        dashboard_url = reverse("dashboard:index")

        for role_name in ("Kepala Lab", "Pimpinan"):
            self.login(role_name)
            for method, url in denied_urls:
                with self.subTest(role=role_name, method=method, url=url):
                    response = getattr(self.client, method)(url)
                    self.assertRedirects(
                        response,
                        dashboard_url,
                        fetch_redirect_response=False,
                    )

        self.assertTrue(BahanOperasional.objects.filter(pk=self.bahan.pk).exists())
        self.assertTrue(BarangLaboratorium.objects.filter(pk=self.barang.pk).exists())

    def test_export_access_matches_requested_roles(self):
        export_urls = (
            reverse("master_data:export_barang_laboratorium"),
            reverse("master_data:export_barang_penunjang"),
            reverse("master_data:export_bahan_operasional"),
            reverse("master_data:export_fasilitas_ruangan"),
            reverse("master_data:export_peralatan_laboratorium"),
        )

        for role_name in ("Super Admin", "Admin Lab", "Teknisi Lab", "Pimpinan"):
            self.login(role_name)
            for export_url in export_urls:
                with self.subTest(role=role_name, url=export_url):
                    response = self.client.get(export_url)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("attachment;", response["Content-Disposition"])

        for role_name in ("Kepala Lab", "User"):
            self.login(role_name)
            for export_url in export_urls:
                with self.subTest(role=role_name, url=export_url):
                    response = self.client.get(export_url)
                    self.assertRedirects(
                        response,
                        reverse("dashboard:index"),
                        fetch_redirect_response=False,
                    )

    def test_manage_access_remains_available_for_lab_roles(self):
        add_url = reverse("master_data:tambah_bahan_operasional")

        for role_name in ("Super Admin", "Admin Lab", "Teknisi Lab"):
            self.login(role_name)
            with self.subTest(role=role_name):
                response = self.client.get(add_url)
                self.assertEqual(response.status_code, 200)

    def test_list_controls_follow_role_capabilities(self):
        list_url = reverse("master_data:data_bahan_operasional")
        export_url = reverse("master_data:export_bahan_operasional")
        add_url = reverse("master_data:tambah_bahan_operasional")
        edit_url = reverse("master_data:edit_bahan_operasional", args=[self.bahan.pk])
        delete_url = reverse("master_data:hapus_bahan_operasional", args=[self.bahan.pk])

        expectations = {
            "Kepala Lab": (False, False, False),
            "Pimpinan": (True, False, False),
            "Admin Lab": (True, True, False),
            "Teknisi Lab": (True, True, False),
            "Super Admin": (True, True, True),
        }
        for role_name, (can_export, can_manage, can_import) in expectations.items():
            self.login(role_name)
            with self.subTest(role=role_name):
                response = self.client.get(list_url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(export_url in response.content.decode(), can_export)
                self.assertEqual(add_url in response.content.decode(), can_manage)
                self.assertEqual(edit_url in response.content.decode(), can_manage)
                self.assertEqual(delete_url in response.content.decode(), can_manage)
                self.assertEqual("Import Data" in response.content.decode(), can_import)

    def test_read_only_detail_hides_edit_action(self):
        detail_url = reverse("master_data:detail_barang_laboratorium", args=[self.barang.pk])
        edit_url = reverse("master_data:edit_barang_laboratorium", args=[self.barang.pk])

        for role_name in ("Kepala Lab", "Pimpinan"):
            self.login(role_name)
            with self.subTest(role=role_name):
                response = self.client.get(detail_url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, edit_url)

    def test_user_role_cannot_open_master_data(self):
        self.login("User")

        response = self.client.get(reverse("master_data:data_bahan_operasional"))

        self.assertRedirects(
            response,
            reverse("dashboard:index"),
            fetch_redirect_response=False,
        )
