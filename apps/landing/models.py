from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.master_data.models import KategoriBarangLaboratoriumChoices


MAX_EQUIPMENT_PHOTOS = 5
TV_SLOT_COUNT = 6


class KontenAlatTV(models.Model):
    nomor = models.PositiveSmallIntegerField(
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(TV_SLOT_COUNT)],
        verbose_name="Nomor Kolom",
    )
    alat = models.ForeignKey(
        "master_data.BarangLaboratorium",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="konten_tv",
        verbose_name="Peralatan Survei Lapangan",
    )

    class Meta:
        ordering = ["nomor"]
        verbose_name = "Konten Alat TV"
        verbose_name_plural = "Konten Alat TV"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(nomor__gte=1, nomor__lte=TV_SLOT_COUNT),
                name="tv_nomor_range",
            ),
        ]

    def __str__(self):
        return f"Kolom {self.nomor}"


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
