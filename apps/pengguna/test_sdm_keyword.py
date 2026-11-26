from datetime import date

from . import test_sdm_peserta as fixtures
from .models import PesertaPelatihan, User


class SdmKeywordTests(fixtures.SdmPesertaTests):
    def add_member(self, training, username='anggota-tersembunyi'):
        user = User.objects.create_user(username=username, first_name='Nama Peserta Khusus', last_name='Akhir')
        PesertaPelatihan.objects.create(pelatihan=training, user=user)
        return user

    def test_username_and_participant_names_find_hidden_data_across_periods(self):
        training, _ = self.create_records(self.owner, 'Arsip kegiatan', day=date(self.today.year - 2, 1, 1))
        member = self.add_member(training)
        for keyword in (member.username, member.first_name, member.last_name, member.username.upper()):
            with self.subTest(keyword=keyword):
                response = self.client.get(self.url, {'training_q': keyword},
                                           HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 200)
                self.assertCountEqual(response.context['pelatihan_terbaru'], [training])
                self.assertEqual(response.context['training_year'], 'all')
                self.assertEqual(response.context['training_month'], 'all')

    def test_multiple_matching_participants_do_not_duplicate_pagination(self):
        first = self.add_member(self.training)
        second = self.add_member(self.training, 'anggota-kedua')
        for index in range(11):
            training, _ = self.create_records(self.owner, f'Kegiatan {index}')
            for member in (first, second):
                PesertaPelatihan.objects.create(pelatihan=training, user=member)
        response = self.client.get(self.url, {'training_q': 'Nama Peserta Khusus', 'training_page': 2})
        self.assertEqual(response.context['training_list']['total_count'], 12)
        self.assertEqual(len(response.context['pelatihan_terbaru']), 2)
        self.assertEqual(len({row.pk for row in response.context['pelatihan_terbaru']}), 2)
        self.assertIn('training_q=Nama+Peserta+Khusus', response.context['training_list']['query'])

    def test_search_of_other_participant_keeps_selected_user_membership(self):
        member = self.add_member(self.training)
        extra, _ = self.create_records(self.owner, 'Kegiatan di luar filter')
        PesertaPelatihan.objects.create(pelatihan=extra, user=member)
        for role in ('Kepala Lab', 'Pimpinan', 'Super Admin'):
            with self.subTest(role=role):
                self.set_role(role)
                response = self.client.get(self.url, {'user': self.member.pk, 'training_q': member.username})
                self.assertCountEqual(response.context['pelatihan_terbaru'], [self.training])
                self.assertEqual(response.context['training_list']['total_count'], 1)
