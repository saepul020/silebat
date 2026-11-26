from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from PIL import Image

from apps.master_data.models import BarangLaboratorium
from apps.pengguna.models import User
from .models import JenisFotoPemeliharaanChoices, PemeliharaanFoto, PemeliharaanItem, PemeliharaanPengajuan


class FileCleanupTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory(prefix='pemeliharaan-cleanup-')
        self.addCleanup(media.cleanup)
        self.media = Path(media.name)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(username='cleanup-pemeliharaan')
        with patch('apps.master_data.signals.ensure_master_qr_code'):
            alat = BarangLaboratorium.objects.create(nama_barang='Alat cleanup', kode_laboratorium='CLN-01')
        self.request = PemeliharaanPengajuan.objects.create(pemohon=self.user, alat=alat)
        self.item = PemeliharaanItem.objects.create(pengajuan=self.request, komponen='Komponen')

    def upload(self):
        output = BytesIO()
        with Image.new('RGB', (12, 12), 'blue') as image:
            image.save(output, format='PNG')
        return SimpleUploadedFile('foto.png', output.getvalue(), content_type='image/png')

    def photo(self, kind=JenisFotoPemeliharaanChoices.PEMERIKSAAN):
        return PemeliharaanFoto.objects.create(item=self.item, jenis=kind, foto=self.upload())

    def test_repeated_replacement_removes_previous_file_for_all_photo_types(self):
        for kind in JenisFotoPemeliharaanChoices.values:
            row = self.photo(kind)
            for _ in range(3):
                old = row.foto
                with self.captureOnCommitCallbacks(execute=True):
                    row.foto = self.upload()
                    row.save(update_fields=['foto'])
                    self.assertTrue(old.storage.exists(old.name))
                self.assertFalse(old.storage.exists(old.name))
                row.refresh_from_db()
                self.assertTrue(row.foto.storage.exists(row.foto.name))
        expected = set(PemeliharaanFoto.objects.values_list('foto', flat=True))
        stored = {file.relative_to(self.media).as_posix() for file in self.media.rglob('*') if file.is_file()}
        self.assertEqual(stored, expected)

    def test_clear_updates_database_and_deletes_storage_after_commit(self):
        row = self.photo()
        old = row.foto
        with self.captureOnCommitCallbacks(execute=True):
            row.foto = ''
            row.save(update_fields=['foto'])
            self.assertTrue(old.storage.exists(old.name))
        row.refresh_from_db()
        self.assertFalse(row.foto)
        self.assertFalse(old.storage.exists(old.name))

    def test_queryset_delete_removes_only_selected_file(self):
        removed, kept = self.photo(), self.photo()
        file = removed.foto
        with self.captureOnCommitCallbacks(execute=True):
            PemeliharaanFoto.objects.filter(pk=removed.pk).delete()
            self.assertTrue(file.storage.exists(file.name))
        self.assertFalse(file.storage.exists(file.name))
        self.assertTrue(kept.foto.storage.exists(kept.foto.name))

    def test_cascade_delete_request_removes_all_photo_types(self):
        files = [self.photo(kind).foto for kind in JenisFotoPemeliharaanChoices.values]
        with self.captureOnCommitCallbacks(execute=True):
            self.request.delete()
            for file in files:
                self.assertTrue(file.storage.exists(file.name))
        self.assertFalse(PemeliharaanFoto.objects.exists())
        for file in files:
            self.assertFalse(file.storage.exists(file.name))

    def test_item_cascade_cleans_its_files(self):
        file = self.photo().foto
        with self.captureOnCommitCallbacks(execute=True):
            self.item.delete()
        self.assertTrue(PemeliharaanPengajuan.objects.filter(pk=self.request.pk).exists())
        self.assertFalse(file.storage.exists(file.name))

    def test_rollback_delete_and_clear_preserve_original_file(self):
        for delete in (True, False):
            with self.subTest(delete=delete):
                row = self.photo()
                pk, file = row.pk, row.foto
                with self.captureOnCommitCallbacks(execute=True):
                    try:
                        with transaction.atomic():
                            if delete:
                                row.delete()
                            else:
                                row.foto = ''
                                row.save(update_fields=['foto'])
                            raise ValueError('rollback')
                    except ValueError:
                        pass
                restored = PemeliharaanFoto.objects.get(pk=pk)
                self.assertEqual(restored.foto.name, file.name)
                self.assertTrue(file.storage.exists(file.name))

    def test_shared_file_survives_until_its_last_reference_is_removed(self):
        first = self.photo()
        file = first.foto
        second = PemeliharaanFoto.objects.create(item=self.item, jenis='kerusakan', foto=file.name)
        with self.captureOnCommitCallbacks(execute=True):
            first.delete()
        self.assertTrue(file.storage.exists(file.name))
        with self.captureOnCommitCallbacks(execute=True):
            second.delete()
        self.assertFalse(file.storage.exists(file.name))

    def test_reference_in_another_app_preserves_file(self):
        row = self.photo()
        file = row.foto
        profile = self.user.safe_profile
        profile.foto_profil = file.name
        profile.save(update_fields=['foto_profil'])
        with self.captureOnCommitCallbacks(execute=True):
            row.delete()
        self.assertTrue(file.storage.exists(file.name))
        with self.captureOnCommitCallbacks(execute=True):
            profile.foto_profil = ''
            profile.save(update_fields=['foto_profil'])
        self.assertFalse(file.storage.exists(file.name))

    def test_unrelated_update_does_not_delete_unsaved_photo_change(self):
        row = self.photo()
        file = row.foto
        row.foto = ''
        row.urutan = 2
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            row.save(update_fields=['urutan'])
        row.refresh_from_db()
        self.assertEqual(callbacks, [])
        self.assertEqual(row.foto.name, file.name)
        self.assertTrue(file.storage.exists(file.name))
