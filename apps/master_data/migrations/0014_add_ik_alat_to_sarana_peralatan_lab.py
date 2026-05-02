# Generated manually to add shared IK Alat document support to asset master data.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0013_finalize_unique_qr_tokens"),
    ]

    operations = [
        migrations.AddField(
            model_name="fasilitasruangan",
            name="ik_alat",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="master_data/ik_alat/",
                validators=[django.core.validators.FileExtensionValidator(["pdf"])],
            ),
        ),
        migrations.AddField(
            model_name="peralatanlaboratorium",
            name="ik_alat",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="master_data/ik_alat/",
                validators=[django.core.validators.FileExtensionValidator(["pdf"])],
            ),
        ),
    ]
