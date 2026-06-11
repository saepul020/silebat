from urllib.parse import quote

from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone

from apps.pengguna.models import Role, User

from apps.operasional.models import InstansiKlien, LayananKegiatan, TimKegiatan
from apps.peminjaman.models import PeminjamanRequest


class EditReturnNavigationTests(TestCase):
    def setUp(self):
        role, _ = Role.objects.get_or_create(nama="Super Admin")
        self.user = User.objects.create_user(username="admin", password="test-pass-123")
        self.user.profile.role = role
        self.user.profile.save(update_fields=["role"])
        self.client.force_login(self.user)
        self.obj = LayananKegiatan.objects.create(jenis_layanan="Layanan Awal")

    def test_update_returns_to_source_page(self):
        next_url = f"{reverse('operasional:data_layanan')}?entries=10&page=3&q=air"
        response = self.client.post(
            reverse("operasional:edit_layanan", args=[self.obj.pk]),
            {
                "jenis_layanan": "Layanan Diperbarui",
                "next": next_url,
            },
        )

        self.assertRedirects(response, next_url, fetch_redirect_response=False)

    def test_list_edit_link_carries_current_page(self):
        items = [
            LayananKegiatan.objects.create(jenis_layanan=f"Layanan {index:02d}")
            for index in range(25)
        ]
        source_url = f"{reverse('operasional:data_layanan')}?entries=10&page=3"
        edit_url = reverse("operasional:edit_layanan", args=[items[20].pk])

        response = self.client.get(source_url)

        self.assertContains(response, f"{edit_url}?next={quote(source_url, safe='/')}")

    def test_invalid_form_keeps_source_page(self):
        next_url = f"{reverse('operasional:data_layanan')}?entries=10&page=3"

        response = self.client.post(
            reverse("operasional:edit_layanan", args=[self.obj.pk]),
            {
                "jenis_layanan": "",
                "next": next_url,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'name="next" value="{escape(next_url)}"')

    def test_external_next_falls_back_to_list(self):
        response = self.client.post(
            reverse("operasional:edit_layanan", args=[self.obj.pk]),
            {
                "jenis_layanan": "Layanan Diperbarui",
                "next": "https://example.org/ambil-alih",
            },
        )

        self.assertRedirects(
            response,
            reverse("operasional:data_layanan"),
            fetch_redirect_response=False,
        )

    def test_delete_active_transaction_layanan_is_blocked(self):
        tim = TimKegiatan.objects.create(nama_tim="Tim Uji")
        instansi = InstansiKlien.objects.create(
            nama_instansi="Instansi Uji",
            alamat_instansi="Alamat Uji",
            organisasi=InstansiKlien.OrganisasiChoices.EKSTERNAL_PU,
        )
        today = timezone.localdate()
        pengajuan = PeminjamanRequest.objects.create(
            peminjam=self.user,
            nama_peminjam="Admin",
            layanan_kegiatan=self.obj,
            tim_kegiatan=tim,
            instansi_tujuan=instansi,
            tanggal_mulai=today,
            tanggal_selesai=today,
        )

        response = self.client.post(reverse("operasional:hapus_layanan", args=[self.obj.pk]))

        self.assertRedirects(
            response,
            reverse("operasional:data_layanan"),
            fetch_redirect_response=False,
        )
        self.assertTrue(LayananKegiatan.objects.filter(pk=self.obj.pk).exists())
        messages = [str(message) for message in response.wsgi_request._messages]
        self.assertTrue(any(pengajuan.nomor_pengajuan in message for message in messages))

    def test_active_transaction_layanan_delete_button_is_locked(self):
        tim = TimKegiatan.objects.create(nama_tim="Tim Uji")
        instansi = InstansiKlien.objects.create(
            nama_instansi="Instansi Uji",
            alamat_instansi="Alamat Uji",
            organisasi=InstansiKlien.OrganisasiChoices.EKSTERNAL_PU,
        )
        today = timezone.localdate()
        PeminjamanRequest.objects.create(
            peminjam=self.user,
            nama_peminjam="Admin",
            layanan_kegiatan=self.obj,
            tim_kegiatan=tim,
            instansi_tujuan=instansi,
            tanggal_mulai=today,
            tanggal_selesai=today,
        )

        response = self.client.get(reverse("operasional:data_layanan"))

        self.assertContains(response, "operasional-delete-lock")
        self.assertContains(response, "disabled")
        self.assertNotContains(response, f'data-delete-url="{reverse("operasional:hapus_layanan", args=[self.obj.pk])}"')
