import uuid

from django.db import migrations


MODEL_NAMES = [
    'BarangLaboratorium',
    'BarangPenunjangOperasional',
    'BahanOperasional',
    'FasilitasRuangan',
    'PeralatanLaboratorium',
]


def populate_qr_tokens(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    for model_name in MODEL_NAMES:
        model = apps.get_model('master_data', model_name)
        for obj in model.objects.using(db_alias).filter(qr_token__isnull=True).iterator():
            obj.qr_token = uuid.uuid4()
            obj.save(update_fields=['qr_token'])


def clear_qr_tokens(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    for model_name in MODEL_NAMES:
        model = apps.get_model('master_data', model_name)
        model.objects.using(db_alias).update(qr_token=None)


class Migration(migrations.Migration):

    dependencies = [
        ('master_data', '0011_add_qr_fields'),
    ]

    operations = [
        migrations.RunPython(populate_qr_tokens, clear_qr_tokens),
    ]
