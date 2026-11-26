from datetime import date

from . import test_sdm_peserta as fixtures


class SdmYearTests(fixtures.SdmPesertaTests):
    def test_all_years_retains_month_and_both_all_show_every_period(self):
        old = date(self.today.year - 2, self.today.month, 1)
        other_month = date(self.today.year - 1, self.today.month % 12 + 1, 1)
        training, log = self.create_records(self.owner, 'Tahun lama', self.member, old)
        extra_training, extra_log = self.create_records(self.owner, 'Bulan lain', self.member, other_month)
        self.set_role('Kepala Lab')
        response = self.client.get(self.url, {
            'user': self.member.pk, 'training_year': 'all', 'log_year': 'all',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assert_rows(response, [self.training, training], [self.log, log])
        for key in ('training_year', 'log_year'):
            self.assertEqual(response.context[key], 'all')
        self.assertContains(response, '<option value="all" selected>Semua</option>', count=2)
        response = self.client.get(self.url, {
            'user': self.member.pk, 'training_year': 'all', 'training_month': 'all',
            'log_year': 'all', 'log_month': 'all',
        })
        self.assert_rows(response, [self.training, training, extra_training], [self.log, log, extra_log])

    def test_all_years_is_independent_and_preserved_in_search_pagination(self):
        self.set_role('Pimpinan')
        for index in range(12):
            self.create_records(self.owner, f'Target {index}', self.member,
                                date(self.today.year - index - 1, self.today.month, 1))
        params = {'user': self.member.pk, 'training_year': 'all', 'training_q': 'Target',
                  'training_page': 2, 'log_year': self.today.year}
        response = self.client.get(self.url, params, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(len(response.context['pelatihan_terbaru']), 2)
        self.assertCountEqual(response.context['logbook_page'], [self.log])
        self.assertEqual(response.context['training_list']['total_count'], 12)
        for listing in ('training_list', 'log_list'):
            query = response.context[listing]['query']
            self.assertIn('training_year=all', query)
            self.assertIn(f'log_year={self.today.year}', query)
            self.assertIn(f'user={self.member.pk}', query)
        params.update(training_entries='all', log_year='all', log_q='Target', log_entries='all')
        response = self.client.get(self.url, params)
        self.assertEqual(len(response.context['pelatihan_terbaru']), 12)
        self.assertEqual(len(response.context['logbook_page']), 12)

    def test_defaults_and_invalid_periods_still_fall_back(self):
        for params in ({}, {'training_year': 'invalid', 'log_year': 'invalid'},
                       {'training_year': 'all', 'training_month': 13,
                        'log_year': 'all', 'log_month': 0},
                       {'training_year': 10000, 'log_year': -1}):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, 200)
                for prefix in ('training', 'log'):
                    self.assertEqual(response.context[prefix + '_year'], self.today.year)
                    self.assertEqual(response.context[prefix + '_month'], self.today.month)
                    self.assertTrue(all(isinstance(year, int) for year in response.context[prefix + '_year_options']))
