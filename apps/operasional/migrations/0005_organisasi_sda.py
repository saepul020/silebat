from django.db import migrations, models


RENAMES = {
    "Internal PU": "Internal SDA",
    "Eksternal PU": "Eksternal SDA",
}


def rename_organisasi(apps, schema_editor, mapping):
    db_alias = schema_editor.connection.alias
    InstansiKlien = apps.get_model("operasional", "InstansiKlien")
    PeminjamanRequest = apps.get_model("peminjaman", "PeminjamanRequest")

    for old_value, new_value in mapping.items():
        InstansiKlien.objects.using(db_alias).filter(organisasi=old_value).update(
            organisasi=new_value
        )

    # Ubah hanya kategori organisasi; pertahankan isi snapshot historis lainnya.
    requests = PeminjamanRequest.objects.using(db_alias).filter(
        report_snapshot__kegiatan__organisasi_instansi__in=list(mapping)
    )
    for obj in requests.iterator():
        kegiatan = obj.report_snapshot["kegiatan"]
        kegiatan["organisasi_instansi"] = mapping[kegiatan["organisasi_instansi"]]
        obj.save(using=db_alias, update_fields=["report_snapshot"])


def forwards(apps, schema_editor):
    rename_organisasi(apps, schema_editor, RENAMES)


def backwards(apps, schema_editor):
    rename_organisasi(apps, schema_editor, {value: key for key, value in RENAMES.items()})


class Migration(migrations.Migration):
    dependencies = [
        ("operasional", "0004_rename_tim_kegiatan_names"),
        ("peminjaman", "0019_merge_borehole_survei"),
    ]

    operations = [
        migrations.AlterField(
            model_name="instansiklien",
            name="organisasi",
            field=models.CharField(
                choices=[
                    ("Internal SDA", "Internal SDA"),
                    ("Eksternal SDA", "Eksternal SDA"),
                    ("Internal BAT", "Internal BAT"),
                ],
                max_length=30,
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
