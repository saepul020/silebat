from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0003_barangpenunjangoperasional_satuan'),
        ('peminjaman', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='peminjamanrequest',
            name='return_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='peminjamanrequest',
            name='return_current_step',
            field=models.CharField(choices=[('none', 'Belum Ada Pengembalian'), ('teknisi_verifikasi', 'Verifikasi Pengembalian Teknisi Lab'), ('teknisi_ba', 'Penyusunan Berita Acara Hilang / Rusak'), ('kepala_ba', 'Verifikasi Berita Acara Kepala Laboratorium'), ('pimpinan_ba', 'Verifikasi Berita Acara Pimpinan'), ('teknisi_transfer', 'Proses Transfer Alat oleh Teknisi Lab'), ('kepala_transfer', 'Verifikasi Transfer Alat Kepala Laboratorium'), ('pimpinan_transfer', 'Verifikasi Transfer Alat Pimpinan'), ('completed', 'Pengembalian Selesai')], default='none', max_length=40),
        ),
        migrations.AddField(
            model_name='peminjamanrequest',
            name='return_inventory_applied',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='peminjamanrequest',
            name='return_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='PengembalianBahanOperasional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty_sisa', models.PositiveIntegerField(default=0)),
                ('note', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bahan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='master_data.bahanoperasional')),
                ('pengajuan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengembalian_bahan_items', to='peminjaman.peminjamanrequest')),
            ],
            options={
                'verbose_name': 'Pengembalian Bahan Operasional',
                'verbose_name_plural': 'Pengembalian Bahan Operasional',
                'ordering': ['bahan__nama_barang'],
                'unique_together': {('pengajuan', 'bahan')},
            },
        ),
        migrations.CreateModel(
            name='PengembalianBarangLaboratorium',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('dikembalikan', 'Dikembalikan'), ('hilang', 'Hilang'), ('rusak', 'Rusak'), ('transfer', 'Transfer')], default='dikembalikan', max_length=20)),
                ('note', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('barang', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='master_data.baranglaboratorium')),
                ('pengajuan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengembalian_lab_items', to='peminjaman.peminjamanrequest')),
                ('transfer_target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='peminjaman.peminjamanrequest')),
            ],
            options={
                'verbose_name': 'Pengembalian Barang Laboratorium',
                'verbose_name_plural': 'Pengembalian Barang Laboratorium',
                'ordering': ['barang__nama_barang'],
                'unique_together': {('pengajuan', 'barang')},
            },
        ),
        migrations.CreateModel(
            name='PengembalianBarangPenunjang',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty_dikembalikan', models.PositiveIntegerField(default=0)),
                ('qty_rusak', models.PositiveIntegerField(default=0)),
                ('qty_hilang', models.PositiveIntegerField(default=0)),
                ('qty_transfer', models.PositiveIntegerField(default=0)),
                ('note', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('barang', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='master_data.barangpenunjangoperasional')),
                ('pengajuan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pengembalian_penunjang_items', to='peminjaman.peminjamanrequest')),
                ('transfer_target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='peminjaman.peminjamanrequest')),
            ],
            options={
                'verbose_name': 'Pengembalian Barang Penunjang Operasional',
                'verbose_name_plural': 'Pengembalian Barang Penunjang Operasional',
                'ordering': ['barang__nama_barang'],
                'unique_together': {('pengajuan', 'barang')},
            },
        ),
    ]
