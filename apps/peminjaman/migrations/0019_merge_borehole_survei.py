from django.db import migrations


SOURCE_NAME = "Borehole"
TARGET_NAME = "Borehole Camera"


def _normalize_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return snapshot, False

    kegiatan = snapshot.get("kegiatan")
    if not isinstance(kegiatan, dict):
        return snapshot, False

    items = kegiatan.get("kegiatan_survei")
    if not isinstance(items, list):
        return snapshot, False

    normalized = []
    target_added = False
    changed = False

    for item in items:
        is_borehole = (
            isinstance(item, str)
            and item.strip().casefold()
            in {SOURCE_NAME.casefold(), TARGET_NAME.casefold()}
        )
        if not is_borehole:
            normalized.append(item)
            continue

        if target_added:
            changed = True
            continue

        normalized.append(TARGET_NAME)
        target_added = True
        changed = changed or item != TARGET_NAME

    if changed:
        kegiatan["kegiatan_survei"] = normalized
    return snapshot, changed


def merge_borehole_survei(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    SurveiKegiatan = apps.get_model("operasional", "SurveiKegiatan")
    PeminjamanRequest = apps.get_model("peminjaman", "PeminjamanRequest")

    survei = SurveiKegiatan.objects.using(db_alias)
    source = survei.filter(jenis_survei=SOURCE_NAME).first()
    target = survei.filter(jenis_survei=TARGET_NAME).first()

    if source and not target:
        source.jenis_survei = TARGET_NAME
        source.save(using=db_alias, update_fields=["jenis_survei"])
        target = source
        source = None

    if source and target:
        field = PeminjamanRequest._meta.get_field("kegiatan_survei")
        through = field.remote_field.through
        owner_fk = field.m2m_field_name()
        survei_fk = field.m2m_reverse_field_name()

        source_links = through.objects.using(db_alias).filter(
            **{f"{survei_fk}_id": source.pk}
        )
        owner_ids = list(
            source_links.values_list(f"{owner_fk}_id", flat=True)
        )
        target_links = [
            through(
                **{
                    f"{owner_fk}_id": owner_id,
                    f"{survei_fk}_id": target.pk,
                }
            )
            for owner_id in owner_ids
        ]
        through.objects.using(db_alias).bulk_create(
            target_links,
            ignore_conflicts=True,
        )
        source.delete(using=db_alias)

    requests = PeminjamanRequest.objects.using(db_alias).exclude(
        report_snapshot__isnull=True
    )
    for obj in requests.iterator():
        snapshot, changed = _normalize_snapshot(obj.report_snapshot)
        if not changed:
            continue
        obj.report_snapshot = snapshot
        obj.save(using=db_alias, update_fields=["report_snapshot"])


class Migration(migrations.Migration):

    dependencies = [
        ("operasional", "0004_rename_tim_kegiatan_names"),
        ("peminjaman", "0018_hapus_verifikasi_user_peminjaman"),
    ]

    operations = [
        migrations.RunPython(
            merge_borehole_survei,
            migrations.RunPython.noop,
        ),
    ]
