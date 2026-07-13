from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
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
from apps.notifikasi.services import sync_transaction_notifications
from .forms import PemeliharaanForm, format_display_date, get_available_alat_queryset
from .models import (
    ACTIVE_PEMELIHARAAN_STEPS,
    FINAL_PEMELIHARAAN_STEPS,
    JenisFotoPemeliharaanChoices,
    KeputusanPemeliharaanChoices,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices,
)
from .pdf_utils import render_pemeliharaan_pdf


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
        PemeliharaanPengajuan.objects.select_related(
            "pemohon",
            "alat",
            "kepala_lab_by",
            "pimpinan_by",
        )
        .prefetch_related("items__fotos", "timeline_entries__actor")
        .order_by("-tanggal_pemeriksaan", "-id")
    )


def _build_alat_components(instance=None):
    return {
        str(item.pk): [
            str(component or "").strip()
            for component in (item.komponen_pemeliharaan or [])
            if str(component or "").strip()
        ]
        for item in get_available_alat_queryset(instance)
    }


def _format_local_date(value):
    if not value:
        return "-"
    return format_display_date(value)


def _prepare_detail_items(obj):
    items = []
    repair_items = []
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
        if item.perlu_perbaikan:
            repair_items.append(item)
    return items, repair_items, pemeriksaan_fotos


def _reset_verifikasi_pemeliharaan(obj):
    obj.kepala_lab_status = KeputusanPemeliharaanChoices.PENDING
    obj.kepala_lab_by = None
    obj.kepala_lab_at = None
    obj.kepala_lab_note = ""
    obj.pimpinan_status = KeputusanPemeliharaanChoices.PENDING
    obj.pimpinan_by = None
    obj.pimpinan_at = None
    obj.pimpinan_note = ""


def _finalkan_pengajuan_baik(obj, user, submitted_at):
    obj.current_step = StepPemeliharaanChoices.SELESAI
    obj.submitted_at = submitted_at
    _reset_verifikasi_pemeliharaan(obj)
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
        "Pelaksana Pemeliharaan",
        "Pengajuan pemeliharaan semua komponen baik dan dinyatakan selesai",
        user,
    )
    obj.catat_riwayat_alat_disetujui()
    obj.tandai_alat_baik_jika_selesai()


def _kirim_pengajuan_ke_kepala_lab(obj, user, submitted_at):
    obj.current_step = StepPemeliharaanChoices.KEPALA_LAB
    obj.submitted_at = submitted_at
    _reset_verifikasi_pemeliharaan(obj)
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
        "Pelaksana Pemeliharaan",
        "Pengajuan pemeliharaan dikirim ke Kepala Lab",
        user,
    )


@login_required
def index(request):
    return redirect("pemeliharaan:list")


@login_required
def daftar_pengajuan(request):
    queryset = _get_pengajuan_queryset().filter(current_step__in=ACTIVE_PEMELIHARAAN_STEPS)
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
def laporan_pemeliharaan(request):
    queryset = _get_pengajuan_queryset().filter(current_step__in=FINAL_PEMELIHARAAN_STEPS)
    if get_role_name(request.user) not in PEMELIHARAAN_ADMIN_ROLES:
        queryset = queryset.filter(pemohon=request.user)

    pagination_context = paginate_list(
        request,
        queryset,
        search_fields=PEMELIHARAAN_LIST_SEARCH_FIELDS,
    )
    return render(
        request,
        "pemeliharaan/pengajuan_list.html",
        {
            **pagination_context,
            "page_title": "Laporan Pemeliharaan",
            "page_subtitle": "Riwayat pengajuan pemeliharaan yang sudah selesai disetujui atau ditolak.",
            "can_delete_pengajuan": _can_delete_pengajuan(request.user),
            "is_report": True,
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
            "Pelaksana Pemeliharaan",
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
            "tanggal_pemeriksaan_display": _format_local_date(tanggal_pemeriksaan),
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
            "Pelaksana Pemeliharaan",
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
            "tanggal_pemeriksaan_display": _format_local_date(obj.tanggal_pemeriksaan),
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

    items, repair_items, pemeriksaan_fotos = _prepare_detail_items(obj)

    return render(
        request,
        "pemeliharaan/pengajuan_detail.html",
        {
            "obj": obj,
            "items": items,
            "repair_items": repair_items,
            "pemeriksaan_fotos": pemeriksaan_fotos,
            "can_delete_pengajuan": _can_delete_pengajuan(request.user),
            "can_submit_pengajuan": _can_submit_pengajuan(request.user, obj),
            "can_edit_pengajuan": _can_edit_pengajuan(request.user, obj),
        },
    )


@login_required
def detail_laporan(request, pk):
    obj = get_object_or_404(
        _get_pengajuan_queryset(),
        pk=pk,
        current_step__in=FINAL_PEMELIHARAAN_STEPS,
    )
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request,
            "Anda tidak memiliki akses untuk melihat laporan pemeliharaan ini.",
        )

    items, repair_items, pemeriksaan_fotos = _prepare_detail_items(obj)
    return render(
        request,
        "pemeliharaan/pengajuan_detail.html",
        {
            "obj": obj,
            "items": items,
            "repair_items": repair_items,
            "pemeriksaan_fotos": pemeriksaan_fotos,
            "can_delete_pengajuan": _can_delete_pengajuan(request.user),
            "can_submit_pengajuan": False,
            "can_edit_pengajuan": False,
            "is_report": True,
        },
    )


@login_required
def download_pdf(request, pk):
    obj = get_object_or_404(
        _get_pengajuan_queryset(),
        pk=pk,
        current_step__in=FINAL_PEMELIHARAAN_STEPS,
    )
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request,
            "Anda tidak memiliki akses untuk mengunduh PDF laporan pemeliharaan ini.",
        )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="laporan-pemeliharaan-{obj.nomor_pengajuan}.pdf"'
    )
    render_pemeliharaan_pdf(response, obj, format_display_date)
    return response


@login_required
def kirim_pengajuan(request, pk):
    if request.method != "POST":
        return redirect("pemeliharaan:list")

    obj = get_object_or_404(
        PemeliharaanPengajuan.objects.prefetch_related("items"),
        pk=pk,
    )
    if not _can_submit_pengajuan(request.user, obj):
        return deny_access(
            request,
            "Anda tidak memiliki akses untuk mengirim pengajuan pemeliharaan ini.",
        )

    langsung_selesai = not obj.perlu_perbaikan
    with transaction.atomic():
        submitted_at = timezone.now()
        if langsung_selesai:
            _finalkan_pengajuan_baik(obj, request.user, submitted_at)
        else:
            _kirim_pengajuan_ke_kepala_lab(obj, request.user, submitted_at)
        sync_transaction_notifications(obj, actor=request.user)

    if langsung_selesai:
        messages.success(
            request,
            "Pengajuan pemeliharaan semua komponen baik dan langsung dinyatakan selesai.",
        )
    else:
        messages.success(
            request,
            "Pengajuan pemeliharaan berhasil dikirim ke Kepala Lab untuk verifikasi.",
        )
    return redirect("pemeliharaan:list")


@login_required
def hapus_pengajuan(request, pk):
    if request.method != "POST":
        return redirect("pemeliharaan:detail", pk=pk)
    if not _can_delete_pengajuan(request.user):
        return deny_access(
            request,
            "Hanya Super Admin yang dapat menghapus pengajuan pemeliharaan.",
        )

    with transaction.atomic():
        obj = get_object_or_404(
            PemeliharaanPengajuan.objects.select_for_update(),
            pk=pk,
        )
        nomor_pengajuan = obj.nomor_pengajuan
        obj.pulihkan_data_alat_awal()
        obj.delete()
    messages.success(request, f"Pengajuan {nomor_pengajuan} berhasil dihapus.")
    if "/laporan/" in (request.META.get("HTTP_REFERER") or ""):
        return redirect("pemeliharaan:laporan")
    return redirect("pemeliharaan:list")
