from django.db import migrations, models


def copy_titles(apps, schema_editor):
    KontenAlatTV = apps.get_model("landing", "KontenAlatTV")
    slots = list(
        KontenAlatTV.objects.using(schema_editor.connection.alias)
        .filter(judul_barang="", alat__isnull=False)
        .select_related("alat")
    )
    for slot in slots:
        slot.judul_barang = slot.alat.nama_barang
    if slots:
        KontenAlatTV.objects.using(schema_editor.connection.alias).bulk_update(slots, ["judul_barang"])


class Migration(migrations.Migration):
    dependencies = [("landing", "0007_tv_slide")]

    operations = [
        migrations.AddField(
            model_name="kontenalattv",
            name="judul_barang",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="Judul Barang"),
        ),
        migrations.RunPython(copy_titles, migrations.RunPython.noop),
    ]
