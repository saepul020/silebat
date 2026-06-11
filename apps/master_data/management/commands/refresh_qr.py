from django.core.management.base import BaseCommand, CommandError

from apps.master_data.models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    FasilitasRuangan,
    PeralatanLaboratorium,
)
from apps.master_data.qr_utils import ensure_master_qr_code, master_qr_file_exists


MASTER_QR_MODELS = (
    BarangLaboratorium,
    BarangPenunjangOperasional,
    BahanOperasional,
    FasilitasRuangan,
    PeralatanLaboratorium,
)


class Command(BaseCommand):
    help = "Regenerate and verify QR-Code PNG files for all master data items."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate every QR-Code PNG even when the current file still exists.",
        )
        parser.add_argument(
            "--refresh-token",
            action="store_true",
            help=(
                "Generate a new qr_token for every item before recreating QR-Code files. "
                "Use this after changing PUBLIC_BASE_URL to avoid browser cache and old printed QR links."
            ),
        )
        parser.add_argument(
            "--clear-db-path",
            action="store_true",
            help="Clear qr_code database paths first, then regenerate them.",
        )
        parser.add_argument(
            "--verbose-items",
            action="store_true",
            help="Print one line for every processed item.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        refresh_token = options["refresh_token"]
        clear_db_path = options["clear_db_path"]
        verbose_items = options["verbose_items"]

        grand_total = 0
        grand_created_or_updated = 0
        grand_existing = 0
        failures = []

        for model in MASTER_QR_MODELS:
            model_total = 0
            model_created_or_updated = 0
            model_existing = 0
            model_failed = 0

            queryset = model.objects.all().order_by("pk")

            for obj in queryset.iterator():
                model_total += 1
                grand_total += 1

                try:
                    if clear_db_path and getattr(obj, "qr_code", None):
                        obj.__class__.objects.filter(pk=obj.pk).update(qr_code="")
                        obj.qr_code.name = ""

                    existed_before = master_qr_file_exists(obj)
                    saved_name = ensure_master_qr_code(
                        obj,
                        force=force or clear_db_path,
                        refresh_token=refresh_token,
                    )

                    obj.refresh_from_db(fields=["qr_token", "qr_code"])
                    exists_after = master_qr_file_exists(obj)

                    if not saved_name or not exists_after:
                        raise RuntimeError(
                            f"QR-Code tidak terbentuk. saved_name={saved_name!r}, "
                            f"db_path={getattr(obj.qr_code, 'name', '')!r}"
                        )

                    if force or refresh_token or clear_db_path or not existed_before:
                        model_created_or_updated += 1
                        grand_created_or_updated += 1
                        status = "UPDATED"
                    else:
                        model_existing += 1
                        grand_existing += 1
                        status = "EXISTS"

                    if verbose_items:
                        self.stdout.write(
                            f"{status}: {model.__name__} ID={obj.pk} -> {obj.qr_code.name}"
                        )

                except Exception as exc:  # noqa: BLE001 - management command should report all row failures
                    model_failed += 1
                    failures.append((model.__name__, obj.pk, str(exc)))
                    self.stdout.write(
                        self.style.ERROR(f"FAILED: {model.__name__} ID={obj.pk} -> {exc}")
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{model.__name__}: total={model_total}, "
                    f"dibuat/diperbarui={model_created_or_updated}, "
                    f"sudah_ada={model_existing}, gagal={model_failed}"
                )
            )

        self.stdout.write("-" * 72)
        self.stdout.write(self.style.SUCCESS(f"Total data diperiksa: {grand_total}"))
        self.stdout.write(
            self.style.SUCCESS(f"Total QR-Code dibuat/diperbarui: {grand_created_or_updated}")
        )
        self.stdout.write(self.style.SUCCESS(f"Total QR-Code sudah ada: {grand_existing}"))

        if failures:
            self.stdout.write(self.style.ERROR(f"Total gagal: {len(failures)}"))
            self.stdout.write(self.style.ERROR("Daftar data yang gagal:"))
            for model_name, pk, error in failures:
                self.stdout.write(self.style.ERROR(f"- {model_name} ID={pk}: {error}"))
            raise CommandError("Sebagian QR-Code gagal dibuat. Lihat daftar error di atas.")

        self.stdout.write(self.style.SUCCESS("Selesai. Semua QR-Code master data valid."))
