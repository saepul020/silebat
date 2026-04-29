from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0005_pengembalian_bahan_transfer"),
    ]

    operations = [
        migrations.AddField(
            model_name="peminjamanrequest",
            name="berkas_pendukung",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="peminjaman/berkas_pendukung/",
                validators=[FileExtensionValidator(["pdf"])],
            ),
        ),
    ]
