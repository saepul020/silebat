import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from .forms import KarirForm
from .models import RiwayatKarir, Role, User


def upload(name='dokumen.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 karir')


class KarirTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        settings = override_settings(MEDIA_ROOT=self.media)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(username='karir-user')
        self.other = User.objects.create_user(username='karir-other')
        self.admin = User.objects.create_user(username='karir-admin')
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = self.admin.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])
        self.client.force_login(self.user)

    def payload(self, **changes):
        data = {
            'perusahaan': 'Instansi Contoh', 'jabatan': 'Analis', 'status': 'Karyawan Tetap',
            'tanggal_mulai': '01 Jan 2020', 'tanggal_selesai': '31 Des 2021',
            'uraian': 'Melakukan analisis laboratorium.', 'dokumen': upload(), 'nomor_dokumen': 'SK/001/2020',
        }
        data.update(changes)
        return data

    def create(self, **changes):
        response = self.client.post(reverse('pengguna:karir_tambah'), self.payload(**changes))
        self.assertRedirects(response, reverse('pengguna:karir_daftar'))
        return RiwayatKarir.objects.get()

    def test_hub_form_and_initial_document_lock(self):
        self.assertContains(self.client.get(reverse('pengguna:data')), reverse('pengguna:karir_daftar'))
        response = self.client.get(reverse('pengguna:karir_tambah'))
        form = response.context['form']
        self.assertTrue(form.fields['nomor_dokumen'].widget.attrs['disabled'])
        self.assertTrue(form.fields['tanggal_selesai'].widget.attrs['disabled'])
        self.assertFalse(form.fields['dokumen'].required)
        self.assertFalse(form.fields['nomor_dokumen'].required)
        self.assertFalse(form.fields['masih_bekerja'].required)
        self.assertTrue(all(field.required for name, field in form.fields.items() if name not in ('dokumen', 'nomor_dokumen', 'masih_bekerja')))
        self.assertContains(response, '<legend>Data Pekerjaan</legend>')
        self.assertNotContains(response, '<legend>Identitas Pekerjaan</legend>')
        self.assertNotContains(response, '<legend>Periode dan Uraian Pekerjaan</legend>')
        self.assertContains(response, 'data-karir-form')
        self.assertContains(response, 'aria-current="page">Data Pengguna</a>')
        self.assertContains(response, 'user_select.js')
        self.assertEqual(form.fields['uraian'].label, 'Uraian Tugas')
        self.assertContains(response, 'placeholder="Tugas 1"')
        self.assertContains(response, 'Tambah Tugas')
        self.assertContains(response, '<em class="user-field__note">(opsional)</em>', html=True)
        self.assertNotContains(response, 'Wajib diisi jika ada dokumen pendukung.')

    def test_job_points_save_in_order_and_render_as_escaped_list(self):
        obj = self.create(uraian=['  Analisis sampel  ', '<script>laporan</script>'])
        self.assertEqual(obj.uraian, 'Analisis sampel\n<script>laporan</script>')
        response = self.client.get(reverse('pengguna:karir_daftar'))
        self.assertContains(response, '<li><span class="user-table__description">Analisis sampel</span></li>', html=True)
        self.assertContains(response, '<li><span class="user-table__description">&lt;script&gt;laporan&lt;/script&gt;</span></li>', html=True)
        self.assertNotContains(response, '<script>laporan</script>')

    def test_legacy_multiline_description_is_editable_as_points(self):
        obj = self.create(uraian='Analisis sampel\r\n\r\nMenyusun laporan')
        url = reverse('pengguna:karir_edit', args=[obj.pk])
        response = self.client.get(url)
        self.assertEqual(response.context['form']['uraian'].value(), ['Analisis sampel', 'Menyusun laporan'])
        data = self.payload(uraian=['Analisis ulang', 'Menyusun laporan'])
        data.pop('dokumen')
        self.assertEqual(self.client.post(url, data).status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.uraian, 'Analisis ulang\nMenyusun laporan')

    def test_empty_or_oversized_job_points_prevent_saving_and_keep_rows(self):
        for points in (['Tugas pertama', '   '], ['x' * 1001]):
            with self.subTest(points=points):
                response = self.client.post(reverse('pengguna:karir_tambah'), self.payload(uraian=points))
                self.assertIn('uraian', response.context['form'].errors)
                self.assertEqual(response.context['form']['uraian'].value(), points)
                self.assertFalse(RiwayatKarir.objects.exists())

    def test_all_routes_require_login(self):
        obj = self.create()
        self.client.logout()
        routes = [('karir_daftar', []), ('karir_tambah', []), ('karir_edit', [obj.pk]),
                  ('karir_hapus', [obj.pk]), ('karir_dokumen', [obj.pk, 'dokumen'])]
        for route, args in routes:
            self.assertEqual(self.client.get(reverse('pengguna:' + route, args=args)).status_code, 302)

    def test_create_persists_fields_and_ignores_forged_owner(self):
        obj = self.create(user=self.other.pk)
        self.assertEqual(obj.user_id, self.user.pk)
        self.assertEqual(obj.jabatan, 'Analis')
        self.assertEqual(obj.nomor_dokumen, 'SK/001/2020')
        self.assertEqual(obj.tanggal_selesai.year, 2021)
        self.assertTrue(obj.dokumen.storage.exists(obj.dokumen.name))

    def test_required_fields_have_errors_on_empty_post(self):
        response = self.client.post(reverse('pengguna:karir_tambah'), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['form'].errors), set(KarirForm.Meta.fields) - {'dokumen', 'nomor_dokumen', 'masih_bekerja'})
        for field in response.context['form'].fields.values():
            if field.required:
                self.assertContains(response, field.error_messages['required'])
        self.assertFalse(RiwayatKarir.objects.exists())

    def test_each_missing_field_prevents_storage_including_document_number(self):
        for name in KarirForm.Meta.fields:
            if name in ('dokumen', 'masih_bekerja'):
                continue
            with self.subTest(field=name):
                response = self.client.post(reverse('pengguna:karir_tambah'), self.payload(**{name: ''}))
                self.assertEqual(response.status_code, 200)
                self.assertIn(name, response.context['form'].errors)
                self.assertFalse(RiwayatKarir.objects.exists())
                self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_ongoing_work_saves_without_end_date_and_restores_on_edit(self):
        obj = self.create(masih_bekerja='on', tanggal_selesai='')
        self.assertTrue(obj.masih_bekerja)
        self.assertIsNone(obj.tanggal_selesai)
        self.assertContains(self.client.get(reverse('pengguna:karir_daftar')), 'Masih Bekerja')
        response = self.client.get(reverse('pengguna:karir_edit', args=[obj.pk]))
        form = response.context['form']
        self.assertTrue(form['masih_bekerja'].value())
        self.assertFalse(form.fields['tanggal_selesai'].required)
        self.assertTrue(form.fields['tanggal_selesai'].widget.attrs['disabled'])

    def test_ongoing_work_still_requires_start_and_rejects_both_choices(self):
        for changes, error in (
            ({'masih_bekerja': 'on', 'tanggal_selesai': '31 Des 2021'}, 'tanggal_selesai'),
            ({'masih_bekerja': 'on', 'tanggal_mulai': '', 'tanggal_selesai': ''}, 'tanggal_mulai'),
        ):
            response = self.client.post(reverse('pengguna:karir_tambah'), self.payload(**changes))
            self.assertEqual(response.status_code, 200)
            self.assertIn(error, response.context['form'].errors)
            self.assertFalse(RiwayatKarir.objects.exists())
            self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_edit_can_switch_between_finished_and_ongoing_work(self):
        obj = self.create()
        url = reverse('pengguna:karir_edit', args=[obj.pk])
        response = self.client.get(url)
        self.assertTrue(response.context['form'].fields['masih_bekerja'].widget.attrs['disabled'])
        data = self.payload(masih_bekerja='on', tanggal_selesai='')
        data.pop('dokumen')
        self.assertEqual(self.client.post(url, data).status_code, 302)
        obj.refresh_from_db()
        self.assertTrue(obj.masih_bekerja)
        self.assertIsNone(obj.tanggal_selesai)
        data['masih_bekerja'] = ''
        response = self.client.post(url, data)
        self.assertIn('tanggal_selesai', response.context['form'].errors)
        obj.refresh_from_db()
        self.assertTrue(obj.masih_bekerja)
        data['tanggal_selesai'] = '31 Des 2021'
        self.assertEqual(self.client.post(url, data).status_code, 302)
        obj.refresh_from_db()
        self.assertFalse(obj.masih_bekerja)
        self.assertIsNotNone(obj.tanggal_selesai)

    def test_database_rejects_end_date_with_ongoing_status_or_missing_end_for_finished(self):
        obj = self.create()
        for changes in ({'masih_bekerja': True}, {'tanggal_selesai': None}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                RiwayatKarir.objects.filter(pk=obj.pk).update(**changes)
        RiwayatKarir.objects.filter(pk=obj.pk).update(masih_bekerja=True, tanggal_selesai=None)
        obj.refresh_from_db()
        self.assertTrue(obj.masih_bekerja)
        self.assertIsNone(obj.tanggal_selesai)

    def test_create_without_document_ignores_forged_document_number(self):
        data = self.payload(nomor_dokumen='Tidak boleh tersimpan tanpa dokumen')
        data.pop('dokumen')
        response = self.client.post(reverse('pengguna:karir_tambah'), data)
        self.assertEqual(response.status_code, 302)
        obj = RiwayatKarir.objects.get()
        self.assertFalse(obj.dokumen)
        self.assertEqual(obj.nomor_dokumen, '')
        self.assertFalse(any(Path(self.media).rglob('*.*')))
        self.assertEqual(self.client.get(reverse('pengguna:karir_dokumen', args=[obj.pk, 'dokumen'])).status_code, 404)
        response = self.client.get(reverse('pengguna:karir_edit', args=[obj.pk]))
        self.assertTrue(response.context['form'].fields['nomor_dokumen'].widget.attrs['disabled'])
        self.assertFalse(response.context['form'].fields['nomor_dokumen'].required)
        data['jabatan'] = 'Posisi Baru'
        self.assertEqual(self.client.post(reverse('pengguna:karir_edit', args=[obj.pk]), data).status_code, 302)

    def test_end_date_widget_opens_only_with_valid_start_and_post_is_still_validated(self):
        for value in ('', '31 Feb 2020'):
            bound = KarirForm(self.payload(tanggal_mulai=value))
            self.assertTrue(bound.fields['tanggal_selesai'].widget.attrs['disabled'])
            response = self.client.post(reverse('pengguna:karir_tambah'), self.payload(tanggal_mulai=value))
            self.assertIn('tanggal_mulai', response.context['form'].errors)
            self.assertFalse(RiwayatKarir.objects.exists())
        bound = KarirForm(self.payload(tanggal_mulai='2020-01-01'))
        self.assertNotIn('disabled', bound.fields['tanggal_selesai'].widget.attrs)

    def test_status_and_document_formats(self):
        for status, _ in RiwayatKarir.STATUS_CHOICES:
            for ext in ('jpg', 'jpeg', 'png', 'pdf', 'PDF'):
                with self.subTest(status=status, extension=ext):
                    data = self.payload(status=status)
                    form = KarirForm(data, {'dokumen': upload('berkas.' + ext)})
                    self.assertTrue(form.is_valid(), form.errors)
                    self.assertNotIn('disabled', form.fields['nomor_dokumen'].widget.attrs)

    def test_bad_status_dates_and_whitespace_are_rejected(self):
        for changes, field in (
            ({'status': 'Tidak valid'}, 'status'), ({'tanggal_mulai': '31 Feb 2020'}, 'tanggal_mulai'),
            ({'tanggal_selesai': '31 Dec 2019'}, 'tanggal_selesai'),
            ({'perusahaan': '   '}, 'perusahaan'), ({'nomor_dokumen': '   '}, 'nomor_dokumen'),
            ({'uraian': '   '}, 'uraian'),
        ):
            response = self.client.post(reverse('pengguna:karir_tambah'), self.payload(**changes))
            self.assertIn(field, response.context['form'].errors)
            self.assertFalse(RiwayatKarir.objects.exists())

    def test_same_day_and_legacy_iso_dates_are_accepted(self):
        obj = self.create(tanggal_mulai='2020-01-01', tanggal_selesai='2020-01-01')
        self.assertEqual(obj.tanggal_mulai, obj.tanggal_selesai)

    def test_database_constraint_guards_date_order(self):
        obj = self.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            RiwayatKarir.objects.filter(pk=obj.pk).update(tanggal_selesai='2019-01-01')

    def test_invalid_and_oversized_documents_do_not_save(self):
        for file in (upload('berkas.exe'), SimpleUploadedFile('besar.pdf', b'x' * (MAX_UPLOAD_SIZE_BYTES + 1))):
            response = self.client.post(reverse('pengguna:karir_tambah'), self.payload(dokumen=file))
            self.assertIn('dokumen', response.context['form'].errors)
            self.assertFalse(RiwayatKarir.objects.exists())
            self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_other_user_cannot_list_edit_delete_or_download(self):
        obj = self.create()
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('pengguna:karir_daftar')), obj.perusahaan)
        for route in ('karir_edit', 'karir_hapus'):
            url = reverse('pengguna:' + route, args=[obj.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {} ).status_code, 404)
        self.assertEqual(self.client.get(reverse('pengguna:karir_dokumen', args=[obj.pk, 'dokumen'])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('pengguna:karir_daftar')), obj.perusahaan)
        self.assertEqual(self.client.get(reverse('pengguna:karir_edit', args=[obj.pk])).status_code, 200)

    def test_owner_and_admin_can_download_and_missing_files_return_404(self):
        obj = self.create()
        url = reverse('pengguna:karir_dokumen', args=[obj.pk, 'dokumen'])
        for actor in (self.user, self.admin):
            self.client.force_login(actor)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
            self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 karir')
        self.assertEqual(self.client.get(reverse('pengguna:karir_dokumen', args=[obj.pk, 'user'])).status_code, 404)
        obj.dokumen.storage.delete(obj.dokumen.name)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_edit_keeps_existing_document_and_unlocked_number(self):
        obj = self.create()
        response = self.client.get(reverse('pengguna:karir_edit', args=[obj.pk]))
        self.assertNotIn('disabled', response.context['form'].fields['nomor_dokumen'].widget.attrs)
        self.assertContains(response, reverse('pengguna:karir_dokumen', args=[obj.pk, 'dokumen']))
        data = self.payload(jabatan='Analis Senior', nomor_dokumen='SK/002/2020', user=self.other.pk)
        data.pop('dokumen')
        self.assertEqual(self.client.post(reverse('pengguna:karir_edit', args=[obj.pk]), data).status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.jabatan, 'Analis Senior')
        self.assertEqual(obj.nomor_dokumen, 'SK/002/2020')
        self.assertEqual(obj.user_id, self.user.pk)
        self.assertTrue(obj.dokumen.storage.exists(obj.dokumen.name))

    def test_replacement_cleans_old_document_only_after_success(self):
        obj = self.create()
        old = obj.dokumen
        url = reverse('pengguna:karir_edit', args=[obj.pk])
        response = self.client.post(url, self.payload(dokumen=upload('invalid-baru.pdf'), nomor_dokumen=''))
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.dokumen.name, old.name)
        self.assertTrue(old.storage.exists(old.name))
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, self.payload(dokumen=upload('baru.pdf')))
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertFalse(old.storage.exists(old.name))
        self.assertTrue(obj.dokumen.storage.exists(obj.dokumen.name))
        self.assertFalse(any(path.name == 'invalid-baru.pdf' for path in Path(self.media).rglob('*')))

    def test_delete_confirmation_and_cleanup(self):
        obj = self.create()
        url = reverse('pengguna:karir_hapus', args=[obj.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(RiwayatKarir.objects.filter(pk=obj.pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(RiwayatKarir.objects.exists())
        self.assertFalse(obj.dokumen.storage.exists(obj.dokumen.name))
