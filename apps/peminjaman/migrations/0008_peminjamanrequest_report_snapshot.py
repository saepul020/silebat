from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("peminjaman", "0007_alter_peminjamanrequest_current_step_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="peminjamanrequest",
            name="report_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
