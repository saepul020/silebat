from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('pengguna', '0019_logbook')]

    operations = [
        migrations.AddField(
            model_name='logbook',
            name='lingkup',
            field=models.CharField(
                choices=[
                    ('Dukungan Manajemen', 'Dukungan Manajemen'),
                    ('Laboratorium', 'Laboratorium'),
                    ('Layanan Teknis', 'Layanan Teknis'),
                    ('Pengembangan Penerapan', 'Pengembangan Penerapan'),
                ],
                default='',
                max_length=30,
                verbose_name='Lingkup Kegiatan',
            ),
            preserve_default=False,
        ),
    ]
