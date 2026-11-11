from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.file_cleanup import delete_file_if_unused

from .models import DokumentasiTV, LandingPeralatanFoto


@receiver(pre_save, sender=DokumentasiTV, dispatch_uid="remember_tv_photo")
def remember_tv_photo(sender, instance, using, raw=False, **kwargs):
    instance._old_foto = ""
    if instance.pk and not raw:
        instance._old_foto = sender.objects.using(using).filter(pk=instance.pk).values_list("foto", flat=True).first() or ""


@receiver(post_save, sender=DokumentasiTV, dispatch_uid="replace_tv_photo")
def replace_tv_photo(sender, instance, using, raw=False, **kwargs):
    old_name = getattr(instance, "_old_foto", "")
    if not raw and old_name and old_name != instance.foto.name:
        transaction.on_commit(lambda: delete_file_if_unused(sender, "foto", old_name), using=using)


@receiver(post_delete, sender=DokumentasiTV, dispatch_uid="cleanup_tv_photo")
def cleanup_tv_photo(sender, instance, using, **kwargs):
    foto = instance.foto
    transaction.on_commit(lambda: delete_file_if_unused(sender, "foto", foto), using=using)


@receiver(
    post_delete,
    sender=LandingPeralatanFoto,
    dispatch_uid="cleanup_landing_equipment_photo",
)
def cleanup_landing_equipment_photo(sender, instance, **kwargs):
    delete_file_if_unused(sender, "foto", instance.foto, exclude_pk=instance.pk)
