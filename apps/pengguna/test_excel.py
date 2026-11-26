from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.test import Client, TestCase
from django.template.loader import render_to_string
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from .excel_data import EXCEL_DATA, excel_headers
from .models import PesertaLogbook, Role, User


class ExcelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='excel-admin')
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = self.admin.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])
        self.user = User.objects.create_user(username='excel-user')
        self.other = User.objects.create_user(username='excel-other')
        self.client.force_login(self.admin)

    def url(self, kind, action='import'):
        return reverse(f'pengguna:{kind}_{action}')

    def row(self, kind):
        config = EXCEL_DATA[kind]
        row = [self.user.username, *config['sample']]
        if config.get('participants'):
            row.append(f'{self.user.username}; {self.other.username}')
        return row

    def workbook(self, kind, rows=None, headers=None):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(headers if headers is not None else excel_headers(EXCEL_DATA[kind]))
        for row in rows if rows is not None else [self.row(kind)]:
            sheet.append(row)
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = 's'
        output = BytesIO()
        workbook.save(output)
        return SimpleUploadedFile('import.xlsx', output.getvalue())

    def post(self, kind, action, **kwargs):
        return self.client.post(self.url(kind), {'import_action': action, **kwargs},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def validate(self, kind, **kwargs):
        return self.post(kind, 'validate', file_import=self.workbook(kind, **kwargs))

    def test_buttons_templates_and_downloads_for_all_menus(self):
        for kind in EXCEL_DATA:
            with self.subTest(kind=kind):
                page = self.client.get(self.url(kind, 'daftar'))
                self.assertContains(page, 'Export Data')
                self.assertContains(page, 'Import Data')
                self.assertContains(page, f'data-import-target="#{kind}-import"')
                self.assertContains(page, 'Data duplikat diperbolehkan.')
                response = self.client.get(self.url(kind, 'format'))
                self.assertEqual(response.status_code, 200)
                book = load_workbook(BytesIO(response.content))
                self.assertEqual(list(next(book.active.values)), excel_headers(EXCEL_DATA[kind]))
                self.assertIn('Referensi Pilihan', book.sheetnames)
                book.close()

    def test_duplicate_rows_are_imported_as_new_records_and_exported(self):
        for kind, config in EXCEL_DATA.items():
            with self.subTest(kind=kind):
                row = self.row(kind)
                response = self.validate(kind, rows=[row, row]).json()
                self.assertTrue(response['can_save'], response)
                model = config['form']._meta.model
                self.assertEqual(model.objects.count(), 0)
                result = self.post(kind, 'save').json()
                self.assertTrue(result['saved'], result)
                self.assertEqual(model.objects.count(), 2)
                for obj in model.objects.all():
                    self.assertEqual(obj.user_id, self.user.pk)
                    if config.get('participants'):
                        self.assertCountEqual(obj.peserta.values_list('user_id', flat=True),
                                              [self.user.pk, self.other.pk])
                exported = self.client.get(self.url(kind, 'export'))
                self.assertEqual(exported.status_code, 200)
                book = load_workbook(BytesIO(exported.content))
                rows = list(book.active.values)
                self.assertEqual(len(rows), 3)
                self.assertEqual(rows[1][0], self.user.username)
                self.assertEqual(rows[1], rows[2])
                book.close()
                self.assertFalse(self.post(kind, 'save').json()['saved'])
                self.assertTrue(self.validate(kind).json()['can_save'])
                self.assertTrue(self.post(kind, 'save').json()['saved'])
                self.assertEqual(model.objects.count(), 3)

    def test_one_invalid_row_prevents_all_saves(self):
        for kind, config in EXCEL_DATA.items():
            with self.subTest(kind=kind):
                bad = self.row(kind)
                bad[1] = ''
                payload = self.validate(kind, rows=[self.row(kind), bad]).json()
                self.assertFalse(payload['can_save'])
                self.assertTrue(any('Baris 3:' in error for error in payload['errors']))
                self.assertFalse(self.post(kind, 'save').json()['saved'])
                self.assertEqual(config['form']._meta.model.objects.count(), 0)

    def test_login_is_required(self):
        self.client.logout()
        for kind in EXCEL_DATA:
            for action in ('format', 'export'):
                self.assertEqual(self.client.get(self.url(kind, action)).status_code, 302)
            self.assertEqual(self.post(kind, 'validate').status_code, 302)
            self.assertEqual(self.post(kind, 'save').status_code, 302)

    def test_all_roles_can_access_buttons_downloads_and_import(self):
        for role_name in ('User', 'Admin Lab', 'Teknisi Lab', 'Kepala Lab', 'Pimpinan', 'Super Admin'):
            actor = self.admin if role_name == 'Super Admin' else self.user
            role, _ = Role.objects.get_or_create(nama=role_name)
            profile = actor.safe_profile
            profile.role = role
            profile.save(update_fields=['role'])
            self.client.force_login(actor)
            for kind in EXCEL_DATA:
                with self.subTest(role=role_name, kind=kind):
                    page = self.client.get(self.url(kind, 'daftar'))
                    self.assertContains(page, 'Export Data')
                    self.assertContains(page, f'id="{kind}-import"')
                    for action in ('format', 'export'):
                        self.assertEqual(self.client.get(self.url(kind, action)).status_code, 200)
                    result = self.validate(kind).json()
                    self.assertTrue(result['can_save'], result)
                    self.assertTrue(self.post(kind, 'save').json()['saved'])

    def test_export_matches_list_ownership_and_participant_access(self):
        for kind, config in EXCEL_DATA.items():
            with self.subTest(kind=kind):
                self.client.force_login(self.admin)
                own, other = self.row(kind), self.row(kind)
                other[0] = self.other.username
                rows = [own, other]
                if config.get('participants'):
                    other[-1] = self.other.username
                    shared = other.copy()
                    shared[-1] = self.user.username
                    rows.append(shared)
                self.assertTrue(self.validate(kind, rows=rows).json()['can_save'])
                self.assertTrue(self.post(kind, 'save').json()['saved'])
                self.client.force_login(self.user)
                response = self.client.get(self.url(kind, 'export'))
                book = load_workbook(BytesIO(response.content))
                values = list(book.active.values)[1:]
                self.assertEqual(len(values), 2 if config.get('participants') else 1)
                self.assertEqual(sum(row[0] == self.user.username for row in values), 1)
                book.close()

    def test_regular_users_cannot_import_for_another_owner(self):
        self.client.force_login(self.user)
        for kind, config in EXCEL_DATA.items():
            with self.subTest(kind=kind):
                row = self.row(kind)
                row[0] = self.other.username
                result = self.validate(kind, rows=[row]).json()
                self.assertFalse(result['can_save'])
                self.assertFalse(self.post(kind, 'save').json()['saved'])
                self.assertEqual(config['form']._meta.model.objects.count(), 0)

    def test_regular_user_is_required_as_participant(self):
        self.client.force_login(self.user)
        for kind in ('pelatihan', 'logbook'):
            row = self.row(kind)
            row[-1] = self.other.username
            result = self.validate(kind, rows=[row]).json()
            self.assertFalse(result['can_save'])
            self.assertTrue(any('Penginput wajib' in error for error in result['errors']))

    def test_regular_user_template_and_empty_identity_default_to_self(self):
        self.client.force_login(self.user)
        for kind, config in EXCEL_DATA.items():
            with self.subTest(kind=kind):
                response = self.client.get(self.url(kind, 'format'))
                book = load_workbook(BytesIO(response.content))
                self.assertEqual(book.active['A2'].value, self.user.username)
                owners = [row[0] for row in list(book['Referensi Pilihan'].values)[1:] if row[0]]
                self.assertEqual(owners, [self.user.username])
                book.close()
                row = self.row(kind)
                row[0] = ''
                if config.get('participants'):
                    row[-1] = ''
                result = self.validate(kind, rows=[row]).json()
                self.assertTrue(result['can_save'], result)
                self.assertTrue(self.post(kind, 'save').json()['saved'])
                obj = config['form']._meta.model.objects.get()
                self.assertEqual(obj.user_id, self.user.pk)
                if config.get('participants'):
                    self.assertEqual(list(obj.peserta.values_list('user_id', flat=True)), [self.user.pk])

    def test_permissions_are_checked_again_after_admin_is_demoted(self):
        self.assertTrue(self.validate('karir').json()['can_save'])
        profile = self.admin.safe_profile
        profile.role = Role.objects.get_or_create(nama='User')[0]
        profile.save(update_fields=['role'])
        result = self.post('karir', 'save').json()
        self.assertFalse(result['saved'])
        self.assertEqual(EXCEL_DATA['karir']['form']._meta.model.objects.count(), 0)

    def test_user_management_import_remains_admin_only(self):
        self.client.force_login(self.user)
        for action in ('export_pengguna', 'download_format_import_pengguna'):
            self.assertNotEqual(self.client.get(reverse('pengguna:' + action)).status_code, 200)
        self.assertNotEqual(self.client.post(reverse('pengguna:import_pengguna'), {
            'import_action': 'save',
        }).status_code, 200)

    def test_shared_import_modal_requires_explicit_opt_in_for_regular_users(self):
        context = {'role_access': {'is_super_admin': False},
                   'request': SimpleNamespace(user=self.user), 'csrf_token': 'test'}
        template = 'components/import_modal.html'
        self.assertNotIn('data-import-modal', render_to_string(template, context))
        context['import_allowed'] = True
        self.assertIn('data-import-modal', render_to_string(template, context))
        context['request'] = SimpleNamespace(user=AnonymousUser())
        self.assertNotIn('data-import-modal', render_to_string(template, context))

    def test_users_and_participants_are_revalidated_before_save(self):
        self.assertTrue(self.validate('logbook').json()['can_save'])
        self.other.delete()
        response = self.post('logbook', 'save').json()
        self.assertFalse(response['saved'])
        self.assertEqual(EXCEL_DATA['logbook']['form']._meta.model.objects.count(), 0)

    def test_imports_are_separate_and_cancel_clears_pending_rows(self):
        self.assertTrue(self.validate('karir').json()['can_save'])
        self.assertTrue(self.validate('portofolio').json()['can_save'])
        self.assertTrue(self.post('karir', 'cancel').json()['cancelled'])
        self.assertFalse(self.post('karir', 'save').json()['saved'])
        self.assertTrue(self.post('portofolio', 'save').json()['saved'])

    def test_bad_file_headers_and_empty_workbook_invalidate_pending_data(self):
        for file in (SimpleUploadedFile('data.csv', b'x'), SimpleUploadedFile('bad.xlsx', b'bad'),
                     SimpleUploadedFile('big.xlsx', b'x' * (7 * 1024 * 1024 + 1)),
                     self.workbook('karir', headers=['Invalid']), self.workbook('karir', rows=[])):
            with self.subTest(file=file.name):
                self.assertTrue(self.validate('karir').json()['can_save'])
                payload = self.post('karir', 'validate', file_import=file).json()
                self.assertFalse(payload['can_save'])
                self.assertFalse(self.post('karir', 'save').json()['saved'])

    def test_dates_choices_scores_and_unknown_users_are_rejected(self):
        for kind, index, value in (
            ('karir', 3, 'Tidak valid'), ('karir', 4, '31 Feb 2020'),
            ('karir', 5, '01 Jan 2019'), ('karir', 6, 'Mungkin'),
            ('pendidikan', 5, '01 Jan 2999'), ('pendidikan', 7, '5.00'),
            ('pelatihan', 1, 'Tidak valid'), ('pelatihan', 6, '01 Jan 2019'),
            ('portofolio', 4, '1800'), ('logbook', 0, 'unknown'), ('logbook', 4, 'unknown'),
        ):
            with self.subTest(kind=kind, index=index, value=value):
                row = self.row(kind)
                row[index] = value
                self.assertFalse(self.validate(kind, rows=[row]).json()['can_save'])

    def test_excel_dates_ongoing_career_and_point_lists(self):
        row = self.row('karir')
        row[4:8] = [date(2020, 1, 1), '', 'Ya', 'Tugas pertama\nTugas kedua']
        result = self.validate('karir', rows=[row]).json()
        self.assertTrue(result['can_save'], result)
        self.assertTrue(self.post('karir', 'save').json()['saved'])
        obj = EXCEL_DATA['karir']['form']._meta.model.objects.get()
        self.assertTrue(obj.masih_bekerja)
        self.assertIsNone(obj.tanggal_selesai)
        self.assertEqual(obj.uraian_poin, ['Tugas pertama', 'Tugas kedua'])

    def test_relation_failure_rolls_back_entire_import(self):
        self.assertTrue(self.validate('logbook', rows=[self.row('logbook')] * 2).json()['can_save'])
        create = PesertaLogbook.objects.bulk_create
        calls = 0

        def save_first(rows):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise IntegrityError
            return create(rows)

        with patch.object(PesertaLogbook.objects, 'bulk_create', side_effect=save_first):
            self.assertFalse(self.post('logbook', 'save').json()['saved'])
        self.assertEqual(EXCEL_DATA['logbook']['form']._meta.model.objects.count(), 0)
        self.assertEqual(PesertaLogbook.objects.count(), 0)

    def test_non_ajax_validation_shows_the_same_modal(self):
        response = self.client.post(self.url('karir'), {
            'import_action': 'validate', 'file_import': self.workbook('karir'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-import-modal-open="true"')
        self.assertContains(response, 'Validasi berhasil.')

    def test_import_only_accepts_post_and_unknown_actions_are_rejected(self):
        self.assertEqual(self.client.get(self.url('karir')).status_code, 405)
        self.assertEqual(self.post('karir', 'unknown').status_code, 400)

    def test_existing_user_template_still_downloads(self):
        response = self.client.get(reverse('pengguna:download_format_import_pengguna'))
        self.assertEqual(response.status_code, 200)
        book = load_workbook(BytesIO(response.content))
        self.assertEqual(book.active.title, 'Format Import Pengguna')
        self.assertGreater(len(book.active.data_validations.dataValidation), 0)
        book.close()

    def test_export_does_not_turn_text_into_excel_formulas(self):
        row = self.row('portofolio')
        row[1] = '=1+1'
        row[3] = '=2+2\nTugas kedua'
        self.assertTrue(self.validate('portofolio', rows=[row]).json()['can_save'])
        self.assertTrue(self.post('portofolio', 'save').json()['saved'])
        response = self.client.get(self.url('portofolio', 'export'))
        book = load_workbook(BytesIO(response.content))
        self.assertNotEqual(book.active['B2'].data_type, 'f')
        self.assertNotEqual(book.active['D2'].data_type, 'f')
        book.close()

    def test_import_requires_csrf_and_rejects_excess_rows(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url('karir'), {'import_action': 'save'}).status_code, 403)
        payload = self.validate('karir', rows=[self.row('karir')] * 5001).json()
        self.assertFalse(payload['can_save'])
        self.assertIn('5000', payload['errors'][0])
