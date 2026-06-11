from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.list_pagination import paginate_list
from apps.core.permissions import (
    ROLE_ADMIN_LAB,
    ROLE_KEPALA_LAB,
    ROLE_PIMPINAN,
    ROLE_SUPER_ADMIN,
    ROLE_TEKNISI_LAB,
    deny_access,
    get_role_name,
)
from apps.master_data.models import BarangLaboratorium

from .forms import PemeliharaanForm
from .models import (
    JenisFotoPemeliharaanChoices,
    KeputusanPemeliharaanChoices,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices,
)


PEMELIHARAAN_LIST_SEARCH_FIELDS = (
    "nomor_pengajuan",
    "snapshot_nama_barang",
    "snapshot_kode_laboratorium",
    "snapshot_tipe_merek_barang",
    "pemohon__username",
    "pemohon__nama_lengkap",
    "current_step",
    "items__komponen",
    "items__kondisi",
)
PEMELIHARAAN_ADMIN_ROLES = {
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN_LAB,
    ROLE_TEKNISI_LAB,
    ROLE_KEPALA_LAB,
    ROLE_PIMPINAN,
}
PEMELIHARAAN_INPUT_ROLES = {
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN_LAB,
    ROLE_TEKNISI_LAB,
}


def _can_view_pengajuan(user, obj):
    if get_role_name(user) in PEMELIHARAAN_ADMIN_ROLES:
        return True
    return obj.pemohon_id == getattr(user, "id", None)


def _can_delete_pengajuan(user):
    return get_role_name(user) == ROLE_SUPER_ADMIN


def _can_input_pengajuan(user):
    return get_role_name(user) in PEMELIHARAAN_INPUT_ROLES


def _can_submit_pengajuan(user, obj):
    role_name = get_role_name(user)
    if role_name not in PEMELIHARAAN_INPUT_ROLES or not obj.is_draft_like:
        return False
    if role_name == ROLE_SUPER_ADMIN:
        return True
    return obj.pemohon_id == getattr(user, "id", None)


def _can_edit_pengajuan(user, obj):
    return _can_submit_pengajuan(user, obj)


def _get_pengajuan_queryset():
    return (
        PemeliharaanPengajuan.objects.select_related("pemohon", "alat")
        .prefetch_related("items__fotos", "timeline_entries__actor")
        .order_by("-tanggal_pemeriksaan", "-id")
    )


def _build_alat_components(instance=None):
    active_alat_ids = PemeliharaanPengajuan.objects.filter(
        current_step__in=(
            StepPemeliharaanChoices.DRAFT,
            StepPemeliharaanChoices.KEPALA_LAB,
            StepPemeliharaanChoices.PIMPINAN,
            StepPemeliharaanChoices.DIKEMBALIKAN,
        ),
        alat__isnull=False,
    )
    if instance and instance.pk:
        active_alat_ids = active_alat_ids.exclude(pk=instance.pk)
    return {
        str(item.pk): [
            str(component or "").strip()
            for component in (item.komponen_pemeliharaan or [])
            if str(component or "").strip()
        ]
        for item in BarangLaboratorium.objects.exclude(
            pk__in=active_alat_ids.values("alat_id")
        ).order_by("nama_barang", "kode_laboratorium")
    }


def _format_local_datetime(value):
    if not value:
        return "-"
    return timezone.localtime(value).strftime("%d %b %Y %H:%M")


@login_required
def index(request):
    return redirect("pemeliharaan:list")


@login_required
def daftar_pengajuan(request):
    queryset = _get_pengajuan_queryset()
    if get_role_name(request.user) not in PEMELIHARAAN_ADMIN_ROLES:
        queryset = queryset.filter(pemohon=request.user)

    pagination_context = paginate_list(
        request,
        queryset,
        search_fields=PEMELIHARAAN_LIST_SEARCH_FIELDS,
    )
    for item in pagination_context["items"]:
        item.can_kirim = _can_submit_pengajuan(request.user, item)
        item.can_edit = _can_edit_pengajuan(request.user, item)
    return render(
        request,
        "pemeliharaan/pengajuan_list.html",
        {
            **pagination_context,
            "page_title": "Pengajuan Pemeliharaan",
            "page_subtitle": "Kelola transaksi pemeriksaan dan tindak lanjut pemeliharaan peralatan survei lapangan.",
            "can_delete_pengajuan": _can_delete_pengajuan(request.user),
        },
    )


@login_required
def tambah_pengajuan(request):
    if not _can_input_pengajuan(request.user):
        return deny_access(
            request,
            "Hanya Admin Lab, Teknisi Lab, atau Super Admin yang dapat membuat pengajuan pemeliharaan.",
        )

    tanggal_pemeriksaan = timezone.now()
    form = PemeliharaanForm(
        request.POST or None,
        request.FILES or None,
        actor=request.user,
        tanggal_pemeriksaan=tanggal_pemeriksaan,
    )
    if request.method == "POST" and form.is_valid():
        pengajuan = form.save()
        pengajuan.add_timeline(
            "Pemohon",
            "Pengajuan pemeliharaan dibuat sebagai draft",
            request.user,
        )
        messages.success(request, "Pengajuan pemeliharaan berhasil disimpan.")
        return redirect("pemeliharaan:detail", pk=pengajuan.pk)

    return render(
        request,
        "pemeliharaan/pengajuan_form.html",
        {
            "form": form,
            "page_title": "Tambah Pengajuan Pemeliharaan",
            "page_subtitle": "Pilih alat, isi kondisi setiap komponen, dan unggah dokumentasi pemeriksaan.",
            "submit_label": "Simpan",
            "alat_components": _build_alat_components(),
            "tanggal_pemeriksaan_display": _format_local_datetime(tanggal_pemeriksaan),
        },
    )


@login_required
def edit_pengajuan(request, pk):
    obj = get_object_or_404(_get_pengajuan_queryset(), pk=pk)
    if not _can_edit_pengajuan(request.user, obj):
        return deny_access(
            request,
            "Pengajuan pemeliharaan hanya dapat diedit saat masih draft atau dikembalikan.",
        )

    form = PemeliharaanForm(
        request.POST or None,
        request.FILES or None,
        actor=request.user,
        instance=obj,
    )
    if request.method == "POST" and form.is_valid():
        pengajuan = form.save()
        pengajuan.add_timeline(
            "Pemohon",
            "Draft pengajuan pemeliharaan diperbarui",
            request.user,
        )
        messages.success(request, "Pengajuan pemeliharaan berhasil diperbarui.")
        return redirect("pemeliharaan:detail", pk=pengajuan.pk)

    return render(
        request,
        "pemeliharaan/pengajuan_form.html",
        {
            "form": form,
            "page_title": "Edit Pengajuan Pemeliharaan",
            "page_subtitle": "Perbarui data pemeriksaan sebelum dikirim ke proses verifikasi.",
            "submit_label": "Simpan",
            "alat_components": _build_alat_components(obj),
            "tanggal_pemeriksaan_display": _format_local_datetime(obj.tanggal_pemeriksaan),
        },
    )


@login_required
def detail_pengajuan(request, pk):
    obj = get_object_or_404(_get_pengajuan_queryset(), pk=pk)
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request,
            "Anda tidak memiliki akses untuk melihat pengajuan pemeliharaan ini.",
        )

    items = []
    pemeriksaan_fotos = []
    for item in obj.items.all():
        fotos = list(item.fotos.all())
        pemeriksaan_fotos.extend(
            foto for foto in fotos if foto.jenis == JenisFotoPemeliharaanChoices.PEMERIKSAAN
        )
        item.foto_perbaikan = [
            foto for foto in fotos if foto.jenis == JenisFotoPemeliharaanChoices.PERBAIKAN
        ]
        item.foto_kerusakan = [
            foto for foto in fotos if foto.jenis == JenisFotoPemeliharaanChoices.KERUSAKAN
        ]
        items.append(item)

    return render(
        request,
        "pemeliharaan/pengajuan_detail.html",
        {
            "obj": obj,
            "items": items,
            "pemeriksaan_fotos": pemeriksaan_fotos,
            "can_delete_pengajuan": _can_delete_pengajuan(request.user),
            "can_submit_pengajuan": _can_submit_pengajuan(request.user, obj),
            "can_edit_pengajuan": _can_edit_pengajuan(request.user, obj),
        },
    )


@login_required
def kirim_pengajuan(request, pk):
    if request.method != "POST":
        return redirect("pemeliharaan:detail", pk=pk)

    obj = get_object_or_404(
        PemeliharaanPengajuan.objects.prefetch_related("items"),
        pk=pk,
    )
    if not _can_submit_pengajuan(request.user, obj):
        return deny_access(
            request,
            "Anda tidak memiliki akses untuk mengirim pengajuan pemeliharaan ini.",
        )

    with transaction.atomic():
        obj.current_step = StepPemeliharaanChoices.KEPALA_LAB
        obj.submitted_at = timezone.now()
        obj.kepala_lab_status = KeputusanPemeliharaanChoices.PENDING
        obj.kepala_lab_by = None
        obj.kepala_lab_at = None
        obj.kepala_lab_note = ""
        obj.pimpinan_status = KeputusanPemeliharaanChoices.PENDING
        obj.pimpinan_by = None
        obj.pimpinan_at = None
        obj.pimpinan_note = ""
        obj.save(
            update_fields=[
                "current_step",
                "submitted_at",
                "kepala_lab_status",
                "kepala_lab_by",
                "kepala_lab_at",
                "kepala_lab_note",
                "pimpinan_status",
                "pimpinan_by",
                "pimpinan_at",
                "pimpinan_note",
                "updated_at",
            ]
        )
        obj.add_timeline(
            "Pemohon",
            "Pengajuan pemeliharaan dikirim ke Kepala Lab",
            request.user,
        )

    messages.success(
        request,
        "Pengajuan pemeliharaan berhasil dikirim ke Kepala Lab untuk verifikasi.",
    )
    return redirect("pemeliharaan:detail", pk=obj.pk)


@login_required
def hapus_pengajuan(request, pk):
    if request.method != "POST":
        return redirect("pemeliharaan:detail", pk=pk)
    if not _can_delete_pengajuan(request.user):
        return deny_access(
            request,
            "Hanya Super Admin yang dapat menghapus pengajuan pemeliharaan.",
        )

    obj = get_object_or_404(PemeliharaanPengajuan, pk=pk)
    nomor_pengajuan = obj.nomor_pengajuan
    obj.pulihkan_kondisi_alat_jika_selesai()
    obj.delete()
    messages.success(request, f"Pengajuan {nomor_pengajuan} berhasil dihapus.")
    return redirect("pemeliharaan:list")
