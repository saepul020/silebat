from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.file_cleanup import delete_instance_files

from .models import BarangLaboratorium, FasilitasRuangan, PeralatanLaboratorium


@receiver(post_delete, sender=BarangLaboratorium)
def cleanup_barang_laboratorium_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_barang", "ik_alat"))


@receiver(post_delete, sender=FasilitasRuangan)
def cleanup_fasilitas_ruangan_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_barang",))


@receiver(post_delete, sender=PeralatanLaboratorium)
def cleanup_peralatan_laboratorium_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_barang",))
