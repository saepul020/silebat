from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from PIL import Image

from .forms import UserProfileForm
from .models import Logbook, Pendidikan, Pelatihan, PesertaPelatihan, Portofolio, RiwayatKarir, User, UserProfile
from .signals import UPLOAD_FIELDS


class UploadCleanupTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory(prefix='silebat-cleanup-')
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create_user(username='cleanup-user')
        self.other = User.objects.create_user(username='cleanup-other')
        day = date(2026, 1, 1)
        self.training = Pelatihan.objects.create(user=self.user, tanggal_mulai=day, tanggal_selesai=day)
        self.member = PesertaPelatihan.objects.create(pelatihan=self.training, user=self.user)
        self.education = Pendidikan.objects.create(user=self.user, tanggal_lulus=day, nilai=3)
        self.records = [
            self.user.safe_profile, self.training, self.member, self.education,
            RiwayatKarir.objects.create(user=self.user, tanggal_mulai=day, masih_bekerja=True),
            Portofolio.objects.create(user=self.user, tahun=2026),
            Logbook.objects.create(user=self.user, tanggal=day),
        ]
        for record in self.records:
            for name in UPLOAD_FIELDS[type(record)]:
                if isinstance(record, UserProfile):
                    output = BytesIO()
                    with Image.new('RGB', (16, 16), 'blue') as image:
                        image.save(output, format='PNG')
                    file = SimpleUploadedFile(name + '.png', output.getvalue())
                else:
                    file = SimpleUploadedFile(name + '.pdf', b'original')
                setattr(record, name, file)
            record.save()

    def test_replacement_deletes_old_files_after_commit_for_every_upload_field(self):
        for record in self.records:
            for name in UPLOAD_FIELDS[type(record)]:
                with self.subTest(model=type(record).__name__, field=name):
                    old = getattr(record, name)
                    with self.captureOnCommitCallbacks(execute=True):
                        setattr(record, name, SimpleUploadedFile(name + '.pdf', b'replacement'))
                        record.save(update_fields=[name])
                        self.assertTrue(old.storage.exists(old.name))
                    self.assertFalse(old.storage.exists(old.name))
                    record.refresh_from_db()
                    current = getattr(record, name)
                    self.assertTrue(current.storage.exists(current.name))

    def test_clearing_files_clears_database_and_storage(self):
        for record in self.records:
            for name in UPLOAD_FIELDS[type(record)]:
                with self.subTest(model=type(record).__name__, field=name):
                    old = getattr(record, name)
                    with self.captureOnCommitCallbacks(execute=True):
                        setattr(record, name, '')
                        record.save(update_fields=[name])
                    record.refresh_from_db()
                    self.assertFalse(getattr(record, name))
                    self.assertFalse(old.storage.exists(old.name))

    def test_queryset_deletion_removes_all_upload_fields(self):
        # Keep the training while deleting its first participant separately.
        PesertaPelatihan.objects.create(pelatihan=self.training, user=self.other)
        for record in self.records:
            if not type(record).objects.filter(pk=record.pk).exists():
                continue
            files = [getattr(record, name) for name in UPLOAD_FIELDS[type(record)]]
            with self.captureOnCommitCallbacks(execute=True):
                type(record).objects.filter(pk=record.pk).delete()
                for file in files:
                    self.assertTrue(file.storage.exists(file.name))
            for file in files:
                self.assertFalse(file.storage.exists(file.name))

    def test_shared_file_is_preserved_across_records_fields_and_models(self):
        profile = self.user.safe_profile
        shared = profile.foto_profil
        profile.ttd_digital = shared.name
        profile.save(update_fields=['ttd_digital'])
        self.education.ijazah = shared.name
        self.education.save(update_fields=['ijazah'])
        other = self.other.safe_profile
        other.foto_profil = shared.name
        other.save(update_fields=['foto_profil'])
        with self.captureOnCommitCallbacks(execute=True):
            profile.foto_profil = ''
            profile.save(update_fields=['foto_profil'])
            profile.ttd_digital = ''
            profile.save(update_fields=['ttd_digital'])
            other.delete()
        self.assertTrue(shared.storage.exists(shared.name))
        with self.captureOnCommitCallbacks(execute=True):
            self.education.ijazah = ''
            self.education.save(update_fields=['ijazah'])
        self.assertFalse(shared.storage.exists(shared.name))

    def test_rollback_keeps_profile_file_and_database_reference(self):
        profile = self.user.safe_profile
        old = profile.foto_profil
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    profile.delete()
                    raise ValueError('rollback')
            except ValueError:
                pass
        restored = UserProfile.objects.get(user=self.user)
        self.assertEqual(restored.foto_profil.name, old.name)
        self.assertTrue(old.storage.exists(old.name))

    def test_file_referenced_by_another_app_is_preserved(self):
        from apps.operasional.models import DataKopDokumen

        profile = self.user.safe_profile
        shared = profile.foto_profil
        DataKopDokumen.objects.create(kop_dokumen=shared.name)
        with self.captureOnCommitCallbacks(execute=True):
            profile.foto_profil = ''
            profile.save(update_fields=['foto_profil'])
        self.assertTrue(shared.storage.exists(shared.name))

    def test_commit_false_defers_clear_until_saved(self):
        profile = self.user.safe_profile
        old = profile.foto_profil
        form = UserProfileForm(data={'hapus_foto_profil': 'on'}, instance=profile)
        self.assertTrue(form.is_valid(), form.errors)
        unsaved = form.save(commit=False)
        self.assertTrue(old.storage.exists(old.name))
        self.assertEqual(type(profile).objects.get(pk=profile.pk).foto_profil.name, old.name)
        with self.captureOnCommitCallbacks(execute=True):
            unsaved.save()
        self.assertFalse(old.storage.exists(old.name))

    def test_update_fields_does_not_delete_unsaved_field_changes(self):
        profile = self.user.safe_profile
        old = profile.foto_profil
        profile.foto_profil = ''
        with self.captureOnCommitCallbacks(execute=True):
            profile.save(update_fields=['alamat'])
        profile.refresh_from_db()
        self.assertEqual(profile.foto_profil.name, old.name)
        self.assertTrue(old.storage.exists(old.name))

    def test_user_cascade_preserves_shared_training_and_cleans_last_membership(self):
        material = self.training.file_materi
        certificate = self.member.file_sertifikat
        PesertaPelatihan.objects.create(pelatihan=self.training, user=self.other)
        profile_file = self.user.safe_profile.foto_profil
        with self.captureOnCommitCallbacks(execute=True):
            self.user.delete()
        self.assertTrue(Pelatihan.objects.filter(pk=self.training.pk).exists())
        self.assertTrue(material.storage.exists(material.name))
        self.assertFalse(certificate.storage.exists(certificate.name))
        self.assertFalse(profile_file.storage.exists(profile_file.name))
        with self.captureOnCommitCallbacks(execute=True):
            self.other.delete()
        self.assertFalse(Pelatihan.objects.filter(pk=self.training.pk).exists())
        self.assertFalse(material.storage.exists(material.name))
