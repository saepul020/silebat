from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.file_cleanup import delete_file_if_unused

from .models import PemeliharaanFoto


def queue_photo_cleanup(sender, file, using):
    if file:
        transaction.on_commit(partial(
            delete_file_if_unused, sender, 'foto', file, using=using, check_references=True,
        ), using=using)


@receiver(pre_save, sender=PemeliharaanFoto)
def remember_photo(sender, instance, using, raw=False, update_fields=None, **kwargs):
    instance._previous_photo = None
    if raw or instance.pk is None or (update_fields is not None and 'foto' not in update_fields):
        return
    previous = sender.objects.using(using).filter(pk=instance.pk).only('foto').first()
    if previous is not None:
        instance._previous_photo = previous.foto


@receiver(post_save, sender=PemeliharaanFoto)
def cleanup_replaced_photo(sender, instance, using, raw=False, **kwargs):
    previous = instance.__dict__.pop('_previous_photo', None)
    if not raw and previous and previous.name != instance.foto.name:
        queue_photo_cleanup(sender, previous, using)


@receiver(post_delete, sender=PemeliharaanFoto)
def cleanup_pemeliharaan_foto(sender, instance, using, **kwargs):
    queue_photo_cleanup(sender, instance.foto, using)
