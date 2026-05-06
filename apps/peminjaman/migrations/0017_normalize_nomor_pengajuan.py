import re

from django.db import migrations


OLD_NOMOR_RE = re.compile(r"^PMJ-(\d{4})(\d{2})(\d{2})-(\d+)$", re.IGNORECASE)
NEW_NOMOR_RE = re.compile(r"^PMJ-(\d{2})(\d{2})(\d{2})-(\d+)$", re.IGNORECASE)


def _serial(value, width):
    try:
        return f"{int(value):0{width}d}"
    except (TypeError, ValueError):
        return value


def _to_new(nomor):
    match = OLD_NOMOR_RE.match(nomor or "")
    if not match:
        return nomor
    tahun, bulan, tanggal, urut = match.groups()
    return f"PMJ-{tahun[-2:]}{bulan}{tanggal}-{_serial(urut, 3)}"


def _to_old(nomor):
    match = NEW_NOMOR_RE.match(nomor or "")
    if not match:
        return nomor
    tahun, bulan, tanggal, urut = match.groups()
    return f"PMJ-20{tahun}{bulan}{tanggal}-{_serial(urut, 4)}"


def _replace_nomor(value, mapping):
    if isinstance(value, str):
        result = value
        for old, new in mapping.items():
            result = result.replace(old, new)
        return result
    if isinstance(value, list):
        return [_replace_nomor(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: _replace_nomor(item, mapping) for key, item in value.items()}
    return value


def _build_mapping(PeminjamanRequest, converter):
    existing = dict(PeminjamanRequest.objects.values_list("nomor_pengajuan", "pk"))
    used_targets = set()
    updates = []
    mapping = {}

    rows = PeminjamanRequest.objects.exclude(nomor_pengajuan="").values_list("pk", "nomor_pengajuan")
    for pk, nomor in rows.iterator():
        target = converter(nomor)
        if not target or target == nomor:
            continue
        other_pk = existing.get(target)
        if other_pk and other_pk != pk:
            continue
        if target in used_targets:
            continue
        used_targets.add(target)
        updates.append((pk, target))
        mapping[nomor] = target
    return mapping, updates


def _update_snapshots(PeminjamanRequest, mapping):
    if not mapping:
        return
    for obj in PeminjamanRequest.objects.exclude(report_snapshot__isnull=True).iterator():
        snapshot = obj.report_snapshot
        new_snapshot = _replace_nomor(snapshot, mapping)
        if new_snapshot != snapshot:
            obj.report_snapshot = new_snapshot
            obj.save(update_fields=["report_snapshot"])


def _update_timeline(PeminjamanTimeline, mapping):
    if not mapping:
        return
    for obj in PeminjamanTimeline.objects.all().iterator():
        updates = []
        for field_name in ("action", "note"):
            current = getattr(obj, field_name, "") or ""
            new_value = _replace_nomor(current, mapping)
            if new_value != current:
                setattr(obj, field_name, new_value)
                updates.append(field_name)
        if updates:
            obj.save(update_fields=updates)


def _apply(apps, converter):
    PeminjamanRequest = apps.get_model("peminjaman", "PeminjamanRequest")
    PeminjamanTimeline = apps.get_model("peminjaman", "PeminjamanTimeline")

    mapping, updates = _build_mapping(PeminjamanRequest, converter)
    for pk, target in updates:
        PeminjamanRequest.objects.filter(pk=pk).update(nomor_pengajuan=target)
    _update_snapshots(PeminjamanRequest, mapping)
    _update_timeline(PeminjamanTimeline, mapping)


def forwards(apps, schema_editor):
    _apply(apps, _to_new)


def backwards(apps, schema_editor):
    _apply(apps, _to_old)


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0016_peminjamanrequest_layanan_kegiatan_lainnya"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
