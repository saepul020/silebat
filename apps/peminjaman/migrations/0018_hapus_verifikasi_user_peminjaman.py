from django.db import migrations, models


def pindahkan_tahap_user_ke_kepala_lab(apps, schema_editor):
    PeminjamanRequest = apps.get_model("peminjaman", "PeminjamanRequest")
    PeminjamanRequest.objects.filter(current_step="user").update(
        current_step="kepala_lab",
        user_verification_status="approved",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0017_normalize_nomor_pengajuan"),
    ]

    operations = [
        migrations.RunPython(
            pindahkan_tahap_user_ke_kepala_lab,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="peminjamanrequest",
            name="current_step",
            field=models.CharField(
                choices=[
                    ("admin_lab", "Verifikasi Peminjaman - Admin Lab"),
                    ("teknisi_lab", "Proses Peminjaman - Teknisi Lab"),
                    ("kepala_lab", "Verifikasi Peminjaman - Kepala Lab"),
                    ("pimpinan", "Verifikasi Peminjaman - Ketua Tim"),
                    ("approved", "Disetujui"),
                    ("rejected", "Ditolak"),
                ],
                default="admin_lab",
                max_length=30,
            ),
        ),
    ]
