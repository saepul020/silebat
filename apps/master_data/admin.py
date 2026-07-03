from django.contrib import admin

from .models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    FasilitasRuangan,
    PeralatanLaboratorium,
)


@admin.register(BarangLaboratorium)
class PeralatanSurveiLapanganAdmin(admin.ModelAdmin):
    list_display = ('nama_barang', 'kategori_barang', 'status_barang', 'kode_laboratorium', 'kondisi_barang', 'ketersediaan', 'lokasi_barang')
    search_fields = ('nama_barang', 'kategori_barang', 'kode_laboratorium', 'kode_aset_bmn', 'tipe_merek_barang', 'lokasi_barang')
    list_filter = ('kategori_barang', 'status_barang', 'kondisi_barang', 'ketersediaan', 'satuan')


@admin.register(BarangPenunjangOperasional)
class BarangPenunjangLapanganAdmin(admin.ModelAdmin):
    list_display = ('nama_barang', 'kategori_barang', 'volume', 'volume_rusak', 'total_volume', 'volume_dipinjam', 'sisa_volume', 'ketersediaan')
    search_fields = ('nama_barang', 'tipe_merek_barang')
    list_filter = ('kategori_barang', 'ketersediaan')


@admin.register(BahanOperasional)
class BahanOperasionalAdmin(admin.ModelAdmin):
    list_display = ('nama_barang', 'kategori_barang', 'volume', 'satuan', 'stok_minimum', 'ketersediaan')
    search_fields = ('nama_barang',)
    list_filter = ('kategori_barang', 'satuan', 'ketersediaan')


@admin.register(FasilitasRuangan)
class SaranaPrasaranaRuanganAdmin(admin.ModelAdmin):
    list_display = ('nama_barang', 'kategori_barang', 'status_barang', 'bervolume', 'kode_laboratorium', 'volume_baik', 'volume_rusak', 'total_volume', 'kondisi_barang', 'ketersediaan', 'lokasi_barang')
    search_fields = ('nama_barang', 'kategori_barang', 'kode_laboratorium', 'kode_aset_bmn', 'tipe_merek_barang', 'lokasi_barang')
    list_filter = ('kategori_barang', 'status_barang', 'bervolume', 'kondisi_barang', 'ketersediaan', 'satuan')


@admin.register(PeralatanLaboratorium)
class PeralatanLaboratoriumAdmin(admin.ModelAdmin):
    list_display = ('nama_barang', 'status_barang', 'bervolume', 'kode_laboratorium', 'volume_baik', 'volume_rusak', 'total_volume', 'kondisi_barang', 'ketersediaan', 'lokasi_barang')
    search_fields = ('nama_barang', 'kode_laboratorium', 'kode_aset_bmn', 'tipe_merek_barang', 'lokasi_barang')
    list_filter = ('status_barang', 'bervolume', 'kondisi_barang', 'ketersediaan', 'satuan')
