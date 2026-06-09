from django.contrib import admin

from .models import LandingPeralatanCard, LandingPeralatanFoto


class LandingPeralatanFotoInline(admin.TabularInline):
    model = LandingPeralatanFoto
    extra = 0
    max_num = 5
    validate_max = True


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
    inlines = (LandingPeralatanFotoInline,)
