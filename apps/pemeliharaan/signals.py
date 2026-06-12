from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.file_cleanup import delete_instance_files

from .models import PemeliharaanFoto


@receiver(post_delete, sender=PemeliharaanFoto)
def cleanup_pemeliharaan_foto(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto",))
