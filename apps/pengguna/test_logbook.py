from io import BytesIO
import shutil
import tempfile
from datetime import date
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from pillow_heif import from_pillow

from apps.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from .models import Logbook, PesertaLogbook, Role, User


def upload(name='dokumentasi.png', content=None):
    if content is None:
        output = BytesIO()
        image = Image.new('RGB', (320, 160), 'blue')
        if name.lower().endswith(('.heic', '.heif')):
            from_pillow(image).save(output, quality=90)
        else:
            image.save(output, format='JPEG' if name.lower().endswith(('.jpg', '.jpeg')) else 'PNG')
        content = output.getvalue()
        image.close()
    return SimpleUploadedFile(name, content)


class LogbookTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        settings = override_settings(MEDIA_ROOT=self.media)
        settings.enable()
        self.addCleanup(settings.disable)
        self.actor = User.objects.create_user(username='logbook-actor')
        self.other = User.objects.create_user(username='logbook-other')
        self.outsider = User.objects.create_user(username='logbook-outsider')
        self.admin = User.objects.create_user(username='logbook-admin')
        role, _ = Role.objects.get_or_create(nama='Super Admin')
        profile = self.admin.safe_profile
        profile.role = role
        profile.save(update_fields=['role'])
        self.client.force_login(self.actor)

    def payload(self, **changes):
        data = {
            'lingkup': 'Laboratorium',
            'tanggal': '25 Nov 2026', 'uraian': 'Melakukan pengujian harian.', 'dokumen': upload(),
            'peserta-TOTAL_FORMS': '2', 'peserta-INITIAL_FORMS': '1',
            'peserta-0-user': str(self.actor.pk), 'peserta-1-user': str(self.other.pk),
        }
        data.update(changes)
        return data

    def create(self, **changes):
        response = self.client.post(reverse('pengguna:logbook_tambah'), self.payload(**changes))
        self.assertRedirects(response, reverse('pengguna:logbook_daftar'))
        return Logbook.objects.get()

    def test_initial_date_sidebar_and_own_participant_lock(self):
        response = self.client.get(reverse('pengguna:logbook_tambah'))
        self.assertEqual(response.context['form']['tanggal'].value(), timezone.localdate())
        peserta = response.context['peserta']
        self.assertTrue(peserta[0].fields['user'].disabled)
        self.assertFalse(peserta[0].removable)
        self.assertNotIn(self.admin, peserta.empty_form.fields['user'].queryset)
        self.assertContains(response, 'aria-current="page">Logbook Harian</a>')
        self.assertContains(response, 'data-user-date-picker="true"')
        self.assertNotContains(response, 'File Sertifikat')

    def test_lingkup_is_first_required_field_and_initially_locks_form(self):
        response = self.client.get(reverse('pengguna:logbook_tambah'))
        form = response.context['form']
        self.assertEqual(next(iter(form.fields)), 'lingkup')
        self.assertTrue(form.fields['lingkup'].required)
        self.assertTrue(form.lock_fields)
        self.assertEqual(list(form.fields['lingkup'].choices), [('', 'Pilih lingkup kegiatan')] + Logbook.LINGKUP_CHOICES)
        self.assertContains(response, 'disabled inert', count=1)
        self.assertContains(response, '<button type="submit" class="btn btn-primary" disabled>Simpan</button>', html=True)

    def test_missing_or_invalid_lingkup_never_saves_records_or_files(self):
        for value in (None, '', '   ', 'Lingkup palsu'):
            with self.subTest(value=value):
                data = self.payload(lingkup=value)
                if value is None:
                    data.pop('lingkup')
                response = self.client.post(reverse('pengguna:logbook_tambah'), data)
                self.assertEqual(response.status_code, 200)
                self.assertIn('lingkup', response.context['form'].errors)
                self.assertTrue(response.context['form'].lock_fields)
                self.assertFalse(Logbook.objects.exists())
                self.assertFalse(PesertaLogbook.objects.exists())
                self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_each_lingkup_is_saved_and_edit_remains_unlocked(self):
        obj = self.create()
        url = reverse('pengguna:logbook_edit', args=[obj.pk])
        for value, _ in Logbook.LINGKUP_CHOICES:
            with self.subTest(lingkup=value):
                data = self.payload(lingkup=value, **{'peserta-INITIAL_FORMS': '2'})
                data.pop('dokumen')
                self.assertEqual(self.client.post(url, data).status_code, 302)
                obj.refresh_from_db()
                self.assertEqual(obj.lingkup, value)
                response = self.client.get(url)
                self.assertEqual(response.context['form']['lingkup'].value(), value)
                self.assertFalse(response.context['form'].lock_fields)
                self.assertNotContains(response, 'disabled inert')

    def test_legacy_logbook_requires_lingkup_on_edit(self):
        obj = self.create()
        Logbook.objects.filter(pk=obj.pk).update(lingkup='')
        url = reverse('pengguna:logbook_edit', args=[obj.pk])
        self.assertTrue(self.client.get(url).context['form'].lock_fields)
        data = self.payload(lingkup='', **{'peserta-INITIAL_FORMS': '2'})
        data.pop('dokumen')
        self.assertEqual(self.client.post(url, data).status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.lingkup, '')
        self.assertEqual(obj.peserta.count(), 2)
        data['lingkup'] = 'Dukungan Manajemen'
        self.assertEqual(self.client.post(url, data).status_code, 302)

    def test_other_errors_keep_selected_lingkup_and_unlock_fields(self):
        response = self.client.post(reverse('pengguna:logbook_tambah'), self.payload(uraian=''))
        self.assertIn('uraian', response.context['form'].errors)
        self.assertEqual(response.context['form']['lingkup'].value(), 'Laboratorium')
        self.assertFalse(response.context['form'].lock_fields)
        self.assertNotContains(response, 'disabled inert')

    def test_create_shares_with_each_participant_and_ignores_forged_actor(self):
        obj = self.create(user=self.outsider.pk, **{'peserta-0-user': str(self.outsider.pk)})
        self.assertEqual(obj.user, self.actor)
        self.assertEqual(obj.tanggal, date(2026, 11, 25))
        self.assertEqual(set(obj.peserta_user.all()), {self.actor, self.other})
        for actor in (self.actor, self.other, self.admin):
            self.client.force_login(actor)
            response = self.client.get(reverse('pengguna:logbook_daftar'))
            self.assertContains(response, obj.uraian)
            self.assertEqual(self.client.get(reverse('pengguna:logbook_edit', args=[obj.pk])).status_code, 200)
        self.client.force_login(self.outsider)
        self.assertNotContains(self.client.get(reverse('pengguna:logbook_daftar')), obj.uraian)
        for route in ('logbook_edit', 'logbook_hapus', 'logbook_dokumen'):
            url = reverse('pengguna:' + route, args=[obj.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {}).status_code, 404)

    def test_admin_selects_first_participant_and_requires_at_least_one(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('pengguna:logbook_tambah'))
        self.assertFalse(response.context['peserta'][0].fields['user'].disabled)
        self.assertFalse(response.context['peserta'][0].removable)
        response = self.client.post(reverse('pengguna:logbook_tambah'), self.payload(**{
            'peserta-0-user': '', 'peserta-TOTAL_FORMS': '1',
        }))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Logbook.objects.exists())
        obj = self.create()
        self.assertEqual(obj.user, self.admin)
        self.assertNotIn(self.admin, obj.peserta_user.all())

    def test_invalid_dates_text_and_participants_never_save_files(self):
        for changes in (
            {'tanggal': ''}, {'tanggal': '31 Feb 2026'}, {'uraian': '   '},
            {'peserta-1-user': str(self.actor.pk)}, {'peserta-1-user': str(self.admin.pk)},
            {'peserta-1-user': '99999999'}, {'peserta-INITIAL_FORMS': '0'},
            {'peserta-TOTAL_FORMS': '0'},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(reverse('pengguna:logbook_tambah'), self.payload(dokumen=upload(), **changes))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors or response.context['peserta'].errors or response.context['peserta'].non_form_errors())
                self.assertFalse(Logbook.objects.exists())
                self.assertFalse(any(Path(self.media).rglob('*.*')))

    def test_document_formats_and_size_are_checked(self):
        from .forms import LogbookForm
        for ext in ('jpg', 'jpeg', 'png', 'heic', 'heif', 'HEIC'):
            form = LogbookForm(self.payload(), {'dokumen': upload('foto.' + ext)})
            self.assertTrue(form.is_valid(), form.errors)
        for file in (upload('berkas.exe'), upload('lama.pdf', b'%PDF-1.4'), upload('rusak.jpg', b'invalid'), upload('besar.png', b'x' * (MAX_UPLOAD_SIZE_BYTES + 1))):
            response = self.client.post(reverse('pengguna:logbook_tambah'), self.payload(dokumen=file))
            self.assertIn('dokumen', response.context['form'].errors)
            self.assertFalse(Logbook.objects.exists())

    def test_document_download_requires_participant_or_admin_and_handles_missing_file(self):
        obj = self.create(dokumen=upload())
        url = reverse('pengguna:logbook_dokumen', args=[obj.pk])
        for actor in (self.actor, self.other, self.admin):
            self.client.force_login(actor)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
            self.assertEqual(b''.join(response.streaming_content), upload().read())
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.actor)
        obj.dokumen.storage.delete(obj.dokumen.name)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_participant_edit_keeps_existing_users_and_shares_updates(self):
        obj = self.create()
        self.client.force_login(self.other)
        url = reverse('pengguna:logbook_edit', args=[obj.pk])
        response = self.client.post(url, self.payload(
            uraian='Uraian diperbarui', tanggal='2026-11-24', **{
                'peserta-INITIAL_FORMS': '2', 'peserta-TOTAL_FORMS': '3',
                'peserta-0-user': str(self.outsider.pk), 'peserta-1-DELETE': 'on',
                'peserta-2-user': str(self.outsider.pk),
            }
        ))
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.user, self.actor)
        self.assertEqual(obj.tanggal, date(2026, 11, 24))
        self.assertEqual(set(obj.peserta_user.all()), {self.actor, self.other, self.outsider})
        self.client.force_login(self.outsider)
        self.assertContains(self.client.get(reverse('pengguna:logbook_daftar')), 'Uraian diperbarui')

    def test_admin_can_remove_participants_but_cannot_remove_all(self):
        obj = self.create()
        self.client.force_login(self.admin)
        url = reverse('pengguna:logbook_edit', args=[obj.pk])
        data = self.payload(**{'peserta-INITIAL_FORMS': '2', 'peserta-0-DELETE': 'on', 'peserta-1-DELETE': 'on'})
        data.pop('dokumen')
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(obj.peserta.count(), 2)
        data['peserta-1-DELETE'] = ''
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(list(obj.peserta_user.all()), [self.other])

    def test_document_replacement_and_delete_cleanup(self):
        obj = self.create(dokumen=upload())
        old = obj.dokumen
        url = reverse('pengguna:logbook_edit', args=[obj.pk])
        data = self.payload(dokumen=upload('baru.jpg'), **{'peserta-INITIAL_FORMS': '2'})
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url, data).status_code, 302)
        obj.refresh_from_db()
        self.assertFalse(old.storage.exists(old.name))
        self.assertTrue(obj.dokumen.storage.exists(obj.dokumen.name))
        response = self.client.get(url)
        self.assertContains(response, reverse('pengguna:logbook_dokumen', args=[obj.pk]))
        self.assertNotContains(response, 'Download dokumen pendidikan')
        self.client.force_login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(reverse('pengguna:logbook_hapus', args=[obj.pk])).status_code, 302)
        self.assertFalse(Logbook.objects.exists())
        self.assertFalse(obj.dokumen.storage.exists(obj.dokumen.name))

    def test_leaving_does_not_remove_other_users_data_or_document(self):
        obj = self.create(dokumen=upload())
        url = reverse('pengguna:logbook_hapus', args=[obj.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(obj.peserta.count(), 2)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(Logbook.objects.filter(pk=obj.pk).exists())
        self.assertEqual(list(obj.peserta_user.all()), [self.other])
        self.assertTrue(obj.dokumen.storage.exists(obj.dokumen.name))
        self.client.force_login(self.other)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Logbook.objects.exists())
        self.assertFalse(obj.dokumen.storage.exists(obj.dokumen.name))

    def test_routes_require_login_and_database_rejects_duplicates(self):
        obj = self.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PesertaLogbook.objects.create(logbook=obj, user=self.actor)
        self.client.logout()
        for route, args in [('logbook_daftar', []), ('logbook_tambah', []),
                            ('logbook_edit', [obj.pk]), ('logbook_hapus', [obj.pk]), ('logbook_dokumen', [obj.pk]), ('logbook_preview', [obj.pk]), ('logbook_upload', [])]:
            self.assertEqual(self.client.get(reverse('pengguna:' + route, args=args)).status_code, 302)

    def test_all_fields_required_and_empty_extra_participant_rejected(self):
        response = self.client.get(reverse('pengguna:logbook_tambah'))
        self.assertTrue(all(field.required for field in response.context['form'].fields.values()))
        for changes, field in (({'dokumen': ''}, 'dokumen'), ({'tanggal': ''}, 'tanggal'), ({'uraian': ''}, 'uraian')):
            response = self.client.post(reverse('pengguna:logbook_tambah'), self.payload(**changes))
            self.assertIn(field, response.context['form'].errors)
            self.assertFalse(Logbook.objects.exists())
        response = self.client.post(reverse('pengguna:logbook_tambah'), self.payload(**{'peserta-1-user': ''}))
        self.assertIn('user', response.context['peserta'][1].errors)
        self.assertFalse(Logbook.objects.exists())
        self.assertContains(self.client.get(reverse('pengguna:logbook_daftar')), 'bi bi-plus-circle')

    def test_original_iphone_file_preserved_and_previews_available_to_participants_only(self):
        original = upload('iphone.heic')
        original_bytes = original.read()
        original.seek(0)
        obj = self.create(dokumen=original)
        with obj.dokumen.open('rb') as stored:
            self.assertEqual(stored.read(), original_bytes)
        url = reverse('pengguna:logbook_preview', args=[obj.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.size, (320, 160))
        listing = self.client.get(reverse('pengguna:logbook_daftar'))
        self.assertContains(listing, f'data-photo-src="{url}"')
        self.assertContains(listing, 'class="inventory-photo__thumb"')
        self.assertContains(listing, 'id="logbook-photo-modal"')
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_preview_upload_validates_without_saving_and_keeps_csrf(self):
        from django.test import Client
        url = reverse('pengguna:logbook_upload')
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, {'dokumen': upload('iphone.heif')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        for data in ({}, {'dokumen': upload('photo.heic', b'invalid')}, {'dokumen': upload('doc.pdf', b'%PDF-1.4')}):
            self.assertEqual(self.client.post(url, data).status_code, 400)
        self.assertFalse(Logbook.objects.exists())
        self.assertFalse(any(Path(self.media).rglob('*.*')))
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.actor)
        self.assertEqual(csrf_client.post(url, {'dokumen': upload('iphone.heic')}).status_code, 403)

    def test_edit_keeps_original_image_when_no_replacement_uploaded(self):
        obj = self.create()
        old_name = obj.dokumen.name
        data = self.payload(**{'peserta-INITIAL_FORMS': '2'})
        data.pop('dokumen')
        response = self.client.post(reverse('pengguna:logbook_edit', args=[obj.pk]), data)
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.dokumen.name, old_name)

    def test_failed_replacement_keeps_original_and_legacy_documents_remain_accessible(self):
        obj = self.create(dokumen=upload('original.jpg'))
        old = obj.dokumen
        with old.open('rb') as file:
            self.assertEqual(file.read(), upload('original.jpg').read())
        url = reverse('pengguna:logbook_edit', args=[obj.pk])
        response = self.client.post(url, self.payload(dokumen=upload('rusak.heic', b'invalid'), **{'peserta-INITIAL_FORMS': '2'}))
        self.assertIn('dokumen', response.context['form'].errors)
        obj.refresh_from_db()
        self.assertEqual(obj.dokumen.name, old.name)
        self.assertTrue(old.storage.exists(old.name))
        obj.dokumen.save('legacy.pdf', upload('legacy.pdf', b'%PDF-1.4'), save=True)
        data = self.payload(**{'peserta-INITIAL_FORMS': '2'})
        data.pop('dokumen')
        self.assertEqual(self.client.post(url, data).status_code, 302)
        response = self.client.get(url)
        self.assertContains(response, 'Download dokumentasi asli')
        self.assertNotContains(response, '(opsional)')
        self.assertEqual(self.client.get(reverse('pengguna:logbook_preview', args=[obj.pk])).status_code, 404)
        listing = self.client.get(reverse('pengguna:logbook_daftar'))
        self.assertContains(listing, reverse('pengguna:logbook_dokumen', args=[obj.pk]))
        self.assertNotContains(listing, 'data-inventory-photo-open')
