from django.db import migrations


DEFAULT_ROLES = {
    'User',
    'Admin Lab',
    'Teknisi Lab',
    'Kepala Lab',
    'Pimpinan',
}

LEGACY_ROLES_TO_DELETE = {
    'Admin',
    'Petugas Laboratorium',
    'Peminjam',
    'Approver',
}


def forwards(apps, schema_editor):
    Role = apps.get_model('pengguna', 'Role')
    UserProfile = apps.get_model('pengguna', 'UserProfile')

    # Pastikan seluruh user tidak lagi menunjuk ke role legacy.
    # Bila masih ada yang lolos dari migrasi sebelumnya, arahkan ke default aman: User.
    fallback_role = Role.objects.filter(nama='User').first()
    if fallback_role:
        UserProfile.objects.filter(role__nama__in=LEGACY_ROLES_TO_DELETE).update(role=fallback_role)

    # Hapus hanya role legacy yang memang sudah tidak dipakai lagi.
    Role.objects.filter(nama__in=LEGACY_ROLES_TO_DELETE).delete()

    # Pengaman tambahan: bila ada role non-default yang nonaktif hasil proses lama,
    # biarkan tetap ada agar tidak menghapus role kustom yang mungkin sengaja dibuat.


def backwards(apps, schema_editor):
    Role = apps.get_model('pengguna', 'Role')

    for role_name in sorted(LEGACY_ROLES_TO_DELETE):
        Role.objects.get_or_create(
            nama=role_name,
            defaults={
                'deskripsi': f'Role legacy hasil rollback migrasi: {role_name}',
                'is_active': False,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pengguna', '0004_sync_roles_and_nama_tim'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
