from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Logbook, Pelatihan, PesertaLogbook, PesertaPelatihan, Portofolio, Role, User


class SdmDashboardTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.user = User.objects.create_user(username='sdm-one')
        self.other = User.objects.create_user(username='sdm-two')
        self.admin = User.objects.create_user(username='sdm-admin')
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = self.admin.safe_profile
        profile.role = role
        profile.save()
        self.url = reverse('pengguna:dashboard_sdm')
        for actor in (self.user, self.other):
            Portofolio.objects.create(user=actor, nama='Proyek', lokasi='Bandung', tahun=self.today.year,
                                      uraian=['Analisis'])
        Portofolio.objects.create(user=self.user, nama='Lama', lokasi='Bandung', tahun=self.today.year-1,
                                  uraian=['Analisis'])
        self.log = Logbook.objects.create(user=self.user, tanggal=self.today, uraian='Kegiatan bersama')
        for actor in (self.user, self.other):
            PesertaLogbook.objects.create(logbook=self.log, user=actor)
        self.old_date = date(self.today.year-1, self.today.month, 1)
        self.old = Logbook.objects.create(user=self.other, tanggal=self.old_date, uraian='Kegiatan lama')
        PesertaLogbook.objects.create(logbook=self.old, user=self.other)
        training = Pelatihan.objects.create(user=self.user, kategori_kegiatan='Seminar',
            tipe_pelatihan=Pelatihan.TIPE_INTERNAL, jenis_pelatihan=Pelatihan.JENIS_LABORATORIUM,
            nama_pelatihan='Seminar bersama', tanggal_mulai=self.today, tanggal_selesai=self.today)
        for actor in (self.user, self.other):
            PesertaPelatihan.objects.create(pelatihan=training, user=actor)

    def test_current_period_aggregation_and_shared_records_count_once(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        chart = response.context['sdm_kategori_chart']
        self.assertEqual(chart['defaultYear'], self.today.year)
        self.assertEqual(chart['rows'], [{'year': self.today.year, 'key': 'Seminar', 'total': 1}])
        self.assertEqual(len(chart['categories']), 4)
        projects = response.context['sdm_portofolio_chart']['rows']
        self.assertEqual(projects, [{'year': self.today.year-1, 'key': str(self.today.year-1), 'total': 1},
                                    {'year': self.today.year, 'key': str(self.today.year), 'total': 2}])
        self.assertEqual(response.context['log_month'], self.today.month)
        self.assertEqual(list(response.context['logbook_page']), [self.log])
        self.assertContains(response, 'sdmKategoriChart')
        self.assertContains(response, 'sdmPortofolioChart')
        self.assertNotContains(response, 'id="sdmPortofolioYear"')

    def test_user_scope_cannot_be_overridden_and_monitor_filter_applies(self):
        for actor, selected in ((self.user, self.other), (self.admin, self.user)):
            self.client.force_login(actor)
            response = self.client.get(self.url, {'user': selected.pk, 'log_year': self.old_date.year, 'log_month': self.old_date.month})
            self.assertEqual(list(response.context['logbook_page']), [])
            self.assertEqual(sum(row['total'] for row in response.context['sdm_portofolio_chart']['rows']), 2)
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {'user': self.other.pk, 'log_year': self.old_date.year, 'log_month': self.old_date.month})
        self.assertEqual(list(response.context['logbook_page']), [self.old])
        self.assertEqual(sum(row['total'] for row in response.context['sdm_portofolio_chart']['rows']), 1)

    def test_bad_month_and_page_fall_back_and_login_is_required(self):
        self.client.force_login(self.user)
        for value in ('invalid', '2026-13', '', '99999-01'):
            response = self.client.get(self.url, {'log_month': value, 'log_page': 'invalid'})
            self.assertEqual(response.context['log_month'], self.today.month)
            self.assertEqual(list(response.context['logbook_page']), [self.log])
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_monthly_pagination_preserves_user_and_month(self):
        for i in range(21):
            obj = Logbook.objects.create(user=self.user, tanggal=self.today, uraian=f'Kegiatan {i}')
            PesertaLogbook.objects.create(logbook=obj, user=self.user)
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {'user': self.user.pk})
        self.assertEqual(response.context['logbook_page'].paginator.count, 22)
        self.assertEqual(len(response.context['logbook_page']), 20)
        self.assertContains(response, 'log_page=2')
        response = self.client.get(self.url, {'user': self.user.pk, 'log_page': 2})
        self.assertEqual(len(response.context['logbook_page']), 2)

    def test_split_periods_and_training_button_removed(self):
        training = Pelatihan.objects.first()
        training.tanggal_mulai = self.old_date
        training.tanggal_selesai = self.old_date
        training.save()
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['pelatihan_terbaru']), [])
        self.assertEqual(response.context['training_year'], self.today.year)
        self.assertEqual(response.context['training_month'], self.today.month)
        self.assertEqual(response.context['log_year'], self.today.year)
        self.assertNotContains(response, 'Lihat Data Pelatihan')
        response = self.client.get(self.url, {'training_year': self.old_date.year,
                                             'training_month': self.old_date.month})
        self.assertEqual(list(response.context['pelatihan_terbaru']), [training])
        self.assertEqual(list(response.context['logbook_page']), [self.log])
        response = self.client.get(self.url, {'log_year': self.old_date.year,
                                             'log_month': self.old_date.month})
        self.assertEqual(list(response.context['logbook_page']), [self.old])
        self.assertEqual(list(response.context['pelatihan_terbaru']), [])

    def test_search_before_pagination_no_duplicate_rows_and_preserves_filters(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {'log_q': 'Kegiatan bersama', 'user': self.user.pk})
        self.assertEqual(list(response.context['logbook_page']), [self.log])
        self.assertEqual(response.context['log_search'], 'Kegiatan bersama')
        for params in ({'log_q': self.other.username}, {'log_q': 'tidak ditemukan'},
                       {'log_q': 'lama'}):
            response = self.client.get(self.url, params)
            expected = [self.log] if params['log_q'] == self.other.username else []
            self.assertEqual(list(response.context['logbook_page']), expected)
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'log_year': self.old_date.year,
            'log_month': self.old_date.month, 'log_q': 'lama', 'user': self.other.pk})
        self.assertEqual(list(response.context['logbook_page']), [])
        for i in range(21):
            obj = Logbook.objects.create(user=self.user, tanggal=self.today, uraian=f'Target {i}')
            PesertaLogbook.objects.create(logbook=obj, user=self.user)
        response = self.client.get(self.url, {'log_q': 'Target', 'training_year': self.old_date.year,
                                             'training_month': 1})
        self.assertEqual(response.context['logbook_page'].paginator.count, 21)
        query = response.context['log_query']
        for text in ('log_q=Target', f'log_year={self.today.year}', 'training_month=1'):
            self.assertIn(text, query)
        self.assertContains(response, 'log_page=2')

    def test_live_tables_have_separate_targets_and_training_search_is_scoped(self):
        self.client.force_login(self.user)
        training = Pelatihan.objects.first()
        training.nama_pelatihan = 'Kegiatan target'
        training.save()
        response = self.client.get(self.url, {'training_q': 'target'},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(list(response.context['pelatihan_terbaru']), [training])
        self.assertEqual(list(response.context['logbook_page']), [self.log])
        self.assertContains(response, 'id="sdm-training-filter"')
        self.assertContains(response, 'id="sdm-logbook-filter"')
        self.assertContains(response, 'data-master-live-filter', count=2)
        self.assertNotContains(response, 'onchange="this.form.submit()" aria-label="Filter bulan')
        response = self.client.get(self.url, {'training_q': 'tidak ada', 'log_q': 'bersama'})
        self.assertEqual(list(response.context['pelatihan_terbaru']), [])
        self.assertEqual(list(response.context['logbook_page']), [self.log])
        self.assertIn('training_q=tidak+ada', response.context['log_query'])
