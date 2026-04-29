from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('peminjaman', '0011_normalize_tim_kegiatan_snapshot_labels'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='peminjamanbaranglaboratorium',
            options={
                'ordering': ['barang__nama_barang'],
                'verbose_name': 'Item Peralatan Survei Lapangan',
                'verbose_name_plural': 'Item Peralatan Survei Lapangan',
            },
        ),
        migrations.AlterModelOptions(
            name='peminjamanbarangpenunjang',
            options={
                'ordering': ['barang__nama_barang'],
                'verbose_name': 'Item Barang Penunjang Lapangan',
                'verbose_name_plural': 'Item Barang Penunjang Lapangan',
            },
        ),
        migrations.AlterModelOptions(
            name='pengembalianbaranglaboratorium',
            options={
                'ordering': ['barang__nama_barang'],
                'verbose_name': 'Pengembalian Peralatan Survei Lapangan',
                'verbose_name_plural': 'Pengembalian Peralatan Survei Lapangan',
            },
        ),
        migrations.AlterModelOptions(
            name='pengembalianbarangpenunjang',
            options={
                'ordering': ['barang__nama_barang'],
                'verbose_name': 'Pengembalian Barang Penunjang Lapangan',
                'verbose_name_plural': 'Pengembalian Barang Penunjang Lapangan',
            },
        ),
    ]
