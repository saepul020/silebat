# Generated manually to add rejected maintenance verification states.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pemeliharaan", "0003_kunci_alat_aktif"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pemeliharaanpengajuan",
            name="current_step",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("kepala_lab", "Verifikasi Pemeliharaan - Kepala Lab"),
                    ("pimpinan", "Verifikasi Pemeliharaan - Ketua Tim Layanan Teknis"),
                    ("selesai", "Selesai"),
                    ("ditolak", "Ditolak"),
                    ("dikembalikan", "Dikembalikan ke Pemohon"),
                ],
                default="draft",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="pemeliharaanpengajuan",
            name="kepala_lab_status",
            field=models.CharField(
                choices=[
                    ("pending", "Menunggu"),
                    ("approved", "Disetujui"),
                    ("rejected", "Ditolak"),
                    ("revision", "Dikembalikan"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="pemeliharaanpengajuan",
            name="pimpinan_status",
            field=models.CharField(
                choices=[
                    ("pending", "Menunggu"),
                    ("approved", "Disetujui"),
                    ("rejected", "Ditolak"),
                    ("revision", "Dikembalikan"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
