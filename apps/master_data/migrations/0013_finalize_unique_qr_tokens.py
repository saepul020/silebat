import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0012_populate_qr_tokens'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baranglaboratorium',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='barangpenunjangoperasional',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='bahanoperasional',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='fasilitasruangan',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='peralatanlaboratorium',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
