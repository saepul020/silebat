from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0005_baranglaboratorium_kategori_barang"),
    ]

    operations = [
        migrations.AlterField(
            model_name="barangpenunjangoperasional",
            name="volume",
            field=models.PositiveIntegerField(default=1, validators=[MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="barangpenunjangoperasional",
            name="volume_rusak",
            field=models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
    ]
