from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('peminjaman', '0002_pengembalian_flow'),
    ]

    operations = [
        migrations.AddField(
            model_name='peminjamanrequest',
            name='return_user_verification_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='peminjamanrequest',
            name='return_user_verification_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='peminjamanrequest',
            name='return_user_verification_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Menunggu'),
                    ('approved', 'Disetujui'),
                    ('rejected', 'Ditolak'),
                    ('revision', 'Perbaiki'),
                    ('ready', 'Siap / Selesai'),
                    ('mismatch', 'Belum Sesuai'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
