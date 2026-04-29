from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0008_master_data_relabel_and_peralatan_lab'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baranglaboratorium',
            name='kode_aset_bmn',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='baranglaboratorium',
            name='kode_laboratorium',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='fasilitasruangan',
            name='kode_aset_bmn',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='fasilitasruangan',
            name='kode_laboratorium',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='peralatanlaboratorium',
            name='kode_aset_bmn',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='peralatanlaboratorium',
            name='kode_laboratorium',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='baranglaboratorium',
            name='kategori_barang',
            field=models.CharField(
                choices=[
                    ('Borehole Camera', 'Borehole Camera'),
                    ('Drone', 'Drone'),
                    ('Geolistrik', 'Geolistrik'),
                    ('Infiltrasi', 'Infiltrasi'),
                    ('Instrumen Keairan', 'Instrumen Keairan'),
                    ('Logging', 'Logging'),
                    ('Topografi (TS)', 'Topografi (TS)'),
                    ('Pendukung Survei Lapangan', 'Pendukung Survei Lapangan'),
                ],
                max_length=40,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name='baranglaboratorium',
            constraint=models.UniqueConstraint(
                Lower('kode_laboratorium'),
                name='uq_survei_kode_lab_ci',
            ),
        ),
        migrations.AddConstraint(
            model_name='baranglaboratorium',
            constraint=models.UniqueConstraint(
                Lower('kode_aset_bmn'),
                name='uq_survei_kode_bmn_ci',
            ),
        ),
        migrations.AddConstraint(
            model_name='peralatanlaboratorium',
            constraint=models.UniqueConstraint(
                Lower('kode_laboratorium'),
                name='uq_perlab_kode_lab_ci',
            ),
        ),
        migrations.AddConstraint(
            model_name='peralatanlaboratorium',
            constraint=models.UniqueConstraint(
                Lower('kode_aset_bmn'),
                name='uq_perlab_kode_bmn_ci',
            ),
        ),
        migrations.AddConstraint(
            model_name='barangpenunjangoperasional',
            constraint=models.UniqueConstraint(
                Lower('nama_barang'),
                name='uq_penunjang_nama_ci',
            ),
        ),
        migrations.AddConstraint(
            model_name='bahanoperasional',
            constraint=models.UniqueConstraint(
                Lower('nama_barang'),
                name='uq_bahan_nama_ci',
            ),
        ),
    ]
