from django.db import migrations, models


def preserve_non_bmn_volume(apps, schema_editor):
    for model_name in ("FasilitasRuangan", "PeralatanLaboratorium"):
        model = apps.get_model("master_data", model_name)
        model.objects.filter(status_barang="Non BMN").update(bervolume=True)


class Migration(migrations.Migration):
    dependencies = [
        ("master_data", "0018_hapus_kondisi_perbaikan"),
    ]

    operations = [
        migrations.AddField(
            model_name="fasilitasruangan",
            name="bervolume",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="peralatanlaboratorium",
            name="bervolume",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="baranglaboratorium",
            name="kode_laboratorium",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="baranglaboratorium",
            name="lokasi_barang",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="fasilitasruangan",
            name="kode_laboratorium",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="fasilitasruangan",
            name="lokasi_barang",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="peralatanlaboratorium",
            name="kode_laboratorium",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="peralatanlaboratorium",
            name="lokasi_barang",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RunPython(
            preserve_non_bmn_volume,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
