# Generated for SILEBAT: add pemeliharaan transaction notification source.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("notifikasi", "0003_rename_notifikasi_n_recipie_9a6625_idx_notifikasi__recipie_34c3e3_idx_and_more"),
        ("pemeliharaan", "0006_snapshot_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="source_pemeliharaan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifikasi_items",
                to="pemeliharaan.pemeliharaanpengajuan",
            ),
        ),
    ]
