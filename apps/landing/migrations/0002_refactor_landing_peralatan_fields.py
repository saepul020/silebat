# Generated manually for SILEBAT landing equipment content refactor.

from django.db import migrations, models


KATEGORI_BARANG_CHOICES = [
    ("Borehole Camera", "Borehole Camera"),
    ("Drone", "Drone"),
    ("Geolistrik", "Geolistrik"),
    ("Infiltrasi", "Infiltrasi"),
    ("Instrumen Keairan", "Instrumen Keairan"),
    ("Logging", "Logging"),
    ("Topografi (TS)", "Topografi (TS)"),
    ("Pendukung Survei Lapangan", "Pendukung Survei Lapangan"),
]


def migrate_existing_card_values(apps, schema_editor):
    LandingPeralatanCard = apps.get_model("landing", "LandingPeralatanCard")
    valid_categories = {value for value, _ in KATEGORI_BARANG_CHOICES}

    for card in LandingPeralatanCard.objects.all():
        old_jenis_alat = (getattr(card, "jenis_alat", "") or "").strip()
        old_brand = (getattr(card, "merek_tipe_alat", "") or "").strip()
        old_merek_tipe = (getattr(card, "merek_tipe", "") or "").strip()

        card.kategori_barang = old_jenis_alat if old_jenis_alat in valid_categories else ""
        card.jenis_barang = old_brand or old_jenis_alat or "-"
        card.merek_tipe_alat = old_merek_tipe or old_brand or "-"
        card.save(update_fields=["kategori_barang", "jenis_barang", "merek_tipe_alat"])


def normalize_unique_urutan(apps, schema_editor):
    LandingPeralatanCard = apps.get_model("landing", "LandingPeralatanCard")
    used = set()
    next_number = 1

    for card in LandingPeralatanCard.objects.order_by("urutan", "nama_barang", "id"):
        current = int(card.urutan or 0)
        if current < 1 or current in used:
            while next_number in used:
                next_number += 1
            card.urutan = next_number
        used.add(int(card.urutan))
        next_number = max(next_number, int(card.urutan) + 1)
        card.save(update_fields=["urutan"])


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="landingperalatancard",
            name="kategori_barang",
            field=models.CharField(
                choices=KATEGORI_BARANG_CHOICES,
                default="",
                max_length=40,
                verbose_name="Kategori Barang",
            ),
        ),
        migrations.AddField(
            model_name="landingperalatancard",
            name="jenis_barang",
            field=models.CharField(default="", max_length=160, verbose_name="Jenis Barang"),
        ),
        migrations.AddField(
            model_name="landingperalatancard",
            name="foto_barang",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="landing/peralatan/",
                verbose_name="Upload Foto Barang",
            ),
        ),
        migrations.RenameField(
            model_name="landingperalatancard",
            old_name="fungsi",
            new_name="fungsi_alat",
        ),
        migrations.RenameField(
            model_name="landingperalatancard",
            old_name="spesifikasi",
            new_name="spesifikasi_alat",
        ),
        migrations.RunPython(migrate_existing_card_values, migrations.RunPython.noop),
        migrations.RunPython(normalize_unique_urutan, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="landingperalatancard",
            name="peralatan",
        ),
        migrations.RemoveField(
            model_name="landingperalatancard",
            name="jenis_alat",
        ),
        migrations.RemoveField(
            model_name="landingperalatancard",
            name="merek_tipe",
        ),
        migrations.RemoveField(
            model_name="landingperalatancard",
            name="icon_class",
        ),
        migrations.AlterField(
            model_name="landingperalatancard",
            name="fungsi_alat",
            field=models.CharField(max_length=220, verbose_name="Fungsi Alat"),
        ),
        migrations.AlterField(
            model_name="landingperalatancard",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Tampilkan"),
        ),
        migrations.AlterField(
            model_name="landingperalatancard",
            name="spesifikasi_alat",
            field=models.TextField(verbose_name="Spesifikasi Alat"),
        ),
        migrations.AlterField(
            model_name="landingperalatancard",
            name="urutan",
            field=models.PositiveIntegerField(unique=True, verbose_name="Urutan Tampil"),
        ),
    ]
