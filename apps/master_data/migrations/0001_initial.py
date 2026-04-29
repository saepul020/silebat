# Generated manually for master_data app.

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='BahanOperasional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_barang', models.CharField(max_length=200)),
                ('volume', models.PositiveIntegerField(default=0)),
                ('satuan', models.CharField(choices=[('Buah', 'Buah'), ('Pak', 'Pak'), ('Rol', 'Rol'), ('Set', 'Set'), ('Box', 'Box'), ('Botol', 'Botol'), ('Jirigen', 'Jirigen'), ('Meter', 'Meter')], max_length=20)),
                ('stok_minimum', models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])),
                ('ketersediaan', models.CharField(choices=[('Baik', 'Baik'), ('Cukup', 'Cukup'), ('Kurang', 'Kurang'), ('Habis', 'Habis')], default='Habis', editable=False, max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Data Bahan Operasional',
                'verbose_name_plural': 'Data Bahan Operasional',
                'ordering': ['nama_barang'],
            },
        ),
        migrations.CreateModel(
            name='BarangLaboratorium',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_barang', models.CharField(max_length=200)),
                ('tipe_merek_barang', models.CharField(max_length=200)),
                ('jenis_barang', models.CharField(max_length=150)),
                ('status_barang', models.CharField(choices=[('BMN', 'BMN'), ('Non BMN', 'Non BMN')], max_length=20)),
                ('kode_aset_bmn', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('kode_laboratorium', models.CharField(max_length=100, unique=True)),
                ('volume', models.PositiveIntegerField(default=1)),
                ('satuan', models.CharField(choices=[('Buah', 'Buah'), ('Unit', 'Unit'), ('Set', 'Set')], default='Unit', max_length=20)),
                ('ketersediaan', models.CharField(choices=[('Tersedia', 'Tersedia'), ('Tidak Tersedia', 'Tidak Tersedia')], default='Tersedia', editable=False, max_length=20)),
                ('tahun_perolehan', models.PositiveIntegerField(blank=True, null=True)),
                ('kondisi_barang', models.CharField(choices=[('Baik', 'Baik'), ('Dalam Pemeliharaan', 'Dalam Pemeliharaan'), ('Dalam Perbaikan', 'Dalam Perbaikan'), ('Rusak', 'Rusak')], default='Baik', max_length=30)),
                ('lokasi_barang', models.CharField(max_length=200)),
                ('foto_barang', models.ImageField(blank=True, null=True, upload_to='master_data/foto_barang/')),
                ('tanggal_pemeliharaan', models.DateField(blank=True, null=True)),
                ('tanggal_perbaikan', models.DateField(blank=True, null=True)),
                ('catatan', models.TextField(blank=True)),
                ('sedang_dipinjam', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ik_alat', models.FileField(blank=True, null=True, upload_to='master_data/ik_alat/', validators=[FileExtensionValidator(['pdf'])])),
            ],
            options={
                'verbose_name': 'Data Barang Laboratorium',
                'verbose_name_plural': 'Data Barang Laboratorium',
                'ordering': ['nama_barang'],
            },
        ),
        migrations.CreateModel(
            name='BarangPenunjangOperasional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_barang', models.CharField(max_length=200)),
                ('tipe_merek_barang', models.CharField(max_length=200)),
                ('volume', models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])),
                ('kategori_barang', models.CharField(choices=[('Penunjang Operasional Alat', 'Penunjang Operasional Alat'), ('Penunjang Operasional Lapangan', 'Penunjang Operasional Lapangan'), ('Penunjang Operasional K3 dan Pelindung', 'Penunjang Operasional K3 dan Pelindung'), ('Barang Penunjang Operasional Ruangan/Kantor', 'Barang Penunjang Operasional Ruangan/Kantor')], max_length=60)),
                ('volume_dipinjam', models.PositiveIntegerField(default=0)),
                ('ketersediaan', models.CharField(choices=[('Tersedia', 'Tersedia'), ('Tidak Tersedia', 'Tidak Tersedia')], default='Tersedia', editable=False, max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Data Barang Penunjang Operasional',
                'verbose_name_plural': 'Data Barang Penunjang Operasional',
                'ordering': ['nama_barang'],
            },
        ),
        migrations.CreateModel(
            name='FasilitasRuangan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_barang', models.CharField(max_length=200)),
                ('tipe_merek_barang', models.CharField(max_length=200)),
                ('jenis_barang', models.CharField(max_length=150)),
                ('status_barang', models.CharField(choices=[('BMN', 'BMN'), ('Non BMN', 'Non BMN')], max_length=20)),
                ('kode_aset_bmn', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('kode_laboratorium', models.CharField(max_length=100, unique=True)),
                ('volume', models.PositiveIntegerField(default=1)),
                ('satuan', models.CharField(choices=[('Buah', 'Buah'), ('Unit', 'Unit'), ('Set', 'Set')], default='Unit', max_length=20)),
                ('ketersediaan', models.CharField(choices=[('Tersedia', 'Tersedia'), ('Tidak Tersedia', 'Tidak Tersedia')], default='Tersedia', editable=False, max_length=20)),
                ('tahun_perolehan', models.PositiveIntegerField(blank=True, null=True)),
                ('kondisi_barang', models.CharField(choices=[('Baik', 'Baik'), ('Dalam Pemeliharaan', 'Dalam Pemeliharaan'), ('Dalam Perbaikan', 'Dalam Perbaikan'), ('Rusak', 'Rusak')], default='Baik', max_length=30)),
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
                'verbose_name': 'Data Fasilitas Ruangan',
                'verbose_name_plural': 'Data Fasilitas Ruangan',
                'ordering': ['nama_barang'],
            },
        ),
    ]
