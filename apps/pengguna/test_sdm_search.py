from datetime import date
from html.parser import HTMLParser

from . import test_sdm_peserta as fixtures


class PeriodParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.periods = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'select' and 'data-search-period' in attrs:
            self.periods[attrs['name']] = 'disabled' in attrs


class SdmSearchTests(fixtures.SdmPesertaTests):
    def test_keyword_overrides_period_only_for_its_own_table(self):
        training, log = self.create_records(self.owner, 'Arsip target', self.member,
                                            date(self.today.year - 2, self.today.month % 12 + 1, 1))
        self.set_role('Kepala Lab')
        for prefix in ('training', 'log'):
            with self.subTest(prefix=prefix):
                response = self.client.get(self.url, {
                    'user': self.member.pk, prefix + '_q': 'Arsip target',
                    prefix + '_year': self.today.year, prefix + '_month': self.today.month,
                }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                expected_training = [training] if prefix == 'training' else [self.training]
                expected_logs = [log] if prefix == 'log' else [self.log]
                self.assert_rows(response, expected_training, expected_logs)
                parser = PeriodParser()
                parser.feed(response.content.decode())
                for current in ('training', 'log'):
                    locked = current == prefix
                    self.assertEqual(response.context[current + '_year'], 'all' if locked else self.today.year)
                    self.assertEqual(response.context[current + '_month'], 'all' if locked else self.today.month)
                    self.assertEqual(parser.periods[current + '_year'], locked)
                    self.assertEqual(parser.periods[current + '_month'], locked)

    def test_search_keeps_membership_and_pagination_across_periods(self):
        self.set_role('Pimpinan')
        for index in range(12):
            self.create_records(self.owner, f'Arsip {index}', self.member,
                                date(self.today.year - index - 1, 1, 1))
        self.create_records(self.member, 'Arsip penginput tanpa peserta', day=date(self.today.year - 1, 1, 1))
        response = self.client.get(self.url, {
            'user': self.member.pk, 'training_q': 'Arsip', 'log_q': 'Arsip',
            'training_year': 'invalid', 'log_month': 99, 'training_page': 2, 'log_page': 2,
        })
        self.assertEqual(len(response.context['pelatihan_terbaru']), 2)
        self.assertEqual(len(response.context['logbook_page']), 2)
        for key in ('training_list', 'log_list'):
            self.assertEqual(response.context[key]['total_count'], 12)
            query = response.context[key]['query']
            for param in ('training_year=all', 'training_month=all', 'log_year=all', 'log_month=all'):
                self.assertIn(param, query)

    def test_empty_or_whitespace_keyword_unlocks_period(self):
        for value in ('', '   '):
            response = self.client.get(self.url, {
                'training_q': value, 'log_q': value,
                'training_year': 'all', 'training_month': 'all',
                'log_year': 'all', 'log_month': 'all',
            })
            parser = PeriodParser()
            parser.feed(response.content.decode())
            self.assertTrue(parser.periods)
            self.assertTrue(all(not locked for locked in parser.periods.values()))
        response = self.client.get(self.url, {'training_month': self.today.month, 'log_month': self.today.month})
        self.assertEqual(response.context['training_month'], self.today.month)
        self.assertEqual(response.context['log_month'], self.today.month)
