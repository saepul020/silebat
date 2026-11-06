from django.db.models.signals import post_delete, post_save
from django.db import transaction
from django.dispatch import receiver

from apps.core.file_cleanup import delete_instance_files

from .models import Pelatihan, PesertaPelatihan, User, UserProfile


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, raw=False, **kwargs):
    if raw:
        return

    UserProfile.objects.get_or_create(user=instance)


@receiver(post_delete, sender=UserProfile)
def cleanup_user_profile_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_profil", "ttd_digital"))


@receiver(post_delete, sender=PesertaPelatihan)
def cleanup_peserta_files(sender, instance, **kwargs):
    transaction.on_commit(lambda: delete_instance_files(instance, ("file_sertifikat",)))


@receiver(post_delete, sender=Pelatihan)
def cleanup_pelatihan_files(sender, instance, **kwargs):
    transaction.on_commit(lambda: delete_instance_files(instance, ("file_materi",)))
