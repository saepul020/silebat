from django.core.validators import MinValueValidator
from django.db import migrations, models


def normalize_existing_category_values(apps, schema_editor):
    BarangLaboratorium = apps.get_model('master_data', 'BarangLaboratorium')
    BarangPenunjangOperasional = apps.get_model('master_data', 'BarangPenunjangOperasional')

    BarangLaboratorium.objects.filter(
        kategori_barang='Penunjang Survei Lapangan'
    ).update(kategori_barang='Pendukung Survei Lapangan')

    BarangPenunjangOperasional.objects.filter(
        kategori_barang='Penunjang Operasional Alat'
    ).update(kategori_barang='Penunjang Operasional Alat Survei')
    BarangPenunjangOperasional.objects.filter(
        kategori_barang='Penunjang Operasional Ruangan/Kantor'
    ).update(kategori_barang='Penunjang Operasional Lapangan')
    BarangPenunjangOperasional.objects.filter(
        kategori_barang='Barang Penunjang Operasional Ruangan/Kantor'
    ).update(kategori_barang='Penunjang Operasional Lapangan')


def reverse_normalize_existing_category_values(apps, schema_editor):
    BarangPenunjangOperasional = apps.get_model('master_data', 'BarangPenunjangOperasional')
    BarangPenunjangOperasional.objects.filter(
        kategori_barang='Penunjang Operasional Alat Survei'
    ).update(kategori_barang='Penunjang Operasional Alat')


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0007_alter_baranglaboratorium_kategori_barang'),
    ]

    operations = [
        migrations.RunPython(
            normalize_existing_category_values,
            reverse_normalize_existing_category_values,
        ),
        migrations.AddField(
            model_name='bahanoperasional',
            name='kategori_barang',
            field=models.CharField(
                choices=[
                    ('Bahan Laboratorium', 'Bahan Laboratorium'),
                    ('Bahan Lapangan', 'Bahan Lapangan'),
                    ('Suku Cadang', 'Suku Cadang'),
                ],
                default='Bahan Lapangan',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='fasilitasruangan',
            name='kategori_barang',
            field=models.CharField(
                choices=[
                    ('Fasilitas Ruangan', 'Fasilitas Ruangan'),
                    ('Fasilitas Lainnya', 'Fasilitas Lainnya'),
                ],
                default='Fasilitas Ruangan',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='fasilitasruangan',
            name='volume_rusak',
            field=models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='baranglaboratorium',
            name='kategori_barang',
            field=models.CharField(
                choices=[
                    ('Borehole Camera', 'Borehole Camera'),
                    ('Drone', 'Drone'),
                    ('Geolistrik', 'Geolistrik'),
                    ('Instrumen Keairan', 'Instrumen Keairan'),
                    ('Logging', 'Logging'),
                    ('Topografi (TS)', 'Topografi (TS)'),
                    ('Pendukung Survei Lapangan', 'Pendukung Survei Lapangan'),
                ],
                max_length=40,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='barangpenunjangoperasional',
            name='kategori_barang',
            field=models.CharField(
                choices=[
                    ('Penunjang Operasional Alat Survei', 'Penunjang Operasional Alat Survei'),
                    ('Penunjang Operasional Lapangan', 'Penunjang Operasional Lapangan'),
                    ('Penunjang Operasional K3 dan Pelindung', 'Penunjang Operasional K3 dan Pelindung'),
                ],
                max_length=60,
            ),
        ),
        migrations.AlterModelOptions(
            name='baranglaboratorium',
            options={
                'ordering': ['nama_barang'],
                'verbose_name': 'Data Peralatan Survei Lapangan',
                'verbose_name_plural': 'Data Peralatan Survei Lapangan',
            },
        ),
        migrations.AlterModelOptions(
            name='barangpenunjangoperasional',
            options={
                'ordering': ['nama_barang'],
                'verbose_name': 'Data Barang Penunjang Lapangan',
                'verbose_name_plural': 'Data Barang Penunjang Lapangan',
            },
        ),
        migrations.AlterModelOptions(
            name='fasilitasruangan',
            options={
                'ordering': ['nama_barang'],
                'verbose_name': 'Data Sarana Prasarana Ruangan',
                'verbose_name_plural': 'Data Sarana Prasarana Ruangan',
            },
        ),
        migrations.CreateModel(
            name='PeralatanLaboratorium',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_barang', models.CharField(max_length=200)),
                ('tipe_merek_barang', models.CharField(max_length=200)),
                ('jenis_barang', models.CharField(max_length=150)),
                ('status_barang', models.CharField(choices=[('BMN', 'BMN'), ('Non BMN', 'Non BMN')], max_length=20)),
                ('kode_aset_bmn', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('kode_laboratorium', models.CharField(max_length=100, unique=True)),
                ('volume', models.PositiveIntegerField(default=1)),
                ('volume_rusak', models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])),
                ('satuan', models.CharField(choices=[('Buah', 'Buah'), ('Unit', 'Unit'), ('Set', 'Set')], default='Unit', max_length=20)),
                ('ketersediaan', models.CharField(choices=[('Tersedia', 'Tersedia'), ('Tidak Tersedia', 'Tidak Tersedia')], default='Tersedia', editable=False, max_length=20)),
                ('tahun_perolehan', models.PositiveIntegerField(blank=True, null=True)),
                ('kondisi_barang', models.CharField(choices=[('Baik', 'Baik'), ('Dalam Pemeliharaan', 'Dalam Pemeliharaan'), ('Dalam Perbaikan', 'Dalam Perbaikan'), ('Rusak', 'Rusak'), ('Hilang', 'Hilang')], default='Baik', max_length=30)),
                ('lokasi_barang', models.CharField(max_length=200)),
                ('foto_barang', models.ImageField(blank=True, null=True, upload_to='master_data/foto_barang/')),
                ('tanggal_pemeliharaan', models.DateField(blank=True, null=True)),
                ('tanggal_perbaikan', models.DateField(blank=True, null=True)),
                ('catatan', models.TextField(blank=True)),
                ('sedang_dipinjam', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Data Peralatan Laboratorium',
                'verbose_name_plural': 'Data Peralatan Laboratorium',
                'ordering': ['nama_barang'],
            },
        ),
    ]
