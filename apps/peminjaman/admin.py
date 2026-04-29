from django.contrib import admin

from .models import (
    PeminjamanBahanOperasional,
    PeminjamanBarangLaboratorium,
    PeminjamanBarangPenunjang,
    PeminjamanPeralatanLaboratorium,
    PeminjamanRequest,
    PeminjamanTimeline,
    PengembalianBahanOperasional,
    PengembalianBarangLaboratorium,
    PengembalianBarangPenunjang,
    PengembalianPeralatanLaboratorium,
)


class PeminjamanBarangLaboratoriumInline(admin.TabularInline):
    model = PeminjamanBarangLaboratorium
    extra = 0


class PeminjamanBarangPenunjangInline(admin.TabularInline):
    model = PeminjamanBarangPenunjang
    extra = 0



class PeminjamanPeralatanLaboratoriumInline(admin.TabularInline):
    model = PeminjamanPeralatanLaboratorium
    extra = 0


class PeminjamanBahanOperasionalInline(admin.TabularInline):
    model = PeminjamanBahanOperasional
    extra = 0


class PengembalianBarangLaboratoriumInline(admin.TabularInline):
    model = PengembalianBarangLaboratorium
    fk_name = "pengajuan"
    extra = 0


class PengembalianBarangPenunjangInline(admin.TabularInline):
    model = PengembalianBarangPenunjang
    fk_name = "pengajuan"
    extra = 0



class PengembalianPeralatanLaboratoriumInline(admin.TabularInline):
    model = PengembalianPeralatanLaboratorium
    fk_name = "pengajuan"
    extra = 0


class PengembalianBahanOperasionalInline(admin.TabularInline):
    model = PengembalianBahanOperasional
    fk_name = "pengajuan"
    extra = 0


class PeminjamanTimelineInline(admin.TabularInline):
    model = PeminjamanTimeline
    extra = 0
    readonly_fields = ('stage', 'action', 'actor', 'note', 'created_at')
    can_delete = False


@admin.register(PeminjamanRequest)
class PeminjamanRequestAdmin(admin.ModelAdmin):
    list_display = (
        'nomor_pengajuan',
        'nama_peminjam',
        'layanan_kegiatan',
        'current_step',
        'return_current_step',
        'submitted_at',
    )
    list_filter = ('current_step', 'return_current_step', 'layanan_kegiatan')
    search_fields = ('nomor_pengajuan', 'nama_peminjam', 'email_peminjam')
    inlines = [
        PeminjamanBarangLaboratoriumInline,
        PeminjamanBarangPenunjangInline,
        PeminjamanPeralatanLaboratoriumInline,
        PeminjamanBahanOperasionalInline,
        PengembalianBarangLaboratoriumInline,
        PengembalianBarangPenunjangInline,
        PengembalianPeralatanLaboratoriumInline,
        PengembalianBahanOperasionalInline,
        PeminjamanTimelineInline,
    ]


admin.site.register(PeminjamanTimeline)
