# Generated manually to remove the retired "Dalam Pemeliharaan" condition choice.

from django.db import migrations, models


OLD_CONDITION = "Dalam Pemeliharaan"
REPLACEMENT_CONDITION = "Dalam Perbaikan"


KONDISI_CHOICES = [
    ("Baik", "Baik"),
    (REPLACEMENT_CONDITION, REPLACEMENT_CONDITION),
    ("Rusak", "Rusak"),
    ("Hilang", "Hilang"),
]


def normalize_retired_condition(apps, schema_editor):
    for model_name in ("BarangLaboratorium", "FasilitasRuangan", "PeralatanLaboratorium"):
        model = apps.get_model("master_data", model_name)
        model.objects.filter(kondisi_barang=OLD_CONDITION).update(
            kondisi_barang=REPLACEMENT_CONDITION
        )


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0015_baranglaboratorium_komponen_pemeliharaan"),
    ]

    operations = [
        migrations.RunPython(normalize_retired_condition, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="baranglaboratorium",
            name="kondisi_barang",
            field=models.CharField(
                choices=KONDISI_CHOICES,
                default="Baik",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="fasilitasruangan",
            name="kondisi_barang",
            field=models.CharField(
                choices=KONDISI_CHOICES,
                default="Baik",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="peralatanlaboratorium",
            name="kondisi_barang",
            field=models.CharField(
                choices=KONDISI_CHOICES,
                default="Baik",
                max_length=30,
            ),
        ),
    ]
