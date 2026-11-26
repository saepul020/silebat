from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.file_cleanup import delete_file_if_unused

from .models import Logbook, Pendidikan, Pelatihan, PesertaPelatihan, Portofolio, RiwayatKarir, User, UserProfile


UPLOAD_FIELDS = {
    UserProfile: ('foto_profil', 'ttd_digital'),
    Pelatihan: ('file_materi',),
    PesertaPelatihan: ('file_sertifikat',),
    Pendidikan: ('ijazah', 'transkrip'),
    RiwayatKarir: ('dokumen',),
    Portofolio: ('dokumen',),
    Logbook: ('dokumen',),
}


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, raw=False, **kwargs):
    if not raw:
        UserProfile.objects.get_or_create(user=instance)


def remember_uploads(sender, instance, using, raw=False, update_fields=None, **kwargs):
    instance._previous_files = {}
    if raw or instance.pk is None:
        return
    fields = [name for name in UPLOAD_FIELDS[sender] if update_fields is None or name in update_fields]
    if not fields:
        return
    previous = sender._base_manager.using(using).filter(pk=instance.pk).only(*fields).first()
    if previous is not None:
        instance._previous_files = {name: getattr(previous, name) for name in fields}


def queue_cleanup(sender, files, using):
    for name, file in files.items():
        if file:
            transaction.on_commit(partial(
                delete_file_if_unused, sender, name, file, using=using, check_references=True,
            ), using=using)


def cleanup_replaced_uploads(sender, instance, using, raw=False, **kwargs):
    previous = instance.__dict__.pop('_previous_files', {})
    if not raw:
        queue_cleanup(sender, {
            name: file for name, file in previous.items()
            if file and file.name != getattr(instance, name).name
        }, using)


def cleanup_deleted_uploads(sender, instance, using, **kwargs):
    queue_cleanup(sender, {name: getattr(instance, name) for name in UPLOAD_FIELDS[sender]}, using)
    if sender is PesertaPelatihan:
        transaction.on_commit(partial(cleanup_empty_training, instance.pelatihan_id, using), using=using)


def cleanup_empty_training(pk, using):
    with transaction.atomic(using=using):
        training = Pelatihan.objects.using(using).select_for_update().filter(pk=pk).first()
        if training is not None and not training.peserta.using(using).exists():
            training.delete(using=using)


for model in UPLOAD_FIELDS:
    for signal, handler in ((pre_save, remember_uploads), (post_save, cleanup_replaced_uploads),
                            (post_delete, cleanup_deleted_uploads)):
        signal.connect(handler, sender=model, dispatch_uid=f'pengguna.{model._meta.model_name}.{handler.__name__}')
