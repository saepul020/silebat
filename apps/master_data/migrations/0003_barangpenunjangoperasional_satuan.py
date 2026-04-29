from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0002_alter_barangpenunjangoperasional_kategori_barang'),
    ]

    operations = [
        migrations.AddField(
            model_name='barangpenunjangoperasional',
            name='satuan',
            field=models.CharField(
                choices=[('Buah', 'Buah'), ('Unit', 'Unit'), ('Set', 'Set')],
                default='Unit',
                max_length=20,
            ),
        ),
    ]
