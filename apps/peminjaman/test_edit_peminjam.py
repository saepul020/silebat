from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.master_data.models import (
    BarangPenunjangOperasional,
    KategoriBarangPenunjangChoices,
    KetersediaanChoices,
)
from apps.operasional.models import (
    InstansiKlien,
    LayananKegiatan,
    SurveiKegiatan,
    TimKegiatan,
)
from apps.pengguna.models import Role, User

from .models import (
    PeminjamanBarangPenunjang,
    PeminjamanRequest,
    PeminjamanTimeline,
    ReturnStepChoices,
    StepChoices,
)


class EditPeminjamPengajuanTests(TestCase):
    def setUp(self):
        self.role_user = Role.objects.create(nama="User")
        self.role_admin = Role.objects.create(nama="Admin Lab")
        self.role_teknisi = Role.objects.create(nama="Teknisi Lab")
        self.user_lama = self._user("lama", "User Lama", self.role_user)
        self.user_baru = self._user("baru", "User Baru", self.role_user)
        self.admin = self._user("admin", "Admin", self.role_admin)
        self.teknisi = self._user("teknisi", "Teknisi", self.role_teknisi)
        self.layanan = LayananKegiatan.objects.create(jenis_layanan="Pengukuran")
        self.survei = SurveiKegiatan.objects.create(jenis_survei="Drone RTK")
        self.tim = TimKegiatan.objects.create(nama_tim="Tim A")
        self.instansi = InstansiKlien.objects.create(
            nama_instansi="Instansi A",
            alamat_instansi="Bandung",
            organisasi=InstansiKlien.OrganisasiChoices.INTERNAL_PU,
        )
        self.barang = BarangPenunjangOperasional.objects.create(
            nama_barang="Tripod",
            tipe_merek_barang="Tipe A",
            volume=1,
            satuan="Unit",
            kategori_barang=KategoriBarangPenunjangChoices.ALAT_SURVEI,
        )
        self.obj = PeminjamanRequest.objects.create(
            peminjam=self.user_lama,
            nama_peminjam="User Lama",
            tanggal_mulai=date(2026, 7, 1),
            tanggal_selesai=date(2026, 7, 2),
            layanan_kegiatan=self.layanan,
            tim_kegiatan=self.tim,
            instansi_tujuan=self.instansi,
            current_step=StepChoices.TEKNISI_LAB,
            return_current_step=ReturnStepChoices.NONE,
        )
        self.obj.kegiatan_survei.add(self.survei)
        PeminjamanBarangPenunjang.objects.create(
            pengajuan=self.obj,
            barang=self.barang,
            volume=1,
        )
        self.obj.apply_inventory_allocation()

    def _user(self, username, first_name, role):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            first_name=first_name,
            email=f"{username}@example.com",
            no_hp=f"08123{User.objects.count():04d}",
            nip=f"1999{User.objects.count():04d}",
        )
        user.safe_profile.role = role
        user.safe_profile.alamat = "Bandung"
        user.safe_profile.save(update_fields=["role", "alamat"])
        return user

    def _post_data(self, peminjam):
        return {
            "peminjam_user": str(peminjam.pk),
            "layanan_kegiatan": str(self.layanan.pk),
            "layanan_kegiatan_lainnya": "",
            "kegiatan_survei": [str(self.survei.pk)],
            "survei_lainnya": "",
            "tim_kegiatan": str(self.tim.pk),
            "instansi_tujuan": str(self.instansi.pk),
            "instansi_tujuan_lainnya": "",
            "tanggal_mulai": "01 Jul 2026",
            "tanggal_selesai": "02 Jul 2026",
            f"penunjang_qty_{self.barang.pk}": "1",
        }

    def test_teknisi_can_select_peminjam_on_edit_page(self):
        self.client.force_login(self.teknisi)

        response = self.client.get(reverse("peminjaman:edit", args=[self.obj.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="peminjam_user"')
        self.assertContains(response, "Pilih Peminjam")

    def test_edit_pengajuan_moves_history_to_new_peminjam(self):
        self.client.force_login(self.teknisi)

        response = self.client.post(
            reverse("peminjaman:edit", args=[self.obj.pk]),
            self._post_data(self.user_baru),
        )

        self.assertEqual(response.status_code, 302)
        self.obj.refresh_from_db()
        self.barang.refresh_from_db()

        self.assertEqual(self.obj.peminjam, self.user_baru)
        self.assertEqual(self.obj.nama_peminjam, "User Baru")
        self.assertFalse(
            PeminjamanRequest.objects.filter(
                pk=self.obj.pk,
                peminjam=self.user_lama,
            ).exists()
        )
        self.assertTrue(
            PeminjamanRequest.objects.filter(
                pk=self.obj.pk,
                peminjam=self.user_baru,
            ).exists()
        )
        self.assertEqual(self.barang.volume_dipinjam, 1)
        self.assertEqual(self.barang.ketersediaan, KetersediaanChoices.TIDAK_TERSEDIA)
        self.assertTrue(
            PeminjamanTimeline.objects.filter(
                pengajuan=self.obj,
                action="Data peminjam diperbarui",
                note__icontains="User Lama",
            ).exists()
        )

    def test_admin_lab_cannot_open_edit_form(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("peminjaman:edit", args=[self.obj.pk]))

        self.assertEqual(response.status_code, 302)

    def test_user_role_cannot_open_edit_form(self):
        self.client.force_login(self.user_lama)

        response = self.client.get(reverse("peminjaman:edit", args=[self.obj.pk]))

        self.assertEqual(response.status_code, 302)
