# Generated manually to restore the maintenance condition choice.

from django.db import migrations, models


KONDISI_CHOICES = [
    ("Baik", "Baik"),
    ("Dalam Pemeliharaan", "Dalam Pemeliharaan"),
    ("Dalam Perbaikan", "Dalam Perbaikan"),
    ("Rusak", "Rusak"),
    ("Hilang", "Hilang"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0016_remove_kondisi_pemeliharaan_choice"),
    ]

    operations = [
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
