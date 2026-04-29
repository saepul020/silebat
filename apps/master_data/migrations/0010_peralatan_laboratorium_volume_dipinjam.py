from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0009_adjust_duplicate_validation_and_infiltrasi'),
    ]

    operations = [
        migrations.AddField(
            model_name='peralatanlaboratorium',
            name='volume_dipinjam',
            field=models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
    ]
