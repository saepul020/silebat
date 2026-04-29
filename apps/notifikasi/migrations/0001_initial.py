# Generated manually for fitur notifikasi SILEBAT.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("peminjaman", "0014_peralatan_laboratorium_items"),
    ]

    operations = [
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("message", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                ("publish_start_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("publish_end_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pengumuman_dibuat",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Pengumuman",
                "verbose_name_plural": "Pengumuman",
                "ordering": ["-publish_start_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("message", models.TextField()),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("verification", "Verifikasi"),
                            ("status", "Status"),
                            ("announcement", "Pengumuman"),
                            ("system", "Sistem"),
                        ],
                        default="system",
                        max_length=30,
                    ),
                ),
                ("link_url", models.CharField(blank=True, max_length=255)),
                ("dedupe_key", models.CharField(blank=True, db_index=True, max_length=220)),
                ("is_read", models.BooleanField(default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifikasi_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_pengajuan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifikasi_items",
                        to="peminjaman.peminjamanrequest",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notifikasi",
                "verbose_name_plural": "Notifikasi",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "is_read", "-created_at"], name="notifikasi_n_recipie_9a6625_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["category", "-created_at"], name="notifikasi_n_categor_e32f7a_idx"),
        ),
    ]
