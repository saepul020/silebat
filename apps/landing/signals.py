from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.file_cleanup import delete_file_if_unused

from .models import LandingPeralatanFoto


@receiver(
    post_delete,
    sender=LandingPeralatanFoto,
    dispatch_uid="cleanup_landing_equipment_photo",
)
def cleanup_landing_equipment_photo(sender, instance, **kwargs):
    delete_file_if_unused(sender, "foto", instance.foto, exclude_pk=instance.pk)
