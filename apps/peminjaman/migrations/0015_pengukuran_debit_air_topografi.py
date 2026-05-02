from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0014_peralatan_laboratorium_items"),
    ]

    operations = [
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_debit_air",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanrequest",
            name="lokasi_topografi",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
