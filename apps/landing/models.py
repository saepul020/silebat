from django.db import models

from apps.master_data.models import KategoriBarangLaboratoriumChoices


MAX_EQUIPMENT_PHOTOS = 5


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
    metode_pengukuran = models.CharField(
        max_length=180,
        blank=True,
        verbose_name="Metode Pengukuran",
    )
    spesifikasi_alat = models.TextField(verbose_name="Spesifikasi Alat")
    ringkasan_alat = models.TextField(verbose_name="Ringkasan Alat")
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


class LandingPeralatanFoto(models.Model):
    card = models.ForeignKey(
        LandingPeralatanCard,
        on_delete=models.CASCADE,
        related_name="fotos",
    )
    foto = models.ImageField(
        upload_to="landing/peralatan/",
        verbose_name="Foto Barang",
    )
    urutan = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["urutan", "id"]
        verbose_name = "Foto Peralatan Landing Page"
        verbose_name_plural = "Foto Peralatan Landing Page"

    def __str__(self):
        return f"Foto {self.card} #{self.urutan}"
