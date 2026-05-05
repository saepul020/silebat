# Generated manually for SILEBAT Pelatihan uraian required form/model state.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pengguna', '0009_pelatihan_uraian'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pelatihan',
            name='uraian_pelatihan',
            field=models.TextField(default=''),
        ),
    ]
