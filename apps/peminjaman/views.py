from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.functions import ExtractYear
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.operasional.models import (
    SurveiKegiatan,
    format_ketua_tim_title,
    normalize_tim_kegiatan_name,
)

from apps.core.list_pagination import paginate_list
from apps.core.excel_utils import build_excel_response
from apps.core.permissions import (
    ROLE_ADMIN_LAB,
    ROLE_KEPALA_LAB,
    ROLE_PIMPINAN,
    ROLE_SUPER_ADMIN,
    ROLE_TEKNISI_LAB,
    ROLE_USER,
    deny_access,
    get_role_name,
)
from apps.notifikasi.services import sync_transaction_notifications
from apps.master_data.models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    PeralatanLaboratorium,
    KategoriBahanOperasionalChoices,
    KategoriBarangLaboratoriumChoices,
    KategoriBarangPenunjangChoices,
    KetersediaanChoices,
    StatusStokBahanChoices,
)

from .forms import (
    PENGAJUAN_CREATOR_ROLES,
    PeminjamanRequestForm,
)
from .models import (
    PeminjamanBahanOperasional,
    PeminjamanBarangLaboratorium,
    PeminjamanBarangPenunjang,
    PeminjamanPeralatanLaboratorium,
    PeminjamanRequest,
    ReturnStepChoices,
    StepChoices,
    build_asal_peminjaman_maps,
    resolve_asal_peminjaman_label,
)


SURVEI_TO_LAB_CATEGORY_MAP = {
    "borehole camera": {KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA},
    "drone rtk": {KategoriBarangLaboratoriumChoices.DRONE},
    "drone video": {KategoriBarangLaboratoriumChoices.DRONE},
    "geolistrik 1d": {KategoriBarangLaboratoriumChoices.GEOLISTRIK},
    "geolistrik 2d": {KategoriBarangLaboratoriumChoices.GEOLISTRIK},
    "kualitas air": {KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN},
    "debit air": {KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN},
    "mat (muka air tanah)": {KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN},
    "pumping test": {KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN},
    "topografi": {KategoriBarangLaboratoriumChoices.TOPOGRAFI_TS},
    "logging test": {KategoriBarangLaboratoriumChoices.LOGGING},
    "infiltrasi": {KategoriBarangLaboratoriumChoices.INFILTRASI},
}
ALWAYS_VISIBLE_LAB_CATEGORIES = {
    KategoriBarangLaboratoriumChoices.PENDUKUNG_SURVEI_LAPANGAN,
}
LAB_CATEGORY_DISPLAY_ORDER = [
    KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA,
    KategoriBarangLaboratoriumChoices.DRONE,
    KategoriBarangLaboratoriumChoices.GEOLISTRIK,
    KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN,
    KategoriBarangLaboratoriumChoices.TOPOGRAFI_TS,
    KategoriBarangLaboratoriumChoices.LOGGING,
    KategoriBarangLaboratoriumChoices.INFILTRASI,
    KategoriBarangLaboratoriumChoices.PENDUKUNG_SURVEI_LAPANGAN,
]
LAB_CATEGORY_ORDER_INDEX = {
    category: index for index, category in enumerate(LAB_CATEGORY_DISPLAY_ORDER)
}
PENUNJANG_CATEGORY_DISPLAY_ORDER = [
    KategoriBarangPenunjangChoices.ALAT_SURVEI,
    KategoriBarangPenunjangChoices.LAPANGAN,
    KategoriBarangPenunjangChoices.K3,
]
PENUNJANG_CATEGORY_ORDER_INDEX = {
    category: index for index, category in enumerate(PENUNJANG_CATEGORY_DISPLAY_ORDER)
}
BAHAN_CATEGORY_DISPLAY_ORDER = [
    KategoriBahanOperasionalChoices.BAHAN_LABORATORIUM,
    KategoriBahanOperasionalChoices.BAHAN_LAPANGAN,
    KategoriBahanOperasionalChoices.SUKU_CADANG,
]
BAHAN_CATEGORY_ORDER_INDEX = {
    category: index for index, category in enumerate(BAHAN_CATEGORY_DISPLAY_ORDER)
}


def _group_items_by_category(items, category_order_index=None):
    category_order_index = category_order_index or {}
    sorted_items = sorted(
        items,
        key=lambda item: (
            category_order_index.get(
                getattr(item, "kategori_barang", None), len(category_order_index)
            ),
            getattr(item, "kategori_barang", "") or "",
            getattr(item, "nama_barang", "") or "",
        ),
    )
    groups = []
    for item in sorted_items:
        kategori_barang = getattr(item, "kategori_barang", None) or "Tanpa Kategori"
        if not groups or groups[-1]["kategori_barang"] != kategori_barang:
            groups.append({"kategori_barang": kategori_barang, "items": []})
        groups[-1]["items"].append(item)
    return groups


def _normalize_survei_label(value):
    return " ".join(str(value or "").strip().lower().split())


def _get_lab_categories_for_survei_labels(labels):
    categories = set(ALWAYS_VISIBLE_LAB_CATEGORIES)
    for label in labels or []:
        categories.update(
            SURVEI_TO_LAB_CATEGORY_MAP.get(_normalize_survei_label(label), set())
        )
    return categories


def _get_survei_labels_from_post(post_data):
    selected_ids = []
    for raw_id in post_data.getlist("kegiatan_survei"):
        try:
            selected_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue
    if not selected_ids:
        return []
    return list(
        SurveiKegiatan.objects.filter(pk__in=selected_ids).values_list(
            "jenis_survei", flat=True
        )
    )


def _get_survei_labels_from_obj(obj):
    if not obj or not getattr(obj, "pk", None):
        return []
    return list(obj.kegiatan_survei.values_list("jenis_survei", flat=True))


MONTH_NAMES_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


def format_date_id(value):
    if not value:
        return "-"
    return (
        f"{value.day:02d} {MONTH_NAMES_ID.get(value.month, value.month)} {value.year}"
    )


def format_optional_numeric_display(value):
    if value is None:
        return "-"
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return "-"
        try:
            numeric_value = Decimal(stripped)
        except (InvalidOperation, ValueError):
            return value
        return "-" if numeric_value == 0 else value
    if isinstance(value, (int, float, Decimal)):
        return "-" if Decimal(str(value)) == 0 else value
    return value


def _normalize_report_tim_kegiatan(snapshot):
    if not isinstance(snapshot, dict):
        return snapshot
    kegiatan = snapshot.get("kegiatan")
    if isinstance(kegiatan, dict):
        kegiatan["tim_kegiatan"] = (
            normalize_tim_kegiatan_name(kegiatan.get("tim_kegiatan")) or "-"
        )
    return snapshot


def _can_view_pengajuan(user, obj):
    role_name = get_role_name(user)
    if role_name in {
        ROLE_SUPER_ADMIN,
        ROLE_ADMIN_LAB,
        ROLE_TEKNISI_LAB,
        ROLE_KEPALA_LAB,
        ROLE_PIMPINAN,
    }:
        return True
    return obj.peminjam_id == user.id


def _can_create_pengajuan(user):
    return get_role_name(user) in PENGAJUAN_CREATOR_ROLES


def _can_delete_pengajuan(user):
    return get_role_name(user) == ROLE_SUPER_ADMIN


def _can_edit_pengajuan(user, obj):
    return (
        get_role_name(user) in {ROLE_SUPER_ADMIN, ROLE_TEKNISI_LAB}
        and obj.current_step == StepChoices.TEKNISI_LAB
        and obj.return_current_step == ReturnStepChoices.NONE
    )


def _get_current_booking_state(obj):
    if not obj or not getattr(obj, "aset_sudah_dialokasikan", False):
        return {
            "lab_ids": set(),
            "penunjang_qty": {},
            "peralatan_lab_qty": {},
            "bahan_qty": {},
        }

    return {
        "lab_ids": {
            item.barang_id
            for item in obj.barang_laboratorium_items.all()
            if item.barang_id
        },
        "penunjang_qty": {
            item.barang_id: item.volume
            for item in obj.barang_penunjang_items.all()
            if item.barang_id
        },
        "peralatan_lab_qty": {
            item.barang_id: item.volume
            for item in obj.peralatan_laboratorium_items.all()
            if item.barang_id
        },
        "bahan_qty": {
            item.bahan_id: item.volume
            for item in obj.bahan_operasional_items.all()
            if item.bahan_id
        },
    }


def _get_validation_messages(error):
    messages_list = getattr(error, "messages", None)
    if messages_list:
        return list(messages_list)
    return [str(error)]


def _mark_quantity_item_selection(item, selected_qty, current_reserved_qty, base_available_qty):
    item.selected_qty = selected_qty
    item.available_stock = max((base_available_qty or 0) + (current_reserved_qty or 0), 0)
    item.is_available_for_selection = item.available_stock > 0
    item.selection_ketersediaan = (
        KetersediaanChoices.TERSEDIA
        if item.is_available_for_selection
        else KetersediaanChoices.TIDAK_TERSEDIA
    )
    item.selection_status_badge_class = (
        "badge-success" if item.is_available_for_selection else "badge-danger"
    )


def _build_inventory_context(selection=None, survei_labels=None, current_obj=None):
    selection = selection or {}
    selected_lab_ids = set(selection.get("lab_ids") or [])
    selected_penunjang_qty = selection.get("penunjang_qty") or {}
    selected_bahan_qty = selection.get("bahan_qty") or {}
    selected_peralatan_lab_qty = selection.get("peralatan_lab_qty") or {}
    current_booking = _get_current_booking_state(current_obj)
    visible_lab_categories = _get_lab_categories_for_survei_labels(survei_labels)

    lab_items = list(
        BarangLaboratorium.objects.order_by("kategori_barang", "nama_barang")
    )
    penunjang_items = list(
        BarangPenunjangOperasional.objects.order_by("kategori_barang", "nama_barang")
    )
    peralatan_lab_items = list(PeralatanLaboratorium.objects.order_by("nama_barang"))
    bahan_items = list(
        BahanOperasional.objects.order_by("kategori_barang", "nama_barang")
    )

    for item in lab_items:
        is_booked_by_current = item.id in current_booking["lab_ids"]
        item.is_selected = item.id in selected_lab_ids
        item.is_available_for_selection = (
            item.ketersediaan == KetersediaanChoices.TERSEDIA or is_booked_by_current
        )
        item.selection_ketersediaan = (
            KetersediaanChoices.TERSEDIA
            if item.is_available_for_selection
            else KetersediaanChoices.TIDAK_TERSEDIA
        )
        item.selection_status_badge_class = (
            "badge-success" if item.is_available_for_selection else "badge-danger"
        )
        item.is_visible_by_survey = (
            item.kategori_barang in visible_lab_categories or item.is_selected
        )

    lab_items.sort(
        key=lambda item: (
            LAB_CATEGORY_ORDER_INDEX.get(
                item.kategori_barang, len(LAB_CATEGORY_ORDER_INDEX)
            ),
            item.kategori_barang or "",
            item.nama_barang or "",
        )
    )
    lab_item_groups = []
    for item in lab_items:
        kategori_barang = item.kategori_barang or "Tanpa Kategori"
        if (
            not lab_item_groups
            or lab_item_groups[-1]["kategori_barang"] != kategori_barang
        ):
            lab_item_groups.append(
                {
                    "kategori_barang": kategori_barang,
                    "items": [],
                    "is_visible": False,
                }
            )
        lab_item_groups[-1]["items"].append(item)
        if item.is_visible_by_survey:
            lab_item_groups[-1]["is_visible"] = True

    for item in penunjang_items:
        _mark_quantity_item_selection(
            item,
            selected_penunjang_qty.get(item.id, 0),
            current_booking["penunjang_qty"].get(item.id, 0),
            item.sisa_volume,
        )

    for item in peralatan_lab_items:
        _mark_quantity_item_selection(
            item,
            selected_peralatan_lab_qty.get(item.id, 0),
            current_booking["peralatan_lab_qty"].get(item.id, 0),
            item.sisa_volume,
        )

    for item in bahan_items:
        item.selected_qty = selected_bahan_qty.get(item.id, 0)
        current_reserved_qty = current_booking["bahan_qty"].get(item.id, 0)
        item.available_stock = max((item.volume or 0) + current_reserved_qty, 0)
        item.is_available_for_selection = item.available_stock > 0
        if item.is_available_for_selection and item.ketersediaan == StatusStokBahanChoices.HABIS:
            item.selection_ketersediaan = "Tersedia"
            item.selection_status_badge_class = "badge-success"
        else:
            item.selection_ketersediaan = (
                item.ketersediaan if item.is_available_for_selection else StatusStokBahanChoices.HABIS
            )
            item.selection_status_badge_class = (
                item.status_badge_class if item.is_available_for_selection else "badge-danger"
            )

    penunjang_item_groups = _group_items_by_category(
        penunjang_items, PENUNJANG_CATEGORY_ORDER_INDEX
    )
    bahan_item_groups = _group_items_by_category(
        bahan_items, BAHAN_CATEGORY_ORDER_INDEX
    )

    return {
        "lab_items": lab_items,
        "lab_item_groups": lab_item_groups,
        "penunjang_items": penunjang_items,
        "penunjang_item_groups": penunjang_item_groups,
        "peralatan_lab_items": peralatan_lab_items,
        "bahan_items": bahan_items,
        "bahan_item_groups": bahan_item_groups,
        "visible_lab_categories": visible_lab_categories,
    }


def _build_selection_state_from_obj(obj):
    return {
        "lab_ids": {item.barang_id for item in obj.barang_laboratorium_items.all()},
        "penunjang_qty": {
            item.barang_id: item.volume for item in obj.barang_penunjang_items.all()
        },
        "peralatan_lab_qty": {
            item.barang_id: item.volume
            for item in obj.peralatan_laboratorium_items.all()
        },
        "bahan_qty": {
            item.bahan_id: item.volume for item in obj.bahan_operasional_items.all()
        },
    }


def _extract_selection_state(post_data):
    selected_lab_ids = set()
    selected_penunjang_qty = {}
    selected_bahan_qty = {}
    selected_peralatan_lab_qty = {}

    for raw_id in post_data.getlist("lab_item_ids"):
        try:
            selected_lab_ids.add(int(raw_id))
        except (TypeError, ValueError):
            continue

    for key, value in post_data.items():
        value = (value or "").strip()
        if key.startswith("penunjang_qty_"):
            try:
                item_id = int(key.replace("penunjang_qty_", ""))
            except ValueError:
                continue
            try:
                selected_penunjang_qty[item_id] = max(int(value or 0), 0)
            except ValueError:
                selected_penunjang_qty[item_id] = value or 0

        if key.startswith("peralatan_lab_qty_"):
            try:
                item_id = int(key.replace("peralatan_lab_qty_", ""))
            except ValueError:
                continue
            try:
                selected_peralatan_lab_qty[item_id] = max(int(value or 0), 0)
            except ValueError:
                selected_peralatan_lab_qty[item_id] = value or 0

        if key.startswith("bahan_qty_"):
            try:
                item_id = int(key.replace("bahan_qty_", ""))
            except ValueError:
                continue
            try:
                selected_bahan_qty[item_id] = max(int(value or 0), 0)
            except ValueError:
                selected_bahan_qty[item_id] = value or 0

    return {
        "lab_ids": selected_lab_ids,
        "penunjang_qty": selected_penunjang_qty,
        "peralatan_lab_qty": selected_peralatan_lab_qty,
        "bahan_qty": selected_bahan_qty,
    }


def _replace_pengajuan_items(
    pengajuan, selected_lab, selected_penunjang, selected_peralatan_lab, selected_bahan
):
    pengajuan.barang_laboratorium_items.all().delete()
    pengajuan.barang_penunjang_items.all().delete()
    pengajuan.peralatan_laboratorium_items.all().delete()
    pengajuan.bahan_operasional_items.all().delete()

    lab_objects = [
        PeminjamanBarangLaboratorium(pengajuan=pengajuan, barang=item)
        for item in selected_lab
    ]
    for item_obj in lab_objects:
        item_obj.sync_snapshot_from_master()
    PeminjamanBarangLaboratorium.objects.bulk_create(lab_objects)

    penunjang_objects = [
        PeminjamanBarangPenunjang(pengajuan=pengajuan, barang=item, volume=qty)
        for item, qty in selected_penunjang
    ]
    for item_obj in penunjang_objects:
        item_obj.sync_snapshot_from_master()
    PeminjamanBarangPenunjang.objects.bulk_create(penunjang_objects)

    peralatan_lab_objects = [
        PeminjamanPeralatanLaboratorium(pengajuan=pengajuan, barang=item, volume=qty)
        for item, qty in selected_peralatan_lab
    ]
    for item_obj in peralatan_lab_objects:
        item_obj.sync_snapshot_from_master()
    PeminjamanPeralatanLaboratorium.objects.bulk_create(peralatan_lab_objects)

    bahan_objects = [
        PeminjamanBahanOperasional(pengajuan=pengajuan, bahan=item, volume=qty)
        for item, qty in selected_bahan
    ]
    for item_obj in bahan_objects:
        item_obj.sync_snapshot_from_master()
    PeminjamanBahanOperasional.objects.bulk_create(bahan_objects)


def _attach_asal_peminjaman_labels(
    obj,
    lab_items=None,
    penunjang_items=None,
    peralatan_lab_items=None,
    bahan_items=None,
):
    asal_maps = build_asal_peminjaman_maps(obj)
    for item in lab_items or []:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "lab", item.barang_id
        )
    for item in penunjang_items or []:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "penunjang", item.barang_id, getattr(item, "volume", 0)
        )
    for item in peralatan_lab_items or []:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "peralatan_lab", item.barang_id, getattr(item, "volume", 0)
        )
    for item in bahan_items or []:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "bahan", item.bahan_id, getattr(item, "volume", 0)
        )
    return asal_maps


def _get_pengajuan_base_queryset():
    return PeminjamanRequest.objects.select_related(
        "peminjam",
        "layanan_kegiatan",
        "tim_kegiatan",
        "instansi_tujuan",
    ).prefetch_related(
        "pengembalian_lab_items",
        "pengembalian_penunjang_items",
        "pengembalian_peralatan_laboratorium_items",
        "pengembalian_bahan_items",
    )


def _get_pengajuan_list_queryset(user, *, is_report=False):
    items = _get_pengajuan_base_queryset()
    if get_role_name(user) == ROLE_USER:
        items = items.filter(peminjam=user)
    if is_report:
        return items.filter(return_current_step=ReturnStepChoices.COMPLETED)
    return items.exclude(return_current_step=ReturnStepChoices.COMPLETED)


def _parse_selected_items(post_data, survei_labels=None, current_obj=None):
    errors = []
    allowed_lab_categories = _get_lab_categories_for_survei_labels(survei_labels)
    current_booking = _get_current_booking_state(current_obj)
    selected_lab = []
    selected_penunjang = []
    selected_bahan = []
    selected_peralatan_lab = []

    lab_map = {item.id: item for item in BarangLaboratorium.objects.all()}
    for raw_id in post_data.getlist("lab_item_ids"):
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        item = lab_map.get(item_id)
        if not item:
            continue
        if item.kategori_barang not in allowed_lab_categories:
            errors.append(
                f'Barang laboratorium "{item.nama_barang}" tidak sesuai dengan pilihan Kegiatan Survei.'
            )
            continue
        is_booked_by_current = item.id in current_booking["lab_ids"]
        if item.ketersediaan != KetersediaanChoices.TERSEDIA and not is_booked_by_current:
            errors.append(
                f'Barang laboratorium "{item.nama_barang}" sudah dibooking/dipinjam dan tidak tersedia untuk dipinjam.'
            )
            continue
        selected_lab.append(item)

    for item in BarangPenunjangOperasional.objects.all().order_by("nama_barang"):
        raw_qty = (post_data.get(f"penunjang_qty_{item.id}") or "").strip()
        if not raw_qty:
            continue
        try:
            qty = int(raw_qty)
        except ValueError:
            errors.append(
                f'Volume barang penunjang "{item.nama_barang}" harus berupa angka.'
            )
            continue
        if qty <= 0:
            continue
        available_stock = item.sisa_volume + current_booking["penunjang_qty"].get(item.id, 0)
        if available_stock <= 0:
            errors.append(
                f'Barang penunjang "{item.nama_barang}" sudah habis/dibooking dan tidak tersedia untuk dipinjam.'
            )
            continue
        if qty > available_stock:
            errors.append(
                f'Volume barang penunjang "{item.nama_barang}" tidak boleh lebih besar dari stok tersedia ({available_stock}).'
            )
            continue
        selected_penunjang.append((item, qty))

    for item in PeralatanLaboratorium.objects.all().order_by("nama_barang"):
        raw_qty = (post_data.get(f"peralatan_lab_qty_{item.id}") or "").strip()
        if not raw_qty:
            continue
        try:
            qty = int(raw_qty)
        except ValueError:
            errors.append(
                f'Volume peralatan laboratorium "{item.nama_barang}" harus berupa angka.'
            )
            continue
        if qty <= 0:
            continue
        available_stock = item.sisa_volume + current_booking["peralatan_lab_qty"].get(item.id, 0)
        if available_stock <= 0:
            errors.append(
                f'Peralatan laboratorium "{item.nama_barang}" sudah habis/dibooking dan tidak tersedia untuk dipinjam.'
            )
            continue
        if qty > available_stock:
            errors.append(
                f'Volume peralatan laboratorium "{item.nama_barang}" tidak boleh lebih besar dari stok tersedia ({available_stock}).'
            )
            continue
        selected_peralatan_lab.append((item, qty))

    for item in BahanOperasional.objects.all().order_by("nama_barang"):
        raw_qty = (post_data.get(f"bahan_qty_{item.id}") or "").strip()
        if not raw_qty:
            continue
        try:
            qty = int(raw_qty)
        except ValueError:
            errors.append(
                f'Volume bahan operasional "{item.nama_barang}" harus berupa angka.'
            )
            continue
        if qty <= 0:
            continue
        available_stock = (item.volume or 0) + current_booking["bahan_qty"].get(item.id, 0)
        if available_stock <= 0:
            errors.append(
                f'Bahan operasional "{item.nama_barang}" sedang habis/dibooking dan tidak bisa dipinjam.'
            )
            continue
        if qty > available_stock:
            errors.append(
                f'Volume bahan operasional "{item.nama_barang}" tidak boleh lebih besar dari stok tersedia ({available_stock}).'
            )
            continue
        selected_bahan.append((item, qty))

    if not any(
        [selected_lab, selected_penunjang, selected_peralatan_lab, selected_bahan]
    ):
        errors.append(
            "Pilih minimal satu barang atau bahan operasional untuk diajukan."
        )

    return (
        selected_lab,
        selected_penunjang,
        selected_peralatan_lab,
        selected_bahan,
        errors,
    )


@login_required
def index(request):
    return redirect("peminjaman:list")


@login_required
def daftar_pengajuan(request):
    queryset = _get_pengajuan_list_queryset(request.user, is_report=False)
    pagination_context = paginate_list(request, queryset)
    role_name = get_role_name(request.user)

    context = {
        "items": pagination_context["items"],
        "page_title": "Permintaan Peminjaman",
        "page_subtitle": "Kelola seluruh pengajuan peminjaman yang masih aktif.",
        "can_add": _can_create_pengajuan(request.user),
        "can_delete": _can_delete_pengajuan(request.user),
        "can_access_pengembalian": role_name
        in {ROLE_SUPER_ADMIN, ROLE_ADMIN_LAB, ROLE_TEKNISI_LAB, ROLE_USER},
        "is_report": False,
    }
    context.update(pagination_context)
    return render(request, "peminjaman/pengajuan_list.html", context)


def _get_report_year_options(queryset):
    current_year = timezone.localdate().year
    years = {current_year}
    db_years = (
        queryset.exclude(return_completed_at__isnull=True)
        .annotate(report_year=ExtractYear("return_completed_at"))
        .values_list("report_year", flat=True)
        .distinct()
    )
    years.update(year for year in db_years if year)
    return sorted(years, reverse=True)


def _normalize_report_year_filter(raw_value, year_options):
    value = str(raw_value or "").strip().lower()
    if value == "all":
        return "all"

    current_year = timezone.localdate().year
    if not value:
        return str(current_year)

    try:
        selected_year = int(value)
    except (TypeError, ValueError):
        return str(current_year)

    if selected_year in year_options:
        return str(selected_year)
    return str(current_year)


def _filter_report_queryset_by_year(queryset, selected_year):
    if str(selected_year).lower() == "all":
        return queryset
    try:
        return queryset.filter(return_completed_at__year=int(selected_year))
    except (TypeError, ValueError):
        return queryset.filter(return_completed_at__year=timezone.localdate().year)


@login_required
def laporan_peminjaman(request):
    base_queryset = _get_pengajuan_list_queryset(request.user, is_report=True)
    report_year_options = _get_report_year_options(base_queryset)
    selected_report_year = _normalize_report_year_filter(request.GET.get("tahun"), report_year_options)
    queryset = _filter_report_queryset_by_year(base_queryset, selected_report_year)
    pagination_context = paginate_list(request, queryset)

    context = {
        "items": pagination_context["items"],
        "page_title": "Laporan Peminjaman",
        "page_subtitle": "Riwayat peminjaman yang sudah selesai proses pengembalian.",
        "can_add": False,
        "can_delete": _can_delete_pengajuan(request.user),
        "can_access_pengembalian": get_role_name(request.user)
        in {
            ROLE_SUPER_ADMIN,
            ROLE_ADMIN_LAB,
            ROLE_TEKNISI_LAB,
            ROLE_KEPALA_LAB,
            ROLE_PIMPINAN,
            ROLE_USER,
        },
        "is_report": True,
        "show_report_year_filter": True,
        "report_year_options": report_year_options,
        "selected_report_year": selected_report_year,
    }
    context.update(pagination_context)
    return render(request, "peminjaman/pengajuan_list.html", context)




def _export_transfer_target_number(item):
    target = getattr(item, "transfer_target", None)
    return getattr(target, "nomor_pengajuan", "") or "-"


def _export_survei_labels(obj):
    labels = [item.jenis_survei for item in obj.kegiatan_survei.all()]
    return "; ".join(labels) if labels else "-"


def _export_instansi_name(obj):
    if obj.instansi_tujuan_lainnya:
        return obj.instansi_tujuan_lainnya
    return str(obj.instansi_tujuan) if obj.instansi_tujuan else "-"


def _export_layanan_name(obj):
    return obj.layanan_kegiatan_label


def _export_tim_name(obj):
    return normalize_tim_kegiatan_name(obj.tim_kegiatan) if obj.tim_kegiatan else "-"


def _export_report_queryset(user):
    return (
        _get_pengajuan_list_queryset(user, is_report=True)
        .prefetch_related("kegiatan_survei")
        .order_by("-return_completed_at", "-submitted_at", "-id")
    )


@login_required
def export_laporan_peminjaman(request):
    if get_role_name(request.user) != ROLE_SUPER_ADMIN:
        return deny_access(request, "Fitur export laporan peminjaman hanya dapat diakses oleh Super Admin.")

    export_queryset = _export_report_queryset(request.user)
    report_year_options = _get_report_year_options(export_queryset)
    selected_report_year = _normalize_report_year_filter(request.GET.get("tahun"), report_year_options)
    queryset = list(_filter_report_queryset_by_year(export_queryset, selected_report_year))

    peminjaman_rows = []
    lab_rows = []
    penunjang_rows = []
    bahan_rows = []
    peralatan_lab_rows = []

    for obj in queryset:
        peminjaman_rows.append([
            obj.nomor_pengajuan,
            obj.peminjam.username if obj.peminjam else "-",
            obj.nama_peminjam,
            obj.no_hp_peminjam,
            obj.email_peminjam,
            obj.nip_peminjam,
            obj.alamat_peminjam,
            _export_layanan_name(obj),
            _export_tim_name(obj),
            _export_instansi_name(obj),
            getattr(obj.instansi_tujuan, "organisasi", "") or "-",
            obj.tanggal_mulai,
            obj.tanggal_selesai,
            obj.return_completed_at,
            obj.total_hari,
            _export_survei_labels(obj),
            obj.survei_lainnya or "-",
            format_optional_numeric_display(obj.titik_geolistrik_1d),
            format_optional_numeric_display(obj.lintasan_geolistrik_2d),
            format_optional_numeric_display(obj.titik_kualitas_air),
            format_optional_numeric_display(obj.titik_mat),
            format_optional_numeric_display(obj.titik_pumping_test),
            format_optional_numeric_display(obj.titik_infiltrasi),
            format_optional_numeric_display(obj.titik_debit_air),
            format_optional_numeric_display(obj.lokasi_topografi),
            format_optional_numeric_display(obj.titik_borehole),
            format_optional_numeric_display(obj.titik_logging),
            obj.get_current_step_display(),
            obj.get_return_current_step_display(),
        ])

        for item in obj.pengembalian_lab_items.all():
            lab_rows.append([
                obj.nomor_pengajuan,
                item.snapshot_nama_barang,
                item.snapshot_tipe_merek_barang,
                item.snapshot_jenis_barang,
                item.snapshot_status_barang,
                item.snapshot_kode_aset_bmn,
                item.snapshot_kode_laboratorium,
                item.snapshot_volume,
                item.snapshot_satuan,
                item.snapshot_kondisi_barang,
                item.snapshot_tahun_perolehan,
                item.get_status_display(),
                _export_transfer_target_number(item),
                item.note,
            ])

        for item in obj.pengembalian_penunjang_items.all():
            penunjang_rows.append([
                obj.nomor_pengajuan,
                item.snapshot_nama_barang,
                item.snapshot_tipe_merek_barang,
                item.snapshot_kategori_barang,
                item.snapshot_satuan,
                item.qty_dikembalikan,
                item.qty_rusak,
                item.qty_hilang,
                item.qty_transfer,
                item.total_processed,
                _export_transfer_target_number(item),
                item.note,
            ])

        for item in obj.pengembalian_bahan_items.all():
            bahan_rows.append([
                obj.nomor_pengajuan,
                item.snapshot_nama_barang,
                item.snapshot_kategori_barang,
                item.snapshot_satuan,
                item.qty_sisa,
                item.qty_transfer,
                item.total_processed,
                _export_transfer_target_number(item),
                item.note,
            ])

        for item in obj.pengembalian_peralatan_laboratorium_items.all():
            peralatan_lab_rows.append([
                obj.nomor_pengajuan,
                item.snapshot_nama_barang,
                item.snapshot_tipe_merek_barang,
                item.snapshot_jenis_barang,
                item.snapshot_status_barang,
                item.snapshot_kode_aset_bmn,
                item.snapshot_kode_laboratorium,
                item.snapshot_volume,
                item.snapshot_satuan,
                item.snapshot_kondisi_barang,
                item.snapshot_tahun_perolehan,
                item.qty_dikembalikan,
                item.qty_rusak,
                item.qty_hilang,
                item.qty_transfer,
                item.total_processed,
                _export_transfer_target_number(item),
                item.note,
            ])

    return build_excel_response(
        "export_laporan_peminjaman.xlsx",
        [
            {
                "title": "Peminjaman",
                "headers": [
                    "Nomor Pengajuan",
                    "Username Peminjam",
                    "Nama Peminjam",
                    "Nomor Telepon",
                    "Email",
                    "NIP / NIK",
                    "Alamat",
                    "Layanan Kegiatan",
                    "Tim Kegiatan",
                    "Instansi Tujuan",
                    "Organisasi Instansi",
                    "Tanggal Mulai",
                    "Tanggal Selesai",
                    "Tanggal Pengembalian",
                    "Total Hari",
                    "Kegiatan Survei",
                    "Survei Lainnya",
                    "Titik Geolistrik 1D",
                    "Lintasan Geolistrik 2D",
                    "Titik Kualitas Air",
                    "Titik MAT",
                    "Titik Pumping Test",
                    "Titik Infiltrasi",
                    "Titik Debit Air",
                    "Lokasi Topografi",
                    "Titik Borehole Camera",
                    "Titik Logging",
                    "Proses Peminjaman",
                    "Proses Pengembalian",
                ],
                "rows": peminjaman_rows,
            },
            {
                "title": "Peralatan Survei",
                "headers": [
                    "Nomor Pengajuan",
                    "Nama Barang",
                    "Tipe / Merek Barang",
                    "Jenis Barang",
                    "Status Barang",
                    "Kode Aset BMN",
                    "Kode Laboratorium",
                    "Volume",
                    "Satuan",
                    "Kondisi Barang",
                    "Tahun Perolehan",
                    "Status Pengembalian",
                    "Tujuan Transfer",
                    "Catatan Pengembalian",
                ],
                "rows": lab_rows,
            },
            {
                "title": "Barang Penunjang",
                "headers": [
                    "Nomor Pengajuan",
                    "Nama Barang",
                    "Tipe / Merek Barang",
                    "Kategori Barang",
                    "Satuan",
                    "Dikembalikan",
                    "Rusak",
                    "Hilang",
                    "Transfer",
                    "Total Diproses",
                    "Tujuan Transfer",
                    "Catatan Pengembalian",
                ],
                "rows": penunjang_rows,
            },
            {
                "title": "Bahan Operasional",
                "headers": [
                    "Nomor Pengajuan",
                    "Nama Barang",
                    "Kategori Barang",
                    "Satuan",
                    "Sisa",
                    "Transfer",
                    "Total Diproses",
                    "Tujuan Transfer",
                    "Catatan Pengembalian",
                ],
                "rows": bahan_rows,
            },
            {
                "title": "Peralatan Lab",
                "headers": [
                    "Nomor Pengajuan",
                    "Nama Barang",
                    "Tipe / Merek Barang",
                    "Jenis Barang",
                    "Status Barang",
                    "Kode Aset BMN",
                    "Kode Laboratorium",
                    "Volume",
                    "Satuan",
                    "Kondisi Barang",
                    "Tahun Perolehan",
                    "Dikembalikan",
                    "Rusak",
                    "Hilang",
                    "Transfer",
                    "Total Diproses",
                    "Tujuan Transfer",
                    "Catatan Pengembalian",
                ],
                "rows": peralatan_lab_rows,
            },
        ],
    )

def _get_peminjam_display_data(user):
    if not user:
        return {
            "id": "",
            "nama": "-",
            "no_hp": "-",
            "email": "-",
            "alamat": "-",
        }

    profile = user.safe_profile
    return {
        "id": str(user.pk),
        "nama": user.get_full_name() or user.username or "-",
        "no_hp": user.no_hp or "-",
        "email": user.email or "-",
        "alamat": profile.alamat or "-",
    }


def _get_selected_form_peminjam(form, fallback_user):
    if not form or "peminjam_user" not in form.fields:
        return fallback_user

    selected_user = None
    if getattr(form, "is_bound", False):
        raw_user_id = form.data.get(form.add_prefix("peminjam_user"))
        if raw_user_id:
            selected_user = form.fields["peminjam_user"].queryset.filter(pk=raw_user_id).first()
    else:
        initial_user = form.initial.get("peminjam_user") or form.fields["peminjam_user"].initial
        if initial_user:
            selected_user = form.fields["peminjam_user"].queryset.filter(pk=getattr(initial_user, "pk", initial_user)).first()

    return selected_user


def _build_peminjam_select_context(form, fallback_user):
    can_select = bool(form and "peminjam_user" in form.fields)
    selected_user = _get_selected_form_peminjam(form, fallback_user)
    selectable_users = []

    if can_select:
        selectable_users = [
            _get_peminjam_display_data(user)
            for user in form.fields["peminjam_user"].queryset
        ]

    return {
        "can_select_peminjam": can_select,
        "selected_peminjam_data": _get_peminjam_display_data(selected_user),
        "peminjam_options_data": selectable_users,
    }


def _apply_peminjam_snapshot(pengajuan, peminjam):
    profile = peminjam.safe_profile
    pengajuan.peminjam = peminjam
    pengajuan.nama_peminjam = peminjam.get_full_name() or peminjam.username
    pengajuan.no_hp_peminjam = peminjam.no_hp or ""
    pengajuan.email_peminjam = peminjam.email or ""
    pengajuan.alamat_peminjam = profile.alamat or ""
    pengajuan.nip_peminjam = peminjam.nip or ""


@login_required
def tambah_pengajuan(request):
    if not _can_create_pengajuan(request.user):
        return deny_access(
            request, 'Hanya role User, Admin Lab, Teknisi Lab, dan Super Admin yang dapat membuat pengajuan peminjaman baru.'
        )

    selection_state = (
        _extract_selection_state(request.POST) if request.method == "POST" else None
    )
    selected_survei_labels = (
        _get_survei_labels_from_post(request.POST) if request.method == "POST" else []
    )
    inventory_context = _build_inventory_context(
        selection_state, selected_survei_labels
    )

    inventory_form_errors = []

    if request.method == "POST":
        form = PeminjamanRequestForm(request.POST, request.FILES, actor=request.user)
        (
            selected_lab,
            selected_penunjang,
            selected_peralatan_lab,
            selected_bahan,
            item_errors,
        ) = _parse_selected_items(request.POST, selected_survei_labels)
        inventory_form_errors = item_errors

        if form.is_valid() and not item_errors:
            try:
                with transaction.atomic():
                    peminjam = form.cleaned_data.get("peminjam_user") or request.user
                    pengajuan = form.save(commit=False)
                    _apply_peminjam_snapshot(pengajuan, peminjam)
                    pengajuan.current_step = StepChoices.ADMIN_LAB
                    pengajuan.save()
                    form.save_m2m()

                    _replace_pengajuan_items(
                        pengajuan,
                        selected_lab,
                        selected_penunjang,
                        selected_peralatan_lab,
                        selected_bahan,
                    )
                    pengajuan.apply_inventory_allocation()
                    pengajuan.add_timeline("Pengajuan", "Pengajuan dibuat dan stok dibooking", request.user)
                    sync_transaction_notifications(pengajuan, actor=request.user)
            except ValidationError as exc:
                inventory_form_errors = _get_validation_messages(exc)
            else:
                messages.success(
                    request,
                    "Pengajuan peminjaman berhasil dibuat, stok sudah dibooking, dan dikirim ke Admin Lab.",
                )
                return redirect("peminjaman:detail", pk=pengajuan.pk)

    else:
        form = PeminjamanRequestForm(actor=request.user)

    return render(
        request,
        "peminjaman/pengajuan_form.html",
        {
            "form": form,
            "page_title": "Tambah Pengajuan Peminjaman",
            "page_subtitle": "Lengkapi data kegiatan dan pilih aset yang akan diajukan untuk dipinjam.",
            "inventory_form_errors": inventory_form_errors,
            **_build_peminjam_select_context(form, request.user),
            **inventory_context,
        },
    )


@login_required
def edit_pengajuan(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "layanan_kegiatan",
            "tim_kegiatan",
            "instansi_tujuan",
        ).prefetch_related(
            "kegiatan_survei",
            "barang_laboratorium_items",
            "barang_penunjang_items",
            "peralatan_laboratorium_items",
            "bahan_operasional_items",
        ),
        pk=pk,
    )

    if not _can_edit_pengajuan(request.user, obj):
        return deny_access(
            request,
            "Form edit peminjaman hanya dapat dilakukan oleh Teknisi Laboratorium dan Super Admin pada tahap verifikasi Teknisi Laboratorium.",
        )

    selection_state = (
        _extract_selection_state(request.POST)
        if request.method == "POST"
        else _build_selection_state_from_obj(obj)
    )
    selected_survei_labels = (
        _get_survei_labels_from_post(request.POST)
        if request.method == "POST"
        else _get_survei_labels_from_obj(obj)
    )
    inventory_context = _build_inventory_context(
        selection_state, selected_survei_labels, current_obj=obj
    )
    inventory_form_errors = []

    if request.method == "POST":
        form = PeminjamanRequestForm(request.POST, request.FILES, instance=obj, actor=request.user)
        (
            selected_lab,
            selected_penunjang,
            selected_peralatan_lab,
            selected_bahan,
            item_errors,
        ) = _parse_selected_items(request.POST, selected_survei_labels, current_obj=obj)
        inventory_form_errors = item_errors

        if form.is_valid() and not item_errors:
            try:
                with transaction.atomic():
                    pengajuan = form.save(commit=False)
                    _apply_peminjam_snapshot(pengajuan, pengajuan.peminjam)
                    pengajuan.save()
                    form.save_m2m()

                    pengajuan.release_inventory_allocation()
                    _replace_pengajuan_items(
                        pengajuan,
                        selected_lab,
                        selected_penunjang,
                        selected_peralatan_lab,
                        selected_bahan,
                    )
                    pengajuan.apply_inventory_allocation()
                    pengajuan.add_timeline(
                        "Peminjaman",
                        "Data pengajuan dan daftar barang diperbarui; booking stok disesuaikan",
                        request.user,
                    )
            except ValidationError as exc:
                inventory_form_errors = _get_validation_messages(exc)
            else:
                messages.success(request, "Data pengajuan peminjaman dan booking stok berhasil diperbarui.")
                return redirect("verifikasi:detail", pk=obj.pk)
    else:
        form = PeminjamanRequestForm(instance=obj, actor=request.user)

    return render(
        request,
        "peminjaman/pengajuan_form.html",
        {
            "form": form,
            "page_title": "Edit Pengajuan Peminjaman",
            "page_subtitle": "Perbarui data kegiatan dan daftar barang yang diajukan sesuai kebutuhan peminjaman yang sedang diproses.",
            "inventory_form_errors": inventory_form_errors,
            **_build_peminjam_select_context(form, obj.peminjam),
            **inventory_context,
        },
    )


@login_required
def hapus_pengajuan(request, pk):
    if request.method != "POST":
        return redirect("peminjaman:detail", pk=pk)

    if not _can_delete_pengajuan(request.user):
        return deny_access(
            request, "Hanya Super Admin yang dapat menghapus pengajuan peminjaman."
        )

    obj = get_object_or_404(
        PeminjamanRequest.objects.prefetch_related(
            "barang_laboratorium_items__barang",
            "barang_penunjang_items__barang",
            "peralatan_laboratorium_items__barang",
            "bahan_operasional_items__bahan",
        ),
        pk=pk,
    )

    nomor_pengajuan = obj.nomor_pengajuan
    with transaction.atomic():
        obj.release_inventory_allocation()
        obj.delete()

    messages.success(request, f"Pengajuan {nomor_pengajuan} berhasil dihapus.")

    referer = request.META.get("HTTP_REFERER") or ""
    if "/laporan/" in referer:
        return redirect("peminjaman:laporan")
    return redirect("peminjaman:list")


@login_required
def detail_pengajuan(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "layanan_kegiatan",
            "tim_kegiatan",
            "instansi_tujuan",
            "admin_lab_by",
            "teknisi_lab_by",
            "kepala_lab_by",
            "pimpinan_by",
        ).prefetch_related(
            "kegiatan_survei",
            "barang_laboratorium_items__barang",
            "barang_penunjang_items__barang",
            "peralatan_laboratorium_items__barang",
            "bahan_operasional_items__bahan",
            "pengembalian_lab_items__barang",
            "pengembalian_penunjang_items__barang",
            "pengembalian_peralatan_laboratorium_items__barang",
            "pengembalian_bahan_items__bahan",
            "timeline_entries__actor",
        ),
        pk=pk,
    )
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request, "Anda tidak memiliki akses untuk melihat pengajuan ini."
        )

    lab_items = list(obj.barang_laboratorium_items.all())
    penunjang_items = list(obj.barang_penunjang_items.all())
    peralatan_lab_items = list(obj.peralatan_laboratorium_items.all())
    bahan_items = list(obj.bahan_operasional_items.all())
    _attach_asal_peminjaman_labels(
        obj, lab_items, penunjang_items, peralatan_lab_items, bahan_items
    )

    return render(
        request,
        "peminjaman/pengajuan_detail.html",
        {
            "obj": obj,
            "survei_items": obj.kegiatan_survei.all(),
            "can_delete_pengajuan": _can_delete_pengajuan(request.user),
            "can_edit_pengajuan": _can_edit_pengajuan(request.user, obj),
            "can_access_pengembalian": get_role_name(request.user)
            in {
                ROLE_SUPER_ADMIN,
                ROLE_ADMIN_LAB,
                ROLE_TEKNISI_LAB,
                ROLE_KEPALA_LAB,
                ROLE_PIMPINAN,
                ROLE_USER,
            },
            "lab_items": lab_items,
            "penunjang_items": penunjang_items,
            "peralatan_lab_items": peralatan_lab_items,
            "bahan_items": bahan_items,
        },
    )


def _get_report_snapshot(obj):
    snapshot = obj.report_snapshot if isinstance(obj.report_snapshot, dict) else {}
    if snapshot and snapshot.get("items"):
        normalized_snapshot = _normalize_report_tim_kegiatan(snapshot)
        existing_pengukuran = normalized_snapshot.get("pengukuran") or []
        existing_keys = {item.get("key") for item in existing_pengukuran if isinstance(item, dict)}
        missing_pengukuran = [
            item for item in obj.get_pengukuran_data() if item.get("key") not in existing_keys
        ]
        if missing_pengukuran:
            normalized_snapshot = {
                **normalized_snapshot,
                "pengukuran": [*existing_pengukuran, *missing_pengukuran],
            }
        return normalized_snapshot
    return _normalize_report_tim_kegiatan(obj.build_report_snapshot())


@login_required
def detail_laporan(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "layanan_kegiatan",
            "tim_kegiatan",
            "instansi_tujuan",
            "admin_lab_by",
            "teknisi_lab_by",
            "kepala_lab_by",
            "pimpinan_by",
        ).prefetch_related(
            "kegiatan_survei",
            "barang_laboratorium_items__barang",
            "barang_penunjang_items__barang",
            "peralatan_laboratorium_items__barang",
            "bahan_operasional_items__bahan",
            "pengembalian_lab_items__barang",
            "pengembalian_lab_items__transfer_target",
            "pengembalian_penunjang_items__barang",
            "pengembalian_penunjang_items__transfer_target",
            "pengembalian_peralatan_laboratorium_items__barang",
            "pengembalian_peralatan_laboratorium_items__transfer_target",
            "pengembalian_bahan_items__bahan",
            "pengembalian_bahan_items__transfer_target",
            "timeline_entries__actor",
        ),
        pk=pk,
        return_current_step=ReturnStepChoices.COMPLETED,
    )
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request, "Anda tidak memiliki akses untuk melihat laporan peminjaman ini."
        )

    report = _get_report_snapshot(obj)
    report_kegiatan = report.get("kegiatan", {})
    report_items = report.get("items", {})

    return render(
        request,
        "peminjaman/laporan_detail.html",
        {
            "obj": obj,
            "report": report,
            "report_peminjam": report.get("peminjam", {}),
            "report_kegiatan": report_kegiatan,
            "report_survei_items": report_kegiatan.get("kegiatan_survei", []),
            "report_lab_items": report_items.get("lab", []),
            "report_penunjang_items": report_items.get("penunjang", []),
            "report_peralatan_lab_items": report_items.get("peralatan_lab", []),
            "report_bahan_items": report_items.get("bahan", []),
            "can_delete_pengajuan": _can_delete_pengajuan(request.user),
        },
    )


def _get_latest_return_teknisi_actor(obj):
    teknisi_entry = (
        obj.timeline_entries.filter(
            action__in=[
                "Verifikasi pengembalian selesai dan diteruskan ke tahap berikutnya",
                "Verifikasi pengembalian selesai dan diteruskan ke Kepala Laboratorium",
                "Verifikasi pengembalian selesai dan pengembalian dinyatakan lengkap",
                "Verifikasi pengembalian selesai dan pengembalian dinyatakan selesai",
                "Verifikasi pengembalian selesai dan diteruskan ke user untuk konfirmasi",
            ]
        )
        .select_related("actor")
        .order_by("-created_at", "-id")
        .first()
    )
    return getattr(teknisi_entry, "actor", None)


def _build_berita_acara_sections(obj):
    rusak_items = []
    hilang_items = []

    for item in obj.pengembalian_lab_items.select_related("barang").all():
        target = (
            rusak_items
            if item.status == "rusak"
            else hilang_items
            if item.status == "hilang"
            else None
        )
        if target is None:
            continue
        target.append(
            {
                "nama": item.snapshot_nama_barang
                or getattr(item.barang, "nama_barang", "-")
                or "-",
                "jenis": "Peralatan Survei Lapangan",
                "jumlah": "1 unit",
                "keterangan": item.note
                or item.snapshot_kode_laboratorium
                or item.snapshot_kode_aset_bmn
                or getattr(item.barang, "kode_laboratorium", "")
                or getattr(item.barang, "kode_aset_bmn", "")
                or "-",
            }
        )

    for item in obj.pengembalian_penunjang_items.select_related("barang").all():
        if item.qty_rusak > 0:
            rusak_items.append(
                {
                    "nama": item.snapshot_nama_barang
                    or getattr(item.barang, "nama_barang", "-")
                    or "-",
                    "jenis": "Barang Penunjang Lapangan",
                    "jumlah": f"{item.qty_rusak} {item.snapshot_satuan or getattr(item.barang, 'satuan', '') or 'unit'}",
                    "keterangan": item.note
                    or item.snapshot_tipe_merek_barang
                    or getattr(item.barang, "tipe_merek_barang", "")
                    or "-",
                }
            )
        if item.qty_hilang > 0:
            hilang_items.append(
                {
                    "nama": item.snapshot_nama_barang
                    or getattr(item.barang, "nama_barang", "-")
                    or "-",
                    "jenis": "Barang Penunjang Lapangan",
                    "jumlah": f"{item.qty_hilang} {item.snapshot_satuan or getattr(item.barang, 'satuan', '') or 'unit'}",
                    "keterangan": item.note
                    or item.snapshot_tipe_merek_barang
                    or getattr(item.barang, "tipe_merek_barang", "")
                    or "-",
                }
            )

    for item in obj.pengembalian_peralatan_laboratorium_items.select_related(
        "barang"
    ).all():
        if item.qty_rusak > 0:
            rusak_items.append(
                {
                    "nama": item.snapshot_nama_barang
                    or getattr(item.barang, "nama_barang", "-")
                    or "-",
                    "jenis": "Peralatan Laboratorium",
                    "jumlah": f"{item.qty_rusak} {item.snapshot_satuan or getattr(item.barang, 'satuan', '') or 'unit'}",
                    "keterangan": item.note
                    or item.snapshot_kode_laboratorium
                    or item.snapshot_kode_aset_bmn
                    or getattr(item.barang, "kode_laboratorium", "")
                    or getattr(item.barang, "kode_aset_bmn", "")
                    or "-",
                }
            )
        if item.qty_hilang > 0:
            hilang_items.append(
                {
                    "nama": item.snapshot_nama_barang
                    or getattr(item.barang, "nama_barang", "-")
                    or "-",
                    "jenis": "Peralatan Laboratorium",
                    "jumlah": f"{item.qty_hilang} {item.snapshot_satuan or getattr(item.barang, 'satuan', '') or 'unit'}",
                    "keterangan": item.note
                    or item.snapshot_kode_laboratorium
                    or item.snapshot_kode_aset_bmn
                    or getattr(item.barang, "kode_laboratorium", "")
                    or getattr(item.barang, "kode_aset_bmn", "")
                    or "-",
                }
            )

    return {"rusak": rusak_items, "hilang": hilang_items}


@login_required
def download_berita_acara_pdf(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "tim_kegiatan__ketua_tim",
            "kepala_lab_by",
        ).prefetch_related(
            "pengembalian_lab_items__barang",
            "pengembalian_penunjang_items__barang",
            "pengembalian_peralatan_laboratorium_items__barang",
            "timeline_entries__actor",
        ),
        pk=pk,
    )
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request, "Anda tidak memiliki akses untuk mengunduh berita acara ini."
        )
    if not obj.can_download_berita_acara:
        messages.error(
            request,
            "Berita acara hanya tersedia setelah proses pengembalian selesai untuk barang rusak atau hilang.",
        )
        return redirect("peminjaman:detail", pk=obj.pk)

    berita_sections = _build_berita_acara_sections(obj)
    if not berita_sections["rusak"] and not berita_sections["hilang"]:
        messages.error(
            request,
            "Data barang rusak atau hilang tidak ditemukan pada pengembalian ini.",
        )
        return redirect("peminjaman:laporan_detail", pk=obj.pk)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="berita-acara-{obj.nomor_pengajuan}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    margin_x = 18 * mm
    content_width = width - (2 * margin_x)
    y = height - 18 * mm

    def wrap_lines(text, *, font="Helvetica", size=10, max_width=None):
        pdf.setFont(font, size)
        max_width = max_width or content_width
        words = str(text or "-").split()
        if not words:
            return ["-"]
        lines = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if pdf.stringWidth(trial, font, size) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def ensure_space(required=18 * mm):
        nonlocal y
        if y >= required:
            return
        pdf.showPage()
        y = height - 18 * mm

    def format_optional_numeric_display(value):
        if value is None:
            return "-"
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return "-"
            try:
                numeric_value = Decimal(stripped)
            except (InvalidOperation, ValueError):
                return value
            return "-" if numeric_value == 0 else value
        if isinstance(value, (int, float, Decimal)):
            return "-" if Decimal(str(value)) == 0 else value
        return value

    def draw_lines(lines, *, font="Helvetica", size=10, gap=4.8 * mm, indent=0):
        nonlocal y
        pdf.setFont(font, size)
        for line_text in lines:
            ensure_space()
            pdf.drawString(margin_x + indent, y, line_text)
            y -= gap

    def draw_signature_block(x, y_top, title, user_obj):
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x, y_top, title)
        signature_y = y_top - 24 * mm
        signature_path = None
        if user_obj is not None:
            try:
                signature_path = (
                    user_obj.safe_profile.ttd_digital.path
                    if user_obj.safe_profile.ttd_digital
                    else None
                )
            except Exception:
                signature_path = None
        if signature_path and Path(signature_path).exists():
            try:
                pdf.drawImage(
                    ImageReader(signature_path),
                    x,
                    signature_y,
                    width=38 * mm,
                    height=18 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
        pdf.line(x, y_top - 27 * mm, x + 52 * mm, y_top - 27 * mm)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(
            x, y_top - 31 * mm, (user_obj.get_full_name() if user_obj else "-")[:42]
        )
        pdf.setFont("Helvetica", 9)
        nip = getattr(user_obj, "nip", "") if user_obj else ""
        pdf.drawString(x, y_top - 35 * mm, f"NIP/NIK: {nip or '-'}")

    pdf.setTitle(f"Berita Acara {obj.nomor_pengajuan}")
    draw_lines(
        ["BERITA ACARA PENGEMBALIAN BARANG RUSAK / HILANG"],
        font="Helvetica-Bold",
        size=13,
        gap=6 * mm,
    )
    draw_lines([f"Nomor Pengajuan: {obj.nomor_pengajuan}"], size=10)
    draw_lines(
        [
            f"Tanggal Dokumen: {format_date_id(timezone.localdate(obj.return_completed_at or timezone.now()))}"
        ],
        size=10,
    )
    y -= 2 * mm

    peminjam_lines = [
        f"Nama: {obj.nama_peminjam}",
        f"Nomor Telepon: {obj.no_hp_peminjam or '-'}",
        f"Email: {obj.email_peminjam or '-'}",
        f"Alamat: {obj.alamat_peminjam or '-'}",
        f"NIP / NIK: {obj.nip_peminjam or '-'}",
    ]
    draw_lines(["A. Data Peminjam"], font="Helvetica-Bold", size=10, gap=5 * mm)
    for item_line in peminjam_lines:
        draw_lines(wrap_lines(item_line, size=10), size=10, indent=5 * mm)
    y -= 1 * mm

    survei_values = [item.jenis_survei for item in obj.kegiatan_survei.all()]
    if obj.survei_lainnya:
        survei_values.append(f"Lainnya: {obj.survei_lainnya}")
    kegiatan_lines = [
        f"Layanan Kegiatan: {obj.layanan_kegiatan_label}",
        f"Kegiatan Survei: {', '.join(survei_values) if survei_values else '-'}",
        f"Tim Kegiatan: {getattr(obj.tim_kegiatan, 'nama_tim', '-')}",
        f"Instansi Tujuan: {getattr(obj.instansi_tujuan, 'nama_instansi', obj.instansi_tujuan_lainnya or '-')}",
        f"Periode Peminjaman: {format_date_id(obj.tanggal_mulai)} s/d {format_date_id(obj.tanggal_selesai)}",
        f"Total Hari: {obj.total_hari} hari",
    ]
    draw_lines(["B. Data Kegiatan"], font="Helvetica-Bold", size=10, gap=5 * mm)
    for item_line in kegiatan_lines:
        draw_lines(wrap_lines(item_line, size=10), size=10, indent=5 * mm)
    y -= 1 * mm

    draw_lines(["C. Daftar Barang Rusak"], font="Helvetica-Bold", size=10, gap=5 * mm)
    if berita_sections["rusak"]:
        for index, item in enumerate(berita_sections["rusak"], start=1):
            lines = [
                f"{index}. {item['nama']} ({item['jenis']})",
                f"Jumlah: {item['jumlah']}",
                f"Keterangan: {item['keterangan']}",
            ]
            for line_text in lines:
                draw_lines(
                    wrap_lines(line_text, size=10, max_width=content_width - (5 * mm)),
                    size=10,
                    indent=5 * mm,
                )
            y -= 1 * mm
    else:
        draw_lines(["-"], size=10, indent=5 * mm)
        y -= 1 * mm

    draw_lines(["D. Daftar Barang Hilang"], font="Helvetica-Bold", size=10, gap=5 * mm)
    if berita_sections["hilang"]:
        for index, item in enumerate(berita_sections["hilang"], start=1):
            lines = [
                f"{index}. {item['nama']} ({item['jenis']})",
                f"Jumlah: {item['jumlah']}",
                f"Keterangan: {item['keterangan']}",
            ]
            for line_text in lines:
                draw_lines(
                    wrap_lines(line_text, size=10, max_width=content_width - (5 * mm)),
                    size=10,
                    indent=5 * mm,
                )
            y -= 1 * mm
    else:
        draw_lines(["-"], size=10, indent=5 * mm)
        y -= 1 * mm

    draw_lines(["E. Keterangan"], font="Helvetica-Bold", size=10, gap=5 * mm)
    keterangans = [
        "Dokumen ini diterbitkan secara otomatis pada akhir proses pengembalian untuk mencatat barang dengan status rusak atau hilang.",
        "Barang yang tercatat dikembalikan dalam kondisi baik atau ditransfer ke pengajuan lain tidak dimasukkan ke dalam berita acara ini.",
    ]
    for keterangan in keterangans:
        draw_lines(
            wrap_lines(f"• {keterangan}", size=10, max_width=content_width - (5 * mm)),
            size=10,
            indent=5 * mm,
        )

    ensure_space(80 * mm)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        width - 78 * mm,
        y,
        f"Bandung, {format_date_id(timezone.localdate(obj.return_completed_at or timezone.now()))}",
    )
    y -= 10 * mm

    teknisi_user = _get_latest_return_teknisi_actor(obj)
    draw_signature_block(margin_x, y, "Peminjam,", obj.peminjam)
    draw_signature_block(width - 80 * mm, y, "Teknisi Laboratorium,", teknisi_user)
    y -= 44 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(width / 2, y, "Mengetahui,")
    y -= 9 * mm

    draw_signature_block(
        margin_x, y, "Kepala Laboratorium,", obj.get_kepala_lab_signer()
    )
    draw_signature_block(
        width - 80 * mm,
        y,
        "Ketua Tim Layanan Teknis,",
        obj.get_return_pimpinan_signer(),
    )

    pdf.showPage()
    pdf.save()
    return response


@login_required
def download_laporan_pdf(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "tim_kegiatan__ketua_tim",
            "teknisi_lab_by",
            "kepala_lab_by",
        ).prefetch_related(
            "kegiatan_survei",
            "barang_laboratorium_items__barang",
            "barang_penunjang_items__barang",
            "peralatan_laboratorium_items__barang",
            "bahan_operasional_items__bahan",
            "pengembalian_lab_items__barang",
            "pengembalian_lab_items__transfer_target",
            "pengembalian_penunjang_items__barang",
            "pengembalian_penunjang_items__transfer_target",
            "pengembalian_peralatan_laboratorium_items__barang",
            "pengembalian_peralatan_laboratorium_items__transfer_target",
            "pengembalian_bahan_items__bahan",
            "pengembalian_bahan_items__transfer_target",
            "timeline_entries__actor",
        ),
        pk=pk,
        return_current_step=ReturnStepChoices.COMPLETED,
    )
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request, "Anda tidak memiliki akses untuk mengunduh PDF laporan ini."
        )

    report = _get_report_snapshot(obj)
    report_peminjam = report.get("peminjam", {})
    report_kegiatan = report.get("kegiatan", {})
    report_items = report.get("items", {})
    report_pengukuran = report.get("pengukuran", []) or []

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="laporan-{obj.nomor_pengajuan}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    margin_x = 18 * mm
    content_width = width - (2 * margin_x)
    y = height - 18 * mm

    def wrap_lines(text, *, font="Helvetica", size=10, max_width=None):
        pdf.setFont(font, size)
        max_width = max_width or content_width
        words = str(text or "-").split()
        if not words:
            return ["-"]
        lines = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if pdf.stringWidth(trial, font, size) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def ensure_space(required=18 * mm):
        nonlocal y
        if y >= required:
            return
        pdf.showPage()
        y = height - 18 * mm

    def draw_lines(lines, *, font="Helvetica", size=10, gap=4.8 * mm, indent=0):
        nonlocal y
        pdf.setFont(font, size)
        for line_text in lines:
            ensure_space()
            pdf.drawString(margin_x + indent, y, line_text)
            y -= gap

    def draw_signature_block(x, y_top, title, user_obj):
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x, y_top, title)
        signature_y = y_top - 24 * mm
        signature_path = None
        if user_obj is not None:
            try:
                signature_path = (
                    user_obj.safe_profile.ttd_digital.path
                    if user_obj.safe_profile.ttd_digital
                    else None
                )
            except Exception:
                signature_path = None
        if signature_path and Path(signature_path).exists():
            try:
                pdf.drawImage(
                    ImageReader(signature_path),
                    x,
                    signature_y,
                    width=38 * mm,
                    height=18 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
        pdf.line(x, y_top - 27 * mm, x + 52 * mm, y_top - 27 * mm)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(
            x, y_top - 31 * mm, (user_obj.get_full_name() if user_obj else "-")[:42]
        )
        pdf.setFont("Helvetica", 9)
        nip = getattr(user_obj, "nip", "") if user_obj else ""
        pdf.drawString(x, y_top - 35 * mm, f"NIP/NIK: {nip or '-'}")

    def draw_item_section(title, entries):
        nonlocal y
        draw_lines([title], font="Helvetica-Bold", size=10, gap=5 * mm)
        if not entries:
            draw_lines(["-"], size=10, indent=5 * mm)
            y -= 1 * mm
            return
        for index, entry_lines in enumerate(entries, start=1):
            first_line = True
            for line_text in entry_lines:
                prefix = f"{index}. " if first_line else "    "
                wrapped = wrap_lines(
                    f"{prefix}{line_text}", size=10, max_width=content_width - (5 * mm)
                )
                draw_lines(wrapped, size=10, indent=5 * mm)
                first_line = False
            y -= 1 * mm

    pdf.setTitle(f"Laporan {obj.nomor_pengajuan}")
    draw_lines(
        ["LAPORAN DETAIL PEMINJAMAN DAN PENGEMBALIAN"],
        font="Helvetica-Bold",
        size=13,
        gap=6 * mm,
    )
    draw_lines(
        [f"Nomor Pengajuan: {report.get('nomor_pengajuan', obj.nomor_pengajuan)}"],
        size=10,
    )
    draw_lines([f"Tanggal Peminjaman: {report.get('submitted_at', '-')}"], size=10)
    draw_lines(
        [f"Tanggal Pengembalian: {report.get('return_started_at', '-')}"], size=10
    )
    draw_lines(
        [f"Pengembalian Selesai: {report.get('return_completed_at', '-')}"], size=10
    )
    y -= 2 * mm

    draw_lines(["A. Data Peminjam"], font="Helvetica-Bold", size=10, gap=5 * mm)
    for item_line in [
        f"Nama: {report_peminjam.get('nama', '-')}",
        f"Nomor Telepon: {report_peminjam.get('nomor_telepon', '-')}",
        f"Email: {report_peminjam.get('email', '-')}",
        f"NIP / NIK: {report_peminjam.get('nip', '-')}",
        f"Alamat: {report_peminjam.get('alamat', '-')}",
    ]:
        draw_lines(wrap_lines(item_line, size=10), size=10, indent=5 * mm)
    y -= 1 * mm

    survei_values = report_kegiatan.get("kegiatan_survei", []) or []
    draw_lines(["B. Data Kegiatan"], font="Helvetica-Bold", size=10, gap=5 * mm)
    for item_line in [
        f"Layanan Kegiatan: {report_kegiatan.get('layanan_kegiatan', '-')}",
        f"Kegiatan Survei: {', '.join(survei_values) if survei_values else '-'}",
        f"Tim Kegiatan: {report_kegiatan.get('tim_kegiatan', '-')}",
        f"Instansi Tujuan: {report_kegiatan.get('instansi_tujuan', '-')}",
        f"Mulai Tanggal: {report_kegiatan.get('mulai_tanggal', '-')}",
        f"Selesai Tanggal: {report_kegiatan.get('selesai_tanggal', '-')}",
        f"Total Hari: {report_kegiatan.get('total_hari', '-')} hari",
    ]:
        draw_lines(wrap_lines(item_line, size=10), size=10, indent=5 * mm)
    y -= 1 * mm

    draw_item_section(
        "C. Data Peralatan Survei Lapangan",
        [
            [
                f"{item.get('nama_barang', '-')} | {item.get('tipe_merek_barang', '-')} | {item.get('kode_laboratorium', '-')}",
                f"Status Pengembalian: {item.get('status_pengembalian', '-')}",
                f"Tujuan Transfer: {item.get('tujuan_transfer', '-')}",
                f"Asal Peminjaman: {item.get('asal_peminjaman', '-')}",
                f"Catatan Pengembalian: {item.get('catatan_pengembalian', '-')}",
            ]
            for item in report_items.get("lab", [])
        ],
    )
    draw_item_section(
        "D. Data Barang Penunjang Lapangan",
        [
            [
                f"{item.get('nama_barang', '-')} | Volume Dipinjam: {item.get('volume_dipinjam', '-')} {item.get('satuan', '-')}",
                f"Dikembalikan: {item.get('qty_dikembalikan', 0)} | Rusak: {item.get('qty_rusak', 0)} | Hilang: {item.get('qty_hilang', 0)} | Transfer: {item.get('qty_transfer', 0)}",
                f"Tujuan Transfer: {item.get('tujuan_transfer', '-')}",
                f"Asal Peminjaman: {item.get('asal_peminjaman', '-')}",
                f"Catatan Pengembalian: {item.get('catatan_pengembalian', '-')}",
            ]
            for item in report_items.get("penunjang", [])
        ],
    )
    draw_item_section(
        "E. Data Bahan Operasional",
        [
            [
                f"{item.get('nama_barang', '-')} | Volume Dipinjam: {item.get('volume_dipinjam', '-')} {item.get('satuan', '-')}",
                f"Sisa: {item.get('qty_sisa', 0)} | Transfer: {item.get('qty_transfer', 0)}",
                f"Tujuan Transfer: {item.get('tujuan_transfer', '-')}",
                f"Asal Peminjaman: {item.get('asal_peminjaman', '-')}",
                f"Catatan Pengembalian: {item.get('catatan_pengembalian', '-')}",
            ]
            for item in report_items.get("bahan", [])
        ],
    )
    draw_item_section(
        "F. Data Peralatan Laboratorium",
        [
            [
                f"{item.get('nama_barang', '-')} | {item.get('tipe_merek_barang', '-')} | {item.get('kode_laboratorium', '-')}",
                f"Volume Dipinjam: {item.get('volume_dipinjam', '-')} {item.get('satuan', '-')}",
                f"Dikembalikan: {item.get('qty_dikembalikan', 0)} | Rusak: {item.get('qty_rusak', 0)} | Hilang: {item.get('qty_hilang', 0)} | Transfer: {item.get('qty_transfer', 0)}",
                f"Tujuan Transfer: {item.get('tujuan_transfer', '-')}",
                f"Asal Peminjaman: {item.get('asal_peminjaman', '-')}",
                f"Catatan Pengembalian: {item.get('catatan_pengembalian', '-')}",
            ]
            for item in report_items.get("peralatan_lab", [])
        ],
    )
    draw_item_section(
        "G. Data Pengukuran",
        [
            [
                f"{item.get('label', '-')} : {format_optional_numeric_display(item.get('display', '-'))}"
            ]
            for item in report_pengukuran
        ],
    )

    ensure_space(80 * mm)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        width - 78 * mm,
        y,
        f"Bandung, {format_date_id(timezone.localdate(obj.return_completed_at or timezone.now()))}",
    )
    y -= 10 * mm

    teknisi_user = _get_latest_return_teknisi_actor(obj)
    draw_signature_block(margin_x, y, "Peminjam,", obj.peminjam)
    draw_signature_block(width - 80 * mm, y, "Teknisi Laboratorium,", teknisi_user)
    y -= 44 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(width / 2, y, "Mengetahui,")
    y -= 9 * mm

    draw_signature_block(
        margin_x, y, "Kepala Laboratorium,", obj.get_kepala_lab_signer()
    )
    draw_signature_block(
        width - 80 * mm,
        y,
        "Ketua Tim Layanan Teknis,",
        obj.get_return_pimpinan_signer(),
    )

    pdf.showPage()
    pdf.save()
    return response


@login_required
def download_pdf(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "tim_kegiatan__ketua_tim",
            "teknisi_lab_by",
            "kepala_lab_by",
        ).prefetch_related(
            "kegiatan_survei",
            "barang_laboratorium_items__barang",
            "barang_penunjang_items__barang",
            "peralatan_laboratorium_items__barang",
            "bahan_operasional_items__bahan",
        ),
        pk=pk,
    )
    if not _can_view_pengajuan(request.user, obj):
        return deny_access(
            request, "Anda tidak memiliki akses untuk mengunduh PDF pengajuan ini."
        )
    if not obj.can_download_pdf:
        messages.error(
            request, "PDF hanya dapat diunduh setelah pengajuan disetujui pimpinan."
        )
        return redirect("peminjaman:detail", pk=obj.pk)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{obj.nomor_pengajuan}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    margin_x = 18 * mm
    y = height - 18 * mm

    def line(text, font="Helvetica", size=10, gap=5 * mm):
        nonlocal y
        pdf.setFont(font, size)
        pdf.drawString(margin_x, y, text)
        y -= gap

    def multiline(title, values):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(margin_x, y, title)
        y -= 5 * mm
        pdf.setFont("Helvetica", 10)
        for value in values:
            pdf.drawString(margin_x + 5 * mm, y, f"• {value}")
            y -= 4.5 * mm
        y -= 2 * mm

    def draw_signature_block(x, y_top, title, user_obj):
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x, y_top, title)
        signature_y = y_top - 24 * mm
        signature_path = None
        if user_obj is not None:
            try:
                signature_path = (
                    user_obj.safe_profile.ttd_digital.path
                    if user_obj.safe_profile.ttd_digital
                    else None
                )
            except Exception:
                signature_path = None
        if signature_path and Path(signature_path).exists():
            try:
                pdf.drawImage(
                    ImageReader(signature_path),
                    x,
                    signature_y,
                    width=38 * mm,
                    height=18 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
        pdf.line(x, y_top - 27 * mm, x + 52 * mm, y_top - 27 * mm)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(
            x, y_top - 31 * mm, (user_obj.get_full_name() if user_obj else "-")[:42]
        )
        pdf.setFont("Helvetica", 9)
        nip = getattr(user_obj, "nip", "") if user_obj else ""
        pdf.drawString(x, y_top - 35 * mm, f"NIP/NIK: {nip or '-'}")

    pdf.setTitle(obj.nomor_pengajuan)
    line("FORMULIR PENGAJUAN PEMINJAMAN", font="Helvetica-Bold", size=13, gap=6 * mm)
    line(f"Nomor Pengajuan: {obj.nomor_pengajuan}")
    line(
        f"Tanggal Pengajuan: {format_date_id(timezone.localtime(obj.submitted_at).date())}"
    )
    y -= 2 * mm

    multiline(
        "A. Data Peminjam",
        [
            f"Nama: {obj.nama_peminjam}",
            f"Nomor Telepon: {obj.no_hp_peminjam or '-'}",
            f"Email: {obj.email_peminjam or '-'}",
            f"Alamat: {obj.alamat_peminjam or '-'}",
        ],
    )
    survei_values = [item.jenis_survei for item in obj.kegiatan_survei.all()]
    if obj.survei_lainnya:
        survei_values.append(f"Lainnya: {obj.survei_lainnya}")
    multiline(
        "B. Data Kegiatan",
        [
            f"Layanan Kegiatan: {obj.layanan_kegiatan_label}",
            f"Kegiatan Survei: {', '.join(survei_values) if survei_values else '-'}",
            f"Tim Kegiatan Pelaksana: {getattr(obj.tim_kegiatan, 'nama_tim', '-')}",
            f"Instansi Tujuan Kegiatan: {getattr(obj.instansi_tujuan, 'nama_instansi', obj.instansi_tujuan_lainnya or '-')}",
            f"Waktu Kegiatan: {format_date_id(obj.tanggal_mulai)} s/d {format_date_id(obj.tanggal_selesai)}",
            f"Total Hari: {obj.total_hari} hari",
        ],
    )
    multiline(
        "C. Data Peralatan Survei Lapangan yang Dipinjam",
        [
            f"{item.barang.nama_barang} | {item.barang.tipe_merek_barang} | {item.barang.kode_laboratorium}"
            for item in obj.barang_laboratorium_items.all()
        ]
        or ["-"],
    )
    multiline(
        "D. Data Barang Penunjang Lapangan yang Dipinjam",
        [
            f"{item.barang.nama_barang} | {item.barang.tipe_merek_barang} | Volume: {item.volume}"
            for item in obj.barang_penunjang_items.all()
        ]
        or ["-"],
    )
    multiline(
        "E. Data Bahan Operasional yang Dipinjam",
        [
            f"{item.bahan.nama_barang} | Volume: {item.volume} {item.bahan.satuan}"
            for item in obj.bahan_operasional_items.all()
        ]
        or ["-"],
    )
    multiline(
        "F. Data Peralatan Laboratorium yang Dipinjam",
        [
            f"{item.barang.nama_barang} | {item.barang.tipe_merek_barang} | {item.barang.kode_laboratorium} | Volume: {item.volume} {item.barang.satuan}"
            for item in obj.peralatan_laboratorium_items.all()
        ]
        or ["-"],
    )


    if y < 90 * mm:
        pdf.showPage()
        y = height - 20 * mm

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        width - 78 * mm,
        y,
        f"Bandung, {format_date_id(timezone.localtime(obj.submitted_at).date())}",
    )
    y -= 10 * mm

    draw_signature_block(margin_x, y, "Peminjam,", obj.peminjam)
    draw_signature_block(
        width - 80 * mm, y, "Petugas Laboratorium,", obj.teknisi_lab_by
    )
    y -= 44 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(width / 2, y, "Mengetahui,")
    y -= 9 * mm

    draw_signature_block(
        margin_x, y, "Kepala Laboratorium,", obj.get_kepala_lab_signer()
    )
    ketua_tim = obj.get_pimpinan_signer()
    ketua_title = format_ketua_tim_title(
        obj.tim_kegiatan.nama_tim if obj.tim_kegiatan else ""
    )
    draw_signature_block(width - 80 * mm, y, ketua_title[:45], ketua_tim)

    pdf.showPage()
    pdf.save()
    return response
