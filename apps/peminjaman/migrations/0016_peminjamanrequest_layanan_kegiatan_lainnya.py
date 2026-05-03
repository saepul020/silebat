# Generated manually for SILEBAT layanan kegiatan lainnya

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0015_pengukuran_debit_air_topografi"),
    ]

    operations = [
        migrations.AddField(
            model_name="peminjamanrequest",
            name="layanan_kegiatan_lainnya",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
