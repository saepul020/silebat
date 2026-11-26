import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from .forms import PendidikanForm
from .models import Pendidikan, Role, User


def upload(name='dokumen.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 dokumen')


class PendidikanTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        setting = override_settings(MEDIA_ROOT=self.media)
        setting.enable()
        self.addCleanup(setting.disable)
        self.user = User.objects.create_user(username='pendidikan-user')
        self.other = User.objects.create_user(username='pendidikan-other')
        self.admin = User.objects.create_user(username='pendidikan-admin')
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = self.admin.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])
        self.client.force_login(self.user)

    def payload(self, **changes):
        data = {
            'tingkat': 'Sarjana (S1)', 'lokasi': 'Dalam Negeri', 'lembaga': 'Universitas Contoh',
            'jurusan': 'Teknik', 'tanggal_lulus': '05 Nov 2020', 'jenis_nilai': 'IPK', 'nilai': '3.75',
            'ijazah': upload('ijazah.pdf'), 'transkrip': upload('transkrip.pdf'),
        }
        data.update(changes)
        return data

    def create(self, **changes):
        response = self.client.post(reverse('pengguna:pendidikan_tambah'), self.payload(**changes))
        self.assertRedirects(response, reverse('pengguna:pendidikan_daftar'))
        return Pendidikan.objects.get()

    def test_menu_form_and_authentication(self):
        response = self.client.get(reverse('pengguna:data'))
        self.assertContains(response, reverse('pengguna:pendidikan_daftar'))
        response = self.client.get(reverse('pengguna:pendidikan_tambah'))
        self.assertContains(response, 'data-user-date-picker')
        self.assertContains(response, 'user_select.js')
        self.assertContains(response, 'aria-current="page">Data Pengguna</a>')
        self.client.logout()
        for route in ('pendidikan_daftar', 'pendidikan_tambah'):
            self.assertEqual(self.client.get(reverse('pengguna:' + route)).status_code, 302)

    def test_create_stores_fields_files_and_ignores_forged_owner(self):
        obj = self.create(user=self.other.pk)
        self.assertEqual(obj.user_id, self.user.pk)
        self.assertEqual(obj.nilai, Decimal('3.75'))
        self.assertEqual(obj.tanggal_lulus.year, 2020)
        for name in ('ijazah', 'transkrip'):
            field = getattr(obj, name)
            self.assertTrue(field.storage.exists(field.name))

    def test_empty_post_has_errors_for_every_field_and_saves_nothing(self):
        response = self.client.post(reverse('pengguna:pendidikan_tambah'), {})
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(set(form.errors), set(form.fields))
        for field in form.fields.values():
            self.assertTrue(field.required)
            self.assertContains(response, field.error_messages['required'])
        self.assertNotContains(response, '(opsional)')
        self.assertFalse(Pendidikan.objects.exists())

    def test_each_missing_field_is_rejected_even_with_other_fields_complete(self):
        for name in PendidikanForm.Meta.fields:
            with self.subTest(field=name):
                data = self.payload(**{name: ''})
                response = self.client.post(reverse('pengguna:pendidikan_tambah'), data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(name, response.context['form'].errors)
                self.assertFalse(Pendidikan.objects.exists())
                self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_sd_smp_can_be_saved_without_jurusan(self):
        for tingkat in PendidikanForm.TANPA_JURUSAN:
            with self.subTest(tingkat=tingkat):
                data = self.payload(tingkat=tingkat)
                data.pop('jurusan')
                response = self.client.post(reverse('pengguna:pendidikan_tambah'), data)
                self.assertRedirects(response, reverse('pengguna:pendidikan_daftar'))
                obj = Pendidikan.objects.get(tingkat=tingkat)
                self.assertEqual(obj.jurusan, '')
                response = self.client.get(reverse('pengguna:pendidikan_edit', args=[obj.pk]))
                form = response.context['form']
                self.assertTrue(form.hide_jurusan)
                self.assertFalse(form.fields['jurusan'].required)
                self.assertTrue(form.fields['jurusan'].disabled)
                self.assertContains(response, 'pendidikan-tanpa-jurusan')

    def test_fields_are_locked_until_a_valid_degree_is_selected(self):
        for tingkat in (None, '', 'Tidak valid'):
            with self.subTest(tingkat=tingkat):
                form = PendidikanForm(initial={'tingkat': tingkat, 'jenis_nilai': 'IPK'})
                self.assertTrue(form.lock_fields)
                self.assertNotIn('disabled', form.fields['tingkat'].widget.attrs)
                for name, field in form.fields.items():
                    if name != 'tingkat':
                        self.assertTrue(field.widget.attrs.get('disabled'), name)
                        self.assertEqual(field.widget.attrs['aria-disabled'], 'true')
        for tingkat, _ in Pendidikan.TINGKAT_CHOICES:
            with self.subTest(tingkat=tingkat):
                form = PendidikanForm(initial={'tingkat': tingkat})
                self.assertFalse(form.lock_fields)
                for name, field in form.fields.items():
                    locked = name == 'nilai' or (name == 'jurusan' and tingkat in PendidikanForm.TANPA_JURUSAN)
                    self.assertEqual(bool(field.widget.attrs.get('disabled')), locked, name)

    def test_missing_degree_rejects_manual_post_and_keeps_existing_data(self):
        obj = self.create()
        data = self.payload(tingkat='', lembaga='Perubahan tidak sah')
        data.pop('ijazah')
        data.pop('transkrip')
        response = self.client.post(reverse('pengguna:pendidikan_edit', args=[obj.pk]), data)
        form = response.context['form']
        self.assertIn('tingkat', form.errors)
        self.assertTrue(form.lock_fields)
        self.assertEqual(form['lembaga'].value(), 'Perubahan tidak sah')
        self.assertTrue(form.fields['lembaga'].widget.attrs['disabled'])
        obj.refresh_from_db()
        self.assertEqual(obj.tingkat, 'Sarjana (S1)')
        self.assertEqual(obj.lembaga, 'Universitas Contoh')

    def test_sd_smp_ignore_forged_jurusan_and_stay_hidden_on_invalid_post(self):
        for tingkat in PendidikanForm.TANPA_JURUSAN:
            with self.subTest(tingkat=tingkat):
                data = self.payload(tingkat=tingkat, jurusan='x' * 300)
                form = PendidikanForm(data, {'ijazah': data['ijazah'], 'transkrip': data['transkrip']})
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data['jurusan'], '')
                response = self.client.post(reverse('pengguna:pendidikan_tambah'), self.payload(
                    tingkat=tingkat, jurusan='', lembaga='',
                ))
                form = response.context['form']
                self.assertTrue(form.hide_jurusan)
                self.assertIn('lembaga', form.errors)
                self.assertNotIn('jurusan', form.errors)
                self.assertFalse(Pendidikan.objects.exists())

    def test_other_degrees_still_require_jurusan(self):
        for tingkat, _ in Pendidikan.TINGKAT_CHOICES:
            if tingkat in PendidikanForm.TANPA_JURUSAN:
                continue
            with self.subTest(tingkat=tingkat):
                data = self.payload(tingkat=tingkat, jurusan='')
                form = PendidikanForm(data, {'ijazah': data['ijazah'], 'transkrip': data['transkrip']})
                self.assertFalse(form.is_valid())
                self.assertIn('jurusan', form.errors)
                self.assertFalse(form.hide_jurusan)
                self.assertFalse(form.fields['jurusan'].disabled)

    def test_edit_degree_updates_jurusan_requirement_and_clears_unused_value(self):
        obj = self.create()
        url = reverse('pengguna:pendidikan_edit', args=[obj.pk])
        data = self.payload(tingkat='SD / Sederajat')
        for name in ('ijazah', 'transkrip', 'jurusan'):
            data.pop(name)
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('pengguna:pendidikan_daftar'))
        obj.refresh_from_db()
        self.assertEqual(obj.jurusan, '')
        data['tingkat'] = 'Sarjana (S1)'
        response = self.client.post(url, data)
        self.assertIn('jurusan', response.context['form'].errors)
        self.assertFalse(response.context['form'].hide_jurusan)
        obj.refresh_from_db()
        self.assertEqual(obj.tingkat, 'SD / Sederajat')
        data['jurusan'] = 'Teknik'
        self.assertRedirects(self.client.post(url, data), reverse('pengguna:pendidikan_daftar'))
        obj.refresh_from_db()
        self.assertEqual(obj.jurusan, 'Teknik')

    def test_score_boundaries_and_widget_lock_follow_selected_type(self):
        blank = PendidikanForm()
        self.assertTrue(blank.fields['nilai'].widget.attrs['disabled'])
        for jenis, maximum in PendidikanForm.NILAI_BATAS.items():
            for value in ('0.00', f'{maximum:.2f}'):
                with self.subTest(jenis=jenis, value=value):
                    data = self.payload(jenis_nilai=jenis, nilai=value)
                    form = PendidikanForm(data, {'ijazah': data['ijazah'], 'transkrip': data['transkrip']})
                    self.assertTrue(form.is_valid(), form.errors)
                    self.assertNotIn('disabled', form.fields['nilai'].widget.attrs)
                    self.assertEqual(form.fields['nilai'].widget.attrs['max'], maximum)
            for value in ('-0.01', str(Decimal(maximum) + Decimal('0.01'))):
                response = self.client.post(reverse('pengguna:pendidikan_tambah'), self.payload(jenis_nilai=jenis, nilai=value))
                self.assertEqual(response.status_code, 200)
                self.assertIn('nilai', response.context['form'].errors)
                self.assertFalse(Pendidikan.objects.exists())

    def test_invalid_score_on_edit_keeps_data_and_documents(self):
        obj = self.create()
        old = obj.ijazah
        response = self.client.post(reverse('pengguna:pendidikan_edit', args=[obj.pk]), self.payload(
            nilai='4.01', ijazah=upload('pengganti.pdf'),
        ))
        self.assertEqual(response.status_code, 200)
        self.assertIn('nilai', response.context['form'].errors)
        obj.refresh_from_db()
        self.assertEqual(obj.nilai, Decimal('3.75'))
        self.assertEqual(obj.ijazah.name, old.name)
        self.assertTrue(old.storage.exists(old.name))
        self.assertFalse(any(path.name == 'pengganti.pdf' for path in Path(self.media).rglob('*')))

    def test_all_degree_location_score_and_file_choices_are_accepted(self):
        for field, choices in (
            ('tingkat', Pendidikan.TINGKAT_CHOICES), ('lokasi', Pendidikan.LOKASI_CHOICES),
            ('jenis_nilai', Pendidikan.NILAI_CHOICES),
        ):
            for value, _ in choices:
                with self.subTest(field=field, value=value):
                    data = self.payload(**{field: value})
                    form = PendidikanForm(data, {'ijazah': data['ijazah'], 'transkrip': data['transkrip']})
                    self.assertTrue(form.is_valid(), form.errors)
        for ext in ('jpg', 'jpeg', 'png', 'pdf', 'PDF'):
            data = self.payload(ijazah=upload('ijazah.' + ext), transkrip=upload('transkrip.' + ext))
            form = PendidikanForm(data, {'ijazah': data['ijazah'], 'transkrip': data['transkrip']})
            self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_fields_and_partial_upload_do_not_save(self):
        for changes in (
            {'tingkat': 'Tidak valid'}, {'lokasi': 'Tidak valid'}, {'jenis_nilai': 'Tidak valid'},
            {'nilai': '-1'}, {'nilai': 'NaN'}, {'nilai': '3.123'}, {'nilai': ''},
            {'tanggal_lulus': (timezone.localdate() + timedelta(days=1)).isoformat()},
            {'tanggal_lulus': '31 Feb 2020'}, {'transkrip': ''}, {'lembaga': '   '},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(reverse('pengguna:pendidikan_tambah'), self.payload(**changes))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.assertFalse(Pendidikan.objects.exists())
                self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_invalid_extension_and_oversized_upload_are_rejected(self):
        for field in ('ijazah', 'transkrip'):
            for file in (upload('virus.exe'), SimpleUploadedFile('besar.pdf', b'x' * (MAX_UPLOAD_SIZE_BYTES + 1))):
                with self.subTest(field=field, name=file.name):
                    response = self.client.post(reverse('pengguna:pendidikan_tambah'), self.payload(**{field: file}))
                    self.assertIn(field, response.context['form'].errors)
                    self.assertFalse(Pendidikan.objects.exists())

    def test_list_and_object_access_are_limited_to_owner_or_admin(self):
        obj = self.create()
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('pengguna:pendidikan_daftar')), obj.lembaga)
        for route in ('pendidikan_edit', 'pendidikan_hapus'):
            url = reverse('pengguna:' + route, args=[obj.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {}).status_code, 404)
        for field in ('ijazah', 'transkrip'):
            self.assertEqual(self.client.get(reverse('pengguna:pendidikan_dokumen', args=[obj.pk, field])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('pengguna:pendidikan_daftar')), obj.lembaga)
        self.assertEqual(self.client.get(reverse('pengguna:pendidikan_edit', args=[obj.pk])).status_code, 200)

    def test_document_download_requires_login_and_access(self):
        obj = self.create()
        for actor in (self.user, self.admin):
            self.client.force_login(actor)
            for field in ('ijazah', 'transkrip'):
                response = self.client.get(reverse('pengguna:pendidikan_dokumen', args=[obj.pk, field]))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
                self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 dokumen')
        self.assertEqual(self.client.get(reverse('pengguna:pendidikan_dokumen', args=[obj.pk, 'user'])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('pengguna:pendidikan_dokumen', args=[obj.pk, 'ijazah'])).status_code, 302)

    def test_edit_retains_files_and_replacement_cleans_old_file(self):
        obj = self.create()
        old = obj.ijazah
        data = self.payload(lembaga='Lembaga Revisi')
        data.pop('ijazah'); data.pop('transkrip')
        response = self.client.post(reverse('pengguna:pendidikan_edit', args=[obj.pk]), data)
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.ijazah.name, old.name)
        self.assertEqual(obj.lembaga, 'Lembaga Revisi')
        data['ijazah'] = upload('ijazah-baru.pdf')
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('pengguna:pendidikan_edit', args=[obj.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(old.storage.exists(old.name))
        obj.refresh_from_db()
        self.assertTrue(obj.ijazah.storage.exists(obj.ijazah.name))

    def test_delete_requires_confirmation_and_cleans_files(self):
        obj = self.create()
        url = reverse('pengguna:pendidikan_hapus', args=[obj.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Pendidikan.objects.filter(pk=obj.pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(url)
        self.assertFalse(Pendidikan.objects.exists())
        self.assertFalse(obj.ijazah.storage.exists(obj.ijazah.name))
        self.assertFalse(obj.transkrip.storage.exists(obj.transkrip.name))

    def test_missing_document_returns_404(self):
        obj = self.create()
        obj.ijazah.storage.delete(obj.ijazah.name)
        self.assertEqual(self.client.get(reverse('pengguna:pendidikan_dokumen', args=[obj.pk, 'ijazah'])).status_code, 404)
