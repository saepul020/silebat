from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.functions import Coalesce, ExtractYear
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.list_pagination import paginate_list
from apps.core.excel_utils import build_excel_response
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
from .forms import (
    PemeliharaanForm,
    PemeliharaanVendorForm,
    format_display_date,
    get_available_alat_queryset,
)
from .models import (
    ACTIVE_PEMELIHARAAN_STEPS,
    FINAL_PEMELIHARAAN_STEPS,
    JenisFotoPemeliharaanChoices,
    KeputusanPemeliharaanChoices,
    PemeliharaanPengajuan,
    PemeliharaanVendor,
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
REPORT_YEAR_ALL = "all"


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


def _can_input_vendor(user, obj):
    role_name = get_role_name(user)
    if (
        role_name not in PEMELIHARAAN_INPUT_ROLES
        or obj.current_step != StepPemeliharaanChoices.VENDOR_DRAFT
        or not obj.perlu_pimpinan
    ):
        return False
    return role_name == ROLE_SUPER_ADMIN or obj.pemohon_id == getattr(user, "id", None)


def _can_submit_vendor(user, obj):
    return _can_input_vendor(user, obj) and obj.has_vendor_data


def _get_pengajuan_queryset():
    return (
        PemeliharaanPengajuan.objects.select_related(
            "pemohon",
            "alat",
            "kepala_lab_by",
            "pimpinan_by",
            "vendor",
            "vendor__kepala_lab_by",
            "vendor__pimpinan_by",
        )
        .prefetch_related("items__fotos", "timeline_entries__actor")
        .order_by("-tanggal_pemeriksaan", "-id")
    )


def _get_report_queryset(user):
    queryset = _get_pengajuan_queryset().filter(current_step__in=FINAL_PEMELIHARAAN_STEPS)
    if get_role_name(user) not in PEMELIHARAAN_ADMIN_ROLES:
        queryset = queryset.filter(pemohon=user)
    return queryset.annotate(
        report_at=Coalesce(
            "vendor__pimpinan_at",
            "pimpinan_at",
            "kepala_lab_at",
            "updated_at",
        )
    )


def _get_report_year_options(queryset):
    current_year = timezone.localdate().year
    years = {current_year}
    db_years = (
        queryset.annotate(report_year=ExtractYear("report_at"))
        .values_list("report_year", flat=True)
        .distinct()
    )
    years.update(year for year in db_years if year)
    return sorted(years, reverse=True)


def _normalize_report_year_filter(raw_value, year_options):
    value = str(raw_value or "").strip().lower()
    if value == REPORT_YEAR_ALL:
        return REPORT_YEAR_ALL
    current_year = timezone.localdate().year
    if not value:
        return str(current_year)
    try:
        selected_year = int(value)
    except (TypeError, ValueError):
        return str(current_year)
    return str(selected_year) if selected_year in year_options else str(current_year)


def _filter_report_queryset_by_year(queryset, selected_year):
    if str(selected_year).lower() == REPORT_YEAR_ALL:
        return queryset
    try:
        return queryset.filter(report_at__year=int(selected_year))
    except (TypeError, ValueError):
        return queryset.filter(report_at__year=timezone.localdate().year)


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
        item.can_input_vendor = _can_input_vendor(request.user, item)
        item.can_submit_vendor = _can_submit_vendor(request.user, item)
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
    base_queryset = _get_report_queryset(request.user)
    report_year_options = _get_report_year_options(base_queryset)
    selected_report_year = _normalize_report_year_filter(
        request.GET.get("tahun"), report_year_options
    )
    queryset = _filter_report_queryset_by_year(base_queryset, selected_report_year)

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
            "show_report_year_filter": True,
            "report_year_options": report_year_options,
            "selected_report_year": selected_report_year,
            "report_year_aria_label": "Filter tahun laporan pemeliharaan",
        },
    )


@login_required
def export_laporan_pemeliharaan(request):
    if get_role_name(request.user) != ROLE_SUPER_ADMIN:
        return deny_access(
            request,
            "Fitur export laporan pemeliharaan hanya dapat diakses oleh Super Admin.",
        )

    export_queryset = _get_report_queryset(request.user)
    report_year_options = _get_report_year_options(export_queryset)
    selected_report_year = _normalize_report_year_filter(
        request.GET.get("tahun"), report_year_options
    )
    queryset = list(
        _filter_report_queryset_by_year(export_queryset, selected_report_year)
    )

    laporan_rows = []
    komponen_rows = []
    vendor_rows = []
    for obj in queryset:
        laporan_rows.append([
            obj.nomor_pengajuan,
            obj.tanggal_pemeriksaan,
            obj.report_at,
            obj.nama_pelaksana,
            obj.jabatan_pelaksana,
            obj.snapshot_nama_barang or "-",
            obj.snapshot_kode_laboratorium or "-",
            obj.snapshot_tipe_merek_barang or "-",
            obj.status_barang_label,
            obj.jenis_pengajuan_label,
            obj.kondisi_ringkas,
            obj.hasil_label,
            obj.status_label,
            getattr(obj.kepala_lab_by, "nama_lengkap", "") or getattr(obj.kepala_lab_by, "username", "") or "-",
            obj.get_kepala_lab_status_display(),
            obj.kepala_lab_note or "-",
            getattr(obj.pimpinan_by, "nama_lengkap", "") or getattr(obj.pimpinan_by, "username", "") or "-",
            obj.get_pimpinan_status_display(),
            obj.pimpinan_note or "-",
        ])

        for item in obj.items.all():
            photo_counts = {
                JenisFotoPemeliharaanChoices.PEMERIKSAAN: 0,
                JenisFotoPemeliharaanChoices.PERBAIKAN: 0,
                JenisFotoPemeliharaanChoices.KERUSAKAN: 0,
            }
            for foto in item.fotos.all():
                photo_counts[foto.jenis] = photo_counts.get(foto.jenis, 0) + 1
            komponen_rows.append([
                obj.nomor_pengajuan,
                item.komponen,
                item.get_kondisi_display(),
                item.get_tindakan_perbaikan_display() if item.tindakan_perbaikan else "-",
                item.uraian_perbaikan or "-",
                item.tanggal_mulai_perbaikan,
                item.tanggal_selesai_perbaikan,
                item.uraian_kerusakan or "-",
                photo_counts[JenisFotoPemeliharaanChoices.PEMERIKSAAN],
                photo_counts[JenisFotoPemeliharaanChoices.PERBAIKAN],
                photo_counts[JenisFotoPemeliharaanChoices.KERUSAKAN],
            ])

        vendor = getattr(obj, "vendor", None)
        if vendor:
            vendor_rows.append([
                obj.nomor_pengajuan,
                vendor.nama_vendor,
                vendor.nama_pic,
                vendor.nomor_hp_pic,
                vendor.alamat,
                vendor.tanggal_mulai,
                vendor.tanggal_selesai,
                vendor.get_kepala_lab_status_display(),
                vendor.kepala_lab_note or "-",
                vendor.get_pimpinan_status_display(),
                vendor.pimpinan_note or "-",
            ])

    return build_excel_response(
        "export_laporan_pemeliharaan.xlsx",
        [
            {
                "title": "Laporan Pemeliharaan",
                "headers": [
                    "Nomor Pengajuan", "Tanggal Pemeriksaan", "Tanggal Selesai",
                    "Pelaksana Pemeliharaan", "Jabatan", "Nama Alat",
                    "Kode Laboratorium", "Tipe / Merek", "Status Barang",
                    "Jenis", "Kondisi", "Hasil", "Proses",
                    "Kepala Lab", "Status Kepala Lab", "Catatan Kepala Lab",
                    "Pimpinan", "Status Pimpinan", "Catatan Pimpinan",
                ],
                "rows": laporan_rows,
            },
            {
                "title": "Detail Komponen",
                "headers": [
                    "Nomor Pengajuan", "Komponen", "Kondisi", "Tindakan Perbaikan",
                    "Uraian Perbaikan", "Mulai Perbaikan", "Selesai Perbaikan",
                    "Uraian Kerusakan", "Foto Pemeriksaan", "Foto Perbaikan",
                    "Foto Kerusakan",
                ],
                "rows": komponen_rows,
            },
            {
                "title": "Data Vendor",
                "headers": [
                    "Nomor Pengajuan", "Nama Vendor", "Nama PIC", "Nomor HP PIC",
                    "Alamat", "Tanggal Mulai", "Tanggal Selesai",
                    "Status Kepala Lab", "Catatan Kepala Lab", "Status Pimpinan",
                    "Catatan Pimpinan",
                ],
                "rows": vendor_rows,
            },
        ],
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
            "can_input_vendor": _can_input_vendor(request.user, obj),
            "can_submit_vendor": _can_submit_vendor(request.user, obj),
        },
    )


@login_required
def data_vendor(request, pk):
    obj = get_object_or_404(_get_pengajuan_queryset(), pk=pk)
    if not _can_input_vendor(request.user, obj):
        return deny_access(
            request,
            "Data vendor hanya dapat diisi oleh pelaksana pemeliharaan pada tahap Input Data Vendor.",
        )

    vendor = PemeliharaanVendor.objects.filter(pengajuan=obj).first()
    form = PemeliharaanVendorForm(
        request.POST or None,
        instance=vendor,
        pengajuan=obj,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            vendor = form.save(commit=False)
            vendor.pengajuan = obj
            vendor.kepala_lab_status = KeputusanPemeliharaanChoices.PENDING
            vendor.kepala_lab_by = None
            vendor.kepala_lab_at = None
            vendor.kepala_lab_note = ""
            vendor.pimpinan_status = KeputusanPemeliharaanChoices.PENDING
            vendor.pimpinan_by = None
            vendor.pimpinan_at = None
            vendor.pimpinan_note = ""
            vendor.submitted_at = None
            vendor.save()
            obj.add_timeline(
                "Pelaksana Pemeliharaan",
                "Data vendor perbaikan disimpan sebagai draft",
                request.user,
            )
        messages.success(request, "Data vendor perbaikan berhasil disimpan sebagai draft.")
        return redirect("pemeliharaan:detail", pk=obj.pk)

    _items, repair_items, _pemeriksaan_fotos = _prepare_detail_items(obj)
    return render(
        request,
        "pemeliharaan/vendor_form.html",
        {
            "obj": obj,
            "form": form,
            "external_items": [item for item in repair_items if item.is_eksternal],
            "page_title": "Data Vendor Perbaikan",
            "page_subtitle": "Lengkapi vendor pelaksana perbaikan eksternal dan simpan sebagai draft.",
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
def kirim_vendor(request, pk):
    if request.method != "POST":
        return redirect("pemeliharaan:detail", pk=pk)

    with transaction.atomic():
        obj = get_object_or_404(
            PemeliharaanPengajuan.objects.select_for_update()
            .prefetch_related("items"),
            pk=pk,
        )
        if not _can_submit_vendor(request.user, obj):
            return deny_access(
                request,
                "Data vendor belum lengkap atau Anda tidak memiliki akses untuk mengirimnya.",
            )

        vendor = get_object_or_404(
            PemeliharaanVendor.objects.select_for_update(),
            pengajuan=obj,
        )
        vendor.submitted_at = timezone.now()
        vendor.kepala_lab_status = KeputusanPemeliharaanChoices.PENDING
        vendor.kepala_lab_by = None
        vendor.kepala_lab_at = None
        vendor.kepala_lab_note = ""
        vendor.pimpinan_status = KeputusanPemeliharaanChoices.PENDING
        vendor.pimpinan_by = None
        vendor.pimpinan_at = None
        vendor.pimpinan_note = ""
        vendor.save()
        previous_step = obj.current_step
        obj.current_step = StepPemeliharaanChoices.VENDOR_KEPALA_LAB
        obj.save(update_fields=["current_step", "updated_at"])
        obj.add_timeline(
            "Pelaksana Pemeliharaan",
            "Data vendor perbaikan dikirim ke Kepala Lab",
            request.user,
        )
        sync_transaction_notifications(
            obj,
            actor=request.user,
            previous_current_step=previous_step,
        )

    messages.success(request, "Data vendor berhasil dikirim ke Kepala Lab untuk verifikasi.")
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
