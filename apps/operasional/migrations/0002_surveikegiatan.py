from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('operasional', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SurveiKegiatan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jenis_survei', models.CharField(max_length=150, unique=True)),
            ],
            options={
                'verbose_name': 'Data Kegiatan Survei',
                'verbose_name_plural': 'Data Kegiatan Survei',
                'ordering': ['jenis_survei'],
            },
        ),
    ]
