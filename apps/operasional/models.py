from django.conf import settings
from django.db import models

TIM_LAYANAN_TEKNIS_NAME = "Tim Layanan Teknis"
TIM_PENGEMBANGAN_PENERAPAN_NAME = "Tim Pengembangan Penerapan"

TIM_KEGIATAN_RENAME_MAP = {
    "Sub Koordinator Layanan Teknis": TIM_LAYANAN_TEKNIS_NAME,
    "Sub Koordinator Pengembangan Penerapan": TIM_PENGEMBANGAN_PENERAPAN_NAME,
}


def normalize_tim_kegiatan_name(nama_tim):
    nama = (str(nama_tim or "")).strip()
    return TIM_KEGIATAN_RENAME_MAP.get(nama, nama)


def format_ketua_tim_title(nama_tim):
    nama = normalize_tim_kegiatan_name(nama_tim)
    if not nama:
        return "Ketua Tim,"
    if nama.lower().startswith("tim "):
        nama = nama[4:].strip()
    return f"Ketua Tim {nama},"


class TimKegiatan(models.Model):
    nama_tim = models.CharField(max_length=150, unique=True)
    ketua_tim = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tim_kegiatan_dipimpin',
    )

    class Meta:
        ordering = ['nama_tim']
        verbose_name = 'Data Tim Kegiatan'
        verbose_name_plural = 'Data Tim Kegiatan'

    def __str__(self):
        return normalize_tim_kegiatan_name(self.nama_tim)


class LayananKegiatan(models.Model):
    jenis_layanan = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ['jenis_layanan']
        verbose_name = 'Data Layanan Kegiatan'
        verbose_name_plural = 'Data Layanan Kegiatan'

    def __str__(self):
        return self.jenis_layanan


class SurveiKegiatan(models.Model):
    jenis_survei = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ['jenis_survei']
        verbose_name = 'Data Kegiatan Survei'
        verbose_name_plural = 'Data Kegiatan Survei'

    def __str__(self):
        return self.jenis_survei


class InstansiKlien(models.Model):
    class OrganisasiChoices(models.TextChoices):
        INTERNAL_PU = 'Internal PU', 'Internal PU'
        EKSTERNAL_PU = 'Eksternal PU', 'Eksternal PU'
        INTERNAL_BAT = 'Internal BAT', 'Internal BAT'

    nama_instansi = models.CharField(max_length=200, unique=True)
    alamat_instansi = models.TextField()
    organisasi = models.CharField(max_length=30, choices=OrganisasiChoices.choices)

    class Meta:
        ordering = ['nama_instansi']
        verbose_name = 'Data Instansi (Klien)'
        verbose_name_plural = 'Data Instansi (Klien)'

    def __str__(self):
        return self.nama_instansi

class DataKopDokumen(models.Model):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    kop_dokumen = models.ImageField(upload_to='operasional/kop_dokumen/')

    class Meta:
        verbose_name = 'Data Kop Dokumen'
        verbose_name_plural = 'Data Kop Dokumen'

    def __str__(self):
        return 'Kop Dokumen'

