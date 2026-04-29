from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('peminjaman', '0004_alter_peminjamanrequest_return_current_step'),
    ]

    operations = [
        migrations.AddField(
            model_name='pengembalianbahanoperasional',
            name='qty_transfer',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pengembalianbahanoperasional',
            name='transfer_target',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='peminjaman.peminjamanrequest'),
        ),
    ]
