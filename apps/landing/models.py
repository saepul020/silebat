from django.db import models

from apps.core.file_cleanup import delete_file_if_unused
from apps.master_data.models import KategoriBarangLaboratoriumChoices


class LandingPeralatanCard(models.Model):
    kategori_barang = models.CharField(
        max_length=40,
        choices=KategoriBarangLaboratoriumChoices.choices,
        default="",
        verbose_name="Kategori Barang",
    )
    nama_barang = models.CharField(max_length=180, verbose_name="Nama Barang")
    jenis_barang = models.CharField(max_length=160, verbose_name="Jenis Barang")
    merek_tipe_alat = models.CharField(max_length=180, verbose_name="Merek / Tipe Alat")
    fungsi_alat = models.CharField(max_length=220, verbose_name="Fungsi Alat")
    spesifikasi_alat = models.TextField(verbose_name="Spesifikasi Alat")
    ringkasan_alat = models.TextField(verbose_name="Ringkasan Alat")
    foto_barang = models.ImageField(
        upload_to="landing/peralatan/",
        blank=True,
        null=True,
        verbose_name="Upload Foto Barang",
    )
    urutan = models.PositiveIntegerField(unique=True, verbose_name="Urutan Tampil")
    is_active = models.BooleanField(default=True, verbose_name="Tampilkan")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["urutan", "nama_barang", "id"]
        verbose_name = "Konten Peralatan Landing Page"
        verbose_name_plural = "Konten Peralatan Landing Page"

    def __str__(self):
        return self.nama_barang or "Konten Peralatan Landing Page"

    def delete(self, *args, **kwargs):
        old_foto_barang = self.foto_barang
        super().delete(*args, **kwargs)
        delete_file_if_unused(type(self), "foto_barang", old_foto_barang, exclude_pk=self.pk)
