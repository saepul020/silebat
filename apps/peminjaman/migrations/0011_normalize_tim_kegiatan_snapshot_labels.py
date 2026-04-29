from django.db import migrations


RENAMES = {
    "Sub Koordinator Layanan Teknis": "Tim Layanan Teknis",
    "Sub Koordinator Pengembangan Penerapan": "Tim Pengembangan Penerapan",
}


def _normalize_snapshots(apps, schema_editor, mapping):
    PeminjamanRequest = apps.get_model("peminjaman", "PeminjamanRequest")

    for obj in PeminjamanRequest.objects.exclude(report_snapshot__isnull=True).iterator():
        snapshot = obj.report_snapshot
        if not isinstance(snapshot, dict):
            continue
        kegiatan = snapshot.get("kegiatan")
        if not isinstance(kegiatan, dict):
            continue
        current = kegiatan.get("tim_kegiatan")
        new_value = mapping.get(current)
        if not new_value:
            continue
        kegiatan["tim_kegiatan"] = new_value
        obj.report_snapshot = snapshot
        obj.save(update_fields=["report_snapshot"])


def _normalize_timeline_text(apps, schema_editor, mapping):
    try:
        PeminjamanTimeline = apps.get_model("peminjaman", "PeminjamanTimeline")
    except LookupError:
        return

    for obj in PeminjamanTimeline.objects.all().iterator():
        updated_fields = []
        for field_name in ("action", "note"):
            value = getattr(obj, field_name, "") or ""
            new_value = value
            for old_name, new_name in mapping.items():
                new_value = new_value.replace(old_name, new_name)
            if new_value != value:
                setattr(obj, field_name, new_value)
                updated_fields.append(field_name)
        if updated_fields:
            obj.save(update_fields=updated_fields)


def forwards(apps, schema_editor):
    _normalize_snapshots(apps, schema_editor, RENAMES)
    _normalize_timeline_text(apps, schema_editor, RENAMES)


def backwards(apps, schema_editor):
    reverse_mapping = {value: key for key, value in RENAMES.items()}
    _normalize_snapshots(apps, schema_editor, reverse_mapping)
    _normalize_timeline_text(apps, schema_editor, reverse_mapping)


class Migration(migrations.Migration):

    dependencies = [
        ("operasional", "0004_rename_tim_kegiatan_names"),
        ("peminjaman", "0010_peminjamanrequest_pengukuran_tambahan"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
