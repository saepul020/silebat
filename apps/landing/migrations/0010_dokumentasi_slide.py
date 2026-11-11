import django.core.validators
import django.db.models.deletion
from django.core.management.color import no_style
from django.db import migrations, models


def move_photos(apps, schema_editor):
    Slide = apps.get_model("landing", "SlideDokumentasi")
    Photo = apps.get_model("landing", "DokumentasiTV")
    alias = schema_editor.connection.alias
    slide = Slide.objects.using(alias).create()
    for photo in Photo.objects.using(alias).all():
        Photo.objects.using(alias).filter(pk=photo.pk).update(slide_id=slide.pk, nomor=photo.pk)
    # Existing slot numbers become photo IDs; advance the identity sequence for new uploads.
    for sql in schema_editor.connection.ops.sequence_reset_sql(no_style(), [Photo]):
        schema_editor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [("landing", "0009_dokumentasi_tv")]

    operations = [
        migrations.CreateModel(
            name="SlideDokumentasi",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))],
            options={
                "ordering": ["pk"],
                "verbose_name": "Slide Dokumentasi TV",
                "verbose_name_plural": "Slide Dokumentasi TV",
            },
        ),
        migrations.RemoveConstraint(model_name="dokumentasitv", name="dokumentasi_nomor_range"),
        migrations.RenameField(model_name="dokumentasitv", old_name="nomor", new_name="id"),
        migrations.AlterField(
            model_name="dokumentasitv", name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AddField(
            model_name="dokumentasitv", name="nomor",
            field=models.PositiveSmallIntegerField(
                default=1,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(6)],
                verbose_name="Nomor Gambar",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dokumentasitv", name="slide",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="fotos", to="landing.slidedokumentasi"),
        ),
        migrations.RunPython(move_photos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="dokumentasitv", name="slide",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fotos", to="landing.slidedokumentasi"),
        ),
        migrations.AlterModelOptions(name="dokumentasitv", options={
            "ordering": ["slide_id", "nomor"], "verbose_name": "Dokumentasi Kegiatan TV", "verbose_name_plural": "Dokumentasi Kegiatan TV",
        }),
        migrations.AddConstraint(
            model_name="dokumentasitv",
            constraint=models.CheckConstraint(condition=models.Q(nomor__gte=1, nomor__lte=6), name="dokumentasi_nomor_range"),
        ),
        migrations.AddConstraint(
            model_name="dokumentasitv",
            constraint=models.UniqueConstraint(fields=("slide", "nomor"), name="dokumentasi_slot_unique"),
        ),
    ]
