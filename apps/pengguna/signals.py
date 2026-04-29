from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.file_cleanup import delete_instance_files

from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    profile, _ = UserProfile.objects.get_or_create(user=instance)
    profile.save()


@receiver(post_delete, sender=UserProfile)
def cleanup_user_profile_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_profil", "ttd_digital"))
