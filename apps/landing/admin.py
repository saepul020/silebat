from django.contrib import admin

from .models import LandingPeralatanCard


@admin.register(LandingPeralatanCard)
class LandingPeralatanCardAdmin(admin.ModelAdmin):
    list_display = ("nama_barang", "kategori_barang", "jenis_barang", "merek_tipe_alat", "urutan", "is_active")
    list_filter = ("is_active", "kategori_barang")
    search_fields = (
        "nama_barang",
        "kategori_barang",
        "jenis_barang",
        "merek_tipe_alat",
        "fungsi_alat",
        "spesifikasi_alat",
    )
    ordering = ("urutan", "nama_barang")
