import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from .forms import PortofolioForm
from .models import Portofolio, Role, User


def upload(name='dokumen.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 portofolio')


class PortofolioTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        settings = override_settings(MEDIA_ROOT=self.media)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(username='portofolio-user')
        self.other = User.objects.create_user(username='portofolio-other')
        self.admin = User.objects.create_user(username='portofolio-admin')
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = self.admin.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])
        self.client.force_login(self.user)

    def payload(self, **changes):
        data = {'nama': 'Survei Sungai', 'lokasi': 'Instansi Contoh', 'uraian': [' Pengukuran lapangan ', 'Analisis data'],
                'tahun': str(timezone.localdate().year), 'nomor_dokumen': ''}
        data.update(changes)
        return data

    def create(self, **changes):
        response = self.client.post(reverse('pengguna:portofolio_tambah'), self.payload(**changes))
        self.assertRedirects(response, reverse('pengguna:portofolio_daftar'))
        return Portofolio.objects.get()

    def test_hub_form_and_year_options(self):
        self.assertContains(self.client.get(reverse('pengguna:data')), reverse('pengguna:portofolio_daftar'))
        response = self.client.get(reverse('pengguna:portofolio_tambah'))
        self.assertContains(response, 'data-komponen-required="true"')
        self.assertContains(response, 'Tambah Tugas')
        self.assertContains(response, 'aria-current="page">Data Pengguna</a>')
        form = response.context['form']
        self.assertFalse(form.fields['dokumen'].required)
        self.assertFalse(form.fields['nomor_dokumen'].required)
        self.assertTrue(form.fields['nomor_dokumen'].widget.attrs['disabled'])
        choices = list(form.fields['tahun'].choices)
        self.assertEqual(choices[1][0], timezone.localdate().year)
        self.assertEqual(choices[-1][0], 1900)

    def test_create_keeps_order_trims_points_and_ignores_forged_owner_and_number(self):
        obj = self.create(user=self.other.pk, nomor_dokumen='Nomor tanpa dokumen')
        self.assertEqual(obj.user_id, self.user.pk)
        self.assertEqual(obj.uraian, ['Pengukuran lapangan', 'Analisis data'])
        self.assertEqual(obj.nomor_dokumen, '')
        self.assertFalse(obj.dokumen)
        response = self.client.get(reverse('pengguna:portofolio_daftar'))
        self.assertContains(response, '<li><span class="user-table__description">Pengukuran lapangan</span></li>')
        self.assertContains(response, '<li><span class="user-table__description">Analisis data</span></li>')

    def test_empty_post_requires_project_location_points_and_year(self):
        response = self.client.post(reverse('pengguna:portofolio_tambah'), {})
        self.assertEqual(set(response.context['form'].errors), {'nama', 'lokasi', 'uraian', 'tahun'})
        self.assertFalse(Portofolio.objects.exists())

    def test_missing_or_blank_points_and_invalid_year_do_not_save(self):
        for changes, field in (
            ({'nama': ' '}, 'nama'), ({'lokasi': ''}, 'lokasi'), ({'uraian': []}, 'uraian'),
            ({'uraian': ['', 'Poin terisi']}, 'uraian'), ({'uraian': ['Poin', '   ']}, 'uraian'),
            ({'uraian': ['x' * 1001]}, 'uraian'), ({'tahun': 'abc'}, 'tahun'),
            ({'tahun': '1899'}, 'tahun'), ({'tahun': str(timezone.localdate().year + 1)}, 'tahun'),
        ):
            with self.subTest(changes=changes):
                response = self.client.post(reverse('pengguna:portofolio_tambah'), self.payload(**changes))
                self.assertIn(field, response.context['form'].errors)
                self.assertFalse(Portofolio.objects.exists())

    def test_document_requires_number_and_invalid_submission_does_not_store_upload(self):
        response = self.client.post(reverse('pengguna:portofolio_tambah'), self.payload(dokumen=upload()))
        self.assertIn('nomor_dokumen', response.context['form'].errors)
        self.assertFalse(Portofolio.objects.exists())
        self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_supported_file_extensions_and_invalid_files(self):
        for ext in ('jpg', 'jpeg', 'png', 'pdf', 'PDF'):
            form = PortofolioForm(self.payload(nomor_dokumen='SK/001'), {'dokumen': upload('file.' + ext)})
            self.assertTrue(form.is_valid(), form.errors)
        for file in (upload('virus.exe'), SimpleUploadedFile('besar.pdf', b'x' * (MAX_UPLOAD_SIZE_BYTES + 1))):
            response = self.client.post(reverse('pengguna:portofolio_tambah'), self.payload(dokumen=file, nomor_dokumen='SK/001'))
            self.assertIn('dokumen', response.context['form'].errors)
            self.assertFalse(Portofolio.objects.exists())

    def test_edit_restores_and_replaces_points_in_order(self):
        obj = self.create()
        url = reverse('pengguna:portofolio_edit', args=[obj.pk])
        response = self.client.get(url)
        self.assertEqual(response.context['form']['uraian'].value(), obj.uraian)
        self.assertContains(response, 'value="Analisis data"')
        self.assertEqual(self.client.post(url, self.payload(uraian=['Poin baru', 'Poin kedua', 'Poin ketiga'])).status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.uraian, ['Poin baru', 'Poin kedua', 'Poin ketiga'])

    def test_invalid_edit_retains_data_and_new_points_for_correction(self):
        obj = self.create()
        response = self.client.post(reverse('pengguna:portofolio_edit', args=[obj.pk]), self.payload(uraian=['', 'Masih terisi']))
        self.assertIn('uraian', response.context['form'].errors)
        self.assertContains(response, 'value="Masih terisi"')
        obj.refresh_from_db()
        self.assertEqual(obj.uraian, ['Pengukuran lapangan', 'Analisis data'])

    def test_points_are_escaped_in_form_and_list(self):
        obj = self.create(uraian=['<script>alert(1)</script>'])
        for route in ('portofolio_daftar', 'portofolio_edit'):
            args = [obj.pk] if route.endswith('edit') else []
            response = self.client.get(reverse('pengguna:' + route, args=args))
            self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
            self.assertNotContains(response, '<script>alert(1)</script>')

    def test_access_is_limited_to_owner_or_admin_and_requires_login(self):
        obj = self.create(dokumen=upload(), nomor_dokumen='SK/001')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('pengguna:portofolio_daftar')), obj.nama)
        for route in ('portofolio_edit', 'portofolio_hapus'):
            url = reverse('pengguna:' + route, args=[obj.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {}).status_code, 404)
        url = reverse('pengguna:portofolio_dokumen', args=[obj.pk, 'dokumen'])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('pengguna:portofolio_daftar')), obj.nama)
        self.assertEqual(self.client.get(reverse('pengguna:portofolio_edit', args=[obj.pk])).status_code, 200)
        self.client.logout()
        for route, args in [('portofolio_daftar', []), ('portofolio_tambah', []), ('portofolio_edit', [obj.pk]),
                            ('portofolio_hapus', [obj.pk]), ('portofolio_dokumen', [obj.pk, 'dokumen'])]:
            self.assertEqual(self.client.get(reverse('pengguna:' + route, args=args)).status_code, 302)

    def test_download_and_missing_document(self):
        obj = self.create(dokumen=upload(), nomor_dokumen='SK/001')
        url = reverse('pengguna:portofolio_dokumen', args=[obj.pk, 'dokumen'])
        for actor in (self.user, self.admin):
            self.client.force_login(actor)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
            self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 portofolio')
        self.assertEqual(self.client.get(reverse('pengguna:portofolio_dokumen', args=[obj.pk, 'user'])).status_code, 404)
        obj.dokumen.storage.delete(obj.dokumen.name)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_edit_keeps_document_or_cleans_old_after_replacement(self):
        obj = self.create(dokumen=upload(), nomor_dokumen='SK/001')
        old = obj.dokumen
        url = reverse('pengguna:portofolio_edit', args=[obj.pk])
        self.assertEqual(self.client.post(url, self.payload(nomor_dokumen='SK/002')).status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.dokumen.name, old.name)
        response = self.client.post(url, self.payload(dokumen=upload('gagal.pdf'), nomor_dokumen=''))
        self.assertIn('nomor_dokumen', response.context['form'].errors)
        self.assertTrue(old.storage.exists(old.name))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url, self.payload(dokumen=upload('baru.pdf'), nomor_dokumen='SK/003')).status_code, 302)
        self.assertFalse(old.storage.exists(old.name))
        obj.refresh_from_db()
        self.assertTrue(obj.dokumen.storage.exists(obj.dokumen.name))
        self.assertFalse(any(path.name == 'gagal.pdf' for path in Path(self.media).rglob('*')))

    def test_delete_confirmation_and_cleanup(self):
        obj = self.create(dokumen=upload(), nomor_dokumen='SK/001')
        url = reverse('pengguna:portofolio_hapus', args=[obj.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Portofolio.objects.exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Portofolio.objects.exists())
        self.assertFalse(obj.dokumen.storage.exists(obj.dokumen.name))

    def test_search_points_and_empty_table_column_counts(self):
        obj = self.create()
        response = self.client.get(reverse('pengguna:portofolio_daftar'), {'q': 'Pengukuran lapangan'})
        self.assertContains(response, obj.nama)
        obj.delete()
        for actor, columns in ((self.user, 6), (self.admin, 7)):
            self.client.force_login(actor)
            self.assertContains(self.client.get(reverse('pengguna:portofolio_daftar')), f'colspan="{columns}"')
