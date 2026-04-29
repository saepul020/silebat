from django.db import migrations


RENAMES = {
    "Sub Koordinator Layanan Teknis": "Tim Layanan Teknis",
    "Sub Koordinator Pengembangan Penerapan": "Tim Pengembangan Penerapan",
}


def _rename_tim_kegiatan(apps, schema_editor, mapping):
    TimKegiatan = apps.get_model("operasional", "TimKegiatan")

    for old_name, new_name in mapping.items():
        old_obj = TimKegiatan.objects.filter(nama_tim=old_name).order_by("id").first()
        if not old_obj:
            continue

        new_obj = TimKegiatan.objects.filter(nama_tim=new_name).order_by("id").first()
        if not new_obj:
            old_obj.nama_tim = new_name
            old_obj.save(update_fields=["nama_tim"])
            continue

        if old_obj.ketua_tim_id and not new_obj.ketua_tim_id:
            new_obj.ketua_tim_id = old_obj.ketua_tim_id
            new_obj.save(update_fields=["ketua_tim"])

        # Repoint direct FK relations that may still reference the legacy row.
        try:
            UserProfile = apps.get_model("pengguna", "UserProfile")
            UserProfile.objects.filter(nama_tim_id=old_obj.id).update(nama_tim_id=new_obj.id)
        except LookupError:
            pass

        try:
            PeminjamanRequest = apps.get_model("peminjaman", "PeminjamanRequest")
            PeminjamanRequest.objects.filter(tim_kegiatan_id=old_obj.id).update(tim_kegiatan_id=new_obj.id)
        except LookupError:
            pass

        old_obj.delete()


def forwards(apps, schema_editor):
    _rename_tim_kegiatan(apps, schema_editor, RENAMES)


def backwards(apps, schema_editor):
    _rename_tim_kegiatan(apps, schema_editor, {value: key for key, value in RENAMES.items()})


class Migration(migrations.Migration):

    dependencies = [
        ("operasional", "0003_datakopdokumen"),
        ("pengguna", "0006_alter_role_options_alter_user_options"),
        ("peminjaman", "0010_peminjamanrequest_pengukuran_tambahan"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
