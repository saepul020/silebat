from django.contrib import admin

from .models import (
    PemeliharaanFoto,
    PemeliharaanItem,
    PemeliharaanPengajuan,
    PemeliharaanTimeline,
    PemeliharaanVendor,
)


class PemeliharaanFotoInline(admin.TabularInline):
    model = PemeliharaanFoto
    extra = 0


class PemeliharaanItemInline(admin.StackedInline):
    model = PemeliharaanItem
    extra = 0
    inlines = []


class PemeliharaanTimelineInline(admin.TabularInline):
    model = PemeliharaanTimeline
    extra = 0
    readonly_fields = ("stage", "action", "actor", "note", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PemeliharaanPengajuan)
class PemeliharaanPengajuanAdmin(admin.ModelAdmin):
    list_display = (
        "nomor_pengajuan",
        "snapshot_nama_barang",
        "snapshot_kode_laboratorium",
        "pemohon",
        "tanggal_pemeriksaan",
        "current_step",
    )
    list_filter = ("tanggal_pemeriksaan", "current_step")
    search_fields = (
        "nomor_pengajuan",
        "snapshot_nama_barang",
        "snapshot_kode_laboratorium",
        "snapshot_tipe_merek_barang",
        "pemohon__username",
    )
    readonly_fields = ("nomor_pengajuan", "created_at", "updated_at")
    inlines = [PemeliharaanItemInline, PemeliharaanTimelineInline]


@admin.register(PemeliharaanItem)
class PemeliharaanItemAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "komponen", "kondisi", "tindakan_perbaikan")
    list_filter = ("kondisi", "tindakan_perbaikan")
    search_fields = ("pengajuan__nomor_pengajuan", "komponen")
    inlines = [PemeliharaanFotoInline]


@admin.register(PemeliharaanFoto)
class PemeliharaanFotoAdmin(admin.ModelAdmin):
    list_display = ("item", "jenis", "urutan", "created_at")
    list_filter = ("jenis",)


@admin.register(PemeliharaanTimeline)
class PemeliharaanTimelineAdmin(admin.ModelAdmin):
    list_display = ("pengajuan", "stage", "action", "actor", "created_at")
    list_filter = ("stage", "created_at")
    search_fields = ("pengajuan__nomor_pengajuan", "action", "actor__username")


@admin.register(PemeliharaanVendor)
class PemeliharaanVendorAdmin(admin.ModelAdmin):
    list_display = (
        "pengajuan",
        "nama_vendor",
        "nama_pic",
        "tanggal_mulai",
        "tanggal_selesai",
    )
    search_fields = (
        "pengajuan__nomor_pengajuan",
        "nama_vendor",
        "nama_pic",
        "nomor_hp_pic",
    )
