# Generated manually to merge "Dalam Perbaikan" into "Dalam Pemeliharaan".

from django.db import migrations, models


OLD_CONDITION = "Dalam Perbaikan"
REPLACEMENT_CONDITION = "Dalam Pemeliharaan"

KONDISI_CHOICES = [
    ("Baik", "Baik"),
    (REPLACEMENT_CONDITION, REPLACEMENT_CONDITION),
    ("Rusak", "Rusak"),
    ("Hilang", "Hilang"),
]


def merge_repair_condition(apps, schema_editor):
    for model_name in ("BarangLaboratorium", "FasilitasRuangan", "PeralatanLaboratorium"):
        model = apps.get_model("master_data", model_name)
        model.objects.filter(kondisi_barang=OLD_CONDITION).update(
            kondisi_barang=REPLACEMENT_CONDITION
        )


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0017_restore_kondisi_pemeliharaan_choice"),
    ]

    operations = [
        migrations.RunPython(merge_repair_condition, migrations.RunPython.noop),
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
