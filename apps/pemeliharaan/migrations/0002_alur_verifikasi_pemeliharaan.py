# Generated manually to add the maintenance verification workflow.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pemeliharaan", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="current_step",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("kepala_lab", "Verifikasi Pemeliharaan - Kepala Lab"),
                    ("pimpinan", "Verifikasi Pemeliharaan - Pimpinan"),
                    ("selesai", "Selesai"),
                    ("dikembalikan", "Dikembalikan ke Pemohon"),
                ],
                default="draft",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="kepala_lab_status",
            field=models.CharField(
                choices=[
                    ("pending", "Menunggu"),
                    ("approved", "Disetujui"),
                    ("revision", "Dikembalikan"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="kepala_lab_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="kepala_lab_pemeliharaan_processed",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="kepala_lab_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="kepala_lab_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="pimpinan_status",
            field=models.CharField(
                choices=[
                    ("pending", "Menunggu"),
                    ("approved", "Disetujui"),
                    ("revision", "Dikembalikan"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="pimpinan_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pimpinan_pemeliharaan_processed",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="pimpinan_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pemeliharaanpengajuan",
            name="pimpinan_note",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="PemeliharaanTimeline",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("stage", models.CharField(max_length=50)),
                ("action", models.CharField(max_length=120)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="timeline_pemeliharaan_actions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pengajuan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timeline_entries",
                        to="pemeliharaan.pemeliharaanpengajuan",
                    ),
                ),
            ],
            options={
                "verbose_name": "Riwayat Verifikasi Pemeliharaan",
                "verbose_name_plural": "Riwayat Verifikasi Pemeliharaan",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
