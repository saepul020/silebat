# Generated manually for revisi jadwal tampil notifikasi SILEBAT.

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifikasi", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="visible_from",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="notification",
            name="visible_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "visible_from", "visible_until"], name="notifikasi_n_recipie_04b7e6_idx"),
        ),
    ]
