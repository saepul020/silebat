# Generated manually for SILEBAT data pelatihan feature.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pengguna', '0006_alter_role_options_alter_user_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pelatihan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipe_pelatihan', models.CharField(choices=[('Pelatihan Internal', 'Pelatihan Internal'), ('Pelatihan Eksternal', 'Pelatihan Eksternal')], max_length=30)),
                ('jenis_pelatihan', models.CharField(choices=[('Laboratorium', 'Laboratorium'), ('Non-Laboratorium', 'Non-Laboratorium')], max_length=30)),
                ('nama_pelatihan', models.CharField(max_length=255)),
                ('tanggal_mulai', models.DateField()),
                ('tanggal_selesai', models.DateField()),
                ('lokasi_pelatihan', models.CharField(max_length=255)),
                ('file_sertifikat', models.FileField(blank=True, null=True, upload_to='pengguna/pelatihan/sertifikat/')),
                ('file_materi', models.FileField(blank=True, null=True, upload_to='pengguna/pelatihan/materi/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='data_pelatihan', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-tanggal_mulai', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pelatihan',
            index=models.Index(fields=['user', '-tanggal_mulai'], name='pengguna_pe_user_id_5e6d87_idx'),
        ),
        migrations.AddIndex(
            model_name='pelatihan',
            index=models.Index(fields=['tipe_pelatihan', 'jenis_pelatihan'], name='pengguna_pe_tipe_pe_7b2f36_idx'),
        ),
    ]
