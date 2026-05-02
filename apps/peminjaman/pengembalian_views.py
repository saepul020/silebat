from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.notifikasi.services import sync_transaction_notifications
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

from apps.operasional.models import TimKegiatan, TIM_LAYANAN_TEKNIS_NAME

from .forms import DATE_HELP_TEXT, parse_flexible_date

from .models import (
    PeminjamanRequest,
    PengembalianBahanOperasional,
    PengembalianBarangLaboratorium,
    PengembalianBarangPenunjang,
    PengembalianPeralatanLaboratorium,
    ReturnItemStatusChoices,
    ReturnStepChoices,
    StepChoices,
    build_asal_peminjaman_maps,
    resolve_asal_peminjaman_label,
)


RETURN_APPROVAL_OPTIONS = [("setujui", "Setuju"), ("perbaiki", "Perbaiki")]
RETURN_PIMPINAN_TEAM_NAME = TIM_LAYANAN_TEKNIS_NAME
RETURN_PIMPINAN_LABEL = "Ketua Tim Layanan Teknis"


def _can_edit_return_end_date(user, obj):
    return get_role_name(user) in {ROLE_TEKNISI_LAB, ROLE_SUPER_ADMIN} and obj.current_step == StepChoices.APPROVED


def _handle_tanggal_selesai_update(request, obj):
    raw_value = (request.POST.get("tanggal_selesai") or "").strip()
    errors = []

    if not _can_edit_return_end_date(request.user, obj):
        return {
            "allowed": False,
            "errors": ["Anda tidak memiliki hak untuk mengubah selesai tanggal pada peminjaman ini."],
            "value": raw_value,
            "open_modal": False,
        }

    if not raw_value:
        errors.append("Selesai tanggal wajib diisi.")
        return {"allowed": True, "errors": errors, "value": raw_value, "open_modal": True}

    try:
        parsed_date = parse_flexible_date(raw_value)
    except (TypeError, ValueError):
        errors.append(DATE_HELP_TEXT)
        return {"allowed": True, "errors": errors, "value": raw_value, "open_modal": True}

    if obj.tanggal_mulai and parsed_date and parsed_date < obj.tanggal_mulai:
        errors.append("Tanggal selesai tidak boleh lebih awal dari tanggal mulai.")
        return {"allowed": True, "errors": errors, "value": raw_value, "open_modal": True}

    previous_date = obj.tanggal_selesai
    obj.tanggal_selesai = parsed_date
    if obj.tanggal_mulai and obj.tanggal_selesai:
        obj.total_hari = ((obj.tanggal_selesai - obj.tanggal_mulai).days or 0) + 1
    obj.save(update_fields=["tanggal_selesai", "total_hari", "updated_at"])

    note = f"Selesai Tanggal diperbarui dari {previous_date.strftime('%d %b %Y')} menjadi {parsed_date.strftime('%d %b %Y')}"
    obj.add_timeline("Peminjaman", "Selesai tanggal peminjaman diperbarui", request.user, note)
    messages.success(request, "Selesai tanggal peminjaman berhasil diperbarui.")
    return {"allowed": True, "errors": [], "value": parsed_date.strftime('%d %b %Y'), "open_modal": False}


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
    return (RETURN_PIMPINAN_TEAM_NAME.casefold() in normalized) or ("layanan teknis" in normalized)


def _can_view_pengembalian(user, obj):
    role_name = get_role_name(user)
    if role_name in {ROLE_SUPER_ADMIN, ROLE_ADMIN_LAB, ROLE_TEKNISI_LAB, ROLE_KEPALA_LAB}:
        return True
    if role_name == ROLE_PIMPINAN:
        return _is_return_pimpinan_actor(user)
    return role_name == ROLE_USER and obj.peminjam_id == user.id


def _can_submit_pengembalian(user, obj):
    role_name = get_role_name(user)
    if role_name in {ROLE_SUPER_ADMIN, ROLE_ADMIN_LAB, ROLE_TEKNISI_LAB}:
        return True
    return role_name == ROLE_USER and obj.peminjam_id == user.id


def _can_process_step(user, obj):
    role_name = get_role_name(user)
    if role_name == ROLE_SUPER_ADMIN:
        return True
    if obj.return_current_step == ReturnStepChoices.NONE:
        return _can_submit_pengembalian(user, obj)
    if obj.return_current_step in {
        ReturnStepChoices.TEKNISI_VERIFICATION,
        ReturnStepChoices.USER_VERIFICATION,
        ReturnStepChoices.TEKNISI_BA,
        ReturnStepChoices.TEKNISI_TRANSFER,
    }:
        return role_name == ROLE_TEKNISI_LAB
    if obj.return_current_step in {ReturnStepChoices.KEPALA_BA, ReturnStepChoices.KEPALA_TRANSFER}:
        return role_name == ROLE_KEPALA_LAB
    if obj.return_current_step in {ReturnStepChoices.PIMPINAN_BA, ReturnStepChoices.PIMPINAN_TRANSFER}:
        return _is_return_pimpinan_actor(user)
    return False


def _get_transfer_targets(obj):
    qs = (
        PeminjamanRequest.objects.filter(
            current_step=StepChoices.APPROVED,
            return_current_step=ReturnStepChoices.NONE,
        )
        .exclude(pk=obj.pk)
        .order_by("-submitted_at")
    )
    return list(qs)


def _build_rows(obj):
    existing_lab = {item.barang_id: item for item in obj.pengembalian_lab_items.all()}
    existing_penunjang = {item.barang_id: item for item in obj.pengembalian_penunjang_items.all()}
    existing_peralatan_lab = {item.barang_id: item for item in obj.pengembalian_peralatan_laboratorium_items.all()}
    existing_bahan = {item.bahan_id: item for item in obj.pengembalian_bahan_items.all()}
    asal_maps = build_asal_peminjaman_maps(obj)

    lab_rows = []
    for borrowed in obj.barang_laboratorium_items.select_related("barang"):
        borrowed.asal_peminjaman_label = resolve_asal_peminjaman_label(asal_maps, "lab", borrowed.barang_id)
        current = existing_lab.get(borrowed.barang_id)
        lab_rows.append(
            {
                "borrowed": borrowed,
                "asal_peminjaman_label": getattr(borrowed, "asal_peminjaman_label", "Laboratorium"),
                "status": getattr(current, "status", ""),
                "transfer_target_id": getattr(current, "transfer_target_id", None),
                "transfer_target": getattr(current, "transfer_target", None),
                "inline_errors": [],
                "field_errors": {},
            }
        )

    penunjang_rows = []
    for borrowed in obj.barang_penunjang_items.select_related("barang"):
        borrowed.asal_peminjaman_label = resolve_asal_peminjaman_label(asal_maps, "penunjang", borrowed.barang_id, getattr(borrowed, "volume", 0))
        current = existing_penunjang.get(borrowed.barang_id)
        default_returned = "" if current is None else current.qty_dikembalikan
        penunjang_rows.append(
            {
                "borrowed": borrowed,
                "qty_dikembalikan": default_returned,
                "qty_rusak": "" if current is None else current.qty_rusak,
                "qty_hilang": "" if current is None else current.qty_hilang,
                "qty_transfer": "" if current is None else current.qty_transfer,
                "transfer_target_id": getattr(current, "transfer_target_id", None),
                "transfer_target": getattr(current, "transfer_target", None),
                "transfer_enabled": bool(getattr(current, "qty_transfer", 0) and getattr(current, "transfer_target_id", None)),
                "inline_errors": [],
                "field_errors": {},
            }
        )

    peralatan_lab_rows = []
    for borrowed in obj.peralatan_laboratorium_items.select_related("barang"):
        borrowed.asal_peminjaman_label = resolve_asal_peminjaman_label(asal_maps, "peralatan_lab", borrowed.barang_id, getattr(borrowed, "volume", 0))
        current = existing_peralatan_lab.get(borrowed.barang_id)
        default_returned = "" if current is None else current.qty_dikembalikan
        peralatan_lab_rows.append(
            {
                "borrowed": borrowed,
                "qty_dikembalikan": default_returned,
                "qty_rusak": "" if current is None else current.qty_rusak,
                "qty_hilang": "" if current is None else current.qty_hilang,
                "qty_transfer": "" if current is None else current.qty_transfer,
                "transfer_target_id": getattr(current, "transfer_target_id", None),
                "transfer_target": getattr(current, "transfer_target", None),
                "transfer_enabled": bool(getattr(current, "qty_transfer", 0) and getattr(current, "transfer_target_id", None)),
                "inline_errors": [],
                "field_errors": {},
            }
        )

    bahan_rows = []
    for borrowed in obj.bahan_operasional_items.select_related("bahan"):
        borrowed.asal_peminjaman_label = resolve_asal_peminjaman_label(asal_maps, "bahan", borrowed.bahan_id, getattr(borrowed, "volume", 0))
        current = existing_bahan.get(borrowed.bahan_id)
        bahan_rows.append(
            {
                "borrowed": borrowed,
                "qty_sisa": getattr(current, "qty_sisa", ""),
                "qty_transfer": "" if current is None else getattr(current, "qty_transfer", 0),
                "transfer_target_id": getattr(current, "transfer_target_id", None),
                "transfer_target": getattr(current, "transfer_target", None),
                "transfer_enabled": bool(getattr(current, "qty_transfer", 0) and getattr(current, "transfer_target_id", None)),
                "inline_errors": [],
                "field_errors": {},
            }
        )

    return lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows


def _parse_int(value, default=0):
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return default


def _parse_optional_non_negative_int(value):
    raw = str(value or "").strip()
    if raw == "":
        return None
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return None


def _parse_pengukuran_data(post_data):
    fields = (
        "titik_geolistrik_1d",
        "lintasan_geolistrik_2d",
        "titik_kualitas_air",
        "titik_mat",
        "titik_pumping_test",
        "titik_infiltrasi",
        "titik_debit_air",
        "lokasi_topografi",
        "titik_borehole",
        "titik_logging",
    )
    return {field: _parse_optional_non_negative_int(post_data.get(field)) for field in fields}


def _build_error_bucket():
    return {
        "global": [],
        "catatan": [],
        "lab": {},
        "penunjang": {},
        "peralatan_lab": {},
        "bahan": {},
    }


def _append_inline_error(error_bucket, section, item_id, message):
    if section in {"global", "catatan"}:
        error_bucket[section].append(message)
        return
    error_bucket.setdefault(section, {}).setdefault(item_id, []).append(message)


def _has_inline_errors(error_bucket):
    return bool(
        error_bucket["global"]
        or error_bucket["catatan"]
        or error_bucket["lab"]
        or error_bucket["penunjang"]
        or error_bucket["peralatan_lab"]
        or error_bucket["bahan"]
    )


def _classify_row_field_errors(section, row, messages):
    field_errors = {}

    def add_error(field_name, message):
        if not message:
            return
        field_errors.setdefault(field_name, []).append(message)

    for message in messages:
        normalized = str(message or "").strip()
        lowered = normalized.lower()

        if section == "lab":
            if "status pengembalian" in lowered:
                add_error("status", normalized)
                continue
            if "tujuan transfer" in lowered:
                add_error("transfer_target", normalized)
                continue
            add_error("status", normalized)
            continue

        if "tujuan transfer" in lowered:
            add_error("transfer_target", normalized)
            continue

        if "isi jumlah" in lowered and "transfer" in lowered:
            add_error("transfer_qty", normalized)
            continue

        if "jumlah dikembalikan (baik)" in lowered:
            add_error("dikembalikan", normalized)
            continue

        if "jumlah dikembalikan" in lowered:
            add_error("dikembalikan", normalized)
            continue

        if "jumlah rusak" in lowered:
            add_error("rusak", normalized)
            continue

        if "jumlah hilang" in lowered:
            add_error("hilang", normalized)
            continue

        if "jumlah transfer" in lowered:
            add_error("transfer_qty", normalized)
            continue

        if "total pengembalian" in lowered or "total dikembalikan dan transfer" in lowered:
            add_error("validation", normalized)
            continue

        add_error("validation", normalized)

    return field_errors



def _bind_inline_errors_to_rows(lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows, error_bucket):
    for row in lab_rows:
        row["inline_errors"] = error_bucket["lab"].get(row["borrowed"].barang_id, [])
        row["field_errors"] = _classify_row_field_errors("lab", row, row["inline_errors"])
    for row in penunjang_rows:
        row["inline_errors"] = error_bucket["penunjang"].get(row["borrowed"].barang_id, [])
        row["field_errors"] = _classify_row_field_errors("penunjang", row, row["inline_errors"])
    for row in peralatan_lab_rows:
        row["inline_errors"] = error_bucket["peralatan_lab"].get(row["borrowed"].barang_id, [])
        row["field_errors"] = _classify_row_field_errors("peralatan_lab", row, row["inline_errors"])
    for row in bahan_rows:
        row["inline_errors"] = error_bucket["bahan"].get(row["borrowed"].bahan_id, [])
        row["field_errors"] = _classify_row_field_errors("bahan", row, row["inline_errors"])
    return lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows


def _serialize_error_bucket(obj, error_bucket):
    serialized = {
        "global": list(error_bucket.get("global", [])),
        "catatan": list(error_bucket.get("catatan", [])),
        "rows": {},
    }

    for section, prefix, queryset, id_attr in (
        ("lab", "lab", obj.barang_laboratorium_items.all(), "barang_id"),
        ("penunjang", "penunjang", obj.barang_penunjang_items.all(), "barang_id"),
        ("peralatan_lab", "peralatan_lab", obj.peralatan_laboratorium_items.all(), "barang_id"),
        ("bahan", "bahan", obj.bahan_operasional_items.all(), "bahan_id"),
    ):
        for borrowed in queryset:
            item_id = getattr(borrowed, id_attr)
            messages = error_bucket.get(section, {}).get(item_id, [])
            if not messages:
                continue
            serialized["rows"][f"{prefix}_{item_id}"] = _classify_row_field_errors(section, {"borrowed": borrowed}, messages)

    return serialized

def _parse_pengembalian_data(obj, post_data):
    transfer_targets = {target.id for target in _get_transfer_targets(obj)}
    error_bucket = _build_error_bucket()
    parsed_lab = []
    parsed_penunjang = []
    parsed_peralatan_lab = []
    parsed_bahan = []

    allowed_lab_statuses = {choice[0] for choice in ReturnItemStatusChoices.choices}

    for borrowed in obj.barang_laboratorium_items.select_related("barang"):
        status = (post_data.get(f"lab_status_{borrowed.barang_id}") or "").strip()
        transfer_target_id = _parse_int(post_data.get(f"lab_transfer_target_{borrowed.barang_id}"), 0) or None

        if not status:
            _append_inline_error(error_bucket, "lab", borrowed.barang_id, "Status pengembalian wajib dipilih.")
            continue
        if status not in allowed_lab_statuses:
            _append_inline_error(error_bucket, "lab", borrowed.barang_id, "Status pengembalian tidak valid.")
            continue
        if status == ReturnItemStatusChoices.TRANSFER:
            if not transfer_target_id or transfer_target_id not in transfer_targets:
                _append_inline_error(error_bucket, "lab", borrowed.barang_id, "Tujuan transfer wajib dipilih.")
                continue
        else:
            transfer_target_id = None

        parsed_lab.append(
            {
                "barang": borrowed.barang,
                "status": status,
                "transfer_target_id": transfer_target_id,
            }
        )

    def parse_multi_qty_rows(queryset, section_key, id_attr):
        parsed_rows = []
        for borrowed in queryset:
            item_id = getattr(borrowed, id_attr)
            max_qty = borrowed.volume
            qty_dikembalikan = _parse_int(post_data.get(f"{section_key}_dikembalikan_{item_id}"))
            qty_rusak = _parse_int(post_data.get(f"{section_key}_rusak_{item_id}"))
            qty_hilang = _parse_int(post_data.get(f"{section_key}_hilang_{item_id}"))
            transfer_enabled = post_data.get(f"{section_key}_transfer_enabled_{item_id}") == "1"
            qty_transfer = _parse_int(post_data.get(f"{section_key}_transfer_{item_id}"))
            transfer_target_id = _parse_int(post_data.get(f"{section_key}_transfer_target_{item_id}"), 0) or None
            row_has_errors = False

            for label, qty in (
                ("Dikembalikan (Baik)", qty_dikembalikan),
                ("Rusak", qty_rusak),
                ("Hilang", qty_hilang),
                ("Transfer", qty_transfer),
            ):
                if qty > max_qty:
                    row_has_errors = True
                    _append_inline_error(
                        error_bucket,
                        section_key,
                        item_id,
                        f'Jumlah {label.lower()} tidak boleh melebihi jumlah dipinjam ({max_qty}).',
                    )

            if not transfer_enabled:
                qty_transfer = 0
                transfer_target_id = None
            else:
                if qty_transfer <= 0:
                    row_has_errors = True
                    _append_inline_error(
                        error_bucket,
                        section_key,
                        item_id,
                        "Jumlah transfer wajib diisi jika checkbox transfer aktif.",
                    )
                if not transfer_target_id or transfer_target_id not in transfer_targets:
                    row_has_errors = True
                    _append_inline_error(
                        error_bucket,
                        section_key,
                        item_id,
                        "Tujuan transfer wajib dipilih.",
                    )

            total_processed = qty_dikembalikan + qty_rusak + qty_hilang + qty_transfer
            if total_processed != max_qty:
                row_has_errors = True
                _append_inline_error(
                    error_bucket,
                    section_key,
                    item_id,
                    f"Total pengembalian harus {max_qty}/{max_qty} sesuai volume peminjaman.",
                )

            if row_has_errors:
                continue

            parsed_rows.append(
                {
                    "barang": borrowed.barang,
                    "qty_dikembalikan": qty_dikembalikan,
                    "qty_rusak": qty_rusak,
                    "qty_hilang": qty_hilang,
                    "qty_transfer": qty_transfer,
                    "transfer_target_id": transfer_target_id,
                }
            )
        return parsed_rows

    parsed_penunjang = parse_multi_qty_rows(
        obj.barang_penunjang_items.select_related("barang"),
        "penunjang",
        "barang_id",
    )
    parsed_peralatan_lab = parse_multi_qty_rows(
        obj.peralatan_laboratorium_items.select_related("barang"),
        "peralatan_lab",
        "barang_id",
    )

    for borrowed in obj.bahan_operasional_items.select_related("bahan"):
        max_qty = borrowed.volume
        qty_sisa = _parse_int(
            post_data.get(f"bahan_dikembalikan_{borrowed.bahan_id}", post_data.get(f"bahan_sisa_{borrowed.bahan_id}"))
        )
        transfer_enabled = post_data.get(f"bahan_transfer_enabled_{borrowed.bahan_id}") == "1"
        qty_transfer = _parse_int(post_data.get(f"bahan_transfer_{borrowed.bahan_id}"))
        transfer_target_id = _parse_int(post_data.get(f"bahan_transfer_target_{borrowed.bahan_id}"), 0) or None
        row_has_errors = False

        for label, qty in (
            ("Dikembalikan", qty_sisa),
            ("Transfer", qty_transfer),
        ):
            if qty > max_qty:
                row_has_errors = True
                _append_inline_error(
                    error_bucket,
                    "bahan",
                    borrowed.bahan_id,
                    f'Jumlah {label.lower()} tidak boleh melebihi jumlah dipinjam ({max_qty}).',
                )

        if not transfer_enabled:
            qty_transfer = 0
            transfer_target_id = None
        else:
            if qty_transfer <= 0:
                row_has_errors = True
                _append_inline_error(
                    error_bucket,
                    "bahan",
                    borrowed.bahan_id,
                    "Jumlah transfer wajib diisi jika checkbox transfer aktif.",
                )
            if not transfer_target_id or transfer_target_id not in transfer_targets:
                row_has_errors = True
                _append_inline_error(
                    error_bucket,
                    "bahan",
                    borrowed.bahan_id,
                    "Tujuan transfer wajib dipilih.",
                )

        total_processed = qty_sisa + qty_transfer
        if total_processed > max_qty:
            row_has_errors = True
            _append_inline_error(
                error_bucket,
                "bahan",
                borrowed.bahan_id,
                f"Total dikembalikan dan transfer tidak boleh melebihi jumlah dipinjam ({max_qty}).",
            )

        if row_has_errors:
            continue

        parsed_bahan.append(
            {
                "bahan": borrowed.bahan,
                "qty_sisa": qty_sisa,
                "qty_transfer": qty_transfer,
                "transfer_target_id": transfer_target_id,
            }
        )

    return parsed_lab, parsed_penunjang, parsed_peralatan_lab, parsed_bahan, error_bucket


@transaction.atomic
def _save_pengembalian_data(obj, parsed_lab, parsed_penunjang, parsed_peralatan_lab, parsed_bahan, pengukuran_data=None):
    lab_ids = []
    for item in parsed_lab:
        lab_ids.append(item["barang"].id)
        PengembalianBarangLaboratorium.objects.update_or_create(
            pengajuan=obj,
            barang=item["barang"],
            defaults={
                "status": item["status"],
                "transfer_target_id": item["transfer_target_id"],
            },
        )
    obj.pengembalian_lab_items.exclude(barang_id__in=lab_ids).delete()

    penunjang_ids = []
    for item in parsed_penunjang:
        penunjang_ids.append(item["barang"].id)
        PengembalianBarangPenunjang.objects.update_or_create(
            pengajuan=obj,
            barang=item["barang"],
            defaults={
                "qty_dikembalikan": item["qty_dikembalikan"],
                "qty_rusak": item["qty_rusak"],
                "qty_hilang": item["qty_hilang"],
                "qty_transfer": item["qty_transfer"],
                "transfer_target_id": item["transfer_target_id"],
            },
        )
    obj.pengembalian_penunjang_items.exclude(barang_id__in=penunjang_ids).delete()

    peralatan_lab_ids = []
    for item in parsed_peralatan_lab:
        peralatan_lab_ids.append(item["barang"].id)
        PengembalianPeralatanLaboratorium.objects.update_or_create(
            pengajuan=obj,
            barang=item["barang"],
            defaults={
                "qty_dikembalikan": item["qty_dikembalikan"],
                "qty_rusak": item["qty_rusak"],
                "qty_hilang": item["qty_hilang"],
                "qty_transfer": item["qty_transfer"],
                "transfer_target_id": item["transfer_target_id"],
            },
        )
    obj.pengembalian_peralatan_laboratorium_items.exclude(barang_id__in=peralatan_lab_ids).delete()

    bahan_ids = []
    for item in parsed_bahan:
        bahan_ids.append(item["bahan"].id)
        PengembalianBahanOperasional.objects.update_or_create(
            pengajuan=obj,
            bahan=item["bahan"],
            defaults={
                "qty_sisa": item["qty_sisa"],
                "qty_transfer": item["qty_transfer"],
                "transfer_target_id": item["transfer_target_id"],
            },
        )
    obj.pengembalian_bahan_items.exclude(bahan_id__in=bahan_ids).delete()

    if pengukuran_data is not None:
        for field_name, value in pengukuran_data.items():
            setattr(obj, field_name, value)
        obj.save(update_fields=[*pengukuran_data.keys(), "updated_at"])


def _build_post_rows(obj, post_data):
    lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows = _build_rows(obj)
    for row in lab_rows:
        barang_id = row["borrowed"].barang_id
        row["status"] = (post_data.get(f"lab_status_{barang_id}") or row["status"] or "").strip()
        row["transfer_target_id"] = _parse_int(post_data.get(f"lab_transfer_target_{barang_id}"), 0) or None
        row["transfer_target"] = None

    for row in penunjang_rows:
        barang_id = row["borrowed"].barang_id
        row["qty_dikembalikan"] = post_data.get(f"penunjang_dikembalikan_{barang_id}", row["qty_dikembalikan"])
        row["qty_rusak"] = post_data.get(f"penunjang_rusak_{barang_id}", row["qty_rusak"])
        row["qty_hilang"] = post_data.get(f"penunjang_hilang_{barang_id}", row["qty_hilang"])
        row["transfer_enabled"] = post_data.get(f"penunjang_transfer_enabled_{barang_id}") == "1"
        row["qty_transfer"] = post_data.get(f"penunjang_transfer_{barang_id}", row["qty_transfer"])
        if not row["transfer_enabled"]:
            row["qty_transfer"] = ""
        row["transfer_target_id"] = _parse_int(post_data.get(f"penunjang_transfer_target_{barang_id}"), 0) or None
        row["transfer_target"] = None
        if not row["transfer_enabled"]:
            row["transfer_target_id"] = None

    for row in peralatan_lab_rows:
        barang_id = row["borrowed"].barang_id
        row["qty_dikembalikan"] = post_data.get(f"peralatan_lab_dikembalikan_{barang_id}", row["qty_dikembalikan"])
        row["qty_rusak"] = post_data.get(f"peralatan_lab_rusak_{barang_id}", row["qty_rusak"])
        row["qty_hilang"] = post_data.get(f"peralatan_lab_hilang_{barang_id}", row["qty_hilang"])
        row["transfer_enabled"] = post_data.get(f"peralatan_lab_transfer_enabled_{barang_id}") == "1"
        row["qty_transfer"] = post_data.get(f"peralatan_lab_transfer_{barang_id}", row["qty_transfer"])
        if not row["transfer_enabled"]:
            row["qty_transfer"] = ""
        row["transfer_target_id"] = _parse_int(post_data.get(f"peralatan_lab_transfer_target_{barang_id}"), 0) or None
        row["transfer_target"] = None
        if not row["transfer_enabled"]:
            row["transfer_target_id"] = None

    for row in bahan_rows:
        bahan_id = row["borrowed"].bahan_id
        row["qty_sisa"] = post_data.get(
            f"bahan_dikembalikan_{bahan_id}",
            post_data.get(f"bahan_sisa_{bahan_id}", row["qty_sisa"]),
        )
        row["transfer_enabled"] = post_data.get(f"bahan_transfer_enabled_{bahan_id}") == "1"
        row["qty_transfer"] = post_data.get(f"bahan_transfer_{bahan_id}", row["qty_transfer"])
        if not row["transfer_enabled"]:
            row["qty_transfer"] = ""
        row["transfer_target_id"] = _parse_int(post_data.get(f"bahan_transfer_target_{bahan_id}"), 0) or None
        row["transfer_target"] = None
        if not row["transfer_enabled"]:
            row["transfer_target_id"] = None

    return lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows


@login_required
def pengembalian_pengajuan(request, pk):
    obj = get_object_or_404(
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "layanan_kegiatan",
            "tim_kegiatan",
            "instansi_tujuan",
        ).prefetch_related(
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
            "kegiatan_survei",
        ),
        pk=pk,
    )

    if not obj.can_open_pengembalian:
        return deny_access(request, "Pengembalian hanya dapat diproses setelah peminjaman disetujui.")
    if not _can_view_pengembalian(request.user, obj):
        return deny_access(request, "Anda tidak memiliki akses untuk melihat proses pengembalian ini.")

    transfer_targets = _get_transfer_targets(obj)
    catatan = ""
    selected_action = "setujui"
    error_bucket = _build_error_bucket()
    tanggal_selesai_form_value = obj.tanggal_selesai.strftime("%d %b %Y") if obj.tanggal_selesai else ""
    tanggal_selesai_form_errors = []
    open_tanggal_selesai_modal = False

    if request.method == "POST" and (request.POST.get("form_action") or "").strip() == "update_tanggal_selesai":
        result = _handle_tanggal_selesai_update(request, obj)
        if not result.get("allowed"):
            return deny_access(request, result.get("errors", ["Anda tidak memiliki akses."])[0])
        tanggal_selesai_form_value = result.get("value") or tanggal_selesai_form_value
        tanggal_selesai_form_errors = result.get("errors") or []
        open_tanggal_selesai_modal = bool(result.get("open_modal"))
        if not tanggal_selesai_form_errors:
            return redirect("peminjaman:pengembalian", pk=obj.pk)
        lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows = _build_rows(obj)
        _bind_inline_errors_to_rows(lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows, error_bucket)

    elif request.method == "POST":
        if not _can_process_step(request.user, obj):
            return deny_access(request, "Anda tidak memiliki hak untuk memproses tahap pengembalian ini.")

        catatan = (request.POST.get("catatan") or "").strip()
        step_action = (request.POST.get("step_action") or "").strip()
        selected_action = (request.POST.get("aksi") or "setujui").strip()

        can_input_return_data = obj.return_current_step in {
            ReturnStepChoices.NONE,
            ReturnStepChoices.TEKNISI_VERIFICATION,
            ReturnStepChoices.TEKNISI_TRANSFER,
        }

        if not can_input_return_data:
            return deny_access(
                request,
                "Aksi verifikasi pengembalian dilakukan melalui app Verifikasi. Halaman ini hanya untuk input data pengembalian.",
            )

        parsed_lab, parsed_penunjang, parsed_peralatan_lab, parsed_bahan, error_bucket = _parse_pengembalian_data(obj, request.POST)
        pengukuran_data = _parse_pengukuran_data(request.POST)
        lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows = _build_post_rows(obj, request.POST)
        _bind_inline_errors_to_rows(lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows, error_bucket)

        if request.headers.get("x-requested-with") == "XMLHttpRequest" and (request.POST.get("validate_only") == "1"):
            return JsonResponse({
                "is_valid": not _has_inline_errors(error_bucket),
                "errors": _serialize_error_bucket(obj, error_bucket),
            })

        if not _has_inline_errors(error_bucket):
            if obj.return_current_step == ReturnStepChoices.NONE:
                if step_action != "ajukan_pengembalian":
                    _append_inline_error(error_bucket, "global", None, "Aksi pengembalian tidak valid.")
                else:
                    _save_pengembalian_data(obj, parsed_lab, parsed_penunjang, parsed_peralatan_lab, parsed_bahan, pengukuran_data)
                    obj.return_current_step = ReturnStepChoices.TEKNISI_VERIFICATION
                    obj.return_started_at = timezone.now()
                    obj.save(update_fields=["return_current_step", "return_started_at", "updated_at"])
                    obj.add_timeline("Pengembalian", "Pengembalian diajukan oleh user", request.user, catatan)
                    sync_transaction_notifications(obj, actor=request.user)
                    messages.success(request, "Data pengembalian berhasil diajukan dan diteruskan ke Teknisi Laboratorium.")
                    return redirect("peminjaman:pengembalian", pk=obj.pk)

            if obj.return_current_step in {ReturnStepChoices.TEKNISI_VERIFICATION, ReturnStepChoices.TEKNISI_TRANSFER}:
                if step_action != "simpan_pengembalian":
                    _append_inline_error(error_bucket, "global", None, "Aksi pengembalian tidak valid.")
                else:
                    _save_pengembalian_data(obj, parsed_lab, parsed_penunjang, parsed_peralatan_lab, parsed_bahan, pengukuran_data)
                    obj.add_timeline(
                        "Pengembalian",
                        "Data pengembalian diperbarui dari halaman Proses Pengembalian",
                        request.user,
                        catatan,
                    )
                    messages.success(request, "Data pengembalian berhasil diperbarui.")
                    if get_role_name(request.user) in {ROLE_TEKNISI_LAB, ROLE_SUPER_ADMIN}:
                        return redirect("verifikasi:detail", pk=obj.pk)
                    return redirect("peminjaman:pengembalian", pk=obj.pk)
    else:
        lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows = _build_rows(obj)
        _bind_inline_errors_to_rows(lab_rows, penunjang_rows, peralatan_lab_rows, bahan_rows, error_bucket)

    role_name = get_role_name(request.user)
    editable_item_form = obj.return_current_step in {
        ReturnStepChoices.NONE,
        ReturnStepChoices.TEKNISI_VERIFICATION,
        ReturnStepChoices.TEKNISI_TRANSFER,
    } and _can_process_step(request.user, obj)
    show_return_form_action = editable_item_form and bool(lab_rows or penunjang_rows or peralatan_lab_rows or bahan_rows)
    if obj.return_current_step == ReturnStepChoices.NONE:
        return_form_action_value = "ajukan_pengembalian"
        return_form_action_label = "Ajukan Pengembalian"
    elif obj.return_current_step in {ReturnStepChoices.TEKNISI_VERIFICATION, ReturnStepChoices.TEKNISI_TRANSFER}:
        return_form_action_value = "simpan_pengembalian"
        return_form_action_label = "Simpan Data Pengembalian"
    else:
        return_form_action_value = ""
        return_form_action_label = ""
    approval_step = obj.return_current_step in {
        ReturnStepChoices.KEPALA_BA,
        ReturnStepChoices.PIMPINAN_BA,
        ReturnStepChoices.KEPALA_TRANSFER,
        ReturnStepChoices.PIMPINAN_TRANSFER,
    }
    show_catatan_box = approval_step or obj.return_current_step in {
        ReturnStepChoices.NONE,
        ReturnStepChoices.TEKNISI_VERIFICATION,
        ReturnStepChoices.TEKNISI_BA,
        ReturnStepChoices.TEKNISI_TRANSFER,
    }

    return render(
        request,
        "peminjaman/pengembalian_form.html",
        {
            "obj": obj,
            "lab_rows": lab_rows,
            "penunjang_rows": penunjang_rows,
            "peralatan_lab_rows": peralatan_lab_rows,
            "bahan_rows": bahan_rows,
            "transfer_targets": transfer_targets,
            "global_errors": error_bucket["global"],
            "catatan_errors": error_bucket["catatan"],
            "catatan": catatan,
            "selected_action": selected_action,
            "return_approval_options": RETURN_APPROVAL_OPTIONS,
            "editable_item_form": editable_item_form,
            "show_return_form_action": show_return_form_action,
            "return_form_action_value": return_form_action_value,
            "return_form_action_label": return_form_action_label,
            "approval_step": approval_step,
            "show_catatan_box": show_catatan_box,
            "role_name": role_name,
            "can_delete_pengajuan": role_name == ROLE_SUPER_ADMIN,
            "has_transfer_targets": bool(transfer_targets),
            "pengukuran_data": obj.get_pengukuran_data(),
            "survei_items": obj.kegiatan_survei.all(),
            "can_edit_tanggal_selesai": _can_edit_return_end_date(request.user, obj),
            "tanggal_selesai_form_value": tanggal_selesai_form_value,
            "tanggal_selesai_form_errors": tanggal_selesai_form_errors,
            "open_tanggal_selesai_modal": open_tanggal_selesai_modal,
            "return_role_label": {
                ReturnStepChoices.NONE: "User",
                ReturnStepChoices.TEKNISI_VERIFICATION: "Teknisi Lab",
                ReturnStepChoices.USER_VERIFICATION: "User",
                ReturnStepChoices.TEKNISI_BA: "Teknisi Lab",
                ReturnStepChoices.TEKNISI_TRANSFER: "Teknisi Lab",
                ReturnStepChoices.KEPALA_BA: "Kepala Lab",
                ReturnStepChoices.KEPALA_TRANSFER: "Kepala Lab",
                ReturnStepChoices.PIMPINAN_BA: RETURN_PIMPINAN_LABEL,
                ReturnStepChoices.PIMPINAN_TRANSFER: RETURN_PIMPINAN_LABEL,
                ReturnStepChoices.COMPLETED: "Selesai",
            }.get(obj.return_current_step, "-")
        },
    )
