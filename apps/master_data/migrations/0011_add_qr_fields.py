from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0010_peralatan_laboratorium_volume_dipinjam'),
    ]

    operations = [
        migrations.AddField(
            model_name='baranglaboratorium',
            name='qr_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='baranglaboratorium',
            name='qr_code',
            field=models.ImageField(blank=True, editable=False, null=True, upload_to='master_data/qr_code/'),
        ),
        migrations.AddField(
            model_name='barangpenunjangoperasional',
            name='qr_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='barangpenunjangoperasional',
            name='qr_code',
            field=models.ImageField(blank=True, editable=False, null=True, upload_to='master_data/qr_code/'),
        ),
        migrations.AddField(
            model_name='bahanoperasional',
            name='qr_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='bahanoperasional',
            name='qr_code',
            field=models.ImageField(blank=True, editable=False, null=True, upload_to='master_data/qr_code/'),
        ),
        migrations.AddField(
            model_name='fasilitasruangan',
            name='qr_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='fasilitasruangan',
            name='qr_code',
            field=models.ImageField(blank=True, editable=False, null=True, upload_to='master_data/qr_code/'),
        ),
        migrations.AddField(
            model_name='peralatanlaboratorium',
            name='qr_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='peralatanlaboratorium',
            name='qr_code',
            field=models.ImageField(blank=True, editable=False, null=True, upload_to='master_data/qr_code/'),
        ),
    ]
