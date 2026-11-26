from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Logbook, Pelatihan, PesertaLogbook, PesertaPelatihan, Role, User


class SdmFilesTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory(prefix='silebat-files-')
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(username='files-user')
        self.other = User.objects.create_user(username='files-other')
        today = timezone.localdate()
        self.training = Pelatihan.objects.create(
            user=self.user, nama_pelatihan='Pelatihan dengan materi', kategori_kegiatan='Seminar',
            tipe_pelatihan=Pelatihan.TIPE_INTERNAL, jenis_pelatihan=Pelatihan.JENIS_LABORATORIUM,
            tanggal_mulai=today, tanggal_selesai=today,
            file_materi=SimpleUploadedFile('materi.pdf', b'%PDF-1.4 materi'),
        )
        PesertaPelatihan.objects.create(pelatihan=self.training, user=self.user)
        output = BytesIO()
        with Image.new('RGB', (40, 20), 'blue') as image:
            image.save(output, format='PNG')
        self.log = Logbook.objects.create(
            user=self.user, tanggal=today, uraian='Logbook dengan foto',
            dokumen=SimpleUploadedFile('foto.png', output.getvalue()),
        )
        PesertaLogbook.objects.create(logbook=self.log, user=self.user)
        self.dashboard = reverse('pengguna:dashboard_sdm')
        self.materi = reverse('pengguna:sdm_materi', args=[self.training.pk])
        self.preview = reverse('pengguna:sdm_preview', args=[self.log.pk])

    def assert_files_available(self):
        response = self.client.get(self.materi)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 materi')
        response = self.client.get(self.preview)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.size, (40, 20))

    def test_participant_download_preview_and_live_rows(self):
        self.client.force_login(self.user)
        self.assert_files_available()
        for params in ({}, {'log_q': 'foto', 'training_entries': 'all', 'log_entries': 'all'}):
            response = self.client.get(self.dashboard, params, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertContains(response, '<th>Materi</th>')
            self.assertContains(response, '<th>Dokumentasi Kegiatan</th>')
            self.assertContains(response, f'href="{self.materi}"')
            self.assertContains(response, f'data-photo-src="{self.preview}"')
            self.assertContains(response, 'id="sdm-photo-modal"', count=1)

    def test_monitor_roles_can_open_visible_files_without_edit_access(self):
        for name in ('Super Admin', 'Kepala Lab', 'Pimpinan'):
            with self.subTest(role=name):
                role, _ = Role.objects.get_or_create(nama=name)
                profile = self.other.safe_profile
                profile.role = role
                profile.save(update_fields=['role'])
                self.client.force_login(self.other)
                response = self.client.get(self.dashboard, {'user': self.user.pk})
                self.assertContains(response, f'data-photo-src="{self.preview}"')
                self.assert_files_available()
                if name != 'Super Admin':
                    self.assertEqual(self.client.get(reverse('pengguna:pelatihan_edit', args=[self.training.pk])).status_code, 404)

    def test_outsider_cannot_override_scope_and_anonymous_must_login(self):
        self.client.force_login(self.other)
        for url in (self.materi, self.preview):
            self.assertEqual(self.client.get(url, {'user': self.user.pk}).status_code, 404)
        self.client.logout()
        for url in (self.materi, self.preview):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_missing_and_invalid_files_return_404(self):
        self.client.force_login(self.user)
        self.training.file_materi = 'pengguna/pelatihan/materi/missing.pdf'
        self.training.save(update_fields=['file_materi'])
        self.log.dokumen = SimpleUploadedFile('rusak.png', b'invalid')
        self.log.save(update_fields=['dokumen'])
        self.assertEqual(self.client.get(self.materi).status_code, 404)
        self.assertEqual(self.client.get(self.preview).status_code, 404)
        self.training.file_materi = ''
        self.training.save(update_fields=['file_materi'])
        self.log.dokumen = ''
        self.log.save(update_fields=['dokumen'])
        self.assertEqual(self.client.get(self.materi).status_code, 404)
        self.assertEqual(self.client.get(self.preview).status_code, 404)
        response = self.client.get(self.dashboard)
        self.assertNotContains(response, f'href="{self.materi}"')
        self.assertNotContains(response, 'data-inventory-photo-open')

    def test_existing_materi_endpoint_keeps_its_permissions(self):
        url = reverse('pengguna:materi_download', args=[self.training.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 materi')
