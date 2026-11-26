from datetime import date

from . import test_sdm_peserta as fixtures
from .models import PesertaLogbook


class SdmStatsTests(fixtures.SdmPesertaTests):
    def test_personal_tasks_cover_full_current_year_by_participation(self):
        self.client.force_login(self.member)
        for day in (date(self.today.year, 1, 1), date(self.today.year, 12, 31),
                    date(self.today.year - 1, 12, 31), date(self.today.year + 1, 1, 1)):
            self.create_records(self.owner, 'Logbook tahunan', self.member, day)
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_tugas'], 3)
        self.assertEqual(response.context['sdm_year'], self.today.year)
        self.assertContains(response, '>Tugas Selesai</p>', count=1)
        self.assertContains(response, '>Total Pelatihan</p>', count=1)
        html = response.content.decode()
        self.assertLess(html.index('>Tugas Selesai</p>'), html.index('>Total Pelatihan</p>'))

    def test_tasks_ignore_table_filters_search_and_pagination(self):
        self.client.force_login(self.member)
        for params in ({'log_year': self.today.year - 1, 'log_month': 1},
                       {'log_q': 'tidak ditemukan', 'training_q': 'tidak ditemukan'},
                       {'log_year': 'all', 'log_month': 'all', 'log_entries': 'all'},
                       {'log_page': 99, 'log_entries': 25}):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.context['total_tugas'], 1)

    def test_monitor_user_filter_and_all_count_records_once(self):
        PesertaLogbook.objects.create(logbook=self.log, user=self.viewer)
        self.create_records(self.owner, 'Tahun lalu', self.member, date(self.today.year - 1, 1, 1))
        for role in ('Kepala Lab', 'Pimpinan', 'Super Admin'):
            self.set_role(role)
            for params, count in (({}, 2), ({'user': 'all'}, 2), ({'user': self.member.pk}, 1),
                                  ({'user': self.owner.pk}, 1), ({'user': self.viewer.pk}, 1)):
                with self.subTest(role=role, params=params):
                    response = self.client.get(self.url, params)
                    self.assertEqual(response.context['total_tugas'], count)

    def test_ordinary_users_with_no_membership_see_zero_even_with_forged_user_filter(self):
        for role in ('User', 'Admin Lab', 'Teknisi Lab'):
            with self.subTest(role=role):
                self.set_role(role)
                response = self.client.get(self.url, {'user': self.member.pk})
                self.assertEqual(response.context['total_tugas'], 0)
