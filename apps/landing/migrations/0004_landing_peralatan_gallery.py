from django.db import migrations, models
import django.db.models.deletion


def migrate_photo_to_gallery(apps, schema_editor):
    Card = apps.get_model("landing", "LandingPeralatanCard")
    Photo = apps.get_model("landing", "LandingPeralatanFoto")
    for card in Card.objects.exclude(foto_barang="").exclude(foto_barang__isnull=True):
        Photo.objects.create(card_id=card.pk, foto=card.foto_barang, urutan=1)


def restore_first_gallery_photo(apps, schema_editor):
    Card = apps.get_model("landing", "LandingPeralatanCard")
    Photo = apps.get_model("landing", "LandingPeralatanFoto")
    for card in Card.objects.all():
        first = Photo.objects.filter(card_id=card.pk).order_by("urutan", "id").first()
        if first:
            card.foto_barang = first.foto
            card.save(update_fields=["foto_barang"])


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0003_alter_landingperalatancard_jenis_barang"),
    ]

    operations = [
        migrations.CreateModel(
            name="LandingPeralatanFoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("foto", models.ImageField(upload_to="landing/peralatan/", verbose_name="Foto Barang")),
                ("urutan", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("card", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fotos", to="landing.landingperalatancard")),
            ],
            options={
                "verbose_name": "Foto Peralatan Landing Page",
                "verbose_name_plural": "Foto Peralatan Landing Page",
                "ordering": ["urutan", "id"],
            },
        ),
        migrations.RunPython(migrate_photo_to_gallery, restore_first_gallery_photo),
        migrations.RemoveField(
            model_name="landingperalatancard",
            name="foto_barang",
        ),
    ]
