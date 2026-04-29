from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0010_peralatan_laboratorium_volume_dipinjam'),
        ('peminjaman', '0013_decouple_report_items_from_master_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='PeminjamanPeralatanLaboratorium',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('volume', models.PositiveIntegerField(default=1)),
                ('snapshot_nama_barang', models.CharField(blank=True, max_length=200)),
                ('snapshot_tipe_merek_barang', models.CharField(blank=True, max_length=200)),
                ('snapshot_jenis_barang', models.CharField(blank=True, max_length=150)),
                ('snapshot_status_barang', models.CharField(blank=True, max_length=20)),
                ('snapshot_kode_aset_bmn', models.CharField(blank=True, max_length=100)),
                ('snapshot_kode_laboratorium', models.CharField(blank=True, max_length=100)),
                ('snapshot_volume', models.PositiveIntegerField(blank=True, null=True)),
                ('snapshot_satuan', models.CharField(blank=True, max_length=20)),
                ('snapshot_kondisi_barang', models.CharField(blank=True, max_length=30)),
                ('snapshot_tahun_perolehan', models.PositiveIntegerField(blank=True, null=True)),
                ('barang', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='master_data.peralatanlaboratorium')),
                ('pengajuan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='peralatan_laboratorium_items', to='peminjaman.peminjamanrequest')),
            ],
            options={
                'verbose_name': 'Item Peralatan Laboratorium',
                'verbose_name_plural': 'Item Peralatan Laboratorium',
                'ordering': ['barang__nama_barang', 'snapshot_nama_barang'],
                'unique_together': {('pengajuan', 'barang')},
            },
        ),
        migrations.CreateModel(
            name='PengembalianPeralatanLaboratorium',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty_dikembalikan', models.PositiveIntegerField(default=0)),
                ('qty_rusak', models.PositiveIntegerField(default=0)),
                ('qty_hilang', models.PositiveIntegerField(default=0)),
                ('qty_transfer', models.PositiveIntegerField(default=0)),
                ('note', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('snapshot_nama_barang', models.CharField(blank=True, max_length=200)),
                ('snapshot_tipe_merek_barang', models.CharField(blank=True, max_length=200)),
                ('snapshot_jenis_barang', models.CharField(blank=True, max_length=150)),
                ('snapshot_status_barang', models.CharField(blank=True, max_length=20)),
                ('snapshot_kode_aset_bmn', models.CharField(blank=True, max_length=100)),
                ('snapshot_kode_laboratorium', models.CharField(blank=True, max_length=100)),
                ('snapshot_volume', models.PositiveIntegerField(blank=True, null=True)),
                ('snapshot_satuan', models.CharField(blank=True, max_length=20)),
                ('snapshot_kondisi_barang', models.CharField(blank=True, max_length=30)),
                ('snapshot_tahun_perolehan', models.PositiveIntegerField(blank=True, null=True)),
                ('barang', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='master_data.peralatanlaboratorium')),
                ('pengajuan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengembalian_peralatan_laboratorium_items', to='peminjaman.peminjamanrequest')),
                ('transfer_target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='peminjaman.peminjamanrequest')),
            ],
            options={
                'verbose_name': 'Pengembalian Peralatan Laboratorium',
                'verbose_name_plural': 'Pengembalian Peralatan Laboratorium',
                'ordering': ['barang__nama_barang', 'snapshot_nama_barang'],
                'unique_together': {('pengajuan', 'barang')},
            },
        ),
    ]
