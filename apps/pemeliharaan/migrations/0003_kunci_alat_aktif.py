# Generated manually to prevent duplicate active maintenance requests.

from django.db import migrations, models


ACTIVE_STEPS = ("draft", "kepala_lab", "pimpinan", "dikembalikan")


class Migration(migrations.Migration):

    dependencies = [
        ("pemeliharaan", "0002_alur_verifikasi_pemeliharaan"),
    ]

    operations = [
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="kondisi_barang_sebelum",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddConstraint(
            model_name="pemeliharaanpengajuan",
            constraint=models.UniqueConstraint(
                condition=models.Q(alat__isnull=False, current_step__in=ACTIVE_STEPS),
                fields=("alat",),
                name="uq_pemeliharaan_alat_aktif",
            ),
        ),
    ]
