from django.core.management.base import BaseCommand

from apps.pengguna.models import DEFAULT_ROLE_NAMES, Role, sync_default_roles


class Command(BaseCommand):
    help = "Menyinkronkan data role default ke database"

    def handle(self, *args, **kwargs):
        self.stdout.write("Memulai sinkronisasi role default...")

        sync_default_roles()

        for nama_role in DEFAULT_ROLE_NAMES:
            role = Role.objects.filter(nama=nama_role).first()

            if role:
                status = "aktif" if role.is_active else "nonaktif"
                self.stdout.write(
                    self.style.SUCCESS(f"Role '{nama_role}' tersedia ({status}).")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"Role '{nama_role}' tidak ditemukan.")
                )

        self.stdout.write(self.style.SUCCESS("Proses sinkronisasi role selesai."))
