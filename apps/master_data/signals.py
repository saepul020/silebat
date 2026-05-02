from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.file_cleanup import delete_instance_files

from .models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    FasilitasRuangan,
    PeralatanLaboratorium,
)
from .qr_utils import ensure_master_qr_code


QR_MASTER_MODELS = (
    BarangLaboratorium,
    BarangPenunjangOperasional,
    BahanOperasional,
    FasilitasRuangan,
    PeralatanLaboratorium,
)


def generate_master_qr_code(sender, instance, created=False, **kwargs):
    # Buat QR untuk data baru dan perbaiki otomatis jika database punya path
    # QR tetapi file PNG fisiknya hilang dari folder media.
    ensure_master_qr_code(instance)


for model in QR_MASTER_MODELS:
    post_save.connect(
        generate_master_qr_code,
        sender=model,
        dispatch_uid=f"generate_master_qr_code_{model.__name__}",
    )


@receiver(post_delete, sender=BarangLaboratorium)
def cleanup_barang_laboratorium_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_barang", "ik_alat", "qr_code"))


@receiver(post_delete, sender=BarangPenunjangOperasional)
def cleanup_barang_penunjang_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("qr_code",))


@receiver(post_delete, sender=BahanOperasional)
def cleanup_bahan_operasional_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("qr_code",))


@receiver(post_delete, sender=FasilitasRuangan)
def cleanup_fasilitas_ruangan_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_barang", "ik_alat", "qr_code"))


@receiver(post_delete, sender=PeralatanLaboratorium)
def cleanup_peralatan_laboratorium_files(sender, instance, **kwargs):
    delete_instance_files(instance, ("foto_barang", "ik_alat", "qr_code"))
