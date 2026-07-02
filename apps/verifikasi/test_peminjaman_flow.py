from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.peminjaman.models import (
    DecisionChoices,
    PeminjamanRequest,
    StepChoices,
)
from apps.pengguna.models import Role, User


class PeminjamanFlowTests(TestCase):
    def setUp(self):
        self.role_teknisi = Role.objects.create(nama="Teknisi Lab")
        self.role_user = Role.objects.create(nama="User")
        self.teknisi = self._user("teknisi", "Teknisi", self.role_teknisi)
        self.peminjam = self._user("peminjam", "Peminjam", self.role_user)
        self.obj = PeminjamanRequest.objects.create(
            peminjam=self.peminjam,
            nama_peminjam="Peminjam",
            tanggal_mulai=date(2026, 7, 1),
            tanggal_selesai=date(2026, 7, 2),
            current_step=StepChoices.TEKNISI_LAB,
        )

    def _user(self, username, first_name, role):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            first_name=first_name,
        )
        user.safe_profile.role = role
        user.safe_profile.save(update_fields=["role"])
        return user

    def test_teknisi_lanjutkan_proses_goes_to_kepala_lab(self):
        self.client.force_login(self.teknisi)

        response = self.client.post(
            reverse("verifikasi:detail", args=[self.obj.pk]),
            {"aksi": "selesai", "catatan": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.current_step, StepChoices.KEPALA_LAB)
        self.assertEqual(self.obj.teknisi_lab_status, DecisionChoices.READY)
        self.assertEqual(self.obj.kepala_lab_status, DecisionChoices.PENDING)
        self.assertTrue(
            self.obj.timeline_entries.filter(
                stage="Teknisi Lab",
                action="Pemenuhan barang selesai dan dikirim ke Kepala Lab",
            ).exists()
        )
