from django.contrib import admin

from .models import DataKopDokumen, InstansiKlien, LayananKegiatan, SurveiKegiatan, TimKegiatan


@admin.register(TimKegiatan)
class TimKegiatanAdmin(admin.ModelAdmin):
    list_display = ('nama_tim', 'ketua_tim')
    search_fields = ('nama_tim', 'ketua_tim__username', 'ketua_tim__first_name')
    list_select_related = ('ketua_tim',)


@admin.register(LayananKegiatan)
class LayananKegiatanAdmin(admin.ModelAdmin):
    list_display = ('jenis_layanan',)
    search_fields = ('jenis_layanan',)


@admin.register(InstansiKlien)
class InstansiKlienAdmin(admin.ModelAdmin):
    list_display = ('nama_instansi', 'organisasi')
    search_fields = ('nama_instansi', 'alamat_instansi', 'organisasi')
    list_filter = ('organisasi',)


@admin.register(SurveiKegiatan)
class SurveiKegiatanAdmin(admin.ModelAdmin):
    list_display = ('jenis_survei',)
    search_fields = ('jenis_survei',)


@admin.register(DataKopDokumen)
class DataKopDokumenAdmin(admin.ModelAdmin):
    list_display = ('id', 'kop_dokumen')
