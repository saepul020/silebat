from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from apps.landing.forms import KontenAlatTVForm
from apps.landing.models import KontenAlatTV
from apps.landing.services import get_tv_slides
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
            for index in range(1, 13)
        ]

    def test_konfigurasi_dua_slide_dan_bisa_dikosongkan(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Konten Alat TV")
        self.assertContains(response, '<select', count=12)
        self.assertContains(response, 'type="text"', count=12)
        self.assertContains(response, 'Judul Barang')
        self.assertEqual(KontenAlatTV.objects.count(), 0)
        data = {f"alat_{index}": alat.pk for index, alat in enumerate(reversed(self.alat), start=1)}
        data.update({f"judul_{index}": f"Judul Barang {index}" for index in range(1, 13)})
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertEqual(
            list(KontenAlatTV.objects.values_list("alat_id", flat=True)),
            [alat.pk for alat in reversed(self.alat)],
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context["form"]["alat_1"].value(), self.alat[-1].pk)
        self.assertEqual(response.context["form"]["judul_1"].value(), "Judul Barang 1")
        data["alat_2"] = ""
        self.client.post(self.url, data)
        self.assertIsNone(KontenAlatTV.objects.get(nomor=2).alat_id)
        self.assertEqual(KontenAlatTV.objects.count(), 12)

    def test_pilihan_tidak_valid_tidak_menyimpan_sebagian(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "alat_1": self.alat[1].pk, "judul_1": "Judul baru",
            "alat_6": 99999999, "judul_6": "Alat tidak valid",
        })
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
            "judul_1": "Satu", "judul_2": "Dua", "judul_6": "Enam",
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
                data.update({name.replace("alat_", "judul_"): "Judul manual" for name in list(data)})
                form = KontenAlatTVForm(data=data)
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                for nomor in range(1, 13):
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

    def test_nomor_slot_dibatasi_satu_sampai_dua_belas(self):
        for nomor in (0, 13):
            with self.subTest(nomor=nomor):
                with self.assertRaises(ValidationError):
                    KontenAlatTV(nomor=nomor).full_clean()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    KontenAlatTV.objects.create(nomor=nomor)
        for nomor in (7, 12):
            slot = KontenAlatTV(nomor=nomor)
            slot.full_clean()
            slot.save()

    def test_display_enam_kolom_satu_query_dan_semua_informasi(self):
        self.alat[0].foto_barang.name = "tv-test-photo.png"
        self.alat[0].save(update_fields=["foto_barang"])
        for nomor, alat in enumerate(self.alat, start=1):
            KontenAlatTV.objects.create(nomor=nomor, alat=alat, judul_barang=f"Judul Alat {nomor}")
        with self.assertNumQueries(1):
            slots = get_tv_slides()[0]["slots"]
        with self.assertNumQueries(0):
            html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": slots})
        self.assertEqual(html.count('class="tv-equipment__card"'), 6)
        for value in ("BMN-TV-1", "Judul Alat 1", "Merek 1", "2026", "Pengadaan APBN", "Baik", "tv-test-photo.png"):
            self.assertIn(value, html)
        response = self.client.get(reverse("dashboard:display", args=[settings.DASHBOARD_TV_SLUG]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="tv-chart-slide is-active" data-tv-slide data-title="Peralatan Survei Lapangan Utama"')
        self.assertContains(response, 'data-tv-dots')
        self.assertEqual(response.content.count(b" data-tv-slide "), 10)

    def test_slot_kosong_dan_penghapusan_alat_aman(self):
        KontenAlatTV.objects.create(nomor=3, alat=self.alat[2])
        self.alat[2].delete()
        self.assertIsNone(KontenAlatTV.objects.get(nomor=3).alat_id)
        slots = get_tv_slides()[0]["slots"]
        self.assertEqual(len(slots), 6)
        html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": slots})
        self.assertEqual(html.count("Belum dipilih"), 6)

    def test_refresh_mengambil_konfigurasi_dan_metadata_terbaru(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0], judul_barang="Judul Manual")
        url = reverse("dashboard:display_active_data", args=[settings.DASHBOARD_TV_SLUG])
        response = self.client.get(url)
        self.assertIn("Judul Manual", response.json()["equipmentSlides"][0]["html"])
        KontenAlatTV.objects.filter(nomor=1).update(alat=self.alat[1])
        BarangLaboratorium.objects.filter(pk=self.alat[1].pk).update(asal_perolehan="Hibah Baru", kondisi_barang="Rusak")
        response = self.client.get(url)
        self.assertIn("Judul Manual", response.json()["equipmentSlides"][0]["html"])
        self.assertIn("Hibah Baru", response.json()["equipmentSlides"][0]["html"])
        self.assertIn("Rusak", response.json()["equipmentSlides"][0]["html"])
        self.assertNotIn("Alat TV 1", response.json()["equipmentSlides"][0]["html"])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("html", response.json())
        self.assertEqual(self.client.get(reverse("dashboard:display_active_data", args=["slug-salah"])).status_code, 404)

    def test_kode_laboratorium_dipakai_jika_kode_bmn_kosong(self):
        self.alat[0].status_barang = "Non BMN"
        self.alat[0].save(update_fields=["status_barang"])
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": get_tv_slides()[0]["slots"]})
        self.assertIn("LAB-TV-1", html)
        self.assertNotIn("BMN-TV-1", html)

    def test_form_query_pilihan_tidak_diulang_untuk_setiap_dropdown(self):
        with self.assertNumQueries(2):
            html = str(KontenAlatTVForm())
        self.assertEqual(html.count('<select'), 12)
        self.assertEqual(html.count('type="text"'), 12)

    def test_judul_wajib_dan_batas_panjang_diamankan_server_side(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0], judul_barang="Judul tersimpan")
        self.client.force_login(self.user)
        for judul in ("", "   ", "J" * 201):
            with self.subTest(judul=judul):
                response = self.client.post(self.url, {
                    "alat_1": self.alat[1].pk, "judul_1": "Judul diubah",
                    "alat_7": self.alat[6].pk, "judul_7": judul,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn("judul_7", response.context["form"].errors)
                self.assertContains(response, 'value="Judul diubah"')
                self.assertEqual(list(KontenAlatTV.objects.values_list("nomor", "alat_id", "judul_barang")), [
                    (1, self.alat[0].pk, "Judul tersimpan"),
                ])

    def test_judul_manual_tetap_saat_nama_master_atau_pilihan_alat_berubah(self):
        self.client.force_login(self.user)
        data = {"alat_1": self.alat[0].pk, "judul_1": "  Judul pilihan admin  "}
        self.assertRedirects(self.client.post(self.url, data), self.url)
        BarangLaboratorium.objects.filter(pk=self.alat[0].pk).update(nama_barang="Nama master berubah")
        response = self.client.get(self.url)
        self.assertEqual(response.context["form"]["judul_1"].value(), "Judul pilihan admin")
        for query in ("", "?tv=1"):
            response = self.client.get(reverse("dashboard:display", args=[settings.DASHBOARD_TV_SLUG]) + query)
            self.assertContains(response, '<h4 class="tv-equipment__name">Judul pilihan admin</h4>', html=True)
        data["alat_1"] = self.alat[1].pk
        self.assertRedirects(self.client.post(self.url, data), self.url)
        slot = KontenAlatTV.objects.get(nomor=1)
        self.assertEqual(slot.alat_id, self.alat[1].pk)
        self.assertEqual(slot.judul_barang, "Judul pilihan admin")
        html = self.client.get(reverse("dashboard:display_active_data", args=[settings.DASHBOARD_TV_SLUG])).json()["equipmentSlides"][0]["html"]
        self.assertIn("Judul pilihan admin", html)
        self.assertIn("Merek 2", html)
        self.assertNotIn("Nama master berubah", html)
        self.assertNotIn("Alat TV 2", html)

    def test_judul_dikosongkan_tidak_mengambil_nama_master_dan_teks_di_escape(self):
        slot = KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": get_tv_slides()[0]["slots"]})
        self.assertIn('<h4 class="tv-equipment__name">-</h4>', html)
        self.assertNotIn("Alat TV 1", html)
        slot.judul_barang = '<script>alert("judul")</script>'
        slot.save(update_fields=["judul_barang"])
        html = render_to_string("dashboard/partials/tv_equipment.html", {"tv_slots": get_tv_slides()[0]["slots"]})
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_migrasi_menyalin_judul_lama_sekali_dan_mempertahankan_judul_manual(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        KontenAlatTV.objects.create(nomor=2, alat=self.alat[1], judul_barang="Judul manual")
        KontenAlatTV.objects.create(nomor=3)
        migration = import_module("apps.landing.migrations.0008_tv_judul")
        migration.copy_titles(apps, SimpleNamespace(connection=connection))
        self.assertEqual(KontenAlatTV.objects.get(nomor=1).judul_barang, "Alat TV 1")
        self.assertEqual(KontenAlatTV.objects.get(nomor=2).judul_barang, "Judul manual")
        self.assertEqual(KontenAlatTV.objects.get(nomor=3).judul_barang, "")
        BarangLaboratorium.objects.filter(pk=self.alat[0].pk).update(nama_barang="Master baru")
        migration.copy_titles(apps, SimpleNamespace(connection=connection))
        self.assertEqual(KontenAlatTV.objects.get(nomor=1).judul_barang, "Alat TV 1")

    def test_existing_first_slide_is_loaded_and_second_slide_starts_empty(self):
        for nomor in range(1, 7):
            KontenAlatTV.objects.create(nomor=nomor, alat=self.alat[nomor - 1])
        form = KontenAlatTVForm()
        self.assertEqual(len(form.slides), 2)
        for index, slot in enumerate(form.slides[0]["slots"]):
            self.assertEqual(slot["alat"].value(), self.alat[index].pk)
        self.assertTrue(all(slot["alat"].value() is None for slot in form.slides[1]["slots"]))
        with self.assertNumQueries(1):
            slides = get_tv_slides()
        self.assertEqual([slot["nomor"] for slot in slides[1]["slots"]], list(range(1, 7)))
        self.assertTrue(all(slot["alat"] is None for slot in slides[1]["slots"]))
        self.assertEqual(KontenAlatTV.objects.count(), 6)

    def test_duplicates_across_slides_and_invalid_second_slide_are_atomic(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0])
        self.client.force_login(self.user)
        data = {"alat_1": self.alat[1].pk, "alat_8": self.alat[1].pk, "judul_1": "Satu", "judul_8": "Delapan"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("kolom 1 slide 1", str(response.context["form"].errors["alat_8"]))
        data["alat_8"] = 999999999
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("alat_8", response.context["form"].errors)
        self.assertEqual(list(KontenAlatTV.objects.values_list("nomor", "alat_id")), [(1, self.alat[0].pk)])

    def test_both_equipment_slides_render_and_refresh_independently(self):
        KontenAlatTV.objects.create(nomor=1, alat=self.alat[0], judul_barang="Judul Satu")
        KontenAlatTV.objects.create(nomor=7, alat=self.alat[6], judul_barang="Judul Tujuh")
        response = self.client.get(reverse("dashboard:display", args=[settings.DASHBOARD_TV_SLUG]))
        self.assertContains(response, 'data-tv-equipment="1"', count=1)
        self.assertContains(response, 'data-tv-equipment="2"', count=1)
        self.assertContains(response, "Judul Tujuh")
        self.assertEqual(response.content.count(b'class="tv-equipment__card'), 18)
        KontenAlatTV.objects.filter(nomor=7).update(alat=self.alat[7], judul_barang="Judul Terbaru")
        BarangLaboratorium.objects.filter(pk=self.alat[7].pk).update(asal_perolehan="Hibah slide dua")
        response = self.client.get(reverse("dashboard:display_active_data", args=[settings.DASHBOARD_TV_SLUG]))
        slides = response.json()["equipmentSlides"]
        self.assertEqual([slide["nomor"] for slide in slides], [1, 2])
        self.assertIn("Judul Satu", slides[0]["html"])
        self.assertNotIn("Judul Terbaru", slides[0]["html"])
        self.assertIn("Judul Terbaru", slides[1]["html"])
        self.assertIn("Hibah slide dua", slides[1]["html"])
        self.assertNotIn("Judul Tujuh", slides[1]["html"])
        self.alat[7].delete()
        with self.assertNumQueries(1):
            slides = get_tv_slides()
        self.assertIsNone(slides[1]["slots"][0]["alat"])
