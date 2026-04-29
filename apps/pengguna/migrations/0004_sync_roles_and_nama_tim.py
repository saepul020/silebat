from django.db import migrations, models
import django.db.models.deletion


DEFAULT_ROLES = [
    'User',
    'Admin Lab',
    'Teknisi Lab',
    'Kepala Lab',
    'Pimpinan',
]

ROLE_RENAME_MAP = {
    'Admin': 'Admin Lab',
    'Petugas Laboratorium': 'Teknisi Lab',
    'Peminjam': 'User',
    'Approver': 'Kepala Lab',
    'Pimpinan': 'Pimpinan',
}


def forwards(apps, schema_editor):
    Role = apps.get_model('pengguna', 'Role')
    UserProfile = apps.get_model('pengguna', 'UserProfile')
    TimKegiatan = apps.get_model('operasional', 'TimKegiatan')

    role_lookup = {}
    for role_name in DEFAULT_ROLES:
        role, _ = Role.objects.get_or_create(nama=role_name, defaults={'is_active': True})
        if not role.is_active:
            role.is_active = True
            role.save(update_fields=['is_active'])
        role_lookup[role_name] = role

    for old_name, new_name in ROLE_RENAME_MAP.items():
        old_role = Role.objects.filter(nama=old_name).first()
        new_role = role_lookup[new_name]
        if old_role:
            UserProfile.objects.filter(role=old_role).update(role=new_role)
            if old_role.nama != new_role.nama:
                old_role.is_active = False
                old_role.save(update_fields=['is_active'])

    for profile in UserProfile.objects.exclude(unit_kerja__isnull=True).exclude(unit_kerja__exact=''):
        nama_tim = (profile.unit_kerja or '').strip()
        if not nama_tim:
            continue
        tim, _ = TimKegiatan.objects.get_or_create(nama_tim=nama_tim)
        profile.nama_tim = tim
        profile.save(update_fields=['nama_tim'])


def backwards(apps, schema_editor):
    UserProfile = apps.get_model('pengguna', 'UserProfile')

    for profile in UserProfile.objects.exclude(nama_tim__isnull=True):
        profile.unit_kerja = str(profile.nama_tim)
        profile.save(update_fields=['unit_kerja'])


class Migration(migrations.Migration):

    dependencies = [
        ('operasional', '0001_initial'),
        ('pengguna', '0003_alter_user_no_hp'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='nama_tim',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='anggota_pengguna', to='operasional.timkegiatan'),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name='userprofile',
            name='unit_kerja',
        ),
    ]
