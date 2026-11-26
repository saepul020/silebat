from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('pengguna', '0011_peserta_pelatihan')]

    operations = [
        migrations.AddField(
            model_name='pelatihan',
            name='kategori_kegiatan',
            field=models.CharField(
                choices=[('Diklat', 'Diklat'), ('Pelatihan', 'Pelatihan'),
                         ('Seminar', 'Seminar'), ('Workshop', 'Workshop')],
                default='Pelatihan',
                max_length=20,
            ),
            preserve_default=False,
        ),
    ]
