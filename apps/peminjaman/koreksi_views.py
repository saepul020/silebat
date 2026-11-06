from copy import deepcopy
from datetime import datetime, time
import json
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.core.permissions import deny_access, is_super_admin
from apps.core.file_cleanup import delete_file_if_unused
from apps.master_data.models import BarangLaboratorium
from .forms import apply_peminjam_snapshot

from .koreksi_forms import (
    ALAT_FIELDS, IDENTITAS_FIELDS, KEGIATAN_FIELDS, PENGUKURAN_FIELDS, RIWAYAT_FIELDS,
    KoreksiAlatFormSet, KoreksiLaporanForm,
)
from .models import (
    PeminjamanBarangLaboratorium, PeminjamanRequest, PengembalianBarangLaboratorium,
    ReturnItemStatusChoices, ReturnStepChoices,
)


def _match_item(item, candidates):
    """Match detached imported rows without confusing multiple NULL master IDs."""
    if item.barang_id:
        for candidate in candidates:
            if candidate.barang_id == item.barang_id:
                return candidate
    for key in ("kode_laboratorium", "kode_aset_bmn", "nama_barang"):
        value = getattr(item, f"snapshot_{key}", "")
        if value and value != "-":
            for candidate in candidates:
                if not candidate.barang_id and getattr(candidate, f"snapshot_{key}") == value:
                    return candidate
    return None


def _report_row(item, rows):
    for key in ("kode_laboratorium", "kode_aset_bmn", "nama_barang"):
        value = getattr(item, f"snapshot_{key}", "")
        if value and value != "-":
            for index, row in enumerate(rows):
                if row.get(key) == value:
                    return rows.pop(index)
    return {}


def _capture(obj):
    fields = ("peminjam", *IDENTITAS_FIELDS, *KEGIATAN_FIELDS, *PENGUKURAN_FIELDS, *RIWAYAT_FIELDS)
    result = {}
    for key in fields:
        field = obj._meta.get_field(key)
        if field.many_to_many:
            result[key] = list(obj.kegiatan_survei.values_list("pk", flat=True))
        elif key == "berkas_pendukung":
            result[key] = obj.berkas_pendukung.name or ""
        else:
            result[key] = getattr(obj, field.attname)
    result["alat"] = list(obj.barang_laboratorium_items.order_by("pk").values())
    result["snapshot"] = deepcopy(obj.report_snapshot)
    return result


def _set_date(obj, attr, value):
    old = getattr(obj, attr)
    local_time = timezone.localtime(old).time() if old else time(8)
    setattr(obj, attr, timezone.make_aware(datetime.combine(value, local_time)))


def _comparison(obj, form, before):
    report = before["snapshot"] or obj.build_report_snapshot()
    peminjam = report.get("peminjam", {})
    kegiatan = report.get("kegiatan", {})
    identitas = [{"name": "peminjam", "label": "Akun Peminjam", "value": peminjam.get("nama") or before["nama_peminjam"] or str(obj.peminjam)}]
    values = {
        **{key: before[key] or "-" for key in KEGIATAN_FIELDS},
        "layanan_kegiatan": kegiatan.get("layanan_kegiatan", obj.layanan_kegiatan_label),
        "tim_kegiatan": kegiatan.get("tim_kegiatan", str(obj.tim_kegiatan or "-")),
        "kegiatan_survei": ", ".join(kegiatan.get("kegiatan_survei", [])) or "-",
        "instansi_tujuan": kegiatan.get("instansi_tujuan", str(obj.instansi_tujuan or "-")),
        "tanggal_mulai": kegiatan.get("mulai_tanggal", obj._format_snapshot_date(obj.tanggal_mulai)),
        "tanggal_selesai": kegiatan.get("selesai_tanggal", obj._format_snapshot_date(obj.tanggal_selesai)),
    }
    for name, attr in zip(("tanggal_persetujuan", "tanggal_pengembalian", "tanggal_selesai_pengembalian"), RIWAYAT_FIELDS):
        value = getattr(obj, attr)
        values[name] = obj._format_snapshot_datetime(value)
    activity = [{"name": name, "label": form.fields[name].label, "value": value} for name, value in values.items()]
    for row, name in zip(activity, values):
        if name == "berkas_pendukung" and before[name]:
            row["value"] = before[name].rsplit("/", 1)[-1]
            row["url"] = obj.berkas_pendukung.storage.url(before[name])
    measurements = {row["key"]: row for row in obj.get_pengukuran_data()}
    measurements.update({row["key"]: row for row in report.get("pengukuran", []) if row.get("key")})
    stored_alat = list(report.get("items", {}).get("lab", []))
    previous_alat = [
        _report_row(SimpleNamespace(**item), stored_alat)
        or {key: item[f"snapshot_{key}"] for key in ALAT_FIELDS}
        for item in before["alat"]
    ]
    previous_alat.extend(stored_alat)
    return {
        "previous_identitas": identitas, "previous_kegiatan": activity,
        "previous_pengukuran": [{"name": key, "label": measurements[key]["label"], "value": measurements[key].get("display", "-")} for key in PENGUKURAN_FIELDS],
        "previous_alat": [dict(item, label=_alat_label(
            item.get("nama_barang"), item.get("tipe_merek_barang"),
            next((item.get(key) for key in ("kode_aset_bmn", "kode_laboratorium") if item.get(key) not in (None, "", "-")), "-"),
        )) for item in previous_alat],
    }


def _alat_label(nama, merk, kode):
    return f"{nama or '-'} - {merk or '-'} ({kode or '-'})"


def _save_correction(obj, form, formset, pairs, before, actor):
    snapshot = deepcopy(obj.report_snapshot) if obj.report_snapshot.get("items") else obj.build_report_snapshot()
    old_rows = list(snapshot.get("items", {}).get("lab", []))
    rows_by_id = {
        item["id"]: _report_row(SimpleNamespace(**item), old_rows) for item in before["alat"]
    }
    previous_kegiatan = deepcopy(snapshot.get("kegiatan", {}))
    obj = form.save(commit=False)
    if "peminjam" in form.pending_fields:
        apply_peminjam_snapshot(obj, form.cleaned_data["peminjam"])
    for attr, name in zip(RIWAYAT_FIELDS, (
        "tanggal_persetujuan", "tanggal_pengembalian", "tanggal_selesai_pengembalian",
    )):
        if name in form.pending_fields:
            _set_date(obj, attr, form.cleaned_data[name])
    obj.save()
    form.save_m2m()

    # Detach first so swapping two historical master links does not violate uniqueness.
    existing_ids = [
        f.instance.pk for f in formset.forms if f.instance.pk and (f.replace_master or f.cleaned_data.get("DELETE"))
    ]
    PeminjamanBarangLaboratorium.objects.filter(pk__in=existing_ids).update(barang=None)
    PengembalianBarangLaboratorium.objects.filter(pk__in=[item.pk for pk, item in pairs.items() if pk in existing_ids and item]).update(barang=None)
    lab_rows = []
    for alat_form in formset.forms:
        data = alat_form.cleaned_data
        if not data:
            continue
        pk = alat_form.instance.pk
        returned = pairs.get(pk)
        if data.get("DELETE"):
            if returned:
                returned.delete()
            if pk:
                PeminjamanBarangLaboratorium.objects.filter(pk=pk).delete()
            continue
        if pk and not alat_form.replace_master:
            row = rows_by_id.get(pk, {}).copy()
            if not row:
                row = {key: getattr(alat_form.instance, f"snapshot_{key}") for key in ALAT_FIELDS}
            lab_rows.append(row)
            continue
        master = data.get("barang")
        values = {}
        for key in ALAT_FIELDS:
            name = f"snapshot_{key}"
            value = getattr(master, key) if master else getattr(alat_form.instance, name)
            values[name] = "" if value is None and not PeminjamanBarangLaboratorium._meta.get_field(name).null else value
        values["barang_id"] = master.pk if master else None
        if pk:
            # Write the same selected-master snapshot to both historical item rows.
            PeminjamanBarangLaboratorium.objects.filter(pk=pk).update(**values)
        else:
            borrowed = PeminjamanBarangLaboratorium(pengajuan=obj, **values)
            PeminjamanBarangLaboratorium.objects.bulk_create([borrowed])
        if returned:
            PengembalianBarangLaboratorium.objects.filter(pk=returned.pk).update(**values)
        else:
            returned = PengembalianBarangLaboratorium(pengajuan=obj, **values)
            PengembalianBarangLaboratorium.objects.bulk_create([returned])
        row = rows_by_id.get(pk, {}).copy()
        row.update({key: values[f"snapshot_{key}"] if values[f"snapshot_{key}"] not in (None, "") else "-" for key in ALAT_FIELDS})
        row.setdefault("asal_peminjaman", "Laboratorium")
        row["status_pengembalian"] = returned.get_status_display()
        row["catatan_pengembalian"] = returned.note or "-"
        row["tujuan_transfer"] = obj._build_transfer_target_label(returned.transfer_target) if returned.transfer_target_id else "-"
        lab_rows.append(row)

    if "peminjam" in form.pending_fields:
        snapshot["peminjam"] = {
            key: getattr(obj, attr) or "-" for key, attr in zip(
                ("nama", "nomor_telepon", "email", "nip", "alamat"), IDENTITAS_FIELDS,
            )
        }
    kegiatan = previous_kegiatan
    # Preserve unmapped imported labels unless their corresponding input changed.
    for key, label in (
        ("layanan_kegiatan", obj.layanan_kegiatan_label),
        ("tim_kegiatan", getattr(obj.tim_kegiatan, "nama_tim", "-")),
        ("instansi_tujuan", getattr(obj.instansi_tujuan, "nama_instansi", obj.instansi_tujuan_lainnya or "-")),
    ):
        manual_key = f"{key}_lainnya"
        if key in form.pending_fields or manual_key in form.pending_fields:
            kegiatan[key] = label
    if form.pending_fields.intersection(("kegiatan_survei", "survei_lainnya")):
        kegiatan["kegiatan_survei"] = list(obj.kegiatan_survei.values_list("jenis_survei", flat=True))
        if obj.survei_lainnya:
            kegiatan["kegiatan_survei"].append(f"Lainnya: {obj.survei_lainnya}")
    if form.pending_fields.intersection(("tanggal_mulai", "tanggal_selesai")):
        kegiatan.update({
            "mulai_tanggal": obj._format_snapshot_date(obj.tanggal_mulai),
            "selesai_tanggal": obj._format_snapshot_date(obj.tanggal_selesai), "total_hari": obj.total_hari,
        })
    if "berkas_pendukung" in form.pending_fields:
        kegiatan["berkas_pendukung"] = obj.berkas_pendukung.name or ""
    snapshot["kegiatan"] = kegiatan
    if form.pending_fields.intersection(PENGUKURAN_FIELDS):
        measured = {row["key"]: row for row in snapshot.get("pengukuran", [])}
        measured.update({row["key"]: row for row in obj.get_pengukuran_data() if row["key"] in form.pending_fields})
        snapshot["pengukuran"] = list(measured.values())
    if any(f.replace_master or f.cleaned_data.get("DELETE") for f in formset.forms):
        snapshot.setdefault("items", {})["lab"] = lab_rows
    for name, attr in (("tanggal_pengembalian", "return_started_at"), ("tanggal_selesai_pengembalian", "return_completed_at")):
        if name in form.pending_fields:
            snapshot[attr] = obj._format_snapshot_datetime(getattr(obj, attr))
    obj.report_snapshot = snapshot
    obj.save(update_fields=["report_snapshot", "updated_at"])
    obj.add_timeline("Koreksi Laporan", "Data peminjaman selesai dikoreksi", actor, json.dumps({
        "sebelum": before, "sesudah": _capture(obj),
    }, ensure_ascii=False, default=str, indent=2))
    previous_file = before["berkas_pendukung"]
    if previous_file and previous_file != (obj.berkas_pendukung.name or ""):
        transaction.on_commit(lambda: delete_file_if_unused(PeminjamanRequest, "berkas_pendukung", previous_file))


@login_required
@require_http_methods(["GET", "POST"])
def koreksi_laporan(request, pk):
    if not is_super_admin(request.user):
        return deny_access(request, "Koreksi laporan hanya dapat dilakukan oleh Super Admin.")
    with transaction.atomic():
        queryset = PeminjamanRequest.objects.all()
        if request.method == "POST":
            queryset = queryset.select_for_update()
        obj = get_object_or_404(queryset, pk=pk, return_current_step=ReturnStepChoices.COMPLETED)
        before = _capture(obj)
        items = obj.barang_laboratorium_items.select_related("barang").order_by("pk")
        returns = list(obj.pengembalian_lab_items.select_related("transfer_target").order_by("pk"))
        pairs = {}
        remaining = returns.copy()
        incoming = set(PengembalianBarangLaboratorium.objects.filter(transfer_target=obj).values_list("barang_id", flat=True))
        protected = set()
        for item in items:
            returned = _match_item(item, remaining)
            pairs[item.pk] = returned
            if returned:
                remaining.remove(returned)
            if (returned and (returned.status != ReturnItemStatusChoices.DIKEMBALIKAN or returned.transfer_target_id)) or (item.barang_id and item.barang_id in incoming):
                protected.add(item.pk)
        post = request.POST if request.method == "POST" else None
        alat_list = list(BarangLaboratorium.objects.order_by("nama_barang", "kode_laboratorium"))
        alat_choices = [("", "Pilih peralatan survei lapangan")] + [
            (item.pk, _alat_label(item.nama_barang, item.tipe_merek_barang, item.kode_aset_bmn or item.kode_laboratorium or item.pk))
            for item in alat_list
        ]
        form = KoreksiLaporanForm(post, request.FILES or None, instance=obj)
        comparison = _comparison(obj, form, before)
        formset = KoreksiAlatFormSet(
            post, queryset=items, prefix="alat", protected_ids=protected,
            form_kwargs={"alat_choices": alat_choices},
        )
        for alat_form in formset:
            alat_form.is_protected = alat_form.instance.pk in protected
        valid_form = form.is_valid() if post is not None else False
        valid_items = formset.is_valid() if post is not None else False
        if valid_form and form.cleaned_data["versi"] != obj.updated_at.isoformat():
            form.add_error(None, "Data laporan sudah berubah. Muat ulang halaman sebelum mengoreksi kembali.")
            valid_form = False
        if valid_form and valid_items:
            if not form.pending_fields and not any(f.replace_master or f.cleaned_data.get("DELETE") for f in formset.forms):
                form.add_error(None, "Isi minimal satu kolom perubahan atau pilih alat yang akan dihapus.")
            elif remaining:
                form.add_error(None, "Ada data pengembalian alat yang tidak cocok dengan daftar pinjaman. Rekonsiliasi data terlebih dahulu.")
            else:
                try:
                    # A savepoint rolls back DB changes before orphan-file cleanup.
                    with transaction.atomic():
                        _save_correction(obj, form, formset, pairs, before, request.user)
                except Exception:
                    new_file = obj.berkas_pendukung
                    if new_file and new_file._committed and new_file.name != before["berkas_pendukung"]:
                        delete_file_if_unused(PeminjamanRequest, "berkas_pendukung", new_file)
                    raise
                messages.success(request, "Koreksi disimpan. Data transaksi, laporan, dan sumber grafik telah diperbarui.")
                return redirect("peminjaman:laporan_detail", pk=obj.pk)
        return render(request, "peminjaman/laporan_koreksi.html", {
            "obj": obj, "form": form, "formset": formset, **comparison,
            "alat_rows": max(len(comparison["previous_alat"]), len(formset.forms)) + 2,
            "sections": [
                {"title": title, "rows": [
                    {"previous": previous, "field": form[name]} for previous, name in zip(comparison[key], names)
                ]}
                for title, key, names in (
                    ("Data Peminjam", "previous_identitas", ("peminjam",)),
                    ("Data Kegiatan", "previous_kegiatan", (*KEGIATAN_FIELDS, "tanggal_persetujuan", "tanggal_pengembalian", "tanggal_selesai_pengembalian")),
                    ("Data Pengukuran Lapangan", "previous_pengukuran", PENGUKURAN_FIELDS),
                )
            ],
            "riwayat_koreksi": obj.timeline_entries.filter(stage="Koreksi Laporan").select_related("actor").order_by("-created_at"),
        })
