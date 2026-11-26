from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Logbook, Pelatihan, PesertaLogbook, PesertaPelatihan, Role, User


class SdmPesertaTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.owner = User.objects.create_user(username='peserta-owner')
        self.member = User.objects.create_user(username='peserta-member')
        self.viewer = User.objects.create_user(username='peserta-viewer')
        self.training, self.log = self.create_records(self.owner, 'Kegiatan bersama', self.member)
        self.own_training, self.own_log = self.create_records(self.member, 'Input tanpa keikutsertaan')
        PesertaPelatihan.objects.create(pelatihan=self.training, user=self.owner)
        PesertaLogbook.objects.create(logbook=self.log, user=self.owner)
        self.url = reverse('pengguna:dashboard_sdm')
        self.client.force_login(self.viewer)

    def set_role(self, role_name):
        role, _ = Role.objects.get_or_create(nama=role_name)
        profile = self.viewer.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])

    def create_records(self, owner, title, member=None, day=None):
        day = day or self.today
        training = Pelatihan.objects.create(
            user=owner, nama_pelatihan=title, kategori_kegiatan='Seminar',
            tipe_pelatihan=Pelatihan.TIPE_INTERNAL, jenis_pelatihan=Pelatihan.JENIS_LABORATORIUM,
            tanggal_mulai=day, tanggal_selesai=day,
        )
        log = Logbook.objects.create(user=owner, tanggal=day, uraian=title)
        if member:
            PesertaPelatihan.objects.create(pelatihan=training, user=member)
            PesertaLogbook.objects.create(logbook=log, user=member)
        return training, log

    def assert_rows(self, response, trainings, logs):
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.context['pelatihan_terbaru'], trainings)
        self.assertCountEqual(response.context['logbook_page'], logs)

    def test_monitor_name_filter_uses_membership_instead_of_creator(self):
        for role in ('Kepala Lab', 'Pimpinan', 'Super Admin'):
            with self.subTest(role=role):
                self.set_role(role)
                response = self.client.get(self.url, {'user': self.member.pk})
                self.assert_rows(response, [self.training], [self.log])
                self.assertEqual(response.context['selected_sdm_user_id'], str(self.member.pk))
                response = self.client.get(self.url, {'user': self.viewer.pk})
                self.assert_rows(response, [], [])

    def test_all_and_placeholder_still_show_every_record(self):
        for role in ('Kepala Lab', 'Pimpinan', 'Super Admin'):
            self.set_role(role)
            for params in ({}, {'user': ''}, {'user': 'all'}):
                with self.subTest(role=role, params=params):
                    self.assert_rows(self.client.get(self.url, params),
                                     [self.training, self.own_training], [self.log, self.own_log])

    def test_ordinary_roles_cannot_activate_name_filter(self):
        for role in ('User', 'Admin Lab', 'Teknisi Lab'):
            self.set_role(role)
            response = self.client.get(self.url, {'user': self.member.pk})
            self.assert_rows(response, [self.training, self.own_training], [self.log, self.own_log])
            self.assertFalse(response.context['show_sdm_user_filter'])

    def test_search_and_pagination_preserve_membership_without_duplicates(self):
        self.set_role('Kepala Lab')
        for index in range(12):
            self.create_records(self.owner, f'Target {index}', self.member)
        # Data penginput yang cocok pencarian harus tetap di luar hasil jika bukan peserta.
        self.create_records(self.member, 'Target penginput')
        response = self.client.get(self.url, {
            'user': self.member.pk, 'training_q': 'Target', 'log_q': 'Target',
            'training_page': 2, 'log_page': 2,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(len(response.context['pelatihan_terbaru']), 2)
        self.assertEqual(len(response.context['logbook_page']), 2)
        for key in ('training_list', 'log_list'):
            self.assertEqual(response.context[key]['total_count'], 12)
            self.assertIn(f'user={self.member.pk}', response.context[key]['query'])
        response = self.client.get(self.url, {'user': self.member.pk, 'log_q': 'peserta-'})
        self.assertEqual(response.context['log_list']['total_count'], 13)
        self.assertEqual(len({row.pk for row in response.context['logbook_page']}), 10)

    def test_year_options_and_all_months_follow_membership(self):
        old_day = date(self.today.year - 2, 1, 1)
        training, log = self.create_records(self.owner, 'Kegiatan lama', self.member, old_day)
        self.set_role('Pimpinan')
        response = self.client.get(self.url, {'user': self.member.pk})
        self.assertIn(old_day.year, response.context['training_year_options'])
        self.assertIn(old_day.year, response.context['log_year_options'])
        response = self.client.get(self.url, {
            'user': self.member.pk, 'training_year': old_day.year, 'training_month': 'all',
            'log_year': old_day.year, 'log_month': 'all',
        })
        self.assert_rows(response, [training], [log])
