from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InstansiKlien',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_instansi', models.CharField(max_length=200, unique=True)),
                ('alamat_instansi', models.TextField()),
                ('organisasi', models.CharField(choices=[('Internal PU', 'Internal PU'), ('Eksternal PU', 'Eksternal PU'), ('Internal BAT', 'Internal BAT')], max_length=30)),
            ],
            options={
                'verbose_name': 'Data Instansi (Klien)',
                'verbose_name_plural': 'Data Instansi (Klien)',
                'ordering': ['nama_instansi'],
            },
        ),
        migrations.CreateModel(
            name='LayananKegiatan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jenis_layanan', models.CharField(max_length=150, unique=True)),
            ],
            options={
                'verbose_name': 'Data Layanan Kegiatan',
                'verbose_name_plural': 'Data Layanan Kegiatan',
                'ordering': ['jenis_layanan'],
            },
        ),
        migrations.CreateModel(
            name='TimKegiatan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_tim', models.CharField(max_length=150, unique=True)),
                ('ketua_tim', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tim_kegiatan_dipimpin', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Data Tim Kegiatan',
                'verbose_name_plural': 'Data Tim Kegiatan',
                'ordering': ['nama_tim'],
            },
        ),
    ]
