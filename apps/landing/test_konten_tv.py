from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from apps.landing.forms import KontenAlatTVForm
from apps.landing.models import KontenAlatTV
from apps.landing.services import get_tv_slots
from apps.master_data.models import BarangLaboratorium
from apps.pengguna.models import Role, User


class KontenAlatTVTests(TestCase):
    def setUp(self):
        qr_patch = patch("apps.master_data.signals.ensure_master_qr_code")
        qr_patch.start()
        self.addCleanup(qr_patch.stop)
        self.user = User.objects.create_user(username="admin-konten-tv")
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        self.user.safe_profile.role = role
        self.user.safe_profile.save(update_fields=["role"])
        self.url = reverse("landing:konten_tv")
        self.alat = [
            BarangLaboratorium.objects.create(
                nama_barang=f"Alat TV {index}", tipe_merek_barang=f"Merek {index}",
                jenis_barang="Alat Survei", status_barang="BMN",
                kode_aset_bmn=f"BMN-TV-{index}", kode_laboratorium=f"LAB-TV-{index}",
                kategori_barang="Borehole Camera", tahun_perolehan=2026,
                asal_perolehan="Pengadaan APBN", kondisi_barang="Baik",
            )
            for index in range(1, 7)
        ]

    def test_konfigurasi_enam_slot_dan_bisa_dikosongkan(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Konten Alat TV")
        self.assertContains(response, '<select', count=6)
        self.assertEqual(KontenAlatTV.objects.count(), 0)
        data = {f"alat_{index}": alat.pk for index, alat in enumerate(reversed(self.alat), start=1)}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertEqual(
            list(KontenAlatTV.objects.values_list("alat_id", flat=True)),
            [alat.pk for alat in reversed(self.alat)],
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["form"]["alat_1"].value(), self.alat[-1].pk)
        data["alat_2"] = ""
        self.client.post(self.url, data)
        self.assertIsNone(KontenAlatTV.objects.get(nomor=2).alat_id)
        self.assertEqual(KontenAlatTV.objects.count(), 6)

    def test_pilihan_tidak_valid_tidak_menyimpan_sebagian(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"alat_1": self.alat[1].pk, "alat_6": 99999999})
        self.assertEqual(response.status_code, 200)
        self.assertIn("alat_6", response.context["form"].errors)
        self.assertEqual(list(KontenAlatTV.objects.values_list("nomor", "alat_id")), [(1, self.alat[0].pk)])

    def test_duplikasi_request_manual_ditolak_tanpa_mengubah_konfigurasi(self):
        for nomor, alat in enumerate(self.alat, start=1):
            KontenAlatTV.objects.create(nomor=nomor, alat=alat)
        before = list(KontenAlatTV.objects.values_list("nomor", "alat_id"))
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "alat_1": self.alat[2].pk,
            "alat_2": self.alat[2].pk,
            "alat_6": self.alat[2].pk,
        })
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        for field in ("alat_2", "alat_6"):
            self.assertIn("sudah dipilih pada kolom 1", str(form.errors[field]))
        with self.assertRaises(ValueError):
            form.save()
        self.assertEqual(list(KontenAlatTV.objects.values_list("nomor", "alat_id")), before)

    def test_kolom_kosong_tidak_dianggap_duplikat_dan_pilihan_bisa_ditukar(self):
        for data in (
            {"alat_1": self.alat[0].pk, "alat_2": self.alat[1].pk},
            {"alat_1": self.alat[1].pk, "alat_2": self.alat[0].pk},
            {},
        ):
            with self.subTest(data=data):
                form = KontenAlatTVForm(data=data)
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                for nomor in range(1, 7):
                    self.assertEqual(KontenAlatTV.objects.get(nomor=nomor).alat_id, data.get(f"alat_{nomor}"))

    def test_hanya_super_admin_bisa_membaca_dan_menyimpan(self):
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(self.url).status_code, 302)
        self.client.force_login(self.user)
        for nama in ("User", "Admin Lab", "Teknisi Lab", "Kepala Lab", "Pimpinan"):
            role, _ = Role.objects.get_or_create(nama=nama)
            self.user.safe_profile.role = role
            self.user.safe_profile.save(update_fields=["role"])
            for method in (self.client.get, self.client.post):
                self.assertRedirects(method(self.url), reverse("dashboard:index"), fetch_redirect_response=False)
        self.assertEqual(KontenAlatTV.objects.count(), 0)

    def test_nomor_slot_dibatasi_satu_sampai_enam(self):
        for nomor in (0, 7):
            with self.subTest(nomor=nomor):
                with self.assertRaises(ValidationError):
                    KontenAlatTV(nomor=nomor).full_clean()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    KontenAlatTV.objects.create(nomor=nomor)

    def test_display_enam_kolom_satu_query_dan_semua_informasi(self):
        self.alat[0].foto_barang.name = "tv-test-photo.png"
        self.alat[0].save(update_fields=["foto_barang"])
        for nomor, alat in enumerate(self.alat, start=1):
            KontenAlatTV.objects.create(nomor=nomor, alat=alat)
        with self.assertNumQueries(1):
            slots = get_tv_slots()
        with self.assertNumQueries(0):
            html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": slots})
        self.assertEqual(html.count('class="tv-equipment__card"'), 6)
        for value in ("BMN-TV-1", "Alat TV 1", "Merek 1", "2026", "Pengadaan APBN", "Baik", "tv-test-photo.png"):
            self.assertIn(value, html)
        response = self.client.get(reverse("dashboard:display", args=[settings.DASHBOARD_TV_SLUG]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="tv-chart-slide is-active" data-tv-slide data-title="Peralatan Survei Lapangan"')
        self.assertContains(response, 'data-tv-dots')
        self.assertEqual(response.content.count(b" data-tv-slide "), 8)

    def test_slot_kosong_dan_penghapusan_alat_aman(self):
        KontenAlatTV.objects.create(nomor=3, alat=self.alat[2])
        self.alat[2].delete()
        self.assertIsNone(KontenAlatTV.objects.get(nomor=3).alat_id)
        slots = get_tv_slots()
        self.assertEqual(len(slots), 6)
        html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": slots})
        self.assertEqual(html.count("Belum dipilih"), 6)

    def test_refresh_mengambil_konfigurasi_dan_metadata_terbaru(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        url = reverse("dashboard:display_active_data", args=[settings.DASHBOARD_TV_SLUG])
        response = self.client.get(url)
        self.assertIn("Alat TV 1", response.json()["equipmentHtml"])
        KontenAlatTV.objects.filter(nomor=1).update(alat=self.alat[1])
        BarangLaboratorium.objects.filter(pk=self.alat[1].pk).update(asal_perolehan="Hibah Baru", kondisi_barang="Rusak")
        response = self.client.get(url)
        self.assertIn("Alat TV 2", response.json()["equipmentHtml"])
        self.assertIn("Hibah Baru", response.json()["equipmentHtml"])
        self.assertIn("Rusak", response.json()["equipmentHtml"])
        self.assertNotIn("Alat TV 1", response.json()["equipmentHtml"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("html", response.json())
        self.assertEqual(self.client.get(reverse("dashboard:display_active_data", args=["slug-salah"])).status_code, 404)

    def test_kode_laboratorium_dipakai_jika_kode_bmn_kosong(self):
        self.alat[0].status_barang = "Non BMN"
        self.alat[0].save(update_fields=["status_barang"])
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": get_tv_slots()})
        self.assertIn("LAB-TV-1", html)
        self.assertNotIn("BMN-TV-1", html)

    def test_form_query_pilihan_tidak_diulang_untuk_setiap_dropdown(self):
        with self.assertNumQueries(2):
            html = str(KontenAlatTVForm())
        self.assertEqual(html.count('<select'), 6)
