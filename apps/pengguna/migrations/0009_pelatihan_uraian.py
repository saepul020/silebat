# Generated manually for SILEBAT Pelatihan uraian field.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pengguna', '0008_rename_pengguna_pe_user_id_5e6d87_idx_pengguna_pe_user_id_4dd45d_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pelatihan',
            name='uraian_pelatihan',
            field=models.TextField(blank=True, default=''),
        ),
    ]
