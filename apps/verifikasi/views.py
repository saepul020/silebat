from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.list_pagination import (
    LIST_ENTRY_OPTIONS,
    LIST_SEARCH_MAX_LENGTH,
    normalize_entries,
    normalize_search,
)
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
from apps.operasional.models import TimKegiatan, TIM_LAYANAN_TEKNIS_NAME
from apps.peminjaman.forms import VerifikasiAksiForm
from apps.peminjaman.models import (
    DecisionChoices,
    PeminjamanRequest,
    ReturnStepChoices,
    StepChoices,
    build_asal_peminjaman_maps,
    resolve_asal_peminjaman_label,
)
from apps.pemeliharaan.models import (
    JenisFotoPemeliharaanChoices,
    KeputusanPemeliharaanChoices,
    PemeliharaanPengajuan,
    StepPemeliharaanChoices,
)


ACTION_CHOICES = {
    StepChoices.ADMIN_LAB: [("tolak", "Tolak"), ("setujui", "Setujui")],
    StepChoices.TEKNISI_LAB: [("selesai", "Lanjutkan Proses")],
    StepChoices.KEPALA_LAB: [
        ("tolak", "Tolak"),
        ("perbaiki", "Perbaiki"),
        ("setujui", "Setujui"),
    ],
    StepChoices.PIMPINAN: [
        ("tolak", "Tolak"),
        ("perbaiki", "Perbaiki"),
        ("setujui", "Setujui"),
    ],
}

RETURN_ACTION_CHOICES = {
    ReturnStepChoices.TEKNISI_VERIFICATION: [("selesai", "Lanjutkan Proses")],
    ReturnStepChoices.USER_VERIFICATION: [
        ("sesuai", "Sudah Sesuai"),
        ("tidak_sesuai", "Belum Sesuai"),
    ],
    ReturnStepChoices.TEKNISI_BA: [("selesai", "Lanjutkan Proses")],
    ReturnStepChoices.KEPALA_BA: [
        ("setujui", "Setujui"),
        ("perbaiki", "Perbaiki"),
    ],
    ReturnStepChoices.PIMPINAN_BA: [
        ("setujui", "Setujui"),
        ("perbaiki", "Perbaiki"),
    ],
    ReturnStepChoices.TEKNISI_TRANSFER: [("selesai", "Lanjutkan Proses")],
    ReturnStepChoices.KEPALA_TRANSFER: [
        ("setujui", "Setujui"),
        ("perbaiki", "Perbaiki"),
    ],
    ReturnStepChoices.PIMPINAN_TRANSFER: [
        ("setujui", "Setujui"),
        ("perbaiki", "Perbaiki"),
    ],
}
VERIFIKASI_LIST_SEARCH_FIELDS = (
    "nomor_pengajuan",
    "nama_peminjam",
    "layanan_kegiatan__jenis_layanan",
    "layanan_kegiatan_lainnya",
    "tim_kegiatan__nama_tim",
    "instansi_tujuan__nama_instansi",
    "instansi_tujuan_lainnya",
    "current_step",
    "return_current_step",
)

RETURN_PIMPINAN_TEAM_NAME = TIM_LAYANAN_TEKNIS_NAME
RETURN_PIMPINAN_LABEL = "Ketua Tim Layanan Teknis"
BORROWER_CONFIRMATION_ROLES = {ROLE_USER, ROLE_ADMIN_LAB, ROLE_TEKNISI_LAB}


ACTION_META = {
    "setujui": {
        "button_class": "btn-primary",
        "submit_class": "btn-primary",
        "requires_note": False,
        "modal_title": "Input Konfirmasi Persetujuan (Opsional)",
        "modal_submit_label": "Kirim Persetujuan",
        "note_label": "Catatan Persetujuan:",
        "note_placeholder": "Tulis catatan persetujuan (opsional).",
    },
    "selesai": {
        "button_class": "btn-primary",
        "submit_class": "btn-primary",
        "requires_note": False,
        "modal_title": "Input Konfirmasi Proses (Opsional)",
        "modal_submit_label": "Kirim Proses",
        "note_label": "Catatan Proses:",
        "note_placeholder": "Tulis catatan proses (opsional).",
    },
    "sesuai": {
        "button_class": "btn-primary",
        "submit_class": "btn-primary",
        "requires_note": False,
        "modal_title": "Input Konfirmasi Kesesuaian (Opsional)",
        "modal_submit_label": "Kirim Verifikasi",
        "note_label": "Catatan Verifikasi:",
        "note_placeholder": "Tulis catatan Kesesuaian (opsional).",
    },
    "tolak": {
        "button_class": "btn-danger",
        "submit_class": "btn-danger",
        "requires_note": True,
        "modal_title": "Input Catatan Penolakan",
        "modal_submit_label": "Kirim Penolakan",
        "note_label": "Catatan Penolakan:",
        "note_placeholder": "Tulis catatan penolakan.",
    },
    "perbaiki": {
        "button_class": "btn-warning",
        "submit_class": "btn-warning",
        "requires_note": True,
        "modal_title": "Input Catatan Perbaikan",
        "modal_submit_label": "Kirim Perbaikan",
        "note_label": "Catatan Perbaikan:",
        "note_placeholder": "Tulis catatan perbaikan.",
    },
    "tidak_sesuai": {
        "button_class": "btn-warning",
        "submit_class": "btn-warning",
        "requires_note": True,
        "modal_title": "Input Catatan Ketidaksesuaian",
        "modal_submit_label": "Kirim Ketidaksesuaian",
        "note_label": "Catatan Ketidaksesuaian:",
        "note_placeholder": "Tulis catatan Ketidaksesuaian",
        "note_help_text": "",
    },
    "kembalikan": {
        "button_class": "btn-warning",
        "submit_class": "btn-warning",
        "requires_note": True,
        "modal_title": "Input Catatan Pengembalian",
        "modal_submit_label": "Kirim Pengembalian",
        "note_label": "Catatan Pengembalian:",
        "note_placeholder": "Tulis alasan pengajuan dikembalikan.",
    },
}

PEMELIHARAAN_ACTION_CHOICES = {
    StepPemeliharaanChoices.KEPALA_LAB: [
        ("tolak", "Tolak"),
        ("perbaiki", "Perbaiki"),
        ("setujui", "Setujui"),
    ],
    StepPemeliharaanChoices.PIMPINAN: [
        ("tolak", "Tolak"),
        ("perbaiki", "Perbaiki"),
        ("setujui", "Setujui"),
    ],
}

def _is_return_verification(obj):
    return obj.return_current_step not in {
        ReturnStepChoices.NONE,
        ReturnStepChoices.COMPLETED,
    }

def _is_return_user_verification(obj):
    return obj.return_current_step == ReturnStepChoices.USER_VERIFICATION

def _is_related_pimpinan(user, obj):
    if get_role_name(user) != ROLE_PIMPINAN:
        return False
    tim_kegiatan = getattr(obj, "tim_kegiatan", None)
    return bool(tim_kegiatan and tim_kegiatan.ketua_tim_id == user.id)

def _get_return_pimpinan_user():
    target_team = (
        TimKegiatan.objects.filter(nama_tim__iexact=RETURN_PIMPINAN_TEAM_NAME)
        .select_related("ketua_tim")
        .order_by("id")
        .first()
    )
    if target_team and target_team.ketua_tim_id:
        return target_team.ketua_tim

    fallback_team = (
        TimKegiatan.objects.filter(nama_tim__icontains="Layanan Teknis")
        .select_related("ketua_tim")
        .order_by("id")
        .first()
    )
    if fallback_team and fallback_team.ketua_tim_id:
        return fallback_team.ketua_tim
    return None

def _is_return_pimpinan_actor(user):
    if get_role_name(user) != ROLE_PIMPINAN:
        return False
    target_user = _get_return_pimpinan_user()
    if target_user is not None:
        return target_user.id == user.id
    try:
        jabatan = (user.safe_profile.jabatan or "").strip()
    except Exception:
        jabatan = ""
    if not jabatan:
        return False
    normalized = jabatan.casefold()
    return (RETURN_PIMPINAN_TEAM_NAME.casefold() in normalized) or (
        "layanan teknis" in normalized
    )

def _can_edit_pengajuan(user, obj):
    return (
        get_role_name(user) in {ROLE_SUPER_ADMIN, ROLE_TEKNISI_LAB}
        and obj.current_step == StepChoices.TEKNISI_LAB
        and not _is_return_verification(obj)
    )

def _can_edit_pengembalian(user, obj):
    return (
        get_role_name(user) in {ROLE_SUPER_ADMIN, ROLE_TEKNISI_LAB}
        and obj.return_current_step == ReturnStepChoices.TEKNISI_VERIFICATION
    )

def _get_pending_queryset(user):
    role_name = get_role_name(user)
    qs = PeminjamanRequest.objects.select_related(
        "peminjam",
        "layanan_kegiatan",
        "tim_kegiatan",
        "instansi_tujuan",
    )
    if role_name == ROLE_SUPER_ADMIN:
        return qs.filter(
            ~Q(current_step__in=[StepChoices.APPROVED, StepChoices.REJECTED])
            | Q(
                return_current_step__in=[
                    ReturnStepChoices.TEKNISI_VERIFICATION,
                    ReturnStepChoices.USER_VERIFICATION,
                    ReturnStepChoices.TEKNISI_BA,
                    ReturnStepChoices.KEPALA_BA,
                    ReturnStepChoices.PIMPINAN_BA,
                    ReturnStepChoices.TEKNISI_TRANSFER,
                    ReturnStepChoices.KEPALA_TRANSFER,
                    ReturnStepChoices.PIMPINAN_TRANSFER,
                ]
            )
        ).distinct()
    if role_name == ROLE_ADMIN_LAB:
        return qs.filter(
            Q(current_step=StepChoices.ADMIN_LAB)
            | Q(return_current_step=ReturnStepChoices.USER_VERIFICATION, peminjam=user)
        ).distinct()
    if role_name == ROLE_TEKNISI_LAB:
        return qs.filter(
            Q(current_step=StepChoices.TEKNISI_LAB)
            | Q(
                return_current_step__in=[
                    ReturnStepChoices.TEKNISI_VERIFICATION,
                    ReturnStepChoices.TEKNISI_BA,
                    ReturnStepChoices.TEKNISI_TRANSFER,
                ]
            )
        ).distinct()
    if role_name == ROLE_USER:
        return qs.filter(
            Q(return_current_step=ReturnStepChoices.USER_VERIFICATION, peminjam=user)
        ).distinct()
    if role_name == ROLE_KEPALA_LAB:
        return qs.filter(
            Q(current_step=StepChoices.KEPALA_LAB)
            | Q(
                return_current_step__in=[
                    ReturnStepChoices.KEPALA_BA,
                    ReturnStepChoices.KEPALA_TRANSFER,
                ]
            )
        ).distinct()
    if role_name == ROLE_PIMPINAN:
        pengajuan_filter = Q(
            current_step=StepChoices.PIMPINAN, tim_kegiatan__ketua_tim=user
        )
        pengembalian_filter = Q(pk__in=[])
        if _is_return_pimpinan_actor(user):
            pengembalian_filter = Q(
                return_current_step__in=[
                    ReturnStepChoices.PIMPINAN_BA,
                    ReturnStepChoices.PIMPINAN_TRANSFER,
                ]
            )
        return qs.filter(pengajuan_filter | pengembalian_filter).distinct()
    return qs.none()


def _get_pending_pemeliharaan_queryset(user):
    role_name = get_role_name(user)
    qs = PemeliharaanPengajuan.objects.select_related("pemohon", "alat").prefetch_related(
        "items"
    )
    if role_name == ROLE_SUPER_ADMIN:
        return qs.filter(
            current_step__in=[
                StepPemeliharaanChoices.KEPALA_LAB,
                StepPemeliharaanChoices.PIMPINAN,
            ]
        )
    if role_name == ROLE_KEPALA_LAB:
        return qs.filter(current_step=StepPemeliharaanChoices.KEPALA_LAB)
    if _is_return_pimpinan_actor(user):
        return qs.filter(current_step=StepPemeliharaanChoices.PIMPINAN)
    return qs.none()


def _get_mixed_sort_value(item):
    value = getattr(item, "submitted_at", None) or getattr(item, "updated_at", None)
    return value or timezone.now()


def _maintenance_search_text(item):
    return " ".join(
        [
            item.nomor_pengajuan or "",
            item.nama_pemohon or "",
            item.alat_label or "",
            item.status_label or "",
            item.kondisi_ringkas or "",
        ]
    )


def _paginate_verifikasi_items(request, peminjaman_qs, pemeliharaan_qs):
    selected_entries = normalize_entries(request.GET.get("entries"))
    search_query = normalize_search(request.GET.get("q"))

    if search_query:
        peminjaman_filter = Q()
        for field in VERIFIKASI_LIST_SEARCH_FIELDS:
            peminjaman_filter |= Q(**{f"{field}__icontains": search_query})
        peminjaman_items = list(peminjaman_qs.filter(peminjaman_filter).distinct())
        pemeliharaan_items = [
            item
            for item in pemeliharaan_qs
            if search_query.casefold() in _maintenance_search_text(item).casefold()
        ]
    else:
        peminjaman_items = list(peminjaman_qs)
        pemeliharaan_items = list(pemeliharaan_qs)

    items = sorted(
        [*peminjaman_items, *pemeliharaan_items],
        key=_get_mixed_sort_value,
        reverse=True,
    )
    total_count = len(items)

    query_params = request.GET.copy()
    query_params.pop("entries", None)
    query_params.pop("page", None)
    if search_query:
        query_params["q"] = search_query
    else:
        query_params.pop("q", None)
    base_query = query_params.urlencode()

    context = {
        "selected_entries": selected_entries,
        "has_entries_filter": bool(request.GET.get("entries")),
        "entry_options": LIST_ENTRY_OPTIONS,
        "search_param": "q",
        "search_query": search_query,
        "search_max_length": LIST_SEARCH_MAX_LENGTH,
        "has_search": bool(search_query),
        "list_filter_params": [],
        "total_count": total_count,
        "start_index": 0,
        "end_index": 0,
        "page_obj": None,
        "is_paginated": False,
        "page_range": [],
        "show_all_entries": False,
        "pagination_base_query": f"{base_query}&" if base_query else "",
    }

    if selected_entries == "all":
        context.update(
            {
                "items": items,
                "start_index": 1 if total_count else 0,
                "end_index": total_count,
                "show_all_entries": True,
            }
        )
        return context

    paginator = Paginator(items, int(selected_entries))
    page_obj = paginator.get_page(request.GET.get("page", 1))
    page_range = paginator.get_elided_page_range(
        page_obj.number,
        on_each_side=1,
        on_ends=1,
    )
    context.update(
        {
            "items": page_obj.object_list,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "page_range": page_range,
            "start_index": page_obj.start_index() if total_count else 0,
            "end_index": page_obj.end_index() if total_count else 0,
        }
    )
    return context


def _user_can_act(user, obj):
    role_name = get_role_name(user)
    if role_name == ROLE_SUPER_ADMIN:
        return obj.current_step in ACTION_CHOICES or _is_return_verification(obj)
    if _is_return_verification(obj):
        if obj.return_current_step == ReturnStepChoices.USER_VERIFICATION:
            return role_name in BORROWER_CONFIRMATION_ROLES and obj.peminjam_id == user.id
        if obj.return_current_step in {
            ReturnStepChoices.TEKNISI_VERIFICATION,
            ReturnStepChoices.TEKNISI_BA,
            ReturnStepChoices.TEKNISI_TRANSFER,
        }:
            return role_name == ROLE_TEKNISI_LAB
        if obj.return_current_step in {
            ReturnStepChoices.KEPALA_BA,
            ReturnStepChoices.KEPALA_TRANSFER,
        }:
            return role_name == ROLE_KEPALA_LAB
        if obj.return_current_step in {
            ReturnStepChoices.PIMPINAN_BA,
            ReturnStepChoices.PIMPINAN_TRANSFER,
        }:
            return _is_return_pimpinan_actor(user)
        return False
    if obj.current_step == StepChoices.ADMIN_LAB:
        return role_name == ROLE_ADMIN_LAB
    if obj.current_step == StepChoices.TEKNISI_LAB:
        return role_name == ROLE_TEKNISI_LAB
    if obj.current_step == StepChoices.KEPALA_LAB:
        return role_name == ROLE_KEPALA_LAB
    if obj.current_step == StepChoices.PIMPINAN:
        return _is_related_pimpinan(user, obj)
    return False


def _user_can_act_pemeliharaan(user, obj):
    role_name = get_role_name(user)
    if role_name == ROLE_SUPER_ADMIN:
        return obj.current_step in PEMELIHARAAN_ACTION_CHOICES
    if obj.current_step == StepPemeliharaanChoices.KEPALA_LAB:
        return role_name == ROLE_KEPALA_LAB
    if obj.current_step == StepPemeliharaanChoices.PIMPINAN:
        return _is_return_pimpinan_actor(user)
    return False

def _action_requires_note(aksi):
    return ACTION_META.get(aksi, {}).get("requires_note", False)

def _get_action_config(aksi, action_choices):
    label_map = dict(action_choices or [])
    if aksi not in label_map:
        return None

    base_meta = ACTION_META.get(aksi, {})
    return {
        "value": aksi,
        "label": label_map.get(aksi, aksi.replace("_", " ").title()),
        "button_class": base_meta.get("button_class", "btn-secondary"),
        "submit_class": base_meta.get("submit_class", "btn-primary"),
        "requires_note": base_meta.get("requires_note", False),
        "modal_title": base_meta.get("modal_title", "Input Catatan"),
        "modal_submit_label": base_meta.get("modal_submit_label", "Kirim"),
        "note_label": base_meta.get("note_label", "Catatan / Alasan"),
        "note_placeholder": base_meta.get(
            "note_placeholder", "Tulis catatan verifikasi di sini."
        ),
        "note_help_text": base_meta.get("note_help_text", ""),
    }

def _build_action_buttons(action_choices):
    return [_get_action_config(aksi, action_choices) for aksi, _label in action_choices]

def _build_pemeliharaan_buttons(action_choices):
    return [button for button in _build_action_buttons(action_choices) if button]

def _reorder_pengembalian_action_buttons(action_buttons):
    order_map = {
        "perbaiki": 0,
        "setujui": 1,
    }
    return sorted(
        action_buttons,
        key=lambda button: order_map.get((button or {}).get("value"), 50),
    )

def _get_detail_context(obj, verification_mode):
    common = {
        "survei_items": obj.kegiatan_survei.all(),
    }
    if verification_mode == "pengembalian":
        asal_maps = build_asal_peminjaman_maps(obj)
        penunjang_borrowed_map = {
            item.barang_id: item
            for item in obj.barang_penunjang_items.select_related("barang")
        }
        peralatan_lab_borrowed_map = {
            item.barang_id: item
            for item in obj.peralatan_laboratorium_items.select_related("barang")
        }
        bahan_borrowed_map = {
            item.bahan_id: item
            for item in obj.bahan_operasional_items.select_related("bahan")
        }
        for borrowed in penunjang_borrowed_map.values():
            borrowed.asal_peminjaman_label = resolve_asal_peminjaman_label(
                asal_maps,
                "penunjang",
                borrowed.barang_id,
                getattr(borrowed, "volume", 0),
            )
        for borrowed in peralatan_lab_borrowed_map.values():
            borrowed.asal_peminjaman_label = resolve_asal_peminjaman_label(
                asal_maps,
                "peralatan_lab",
                borrowed.barang_id,
                getattr(borrowed, "volume", 0),
            )
        for borrowed in bahan_borrowed_map.values():
            borrowed.asal_peminjaman_label = resolve_asal_peminjaman_label(
                asal_maps, "bahan", borrowed.bahan_id, getattr(borrowed, "volume", 0)
            )

        penunjang_rows = []
        for item in obj.pengembalian_penunjang_items.select_related(
            "barang", "transfer_target"
        ):
            borrowed = penunjang_borrowed_map.get(item.barang_id)
            penunjang_rows.append(
                {
                    "item": item,
                    "borrowed_volume": getattr(borrowed, "volume", 0),
                    "asal_peminjaman_label": getattr(
                        borrowed, "asal_peminjaman_label", "Laboratorium"
                    ),
                }
            )

        peralatan_lab_rows = []
        for item in obj.pengembalian_peralatan_laboratorium_items.select_related(
            "barang", "transfer_target"
        ):
            borrowed = peralatan_lab_borrowed_map.get(item.barang_id)
            peralatan_lab_rows.append(
                {
                    "item": item,
                    "borrowed_volume": getattr(borrowed, "volume", 0),
                    "asal_peminjaman_label": getattr(
                        borrowed, "asal_peminjaman_label", "Laboratorium"
                    ),
                }
            )

        bahan_rows = []
        for item in obj.pengembalian_bahan_items.select_related("bahan"):
            borrowed = bahan_borrowed_map.get(item.bahan_id)
            bahan_rows.append(
                {
                    "item": item,
                    "borrowed_volume": getattr(borrowed, "volume", 0),
                    "asal_peminjaman_label": getattr(
                        borrowed, "asal_peminjaman_label", "Laboratorium"
                    ),
                }
            )

        return_meta = {
            ReturnStepChoices.TEKNISI_VERIFICATION: {
                "page_subtitle": "Teknisi Laboratorium memverifikasi data pengembalian yang diajukan user.",
                "action_card_title": "Aksi Verifikasi Teknisi Lab",
                "action_card_subtitle": "Periksa data pengembalian. Jika seluruh item hanya dikembalikan baik, proses selesai di tahap ini. Jika ada transfer, rusak, atau hilang, proses dilanjutkan ke Kepala Lab.",
            },
            ReturnStepChoices.USER_VERIFICATION: {
                "page_subtitle": "Tahap verifikasi user pengembalian lama.",
                "action_card_title": "Aksi Verifikasi User",
                "action_card_subtitle": "Tahap ini dipertahankan untuk kompatibilitas data lama.",
            },
            ReturnStepChoices.TEKNISI_BA: {
                "page_subtitle": "Tahap teknisi lama pada alur pengembalian.",
                "action_card_title": "Aksi Verifikasi Teknisi Lab",
                "action_card_subtitle": "Tahap ini dipertahankan untuk kompatibilitas data lama.",
            },
            ReturnStepChoices.KEPALA_BA: {
                "page_subtitle": "Kepala Lab memverifikasi pengembalian untuk item transfer, rusak, atau hilang.",
                "action_card_title": "Aksi Verifikasi Kepala Lab",
                "action_card_subtitle": "Pilih Setujui untuk melanjutkan ke Ketua Tim Layanan Teknis, atau Perbaiki untuk mengembalikan ke Teknisi Laboratorium.",
            },
            ReturnStepChoices.PIMPINAN_BA: {
                "page_subtitle": "Ketua Tim Layanan Teknis memverifikasi pengembalian sebelum dinyatakan selesai.",
                "action_card_title": "Aksi Verifikasi Ketua Tim",
                "action_card_subtitle": "Pilih Setujui untuk menyelesaikan pengembalian. Jika terdapat item rusak atau hilang, dokumen berita acara akan tersedia otomatis setelah selesai.",
            },
            ReturnStepChoices.TEKNISI_TRANSFER: {
                "page_subtitle": "Tahap teknisi lama pada alur pengembalian.",
                "action_card_title": "Aksi Verifikasi Teknisi Lab",
                "action_card_subtitle": "Tahap ini dipertahankan untuk kompatibilitas data lama.",
            },
            ReturnStepChoices.KEPALA_TRANSFER: {
                "page_subtitle": "Kepala Lab memverifikasi pengembalian untuk item transfer, rusak, atau hilang.",
                "action_card_title": "Aksi Verifikasi Kepala Lab",
                "action_card_subtitle": "Pilih Setujui untuk melanjutkan ke Ketua Tim Layanan Teknis, atau Perbaiki untuk mengembalikan ke Teknisi Laboratorium.",
            },
            ReturnStepChoices.PIMPINAN_TRANSFER: {
                "page_subtitle": "Ketua Tim Layanan Teknis memverifikasi pengembalian sebelum dinyatakan selesai.",
                "action_card_title": "Aksi Verifikasi Ketua Tim",
                "action_card_subtitle": "Pilih Setujui untuk menyelesaikan pengembalian. Jika terdapat item rusak atau hilang, dokumen berita acara akan tersedia otomatis setelah selesai.",
            },
        }.get(obj.return_current_step, {})

        lab_rows = []
        for item in obj.pengembalian_lab_items.select_related(
            "barang", "transfer_target"
        ).all():
            lab_rows.append(
                {
                    "item": item,
                    "asal_peminjaman_label": resolve_asal_peminjaman_label(
                        asal_maps, "lab", item.barang_id
                    ),
                }
            )
        return {
            **common,
            "lab_rows": lab_rows,
            "penunjang_rows": penunjang_rows,
            "peralatan_lab_rows": peralatan_lab_rows,
            "bahan_rows": bahan_rows,
            "has_lab_return_rows": bool(lab_rows),
            "has_penunjang_return_rows": bool(penunjang_rows),
            "has_peralatan_lab_return_rows": bool(peralatan_lab_rows),
            "has_bahan_return_rows": bool(bahan_rows),
            "page_title": "Detail Verifikasi Pengembalian",
            "page_subtitle": return_meta.get(
                "page_subtitle", "Verifikasi data pengembalian per alat."
            ),
            "timeline_title": "Riwayat Verifikasi Pengembalian",
            "action_card_title": return_meta.get(
                "action_card_title", "Aksi Verifikasi Pengembalian"
            ),
            "action_card_subtitle": return_meta.get(
                "action_card_subtitle",
                "Pilih aksi sesuai tahap pengembalian yang sedang berjalan.",
            ),
            "return_process_label": return_meta.get(
                "return_process_label", "Buka Form Pengembalian"
            ),
            "pengukuran_data": obj.get_pengukuran_data(),
        }
    lab_items = list(obj.barang_laboratorium_items.all())
    penunjang_items = list(obj.barang_penunjang_items.all())
    peralatan_lab_items = list(obj.peralatan_laboratorium_items.all())
    bahan_items = list(obj.bahan_operasional_items.all())
    asal_maps = build_asal_peminjaman_maps(obj)
    for item in lab_items:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "lab", item.barang_id
        )
    for item in penunjang_items:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "penunjang", item.barang_id, getattr(item, "volume", 0)
        )
    for item in peralatan_lab_items:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "peralatan_lab", item.barang_id, getattr(item, "volume", 0)
        )
    for item in bahan_items:
        item.asal_peminjaman_label = resolve_asal_peminjaman_label(
            asal_maps, "bahan", item.bahan_id, getattr(item, "volume", 0)
        )
    return {
        **common,
        "lab_items": lab_items,
        "penunjang_items": penunjang_items,
        "peralatan_lab_items": peralatan_lab_items,
        "bahan_items": bahan_items,
        "has_lab_items": bool(lab_items),
        "has_penunjang_items": bool(penunjang_items),
        "has_peralatan_lab_items": bool(peralatan_lab_items),
        "has_bahan_items": bool(bahan_items),
        "page_title": "Detail Verifikasi Pengajuan",
        "page_subtitle": "Verifikasi pengajuan peminjaman Laboratorium.",
        "timeline_title": "Riwayat Verifikasi",
    }


@login_required
def index(request):
    pagination_context = _paginate_verifikasi_items(
        request,
        _get_pending_queryset(request.user),
        _get_pending_pemeliharaan_queryset(request.user),
    )
    context = {
        "items": pagination_context["items"],
        "page_title": "Verifikasi Permintaan",
        "page_subtitle": "Kelola proses verifikasi transaksi SILEBAT.",
    }
    context.update(pagination_context)
    return render(request, "verifikasi/verifikasi_list.html", context)


@login_required
def detail(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "layanan_kegiatan",
            "tim_kegiatan",
            "instansi_tujuan",
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
            "timeline_entries__actor",
        ),
        pk=pk,
    )

    if not _user_can_act(request.user, obj):
        return deny_access(
            request, "Anda tidak memiliki giliran verifikasi untuk pengajuan ini."
        )

    verification_mode = "pengembalian" if _is_return_verification(obj) else "pengajuan"
    action_choices = (
        RETURN_ACTION_CHOICES.get(obj.return_current_step, [])
        if verification_mode == "pengembalian"
        else ACTION_CHOICES.get(obj.current_step, [])
    )
    action_buttons = [
        button for button in _build_action_buttons(action_choices) if button
    ]
    if verification_mode == "pengembalian":
        action_buttons = _reorder_pengembalian_action_buttons(action_buttons)
    selected_action = ""
    catatan_value = ""
    open_action_modal = False

    if request.method == "POST":
        form = VerifikasiAksiForm(request.POST, action_choices=action_choices)
        selected_action = (request.POST.get("aksi") or "").strip()
        catatan_value = (request.POST.get("catatan") or "").strip()
        if form.is_valid():
            aksi = form.cleaned_data["aksi"]
            catatan = (form.cleaned_data.get("catatan") or "").strip()

            if _action_requires_note(aksi) and not catatan:
                error_label = ACTION_META.get(aksi, {}).get(
                    "note_label", "Catatan / Alasan"
                )
                error_label = error_label.replace(":", "").strip()
                form.add_error(
                    "catatan",
                    f"*{error_label} wajib diisi.",
                )
                open_action_modal = True
                selected_action = aksi
            else:
                previous_current_step = obj.current_step
                previous_return_step = obj.return_current_step
                _process_action(
                    request, obj, aksi, catatan, verification_mode=verification_mode
                )
                sync_transaction_notifications(
                    obj,
                    actor=request.user,
                    source_action=aksi,
                    previous_current_step=previous_current_step,
                    previous_return_step=previous_return_step,
                    action_note=catatan,
                )
                return redirect("verifikasi:index")
        elif _action_requires_note(selected_action):
            open_action_modal = True
    else:
        form = VerifikasiAksiForm(action_choices=action_choices)

    active_action = _get_action_config(selected_action, action_choices)

    role_name = get_role_name(request.user)

    return render(
        request,
        "verifikasi/verifikasi_detail.html",
        {
            "obj": obj,
            "form": form,
            "action_buttons": action_buttons,
            "active_action": active_action,
            "selected_action": selected_action,
            "catatan_value": catatan_value,
            "open_action_modal": open_action_modal,
            "verification_mode": verification_mode,
            "can_delete_pengajuan": role_name == ROLE_SUPER_ADMIN,
            "show_return_process_link": False,
            "can_edit_pengajuan": _can_edit_pengajuan(request.user, obj),
            "can_edit_pengembalian": _can_edit_pengembalian(request.user, obj),
            **_get_detail_context(obj, verification_mode),
        },
    )


def _get_pemeliharaan_detail_context(obj):
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

    return {
        "items": items,
        "repair_items": repair_items,
        "pemeriksaan_fotos": pemeriksaan_fotos,
        "page_title": "Detail Verifikasi Pemeliharaan",
        "page_subtitle": "Verifikasi pengajuan pemeliharaan peralatan survei lapangan.",
        "timeline_title": "Riwayat Verifikasi",
    }


@login_required
def detail_pemeliharaan(request, pk):
    obj = get_object_or_404(
        PemeliharaanPengajuan.objects.select_related("pemohon", "alat").prefetch_related(
            "items__fotos",
            "timeline_entries__actor",
        ),
        pk=pk,
    )

    if not _user_can_act_pemeliharaan(request.user, obj):
        return deny_access(
            request,
            "Anda tidak memiliki giliran verifikasi untuk pengajuan pemeliharaan ini.",
        )

    action_choices = PEMELIHARAAN_ACTION_CHOICES.get(obj.current_step, [])
    action_buttons = _build_pemeliharaan_buttons(action_choices)
    selected_action = ""
    catatan_value = ""
    open_action_modal = False

    if request.method == "POST":
        form = VerifikasiAksiForm(request.POST, action_choices=action_choices)
        selected_action = (request.POST.get("aksi") or "").strip()
        catatan_value = (request.POST.get("catatan") or "").strip()
        if form.is_valid():
            aksi = form.cleaned_data["aksi"]
            catatan = (form.cleaned_data.get("catatan") or "").strip()
            if _action_requires_note(aksi) and not catatan:
                error_label = ACTION_META.get(aksi, {}).get(
                    "note_label", "Catatan / Alasan"
                )
                form.add_error("catatan", f"*{error_label.replace(':', '').strip()} wajib diisi.")
                open_action_modal = True
                selected_action = aksi
            else:
                _process_pemeliharaan_action(request, obj, aksi, catatan)
                return redirect("verifikasi:index")
        elif _action_requires_note(selected_action):
            open_action_modal = True
    else:
        form = VerifikasiAksiForm(action_choices=action_choices)

    active_action = _get_action_config(selected_action, action_choices)

    return render(
        request,
        "verifikasi/verifikasi_detail.html",
        {
            "obj": obj,
            "form": form,
            "action_buttons": action_buttons,
            "active_action": active_action,
            "selected_action": selected_action,
            "catatan_value": catatan_value,
            "open_action_modal": open_action_modal,
            "verification_mode": "pemeliharaan",
            "can_delete_pengajuan": False,
            "show_return_process_link": False,
            "can_edit_pengajuan": False,
            "can_edit_pengembalian": False,
            **_get_pemeliharaan_detail_context(obj),
        },
    )


def _reject_peminjaman(request, obj, status_field, stage, timeline_action, user, catatan):
    setattr(obj, status_field, DecisionChoices.REJECTED)
    obj.current_step = StepChoices.REJECTED
    obj.save()
    obj.release_inventory_allocation()
    obj.add_timeline(stage, timeline_action, user, catatan)
    messages.success(request, "Pengajuan berhasil ditolak.")


def _process_pemeliharaan_action(request, obj, aksi, catatan):
    now = timezone.now()
    user = request.user

    if obj.current_step == StepPemeliharaanChoices.KEPALA_LAB:
        obj.kepala_lab_by = user
        obj.kepala_lab_at = now
        obj.kepala_lab_note = catatan
        if aksi == "tolak":
            obj.kepala_lab_status = KeputusanPemeliharaanChoices.REJECTED
            obj.current_step = StepPemeliharaanChoices.DITOLAK
            obj.add_timeline(
                "Kepala Lab",
                "Pengajuan pemeliharaan ditolak Kepala Lab dan dinyatakan selesai",
                user,
                catatan,
            )
            messages.success(
                request,
                "Pengajuan pemeliharaan ditolak dan proses selesai.",
            )
        elif aksi == "perbaiki":
            obj.kepala_lab_status = KeputusanPemeliharaanChoices.REVISION
            obj.current_step = StepPemeliharaanChoices.DIKEMBALIKAN
            obj.add_timeline(
                "Kepala Lab",
                "Pengajuan pemeliharaan dikembalikan oleh Kepala Lab untuk perbaikan",
                user,
                catatan,
            )
            messages.success(
                request,
                "Pengajuan pemeliharaan dikembalikan ke pemohon untuk perbaikan.",
            )
        elif aksi == "setujui":
            obj.kepala_lab_status = KeputusanPemeliharaanChoices.APPROVED
            if obj.perlu_pimpinan:
                obj.current_step = StepPemeliharaanChoices.PIMPINAN
                obj.add_timeline(
                    "Kepala Lab",
                    "Pengajuan pemeliharaan disetujui Kepala Lab dan diteruskan ke Ketua Tim Layanan Teknis",
                    user,
                    catatan,
                )
                messages.success(
                    request,
                    "Pengajuan pemeliharaan disetujui dan diteruskan ke Ketua Tim Layanan Teknis.",
                )
            else:
                obj.current_step = StepPemeliharaanChoices.SELESAI
                obj.add_timeline(
                    "Kepala Lab",
                    "Pengajuan pemeliharaan disetujui Kepala Lab dan dinyatakan selesai",
                    user,
                    catatan,
                )
                messages.success(
                    request,
                    "Pengajuan pemeliharaan disetujui dan proses selesai.",
                )
        else:
            messages.error(request, "Aksi verifikasi pemeliharaan tidak valid.")
            return
        obj.save()
        if obj.current_step == StepPemeliharaanChoices.SELESAI:
            obj.catat_riwayat_alat_disetujui()
            obj.tandai_alat_baik_jika_selesai()
        elif obj.current_step == StepPemeliharaanChoices.DITOLAK:
            obj.pulihkan_kondisi_alat_awal()
        return

    if obj.current_step == StepPemeliharaanChoices.PIMPINAN:
        obj.pimpinan_by = user
        obj.pimpinan_at = now
        obj.pimpinan_note = catatan
        if aksi == "tolak":
            obj.pimpinan_status = KeputusanPemeliharaanChoices.REJECTED
            obj.current_step = StepPemeliharaanChoices.DITOLAK
            obj.add_timeline(
                "Ketua Tim Layanan Teknis",
                "Pengajuan pemeliharaan ditolak Ketua Tim Layanan Teknis dan dinyatakan selesai",
                user,
                catatan,
            )
            messages.success(
                request,
                "Pengajuan pemeliharaan ditolak Ketua Tim Layanan Teknis dan proses selesai.",
            )
        elif aksi == "perbaiki":
            obj.pimpinan_status = KeputusanPemeliharaanChoices.REVISION
            obj.current_step = StepPemeliharaanChoices.DIKEMBALIKAN
            obj.add_timeline(
                "Ketua Tim Layanan Teknis",
                "Pengajuan pemeliharaan dikembalikan oleh Ketua Tim Layanan Teknis untuk perbaikan",
                user,
                catatan,
            )
            messages.success(
                request,
                "Pengajuan pemeliharaan dikembalikan ke pemohon untuk perbaikan.",
            )
        elif aksi == "setujui":
            obj.pimpinan_status = KeputusanPemeliharaanChoices.APPROVED
            obj.current_step = StepPemeliharaanChoices.SELESAI
            obj.add_timeline(
                "Ketua Tim Layanan Teknis",
                "Pengajuan pemeliharaan disetujui Ketua Tim Layanan Teknis dan dinyatakan selesai",
                user,
                catatan,
            )
            messages.success(
                request,
                "Pengajuan pemeliharaan disetujui Ketua Tim Layanan Teknis dan proses selesai.",
            )
        else:
            messages.error(request, "Aksi verifikasi pemeliharaan tidak valid.")
            return
        obj.save()
        if obj.current_step == StepPemeliharaanChoices.SELESAI:
            obj.catat_riwayat_alat_disetujui()
            obj.tandai_alat_baik_jika_selesai()
        elif obj.current_step == StepPemeliharaanChoices.DITOLAK:
            obj.pulihkan_kondisi_alat_awal()
        return

def _process_action(request, obj, aksi, catatan, verification_mode="pengajuan"):
    now = timezone.now()
    user = request.user

    if verification_mode == "pengembalian":
        if obj.return_current_step == ReturnStepChoices.TEKNISI_VERIFICATION:
            next_step = obj.get_step_pengembalian()
            obj.return_current_step = next_step
            obj.save(update_fields=["return_current_step", "updated_at"])
            if next_step == ReturnStepChoices.COMPLETED:
                obj.add_timeline(
                    "Pengembalian",
                    "Verifikasi pengembalian disetujui Teknisi Lab dan pengembalian dinyatakan selesai",
                    user,
                    catatan,
                )
                obj.apply_pengembalian_inventory()
                messages.success(
                    request,
                    "Verifikasi Teknisi Lab selesai dan pengembalian dinyatakan selesai.",
                )
            else:
                obj.add_timeline(
                    "Pengembalian",
                    "Verifikasi pengembalian disetujui Teknisi Lab dan diteruskan ke Kepala Lab",
                    user,
                    catatan,
                )
                messages.success(
                    request,
                    "Verifikasi Teknisi Lab selesai. Menunggu verifikasi Kepala Lab.",
                )
            return

        if obj.return_current_step == ReturnStepChoices.USER_VERIFICATION:
            obj.return_user_verification_at = now
            obj.return_user_verification_note = catatan
            if aksi == "sesuai":
                obj.return_user_verification_status = DecisionChoices.APPROVED
                next_step = obj.get_step_pengembalian()
                obj.return_current_step = next_step
                obj.save(
                    update_fields=[
                        "return_user_verification_status",
                        "return_user_verification_at",
                        "return_user_verification_note",
                        "return_current_step",
                        "updated_at",
                    ]
                )
                obj.add_timeline(
                    "User",
                    "Data pengembalian dinyatakan sudah sesuai oleh User",
                    user,
                    catatan,
                )
                if next_step == ReturnStepChoices.COMPLETED:
                    obj.apply_pengembalian_inventory()
                    messages.success(
                        request,
                        "Verifikasi user berhasil. Pengembalian selesai diproses.",
                    )
                else:
                    messages.success(
                        request,
                        "Verifikasi user berhasil. Proses dilanjutkan ke Kepala Lab.",
                    )
            else:
                obj.return_user_verification_status = DecisionChoices.MISMATCH
                obj.return_current_step = ReturnStepChoices.TEKNISI_VERIFICATION
                obj.save(
                    update_fields=[
                        "return_user_verification_status",
                        "return_user_verification_at",
                        "return_user_verification_note",
                        "return_current_step",
                        "updated_at",
                    ]
                )
                obj.add_timeline(
                    "User",
                    "Data pengembalian dinyatakan belum sesuai oleh User",
                    user,
                    catatan,
                )
                messages.success(
                    request,
                    "Data pengembalian dikembalikan ke Teknisi Laboratorium untuk perbaikan.",
                )
            return

        if obj.return_current_step in {
            ReturnStepChoices.TEKNISI_BA,
            ReturnStepChoices.TEKNISI_TRANSFER,
        }:
            obj.return_current_step = ReturnStepChoices.KEPALA_BA
            obj.save(update_fields=["return_current_step", "updated_at"])
            obj.add_timeline(
                "Pengembalian",
                "Tahap teknisi lama dialihkan ke verifikasi Kepala Lab",
                user,
                catatan,
            )
            messages.success(request, "Proses pengembalian diteruskan ke Kepala Lab.")
            return

        if obj.return_current_step in {
            ReturnStepChoices.KEPALA_BA,
            ReturnStepChoices.KEPALA_TRANSFER,
        }:
            if aksi == "setujui":
                obj.return_current_step = ReturnStepChoices.PIMPINAN_BA
                obj.save(update_fields=["return_current_step", "updated_at"])
                obj.add_timeline(
                    "Pengembalian",
                    "Pengembalian disetujui Kepala Lab",
                    user,
                    catatan,
                )
                messages.success(
                    request, "Pengembalian diteruskan ke Ketua Tim Layanan Teknis."
                )
            elif aksi == "perbaiki":
                obj.return_current_step = ReturnStepChoices.TEKNISI_VERIFICATION
                obj.save(update_fields=["return_current_step", "updated_at"])
                obj.add_timeline(
                    "Pengembalian",
                    "Pengembalian dikembalikan ke Teknisi Lab untuk perbaikan",
                    user,
                    catatan,
                )
                messages.success(
                    request, "Pengembalian dikembalikan ke Teknisi Laboratorium."
                )
            else:
                messages.error(
                    request, "Aksi verifikasi tidak valid untuk tahap pengembalian ini."
                )
            return

        if obj.return_current_step in {
            ReturnStepChoices.PIMPINAN_BA,
            ReturnStepChoices.PIMPINAN_TRANSFER,
        }:
            if aksi == "setujui":
                obj.add_timeline(
                    "Pengembalian",
                    "Pengembalian disetujui Ketua Tim Layanan Teknis dan dinyatakan selesai",
                    user,
                    catatan,
                )
                obj.return_current_step = ReturnStepChoices.COMPLETED
                obj.save(update_fields=["return_current_step", "updated_at"])
                obj.apply_pengembalian_inventory()
                if obj.pengembalian_has_issue():
                    messages.success(
                        request,
                        "Pengembalian disetujui dan selesai. Dokumen berita acara tersedia otomatis untuk item rusak atau hilang.",
                    )
                else:
                    messages.success(
                        request,
                        "Pengembalian disetujui dan proses pengembalian selesai.",
                    )
            elif aksi == "perbaiki":
                obj.return_current_step = ReturnStepChoices.TEKNISI_VERIFICATION
                obj.save(update_fields=["return_current_step", "updated_at"])
                obj.add_timeline(
                    "Pengembalian",
                    "Pengembalian dikembalikan oleh Ketua Tim Layanan Teknis untuk perbaikan",
                    user,
                    catatan,
                )
                messages.success(
                    request, "Pengembalian dikembalikan ke Teknisi Laboratorium."
                )
            else:
                messages.error(
                    request, "Aksi verifikasi tidak valid untuk tahap pengembalian ini."
                )
            return

    if obj.current_step == StepChoices.ADMIN_LAB:
        obj.admin_lab_by = user
        obj.admin_lab_at = now
        obj.admin_lab_note = catatan
        if aksi == "setujui":
            obj.admin_lab_status = DecisionChoices.APPROVED
            obj.current_step = StepChoices.TEKNISI_LAB
            obj.add_timeline(
                "Admin Lab", "Pengajuan disetujui Admin Lab", user, catatan
            )
            obj.save()
            messages.success(request, "Pengajuan berhasil diteruskan ke Teknisi Lab.")
        else:
            _reject_peminjaman(
                request,
                obj,
                "admin_lab_status",
                "Admin Lab",
                "Pengajuan ditolak Admin Lab",
                user,
                catatan,
            )
        return

    if obj.current_step == StepChoices.TEKNISI_LAB:
        if not obj.teknisi_lab_by_id:
            obj.teknisi_lab_by = user
        obj.teknisi_lab_at = now
        obj.teknisi_lab_note = catatan
        obj.teknisi_lab_status = DecisionChoices.READY
        obj.kepala_lab_status = DecisionChoices.PENDING
        obj.current_step = StepChoices.KEPALA_LAB
        obj.add_timeline(
            "Teknisi Lab",
            "Pemenuhan barang selesai dan dikirim ke Kepala Lab",
            user,
            catatan,
        )
        obj.save()
        messages.success(
            request,
            "Pengajuan berhasil diteruskan ke Kepala Lab.",
        )
        return

    if obj.current_step == StepChoices.KEPALA_LAB:
        obj.kepala_lab_by = user
        obj.kepala_lab_at = now
        obj.kepala_lab_note = catatan
        if aksi == "setujui":
            obj.kepala_lab_status = DecisionChoices.APPROVED
            obj.current_step = StepChoices.PIMPINAN
            obj.add_timeline(
                "Kepala Laboratorium",
                "Pengajuan disetujui Kepala Laboratorium",
                user,
                catatan,
            )
            obj.save()
            messages.success(
                request,
                "Pengajuan diteruskan ke tahap verifikasi ketua tim.",
            )
        elif aksi == "tolak":
            _reject_peminjaman(
                request,
                obj,
                "kepala_lab_status",
                "Kepala Laboratorium",
                "Pengajuan ditolak Kepala Laboratorium",
                user,
                catatan,
            )
        else:
            obj.kepala_lab_status = DecisionChoices.REVISION
            obj.teknisi_lab_status = DecisionChoices.PENDING
            obj.current_step = StepChoices.TEKNISI_LAB
            obj.add_timeline(
                "Kepala Laboratorium",
                "Pengajuan dikembalikan ke Teknisi Lab untuk perbaikan",
                user,
                catatan,
            )
            obj.save()
            messages.success(
                request,
                "Pengajuan berhasil dikembalikan ke Teknisi Lab untuk perbaikan.",
            )
        return

    if obj.current_step == StepChoices.PIMPINAN:
        obj.pimpinan_by = user
        obj.pimpinan_at = now
        obj.pimpinan_note = catatan
        if aksi == "setujui":
            obj.pimpinan_status = DecisionChoices.APPROVED
            obj.current_step = StepChoices.APPROVED
            obj.save()
            # Pengajuan baru sudah membooking stok saat dibuat; baris ini menjadi pengaman untuk data lama.
            obj.apply_inventory_allocation()
            obj.add_timeline(
                "Pimpinan",
                "Pengajuan disetujui pimpinan dan dinyatakan sah",
                user,
                catatan,
            )
            messages.success(
                request,
                "Pengajuan selesai disetujui. Form peminjaman kini sah dan PDF dapat diunduh.",
            )
        elif aksi == "tolak":
            _reject_peminjaman(
                request,
                obj,
                "pimpinan_status",
                "Pimpinan",
                "Pengajuan ditolak pimpinan",
                user,
                catatan,
            )
        else:
            obj.pimpinan_status = DecisionChoices.REVISION
            obj.teknisi_lab_status = DecisionChoices.PENDING
            obj.current_step = StepChoices.TEKNISI_LAB
            obj.save()
            obj.add_timeline(
                "Pimpinan",
                "Pengajuan dikembalikan ke Teknisi Lab untuk perbaikan",
                user,
                catatan,
            )
            messages.success(
                request,
                "Pengajuan berhasil dikembalikan ke Teknisi Lab untuk perbaikan.",
            )
        return
