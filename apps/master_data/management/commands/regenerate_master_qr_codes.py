from django.core.management.base import BaseCommand

from apps.master_data.models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    FasilitasRuangan,
    PeralatanLaboratorium,
)
from apps.master_data.qr_utils import ensure_master_qr_code, master_qr_file_exists


class Command(BaseCommand):
    help = "Regenerate QR-Code PNG files for all master data items."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete and recreate existing QR-Code PNG files. Use this after changing PUBLIC_BASE_URL.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        models = (
            BarangLaboratorium,
            BarangPenunjangOperasional,
            BahanOperasional,
            FasilitasRuangan,
            PeralatanLaboratorium,
        )

        total = 0
        regenerated = 0

        for model in models:
            for obj in model.objects.all().iterator():
                total += 1
                existed_before = master_qr_file_exists(obj)
                ensure_master_qr_code(obj, force=force)
                existed_after = master_qr_file_exists(obj)
                if force or (not existed_before and existed_after):
                    regenerated += 1

        self.stdout.write(self.style.SUCCESS(f"QR-Code diperiksa: {total} data."))
        self.stdout.write(self.style.SUCCESS(f"QR-Code dibuat/diperbarui: {regenerated} data."))
