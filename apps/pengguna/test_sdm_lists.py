from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Logbook, Pelatihan, PesertaLogbook, PesertaPelatihan, Role, User


class SdmListsTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory(prefix='sdm-lists-')
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.today = timezone.localdate()
        self.owner = User.objects.create_user(username='owner-a', first_name='Penginput A')
        self.other = User.objects.create_user(username='owner-b', first_name='Penginput B')
        self.viewer = User.objects.create_user(username='viewer')
        self.admin = User.objects.create_user(username='admin-owner')
        self.set_role(self.admin, 'Super Admin')
        self.training, self.log = self.create_records(self.owner, 'Data A')
        self.other_training, self.other_log = self.create_records(self.other, 'Data B')
        self.admin_training, self.admin_log = self.create_records(self.admin, 'Data admin')
        # Peserta sengaja berbeda dari penginput untuk menguji dasar filter.
        PesertaPelatihan.objects.create(pelatihan=self.training, user=self.other)
        PesertaPelatihan.objects.create(pelatihan=self.other_training, user=self.owner)
        PesertaLogbook.objects.create(logbook=self.log, user=self.other)
        PesertaLogbook.objects.create(logbook=self.other_log, user=self.owner)
        self.url = reverse('pengguna:dashboard_sdm')
        self.client.force_login(self.viewer)

    def set_role(self, user, name):
        role, _ = Role.objects.get_or_create(nama=name)
        profile = user.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])

    def create_records(self, owner, title, day=None):
        day = day or self.today
        training = Pelatihan.objects.create(
            user=owner, nama_pelatihan=title, kategori_kegiatan='Seminar',
            tipe_pelatihan=Pelatihan.TIPE_INTERNAL, jenis_pelatihan=Pelatihan.JENIS_LABORATORIUM,
            tanggal_mulai=day, tanggal_selesai=day,
        )
        log = Logbook.objects.create(user=owner, tanggal=day, uraian=title)
        return training, log

    def assert_rows(self, response, trainings, logs):
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context['pelatihan_terbaru'], trainings)
        self.assertCountEqual(response.context['logbook_page'], logs)

    def test_all_users_can_read_all_creators_without_participant_membership(self):
        for role in ('User', 'Admin Lab', 'Teknisi Lab'):
            with self.subTest(role=role):
                self.set_role(self.viewer, role)
                response = self.client.get(self.url)
                self.assert_rows(response, [self.training, self.other_training, self.admin_training],
                                 [self.log, self.other_log, self.admin_log])
                self.assertFalse(response.context['show_sdm_user_filter'])
                self.assertContains(response, 'Penginput A')

    def test_monitor_filters_use_creator_and_include_admin_creators(self):
        for role in ('Kepala Lab', 'Pimpinan', 'Super Admin'):
            self.set_role(self.viewer, role)
            for owner, training, log in ((self.owner, self.training, self.log),
                                         (self.other, self.other_training, self.other_log),
                                         (self.admin, self.admin_training, self.admin_log)):
                with self.subTest(role=role, owner=owner.username):
                    response = self.client.get(self.url, {'user': owner.pk})
                    self.assert_rows(response, [training], [log])
                    self.assertEqual(response.context['selected_sdm_user_id'], str(owner.pk))

    def test_monitor_placeholder_and_invalid_selection_show_all(self):
        for role in ('Kepala Lab', 'Pimpinan', 'Super Admin'):
            self.set_role(self.viewer, role)
            for params in ({}, {'user': ''}, {'user': 'invalid'}, {'user': '999999999'}):
                with self.subTest(role=role, params=params):
                    response = self.client.get(self.url, params)
                    self.assert_rows(response, [self.training, self.other_training, self.admin_training],
                                     [self.log, self.other_log, self.admin_log])
                    self.assertEqual(response.context['selected_sdm_user_id'], '')

    def test_regular_user_query_cannot_activate_name_filter(self):
        for value in (self.owner.pk, self.admin.pk, 'invalid'):
            response = self.client.get(self.url, {'user': value})
            self.assert_rows(response, [self.training, self.other_training, self.admin_training],
                             [self.log, self.other_log, self.admin_log])

    def test_period_search_and_pagination_keep_creator_filter(self):
        self.set_role(self.viewer, 'Kepala Lab')
        for index in range(12):
            self.create_records(self.owner, f'Target {index}')
        response = self.client.get(self.url, {
            'user': self.owner.pk, 'training_q': 'Target', 'log_q': 'Target',
            'training_page': 2, 'log_page': 2,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(len(response.context['pelatihan_terbaru']), 2)
        self.assertEqual(len(response.context['logbook_page']), 2)
        for name in ('training_list', 'log_list'):
            self.assertEqual(response.context[name]['total_count'], 12)
            self.assertIn(f'user={self.owner.pk}', response.context[name]['query'])
        response = self.client.get(self.url, {'training_q': 'Penginput B', 'log_q': 'Penginput B'})
        self.assert_rows(response, [self.other_training], [self.log, self.other_log])

    def test_year_options_include_other_creators_and_all_months_work(self):
        old_day = date(self.today.year - 2, 1, 1)
        training, log = self.create_records(self.other, 'Riwayat B', old_day)
        response = self.client.get(self.url)
        self.assertIn(old_day.year, response.context['training_year_options'])
        self.assertIn(old_day.year, response.context['log_year_options'])
        response = self.client.get(self.url, {
            'training_year': old_day.year, 'training_month': 'all',
            'log_year': old_day.year, 'log_month': 'all',
        })
        self.assert_rows(response, [training], [log])

    def test_personal_chart_scope_still_uses_participation(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_pelatihan'], 1)
        self.assertEqual(sum(row['total'] for row in response.context['sdm_tipe_chart']['rows']), 1)
        self.assertEqual(response.context['training_list']['total_count'], 3)

    def test_shared_files_are_readable_but_management_stays_restricted(self):
        self.training.file_materi.save('materi.pdf', SimpleUploadedFile('materi.pdf', b'%PDF-1.4'))
        output = BytesIO()
        with Image.new('RGB', (20, 10), 'blue') as image:
            image.save(output, format='PNG')
        self.log.dokumen.save('foto.png', SimpleUploadedFile('foto.png', output.getvalue()))
        response = self.client.get(reverse('pengguna:sdm_materi', args=[self.training.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4')
        response = self.client.get(reverse('pengguna:sdm_preview', args=[self.log.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        for name, pk in (('pelatihan_edit', self.training.pk), ('pelatihan_hapus', self.training.pk),
                         ('materi_download', self.training.pk), ('logbook_edit', self.log.pk),
                         ('logbook_hapus', self.log.pk), ('logbook_preview', self.log.pk)):
            self.assertEqual(self.client.get(reverse('pengguna:' + name, args=[pk])).status_code, 404)
        self.client.logout()
        for name, pk in (('dashboard_sdm', None), ('sdm_materi', self.training.pk), ('sdm_preview', self.log.pk)):
            self.assertEqual(self.client.get(reverse('pengguna:' + name, args=[pk] if pk else [])).status_code, 302)
