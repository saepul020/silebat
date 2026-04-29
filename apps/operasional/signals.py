from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.file_cleanup import delete_instance_files

from .models import DataKopDokumen


@receiver(post_delete, sender=DataKopDokumen)
def hapus_file_kop_dokumen(sender, instance, **kwargs):
    delete_instance_files(instance, ("kop_dokumen",))
