from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0004_alter_baranglaboratorium_kondisi_barang_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='baranglaboratorium',
            name='kategori_barang',
            field=models.CharField(
                choices=[
                    ('Geolistrik', 'Geolistrik'),
                    ('Instrumen Keairan', 'Instrumen Keairan'),
                    ('Topografi (TS)', 'Topografi (TS)'),
                    ('Drone', 'Drone'),
                    ('Borehole Camera', 'Borehole Camera'),
                    ('Logging', 'Logging'),
                    ('Pendukung Survei Lapangan', 'Pendukung Survei Lapangan'),
                    ('Penunjang Survei Lapangan', 'Penunjang Survei Lapangan'),
                ],
                max_length=40,
                null=True,
            ),
        ),
    ]
