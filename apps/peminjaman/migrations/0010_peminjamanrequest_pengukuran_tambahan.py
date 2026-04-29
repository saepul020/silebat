from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0009_peminjamanrequest_data_pengukuran"),
    ]

    operations = [
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_pumping_test",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_infiltrasi",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
