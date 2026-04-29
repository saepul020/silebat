from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0008_peminjamanrequest_report_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_geolistrik_1d",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanrequest",
            name="lintasan_geolistrik_2d",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_kualitas_air",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_mat",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_borehole",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanrequest",
            name="titik_logging",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
