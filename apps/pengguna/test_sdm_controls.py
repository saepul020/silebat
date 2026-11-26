from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Logbook, Pelatihan, PesertaLogbook, PesertaPelatihan, User


class SdmControlsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.user = User.objects.create_user(username='controls-user')
        cls.other = User.objects.create_user(username='controls-other')
        cls.url = reverse('pengguna:dashboard_sdm')
        for index in range(26):
            cls.create_records(cls.user, cls.today, f'Target {index}')
        cls.other_month = date(cls.today.year, cls.today.month % 12 + 1, 1)
        cls.create_records(cls.user, cls.other_month, 'Bulan lain')
        cls.create_records(cls.user, date(cls.today.year - 1, 1, 1), 'Tahun lalu')
        cls.create_records(cls.other, cls.today, 'Data privat')

    @classmethod
    def create_records(cls, actor, day, label):
        training = Pelatihan.objects.create(
            user=actor, nama_pelatihan=label, kategori_kegiatan='Seminar',
            tipe_pelatihan=Pelatihan.TIPE_INTERNAL,
            jenis_pelatihan=Pelatihan.JENIS_LABORATORIUM,
            tanggal_mulai=day, tanggal_selesai=day,
        )
        PesertaPelatihan.objects.create(pelatihan=training, user=actor)
        log = Logbook.objects.create(user=actor, tanggal=day, uraian=label)
        PesertaLogbook.objects.create(logbook=log, user=actor)

    def setUp(self):
        self.client.force_login(self.user)

    def test_entry_options_and_invalid_values(self):
        for value, count in [('10', 10), ('25', 25), ('50', 26), ('100', 26),
                             ('all', 26), ('invalid', 10), ('0', 10), ('-1', 10)]:
            with self.subTest(value=value):
                response = self.client.get(self.url, {
                    'training_entries': value, 'log_entries': value,
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context['pelatihan_terbaru']), count)
                self.assertEqual(len(response.context['logbook_page']), count)
                for key in ('training_list', 'log_list'):
                    self.assertEqual(response.context[key]['total_count'], 26)
        self.assertContains(response, 'name="training_entries"')
        self.assertContains(response, 'name="log_entries"')
        self.assertContains(response, 'value="all">Semua</option>', count=4)

    def test_all_months_keeps_year_search_and_ownership(self):
        params = {'training_month': 'all', 'log_month': 'all',
                  'training_entries': 'all', 'log_entries': 'all', 'user': self.other.pk}
        response = self.client.get(self.url, params)
        self.assertEqual(len(response.context['pelatihan_terbaru']), 27)
        self.assertEqual(len(response.context['logbook_page']), 27)
        self.assertNotContains(response, 'Data privat')
        self.assertNotContains(response, 'Tahun lalu')
        params.update(training_q='Bulan lain', log_q='Bulan lain')
        response = self.client.get(self.url, params)
        self.assertEqual(len(response.context['pelatihan_terbaru']), 1)
        self.assertEqual(len(response.context['logbook_page']), 1)
        self.assertEqual(response.context['training_month'], 'all')
        self.assertEqual(response.context['log_month'], 'all')

    def test_independent_pagination_and_preserved_filters(self):
        response = self.client.get(self.url, {
            'training_entries': '25', 'training_page': '2', 'training_month': 'all',
            'log_entries': '10', 'log_page': '2', 'log_q': 'Target',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(len(response.context['pelatihan_terbaru']), 2)
        self.assertEqual(len(response.context['logbook_page']), 10)
        self.assertEqual(response.context['training_list']['page_obj'].number, 2)
        self.assertEqual(response.context['log_list']['page_obj'].number, 2)
        for key in ('training_list', 'log_list'):
            query = response.context[key]['query']
            self.assertIn('training_entries=25', query)
            self.assertIn('log_entries=10', query)
            self.assertIn('training_month=all', query)
            self.assertIn('log_q=Target', query)
        self.assertContains(response, 'training_page=1')
        self.assertContains(response, 'log_page=3')
