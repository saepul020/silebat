# Generated manually to store routine maintenance component lists for survey equipment.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0014_add_ik_alat_to_sarana_peralatan_lab"),
    ]

    operations = [
        migrations.AddField(
            model_name="baranglaboratorium",
            name="komponen_pemeliharaan",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
