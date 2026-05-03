# Generated manually for SILEBAT landing page configuration.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("master_data", "0014_add_ik_alat_to_sarana_peralatan_lab"),
    ]

    operations = [
        migrations.CreateModel(
            name="LandingPeralatanCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("jenis_alat", models.CharField(max_length=120, verbose_name="Jenis Alat")),
                ("merek_tipe_alat", models.CharField(max_length=180, verbose_name="Merek / Tipe Alat")),
                ("nama_barang", models.CharField(max_length=180, verbose_name="Nama Barang")),
                ("ringkasan_alat", models.TextField(verbose_name="Ringkasan Alat")),
                ("fungsi", models.CharField(max_length=220, verbose_name="Fungsi")),
                ("merek_tipe", models.CharField(max_length=180, verbose_name="Merek/Tipe")),
                ("spesifikasi", models.TextField(verbose_name="Spesifikasi")),
                ("icon_class", models.CharField(default="bi bi-tools", help_text="Contoh: bi bi-lightning-charge-fill, bi bi-moisture, bi bi-send-fill.", max_length=80, verbose_name="Icon Bootstrap")),
                ("urutan", models.PositiveIntegerField(default=0, verbose_name="Urutan Tampil")),
                ("is_active", models.BooleanField(default=True, verbose_name="Tampilkan di Landing Page")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("peralatan", models.ForeignKey(blank=True, help_text="Opsional. Jika dipilih, nama barang, jenis alat, dan merek/tipe dapat mengikuti data master.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="landing_cards", to="master_data.peralatanlaboratorium", verbose_name="Referensi Data Peralatan Laboratorium")),
            ],
            options={
                "verbose_name": "Konten Peralatan Landing Page",
                "verbose_name_plural": "Konten Peralatan Landing Page",
                "ordering": ["urutan", "nama_barang", "id"],
            },
        ),
    ]
