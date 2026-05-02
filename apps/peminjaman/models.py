from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.utils import timezone

from apps.master_data.models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    PeralatanLaboratorium,
    KondisiBarangChoices,
    StatusBarangChoices,
)
from apps.operasional.models import InstansiKlien, LayananKegiatan, SurveiKegiatan, TimKegiatan, TIM_LAYANAN_TEKNIS_NAME


class StepChoices(models.TextChoices):
    ADMIN_LAB = "admin_lab", "Verifikasi Peminjaman - Admin Lab"
    TEKNISI_LAB = "teknisi_lab", "Proses Peminjaman - Teknisi Lab"
    USER = "user", "Verifikasi Peminjaman - User"
    KEPALA_LAB = "kepala_lab", "Verifikasi Peminjaman - Kepala Lab"
    PIMPINAN = "pimpinan", "Verifikasi Peminjaman - Ketua Tim"
    APPROVED = "approved", "Disetujui"
    REJECTED = "rejected", "Ditolak"


class DecisionChoices(models.TextChoices):
    PENDING = "pending", "Menunggu"
    APPROVED = "approved", "Disetujui"
    REJECTED = "rejected", "Ditolak"
    REVISION = "revision", "Perbaiki"
    READY = "ready", "Siap / Selesai"
    MISMATCH = "mismatch", "Belum Sesuai"


class ReturnStepChoices(models.TextChoices):
    NONE = "none", "Belum Ada Pengembalian"
    TEKNISI_VERIFICATION = "teknisi_verifikasi", "Verifikasi Pengembalian - Teknisi Lab"
    USER_VERIFICATION = "user_verifikasi", "Verifikasi Pengembalian - User"
    TEKNISI_BA = "teknisi_ba", "Verifikasi Pengembalian - Teknisi Lab"
    KEPALA_BA = "kepala_ba", "Verifikasi Pengembalian - Kepala Lab"
    PIMPINAN_BA = "pimpinan_ba", "Verifikasi Pengembalian - Ketua Tim"
    TEKNISI_TRANSFER = "teknisi_transfer", "Verifikasi Pengembalian - Teknisi Lab"
    KEPALA_TRANSFER = "kepala_transfer", "Verifikasi Pengembalian - Kepala Lab"
    PIMPINAN_TRANSFER = "pimpinan_transfer", "Verifikasi Pengembalian - Ketua Tim"
    COMPLETED = "completed", "Pengembalian Selesai"


class ReturnItemStatusChoices(models.TextChoices):
    DIKEMBALIKAN = "dikembalikan", "Dikembalikan"
    HILANG = "hilang", "Hilang"
    RUSAK = "rusak", "Rusak"
    TRANSFER = "transfer", "Transfer"


RETURN_PIMPINAN_TEAM_NAME = TIM_LAYANAN_TEKNIS_NAME
RETURN_PIMPINAN_LABEL = "Ketua Tim Layanan Teknis"


def _snapshot_text(source, attr, current="", default="-"):
    if source is not None:
        value = getattr(source, attr, None)
        if value not in (None, ""):
            return str(value)
    if current not in (None, ""):
        return str(current)
    return default


def _snapshot_int(source, attr, current=None):
    if source is not None:
        value = getattr(source, attr, None)
        if value is not None:
            return value
    return current


class PeminjamanRequest(models.Model):
    nomor_pengajuan = models.CharField(max_length=30, unique=True, blank=True)
    peminjam = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pengajuan_peminjaman",
    )

    nama_peminjam = models.CharField(max_length=255)
    no_hp_peminjam = models.CharField(max_length=50, blank=True)
    email_peminjam = models.EmailField(blank=True)
    alamat_peminjam = models.TextField(blank=True)
    nip_peminjam = models.CharField(max_length=100, blank=True)

    layanan_kegiatan = models.ForeignKey(
        LayananKegiatan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan_peminjaman",
    )
    kegiatan_survei = models.ManyToManyField(SurveiKegiatan, blank=True)
    survei_lainnya = models.CharField(max_length=255, blank=True)
    tim_kegiatan = models.ForeignKey(
        TimKegiatan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan_peminjaman",
    )
    instansi_tujuan = models.ForeignKey(
        InstansiKlien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan_peminjaman",
    )
    instansi_tujuan_lainnya = models.CharField(max_length=255, blank=True)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    total_hari = models.PositiveIntegerField(default=1)
    berkas_pendukung = models.FileField(
        upload_to="peminjaman/berkas_pendukung/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf"])],
    )

    current_step = models.CharField(
        max_length=30,
        choices=StepChoices.choices,
        default=StepChoices.ADMIN_LAB,
    )
    aset_sudah_dialokasikan = models.BooleanField(default=False)

    admin_lab_status = models.CharField(
        max_length=20,
        choices=DecisionChoices.choices,
        default=DecisionChoices.PENDING,
    )
    admin_lab_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_lab_peminjaman_processed",
    )
    admin_lab_at = models.DateTimeField(null=True, blank=True)
    admin_lab_note = models.TextField(blank=True)

    teknisi_lab_status = models.CharField(
        max_length=20,
        choices=DecisionChoices.choices,
        default=DecisionChoices.PENDING,
    )
    teknisi_lab_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teknisi_lab_peminjaman_processed",
    )
    teknisi_lab_at = models.DateTimeField(null=True, blank=True)
    teknisi_lab_note = models.TextField(blank=True)

    user_verification_status = models.CharField(
        max_length=20,
        choices=DecisionChoices.choices,
        default=DecisionChoices.PENDING,
    )
    user_verification_at = models.DateTimeField(null=True, blank=True)
    user_verification_note = models.TextField(blank=True)

    kepala_lab_status = models.CharField(
        max_length=20,
        choices=DecisionChoices.choices,
        default=DecisionChoices.PENDING,
    )
    kepala_lab_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kepala_lab_peminjaman_processed",
    )
    kepala_lab_at = models.DateTimeField(null=True, blank=True)
    kepala_lab_note = models.TextField(blank=True)

    pimpinan_status = models.CharField(
        max_length=20,
        choices=DecisionChoices.choices,
        default=DecisionChoices.PENDING,
    )
    pimpinan_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pimpinan_peminjaman_processed",
    )
    pimpinan_at = models.DateTimeField(null=True, blank=True)
    pimpinan_note = models.TextField(blank=True)

    return_current_step = models.CharField(
        max_length=40,
        choices=ReturnStepChoices.choices,
        default=ReturnStepChoices.NONE,
    )
    return_started_at = models.DateTimeField(null=True, blank=True)
    return_user_verification_status = models.CharField(
        max_length=20,
        choices=DecisionChoices.choices,
        default=DecisionChoices.PENDING,
    )
    return_user_verification_at = models.DateTimeField(null=True, blank=True)
    return_user_verification_note = models.TextField(blank=True)
    return_completed_at = models.DateTimeField(null=True, blank=True)
    return_inventory_applied = models.BooleanField(default=False)
    report_snapshot = models.JSONField(default=dict, blank=True)

    titik_geolistrik_1d = models.PositiveIntegerField(null=True, blank=True)
    lintasan_geolistrik_2d = models.PositiveIntegerField(null=True, blank=True)
    titik_kualitas_air = models.PositiveIntegerField(null=True, blank=True)
    titik_mat = models.PositiveIntegerField(null=True, blank=True)
    titik_pumping_test = models.PositiveIntegerField(null=True, blank=True)
    titik_infiltrasi = models.PositiveIntegerField(null=True, blank=True)
    titik_debit_air = models.PositiveIntegerField(null=True, blank=True)
    lokasi_topografi = models.PositiveIntegerField(null=True, blank=True)
    titik_borehole = models.PositiveIntegerField(null=True, blank=True)
    titik_logging = models.PositiveIntegerField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]
        verbose_name = "Pengajuan Peminjaman"
        verbose_name_plural = "Pengajuan Peminjaman"

    def __str__(self):
        return self.nomor_pengajuan or f"Peminjaman #{self.pk}"

    def clean(self):
        super().clean()
        if self.tanggal_selesai and self.tanggal_mulai and self.tanggal_selesai < self.tanggal_mulai:
            raise ValidationError({"tanggal_selesai": "Tanggal selesai tidak boleh lebih awal dari tanggal mulai."})
        if self.tanggal_mulai and self.tanggal_selesai:
            self.total_hari = ((self.tanggal_selesai - self.tanggal_mulai).days or 0) + 1

    def save(self, *args, **kwargs):
        if self.tanggal_mulai and self.tanggal_selesai:
            self.total_hari = ((self.tanggal_selesai - self.tanggal_mulai).days or 0) + 1
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.nomor_pengajuan:
            tanggal = timezone.localdate(self.submitted_at or timezone.now())
            self.nomor_pengajuan = f"PMJ-{tanggal.strftime('%Y%m%d')}-{self.pk:04d}"
            super().save(update_fields=["nomor_pengajuan"])

    @property
    def can_download_pdf(self):
        return self.current_step == StepChoices.APPROVED

    @property
    def status_label(self):
        return self.get_current_step_display()

    @property
    def proses_peminjaman_label(self):
        return self.get_current_step_display()

    @property
    def proses_peminjaman_badge_class(self):
        return self.status_badge_class

    @property
    def status_badge_class(self):
        return {
            StepChoices.ADMIN_LAB: "badge-warning",
            StepChoices.TEKNISI_LAB: "badge-primary",
            StepChoices.USER: "badge-warning",
            StepChoices.KEPALA_LAB: "badge-warning",
            StepChoices.PIMPINAN: "badge-warning",
            StepChoices.APPROVED: "badge-success",
            StepChoices.REJECTED: "badge-danger",
        }.get(self.current_step, "badge-secondary")

    @property
    def proses_pengembalian_badge_class(self):
        return {
            ReturnStepChoices.NONE: "badge-secondary",
            ReturnStepChoices.TEKNISI_VERIFICATION: "badge-primary",
            ReturnStepChoices.USER_VERIFICATION: "badge-warning",
            ReturnStepChoices.TEKNISI_BA: "badge-primary",
            ReturnStepChoices.KEPALA_BA: "badge-warning",
            ReturnStepChoices.PIMPINAN_BA: "badge-warning",
            ReturnStepChoices.TEKNISI_TRANSFER: "badge-primary",
            ReturnStepChoices.KEPALA_TRANSFER: "badge-warning",
            ReturnStepChoices.PIMPINAN_TRANSFER: "badge-warning",
            ReturnStepChoices.COMPLETED: "badge-success",
        }.get(self.return_current_step, "badge-secondary")

    @property
    def proses_pengembalian_label(self):
        return self.get_return_current_step_label()

    @property
    def can_open_pengembalian(self):
        return self.current_step == StepChoices.APPROVED or self.return_current_step != ReturnStepChoices.NONE

    @property
    def active_verification_label(self):
        if self.return_current_step not in {ReturnStepChoices.NONE, ReturnStepChoices.COMPLETED}:
            return self.get_return_current_step_label()
        return self.status_label

    @property
    def active_verification_badge_class(self):
        if self.return_current_step not in {ReturnStepChoices.NONE, ReturnStepChoices.COMPLETED}:
            return self.proses_pengembalian_badge_class
        return self.status_badge_class

    @property
    def can_start_pengembalian(self):
        return self.current_step == StepChoices.APPROVED and self.return_current_step != ReturnStepChoices.COMPLETED

    @property
    def is_pengembalian_selesai(self):
        return self.return_current_step == ReturnStepChoices.COMPLETED

    @property
    def can_download_berita_acara(self):
        return self.is_pengembalian_selesai and self.pengembalian_has_issue()

    @property
    def ketua_tim_user(self):
        return getattr(self.tim_kegiatan, "ketua_tim", None)

    def _get_role_signer(self, role_name):
        return (
            self.peminjam.__class__.objects.filter(profile__role__nama=role_name)
            .select_related("profile")
            .order_by("id")
            .first()
        )

    def get_kepala_lab_signer(self):
        kepala_lab_user = self._get_role_signer("Kepala Lab")
        if kepala_lab_user is not None:
            return kepala_lab_user
        if self.kepala_lab_by_id:
            return self.kepala_lab_by
        return None

    @staticmethod
    def _build_transfer_target_label(target):
        if target is None:
            return "-"
        nomor = getattr(target, "nomor_pengajuan", "") or "-"
        nama = getattr(target, "nama_peminjam", "") or "-"
        return f"{nomor} - {nama}"

    @staticmethod
    def _format_snapshot_datetime(value):
        if not value:
            return "-"
        return timezone.localtime(value).strftime("%d %b %Y | %H:%M WIB")

    @staticmethod
    def _format_snapshot_date(value):
        if not value:
            return "-"
        return value.strftime("%d %b %Y")

    @property
    def pengukuran_fields(self):
        return [
            ("titik_geolistrik_1d", "Titik Geolistrik 1D"),
            ("lintasan_geolistrik_2d", "Lintasan Geolistrik 2D"),
            ("titik_kualitas_air", "Titik Kualitas Air"),
            ("titik_mat", "Titik MAT"),
            ("titik_pumping_test", "Titik Pumping Test"),
            ("titik_infiltrasi", "Titik Infiltrasi"),
            ("titik_debit_air", "Titik Debit Air"),
            ("lokasi_topografi", "Lokasi Topografi"),
            ("titik_borehole", "Titik Borehole Camera"),
            ("titik_logging", "Titik Logging"),
        ]

    @staticmethod
    def _format_pengukuran_display(value):
        if value is None:
            return "-"
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return "-"
            try:
                numeric_value = Decimal(stripped)
            except (InvalidOperation, ValueError):
                return value
            return "-" if numeric_value == 0 else value
        if isinstance(value, (int, float, Decimal)):
            return "-" if Decimal(str(value)) == 0 else value
        return value

    def get_pengukuran_data(self):
        return [
            {
                "key": key,
                "label": label,
                "value": getattr(self, key, None),
                "display": self._format_pengukuran_display(getattr(self, key, None)),
            }
            for key, label in self.pengukuran_fields
        ]

    def build_report_snapshot(self):
        asal_maps = build_asal_peminjaman_maps(self)

        lab_return_map = {
            item.barang_id: item
            for item in self.pengembalian_lab_items.select_related("transfer_target").all()
        }
        penunjang_return_map = {
            item.barang_id: item
            for item in self.pengembalian_penunjang_items.select_related("transfer_target").all()
        }
        peralatan_lab_return_map = {
            item.barang_id: item
            for item in self.pengembalian_peralatan_laboratorium_items.select_related("transfer_target").all()
        }
        bahan_return_map = {
            item.bahan_id: item
            for item in self.pengembalian_bahan_items.select_related("transfer_target").all()
        }

        survei_items = [item.jenis_survei for item in self.kegiatan_survei.all()]
        if self.survei_lainnya:
            survei_items.append(f"Lainnya: {self.survei_lainnya}")

        lab_items = []
        for borrowed in self.barang_laboratorium_items.select_related("barang").all():
            returned = lab_return_map.get(borrowed.barang_id)
            lab_items.append(
                {
                    "nama_barang": borrowed.snapshot_nama_barang or "-",
                    "tipe_merek_barang": borrowed.snapshot_tipe_merek_barang or "-",
                    "jenis_barang": borrowed.snapshot_jenis_barang or "-",
                    "status_barang": borrowed.snapshot_status_barang or "-",
                    "kode_aset_bmn": borrowed.snapshot_kode_aset_bmn or "-",
                    "kode_laboratorium": borrowed.snapshot_kode_laboratorium or "-",
                    "volume": borrowed.snapshot_volume if borrowed.snapshot_volume not in (None, "") else "-",
                    "satuan": borrowed.snapshot_satuan or "-",
                    "kondisi_barang": borrowed.snapshot_kondisi_barang or "-",
                    "tahun_perolehan": borrowed.snapshot_tahun_perolehan if borrowed.snapshot_tahun_perolehan not in (None, "") else "-",
                    "asal_peminjaman": resolve_asal_peminjaman_label(asal_maps, "lab", borrowed.barang_id),
                    "status_pengembalian": returned.get_status_display() if returned else "-",
                    "tujuan_transfer": self._build_transfer_target_label(returned.transfer_target) if returned and returned.status == ReturnItemStatusChoices.TRANSFER else "-",
                    "catatan_pengembalian": (returned.note or "-") if returned else "-",
                }
            )

        penunjang_items = []
        for borrowed in self.barang_penunjang_items.select_related("barang").all():
            returned = penunjang_return_map.get(borrowed.barang_id)
            penunjang_items.append(
                {
                    "nama_barang": borrowed.snapshot_nama_barang or "-",
                    "tipe_merek_barang": borrowed.snapshot_tipe_merek_barang or "-",
                    "kategori_barang": borrowed.snapshot_kategori_barang or "-",
                    "volume_dipinjam": borrowed.volume,
                    "satuan": borrowed.snapshot_satuan or "-",
                    "asal_peminjaman": resolve_asal_peminjaman_label(asal_maps, "penunjang", borrowed.barang_id, getattr(borrowed, "volume", 0)),
                    "qty_dikembalikan": getattr(returned, "qty_dikembalikan", 0),
                    "qty_rusak": getattr(returned, "qty_rusak", 0),
                    "qty_hilang": getattr(returned, "qty_hilang", 0),
                    "qty_transfer": getattr(returned, "qty_transfer", 0),
                    "tujuan_transfer": self._build_transfer_target_label(returned.transfer_target) if returned and getattr(returned, "qty_transfer", 0) > 0 else "-",
                    "catatan_pengembalian": (returned.note or "-") if returned else "-",
                }
            )

        peralatan_lab_items = []
        for borrowed in self.peralatan_laboratorium_items.select_related("barang").all():
            returned = peralatan_lab_return_map.get(borrowed.barang_id)
            peralatan_lab_items.append(
                {
                    "nama_barang": borrowed.snapshot_nama_barang or "-",
                    "tipe_merek_barang": borrowed.snapshot_tipe_merek_barang or "-",
                    "jenis_barang": borrowed.snapshot_jenis_barang or "-",
                    "status_barang": borrowed.snapshot_status_barang or "-",
                    "kode_aset_bmn": borrowed.snapshot_kode_aset_bmn or "-",
                    "kode_laboratorium": borrowed.snapshot_kode_laboratorium or "-",
                    "volume_dipinjam": borrowed.volume,
                    "satuan": borrowed.snapshot_satuan or "-",
                    "kondisi_barang": borrowed.snapshot_kondisi_barang or "-",
                    "tahun_perolehan": borrowed.snapshot_tahun_perolehan if borrowed.snapshot_tahun_perolehan not in (None, "") else "-",
                    "asal_peminjaman": resolve_asal_peminjaman_label(asal_maps, "peralatan_lab", borrowed.barang_id, getattr(borrowed, "volume", 0)),
                    "qty_dikembalikan": getattr(returned, "qty_dikembalikan", 0),
                    "qty_rusak": getattr(returned, "qty_rusak", 0),
                    "qty_hilang": getattr(returned, "qty_hilang", 0),
                    "qty_transfer": getattr(returned, "qty_transfer", 0),
                    "tujuan_transfer": self._build_transfer_target_label(returned.transfer_target) if returned and getattr(returned, "qty_transfer", 0) > 0 else "-",
                    "catatan_pengembalian": (returned.note or "-") if returned else "-",
                }
            )

        bahan_items = []
        for borrowed in self.bahan_operasional_items.select_related("bahan").all():
            returned = bahan_return_map.get(borrowed.bahan_id)
            bahan_items.append(
                {
                    "nama_barang": borrowed.snapshot_nama_barang or "-",
                    "volume_dipinjam": borrowed.volume,
                    "satuan": borrowed.snapshot_satuan or "-",
                    "asal_peminjaman": resolve_asal_peminjaman_label(asal_maps, "bahan", borrowed.bahan_id, getattr(borrowed, "volume", 0)),
                    "qty_sisa": getattr(returned, "qty_sisa", 0),
                    "qty_transfer": getattr(returned, "qty_transfer", 0),
                    "tujuan_transfer": self._build_transfer_target_label(returned.transfer_target) if returned and getattr(returned, "qty_transfer", 0) > 0 else "-",
                    "catatan_pengembalian": (returned.note or "-") if returned else "-",
                }
            )

        return {
            "nomor_pengajuan": self.nomor_pengajuan or "-",
            "submitted_at": self._format_snapshot_datetime(self.submitted_at),
            "return_started_at": self._format_snapshot_datetime(self.return_started_at),
            "return_completed_at": self._format_snapshot_datetime(self.return_completed_at),
            "proses_peminjaman_label": self.proses_peminjaman_label,
            "proses_pengembalian_label": self.proses_pengembalian_label,
            "pengembalian_status_text": self.pengembalian_status_text,
            "peminjam": {
                "nama": self.nama_peminjam or "-",
                "nomor_telepon": self.no_hp_peminjam or "-",
                "email": self.email_peminjam or "-",
                "nip": self.nip_peminjam or "-",
                "alamat": self.alamat_peminjam or "-",
            },
            "kegiatan": {
                "layanan_kegiatan": getattr(self.layanan_kegiatan, "jenis_layanan", "-") or "-",
                "kegiatan_survei": survei_items,
                "tim_kegiatan": getattr(self.tim_kegiatan, "nama_tim", "-") or "-",
                "instansi_tujuan": getattr(self.instansi_tujuan, "nama_instansi", self.instansi_tujuan_lainnya or "-") or "-",
                "mulai_tanggal": self._format_snapshot_date(self.tanggal_mulai),
                "selesai_tanggal": self._format_snapshot_date(self.tanggal_selesai),
                "total_hari": self.total_hari,
                "berkas_pendukung": getattr(self.berkas_pendukung, "name", "") or "",
            },
            "pengukuran": self.get_pengukuran_data(),
            "items": {
                "lab": lab_items,
                "penunjang": penunjang_items,
                "peralatan_lab": peralatan_lab_items,
                "bahan": bahan_items,
            },
        }

    def ensure_report_snapshot(self, save=True):
        snapshot = self.build_report_snapshot()
        self.report_snapshot = snapshot
        if save and self.pk:
            self.save(update_fields=["report_snapshot", "updated_at"])
        return snapshot

    def get_pimpinan_signer(self):
        return self.ketua_tim_user

    def get_return_pimpinan_signer(self):
        target_team = (
            TimKegiatan.objects.filter(nama_tim__iexact=RETURN_PIMPINAN_TEAM_NAME)
            .select_related("ketua_tim")
            .order_by("id")
            .first()
        )
        if target_team and target_team.ketua_tim_id:
            return target_team.ketua_tim

        fallback_team = (
            TimKegiatan.objects.filter(
                nama_tim__icontains="Layanan Teknis"
            )
            .select_related("ketua_tim")
            .order_by("id")
            .first()
        )
        if fallback_team and fallback_team.ketua_tim_id:
            return fallback_team.ketua_tim

        user_model = self.peminjam.__class__
        contains = (
            user_model.objects.filter(
                profile__role__nama="Pimpinan",
                profile__jabatan__icontains="Layanan Teknis",
            )
            .select_related("profile")
            .order_by("id")
            .first()
        )
        if contains:
            return contains
        return self.get_pimpinan_signer()

    def get_return_current_step_label(self):
        if self.return_current_step == ReturnStepChoices.NONE:
            return "Belum Diproses"
        if self.return_current_step in {
            ReturnStepChoices.PIMPINAN_BA,
            ReturnStepChoices.PIMPINAN_TRANSFER,
        }:
            return f"Verifikasi Pengembalian - {RETURN_PIMPINAN_LABEL}"
        return self.get_return_current_step_display()

    def get_pengembalian_status_tags(self):
        tags = []

        has_dikembalikan = self.pengembalian_lab_items.filter(status=ReturnItemStatusChoices.DIKEMBALIKAN).exists()
        has_transfer = self.pengembalian_lab_items.filter(status=ReturnItemStatusChoices.TRANSFER).exists()
        has_hilang = self.pengembalian_lab_items.filter(status=ReturnItemStatusChoices.HILANG).exists()
        has_rusak = self.pengembalian_lab_items.filter(status=ReturnItemStatusChoices.RUSAK).exists()

        for item in self.pengembalian_penunjang_items.all():
            if item.qty_dikembalikan > 0:
                has_dikembalikan = True
            if item.qty_transfer > 0:
                has_transfer = True
            if item.qty_hilang > 0:
                has_hilang = True
            if item.qty_rusak > 0:
                has_rusak = True

        for item in self.pengembalian_peralatan_laboratorium_items.all():
            if item.qty_dikembalikan > 0:
                has_dikembalikan = True
            if item.qty_transfer > 0:
                has_transfer = True
            if item.qty_hilang > 0:
                has_hilang = True
            if item.qty_rusak > 0:
                has_rusak = True

        for item in self.pengembalian_bahan_items.all():
            if item.qty_sisa > 0:
                has_dikembalikan = True
            if item.qty_transfer > 0:
                has_transfer = True

        if has_dikembalikan:
            tags.append("Dikembalikan")
        if has_transfer:
            tags.append("Transfer")
        if has_hilang:
            tags.append("Hilang")
        if has_rusak:
            tags.append("Rusak")
        return tags

    @property
    def pengembalian_status_tags(self):
        return self.get_pengembalian_status_tags()

    @property
    def pengembalian_status_text(self):
        tags = self.get_pengembalian_status_tags()
        return ", ".join(tags) if tags else "Belum ada data pengembalian"

    def pengembalian_has_issue(self):
        return (
            self.pengembalian_lab_items.filter(
                status__in=[ReturnItemStatusChoices.HILANG, ReturnItemStatusChoices.RUSAK]
            ).exists()
            or any(
                item.qty_hilang > 0 or item.qty_rusak > 0
                for item in self.pengembalian_penunjang_items.all()
            )
            or any(
                item.qty_hilang > 0 or item.qty_rusak > 0
                for item in self.pengembalian_peralatan_laboratorium_items.all()
            )
        )

    def pengembalian_has_transfer(self):
        return (
            self.pengembalian_lab_items.filter(status=ReturnItemStatusChoices.TRANSFER).exists()
            or any(item.qty_transfer > 0 for item in self.pengembalian_penunjang_items.all())
            or any(item.qty_transfer > 0 for item in self.pengembalian_peralatan_laboratorium_items.all())
            or any(item.qty_transfer > 0 for item in self.pengembalian_bahan_items.all())
        )

    def requires_extended_pengembalian_verification(self):
        return self.pengembalian_has_issue() or self.pengembalian_has_transfer()

    def get_next_pengembalian_step_after_teknisi_verification(self):
        if self.requires_extended_pengembalian_verification():
            return ReturnStepChoices.KEPALA_BA
        return ReturnStepChoices.COMPLETED

    def get_next_pengembalian_step_after_user_verification(self):
        if self.requires_extended_pengembalian_verification():
            return ReturnStepChoices.KEPALA_BA
        return ReturnStepChoices.COMPLETED

    @transaction.atomic
    def apply_inventory_allocation(self):
        """Booking stok sejak pengajuan dibuat agar tidak bisa dipilih pengajuan lain."""
        if self.aset_sudah_dialokasikan:
            return

        lab_items = list(self.barang_laboratorium_items.select_related("barang"))
        penunjang_items = list(self.barang_penunjang_items.select_related("barang"))
        peralatan_lab_items = list(self.peralatan_laboratorium_items.select_related("barang"))
        bahan_items = list(self.bahan_operasional_items.select_related("bahan"))

        locked_lab = {
            item.id: item
            for item in BarangLaboratorium.objects.select_for_update().filter(
                id__in=[item.barang_id for item in lab_items if item.barang_id]
            )
        }
        locked_penunjang = {
            item.id: item
            for item in BarangPenunjangOperasional.objects.select_for_update().filter(
                id__in=[item.barang_id for item in penunjang_items if item.barang_id]
            )
        }
        locked_peralatan_lab = {
            item.id: item
            for item in PeralatanLaboratorium.objects.select_for_update().filter(
                id__in=[item.barang_id for item in peralatan_lab_items if item.barang_id]
            )
        }
        locked_bahan = {
            item.id: item
            for item in BahanOperasional.objects.select_for_update().filter(
                id__in=[item.bahan_id for item in bahan_items if item.bahan_id]
            )
        }

        for item in lab_items:
            barang = locked_lab.get(item.barang_id)
            if barang is None:
                continue
            if barang.kondisi_barang != KondisiBarangChoices.BAIK or barang.sedang_dipinjam:
                raise ValidationError(
                    f'Barang laboratorium "{barang.nama_barang}" sudah tidak tersedia untuk dibooking.'
                )
            barang.sedang_dipinjam = True
            barang.save(update_fields=["sedang_dipinjam", "ketersediaan", "updated_at"])

        for item in penunjang_items:
            barang = locked_penunjang.get(item.barang_id)
            if barang is None:
                continue
            if item.volume > barang.sisa_volume:
                raise ValidationError(
                    f'Volume barang penunjang "{barang.nama_barang}" melebihi stok tersedia ({barang.sisa_volume}).'
                )
            barang.volume_dipinjam = (barang.volume_dipinjam or 0) + item.volume
            barang.save()

        for item in peralatan_lab_items:
            barang = locked_peralatan_lab.get(item.barang_id)
            if barang is None:
                continue
            if item.volume > barang.sisa_volume:
                raise ValidationError(
                    f'Volume peralatan laboratorium "{barang.nama_barang}" melebihi stok tersedia ({barang.sisa_volume}).'
                )
            barang.volume_dipinjam = (barang.volume_dipinjam or 0) + item.volume
            barang.save()

        for item in bahan_items:
            bahan = locked_bahan.get(item.bahan_id)
            if bahan is None:
                continue
            if item.volume > (bahan.volume or 0):
                raise ValidationError(
                    f'Volume bahan operasional "{bahan.nama_barang}" melebihi stok tersedia ({bahan.volume or 0}).'
                )
            bahan.volume = max((bahan.volume or 0) - item.volume, 0)
            bahan.save()

        self.aset_sudah_dialokasikan = True
        self.save(update_fields=["aset_sudah_dialokasikan", "updated_at"])

    @transaction.atomic
    def release_inventory_allocation(self):
        if not self.aset_sudah_dialokasikan:
            return

        lab_items = list(self.barang_laboratorium_items.select_related("barang"))
        penunjang_items = list(self.barang_penunjang_items.select_related("barang"))
        peralatan_lab_items = list(self.peralatan_laboratorium_items.select_related("barang"))
        bahan_items = list(self.bahan_operasional_items.select_related("bahan"))

        locked_lab = {
            item.id: item
            for item in BarangLaboratorium.objects.select_for_update().filter(
                id__in=[item.barang_id for item in lab_items if item.barang_id]
            )
        }
        locked_penunjang = {
            item.id: item
            for item in BarangPenunjangOperasional.objects.select_for_update().filter(
                id__in=[item.barang_id for item in penunjang_items if item.barang_id]
            )
        }
        locked_peralatan_lab = {
            item.id: item
            for item in PeralatanLaboratorium.objects.select_for_update().filter(
                id__in=[item.barang_id for item in peralatan_lab_items if item.barang_id]
            )
        }
        locked_bahan = {
            item.id: item
            for item in BahanOperasional.objects.select_for_update().filter(
                id__in=[item.bahan_id for item in bahan_items if item.bahan_id]
            )
        }

        for item in lab_items:
            barang = locked_lab.get(item.barang_id)
            if barang is None:
                continue
            still_booked_elsewhere = PeminjamanBarangLaboratorium.objects.filter(
                barang_id=barang.id,
                pengajuan__aset_sudah_dialokasikan=True,
            ).exclude(pengajuan_id=self.pk).exists()
            barang.sedang_dipinjam = still_booked_elsewhere
            barang.save(update_fields=["sedang_dipinjam", "ketersediaan", "updated_at"])

        for item in penunjang_items:
            barang = locked_penunjang.get(item.barang_id)
            if barang is None:
                continue
            barang.volume_dipinjam = max((barang.volume_dipinjam or 0) - item.volume, 0)
            barang.save()

        for item in peralatan_lab_items:
            barang = locked_peralatan_lab.get(item.barang_id)
            if barang is None:
                continue
            barang.volume_dipinjam = max((barang.volume_dipinjam or 0) - item.volume, 0)
            barang.save()

        for item in bahan_items:
            bahan = locked_bahan.get(item.bahan_id)
            if bahan is None:
                continue
            bahan.volume = (bahan.volume or 0) + item.volume
            bahan.save()

        self.aset_sudah_dialokasikan = False
        self.save(update_fields=["aset_sudah_dialokasikan", "updated_at"])

    def _append_barang_catatan(self, barang, tambahan):
        existing = (barang.catatan or "").strip()
        if tambahan and tambahan not in existing:
            barang.catatan = f"{existing}\n{tambahan}".strip() if existing else tambahan

    @transaction.atomic
    def apply_pengembalian_inventory(self):
        if self.return_inventory_applied:
            return

        for item in self.pengembalian_lab_items.select_related("barang", "transfer_target"):
            barang = item.barang
            if barang is None:
                continue
            if item.status == ReturnItemStatusChoices.DIKEMBALIKAN:
                barang.sedang_dipinjam = False
                barang.kondisi_barang = KondisiBarangChoices.BAIK
                barang.volume = 1
                barang.save(update_fields=["sedang_dipinjam", "kondisi_barang", "volume", "ketersediaan", "updated_at"])
            elif item.status == ReturnItemStatusChoices.RUSAK:
                barang.sedang_dipinjam = False
                barang.kondisi_barang = KondisiBarangChoices.RUSAK
                barang.volume = 1
                self._append_barang_catatan(barang, f"Rusak saat pengembalian pada {self.nomor_pengajuan}.")
                barang.save(update_fields=["sedang_dipinjam", "kondisi_barang", "volume", "ketersediaan", "catatan", "updated_at"])
            elif item.status == ReturnItemStatusChoices.HILANG:
                barang.sedang_dipinjam = False
                barang.kondisi_barang = KondisiBarangChoices.HILANG
                barang.volume = 0
                self._append_barang_catatan(barang, f"Hilang saat pengembalian pada {self.nomor_pengajuan}.")
                barang.save(update_fields=["sedang_dipinjam", "kondisi_barang", "volume", "ketersediaan", "catatan", "updated_at"])
            elif item.status == ReturnItemStatusChoices.TRANSFER and item.transfer_target_id:
                PeminjamanBarangLaboratorium.objects.get_or_create(
                    pengajuan=item.transfer_target,
                    barang=barang,
                )

        for item in self.pengembalian_penunjang_items.select_related("barang", "transfer_target"):
            barang = item.barang
            if barang is None:
                continue
            qty_release = item.qty_dikembalikan + item.qty_rusak + item.qty_hilang
            if qty_release > 0:
                barang.volume_dipinjam = max((barang.volume_dipinjam or 0) - qty_release, 0)
            if item.qty_hilang > 0:
                barang.volume = max((barang.volume or 0) - item.qty_hilang, 0)
            if item.qty_rusak > 0:
                barang.volume = max((barang.volume or 0) - item.qty_rusak, 0)
                barang.volume_rusak = (barang.volume_rusak or 0) + item.qty_rusak
            barang.save()

            if item.qty_transfer > 0 and item.transfer_target_id:
                target_item, created = PeminjamanBarangPenunjang.objects.get_or_create(
                    pengajuan=item.transfer_target,
                    barang=barang,
                    defaults={"volume": item.qty_transfer},
                )
                if not created:
                    target_item.volume = (target_item.volume or 0) + item.qty_transfer
                    target_item.save(update_fields=["volume"])

        for item in self.pengembalian_peralatan_laboratorium_items.select_related("barang", "transfer_target"):
            barang = item.barang
            if barang is None:
                continue
            qty_release = item.qty_dikembalikan + item.qty_rusak + item.qty_hilang
            if qty_release > 0:
                barang.volume_dipinjam = max((barang.volume_dipinjam or 0) - qty_release, 0)
            if item.qty_hilang > 0:
                barang.volume = max((barang.volume or 0) - item.qty_hilang, 0)
                if barang.status_barang == StatusBarangChoices.BMN:
                    barang.kondisi_barang = KondisiBarangChoices.HILANG
                self._append_barang_catatan(barang, f"Hilang saat pengembalian pada {self.nomor_pengajuan}.")
            if item.qty_rusak > 0:
                barang.volume = max((barang.volume or 0) - item.qty_rusak, 0)
                barang.volume_rusak = (barang.volume_rusak or 0) + item.qty_rusak
                if barang.status_barang == StatusBarangChoices.BMN:
                    barang.kondisi_barang = KondisiBarangChoices.RUSAK
                self._append_barang_catatan(barang, f"Rusak saat pengembalian pada {self.nomor_pengajuan}.")
            if item.qty_dikembalikan > 0 and item.qty_rusak == 0 and item.qty_hilang == 0 and barang.status_barang == StatusBarangChoices.BMN:
                barang.kondisi_barang = KondisiBarangChoices.BAIK
            barang.save()

            if item.qty_transfer > 0 and item.transfer_target_id:
                target_item, created = PeminjamanPeralatanLaboratorium.objects.get_or_create(
                    pengajuan=item.transfer_target,
                    barang=barang,
                    defaults={"volume": item.qty_transfer},
                )
                if not created:
                    target_item.volume = (target_item.volume or 0) + item.qty_transfer
                    target_item.save(update_fields=["volume"])

        for item in self.pengembalian_bahan_items.select_related("bahan", "transfer_target"):
            bahan = item.bahan
            if bahan is None:
                continue
            if item.qty_sisa > 0:
                bahan.volume = (bahan.volume or 0) + item.qty_sisa
                bahan.save()

            if item.qty_transfer > 0 and item.transfer_target_id:
                target_item, created = PeminjamanBahanOperasional.objects.get_or_create(
                    pengajuan=item.transfer_target,
                    bahan=bahan,
                    defaults={"volume": item.qty_transfer},
                )
                if not created:
                    target_item.volume = (target_item.volume or 0) + item.qty_transfer
                    target_item.save(update_fields=["volume"])

        self.return_inventory_applied = True
        self.return_completed_at = timezone.now()
        self.report_snapshot = self.build_report_snapshot()
        self.save(update_fields=["return_inventory_applied", "return_completed_at", "report_snapshot", "updated_at"])

    def add_timeline(self, stage, action, actor=None, note=""):
        return PeminjamanTimeline.objects.create(
            pengajuan=self,
            stage=stage,
            action=action,
            actor=actor,
            note=note or "",
        )



class PeminjamanBarangLaboratorium(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="barang_laboratorium_items",
    )
    barang = models.ForeignKey(
        BarangLaboratorium,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_tipe_merek_barang = models.CharField(max_length=200, blank=True)
    snapshot_jenis_barang = models.CharField(max_length=150, blank=True)
    snapshot_status_barang = models.CharField(max_length=20, blank=True)
    snapshot_kode_aset_bmn = models.CharField(max_length=100, blank=True)
    snapshot_kode_laboratorium = models.CharField(max_length=100, blank=True)
    snapshot_volume = models.PositiveIntegerField(null=True, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)
    snapshot_kondisi_barang = models.CharField(max_length=30, blank=True)
    snapshot_tahun_perolehan = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("pengajuan", "barang")
        ordering = ["barang__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Item Peralatan Survei Lapangan"
        verbose_name_plural = "Item Peralatan Survei Lapangan"

    def sync_snapshot_from_master(self):
        barang = self.barang
        self.snapshot_nama_barang = _snapshot_text(barang, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_tipe_merek_barang = _snapshot_text(barang, "tipe_merek_barang", self.snapshot_tipe_merek_barang)
        self.snapshot_jenis_barang = _snapshot_text(barang, "jenis_barang", self.snapshot_jenis_barang)
        self.snapshot_status_barang = _snapshot_text(barang, "status_barang", self.snapshot_status_barang)
        self.snapshot_kode_aset_bmn = _snapshot_text(barang, "kode_aset_bmn", self.snapshot_kode_aset_bmn)
        self.snapshot_kode_laboratorium = _snapshot_text(barang, "kode_laboratorium", self.snapshot_kode_laboratorium)
        self.snapshot_volume = _snapshot_int(barang, "volume", self.snapshot_volume)
        self.snapshot_satuan = _snapshot_text(barang, "satuan", self.snapshot_satuan)
        self.snapshot_kondisi_barang = _snapshot_text(barang, "kondisi_barang", self.snapshot_kondisi_barang)
        self.snapshot_tahun_perolehan = _snapshot_int(barang, "tahun_perolehan", self.snapshot_tahun_perolehan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.barang or '-'}"


class PeminjamanBarangPenunjang(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="barang_penunjang_items",
    )
    barang = models.ForeignKey(
        BarangPenunjangOperasional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    volume = models.PositiveIntegerField(default=1)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_tipe_merek_barang = models.CharField(max_length=200, blank=True)
    snapshot_kategori_barang = models.CharField(max_length=60, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("pengajuan", "barang")
        ordering = ["barang__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Item Barang Penunjang Lapangan"
        verbose_name_plural = "Item Barang Penunjang Lapangan"

    def sync_snapshot_from_master(self):
        barang = self.barang
        self.snapshot_nama_barang = _snapshot_text(barang, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_tipe_merek_barang = _snapshot_text(barang, "tipe_merek_barang", self.snapshot_tipe_merek_barang)
        self.snapshot_kategori_barang = _snapshot_text(barang, "kategori_barang", self.snapshot_kategori_barang)
        self.snapshot_satuan = _snapshot_text(barang, "satuan", self.snapshot_satuan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.barang or '-'} ({self.volume})"



class PeminjamanPeralatanLaboratorium(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="peralatan_laboratorium_items",
    )
    barang = models.ForeignKey(
        PeralatanLaboratorium,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    volume = models.PositiveIntegerField(default=1)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_tipe_merek_barang = models.CharField(max_length=200, blank=True)
    snapshot_jenis_barang = models.CharField(max_length=150, blank=True)
    snapshot_status_barang = models.CharField(max_length=20, blank=True)
    snapshot_kode_aset_bmn = models.CharField(max_length=100, blank=True)
    snapshot_kode_laboratorium = models.CharField(max_length=100, blank=True)
    snapshot_volume = models.PositiveIntegerField(null=True, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)
    snapshot_kondisi_barang = models.CharField(max_length=30, blank=True)
    snapshot_tahun_perolehan = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("pengajuan", "barang")
        ordering = ["barang__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Item Peralatan Laboratorium"
        verbose_name_plural = "Item Peralatan Laboratorium"

    def sync_snapshot_from_master(self):
        barang = self.barang
        self.snapshot_nama_barang = _snapshot_text(barang, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_tipe_merek_barang = _snapshot_text(barang, "tipe_merek_barang", self.snapshot_tipe_merek_barang)
        self.snapshot_jenis_barang = _snapshot_text(barang, "jenis_barang", self.snapshot_jenis_barang)
        self.snapshot_status_barang = _snapshot_text(barang, "status_barang", self.snapshot_status_barang)
        self.snapshot_kode_aset_bmn = _snapshot_text(barang, "kode_aset_bmn", self.snapshot_kode_aset_bmn)
        self.snapshot_kode_laboratorium = _snapshot_text(barang, "kode_laboratorium", self.snapshot_kode_laboratorium)
        self.snapshot_volume = _snapshot_int(barang, "volume", self.snapshot_volume)
        self.snapshot_satuan = _snapshot_text(barang, "satuan", self.snapshot_satuan)
        self.snapshot_kondisi_barang = _snapshot_text(barang, "kondisi_barang", self.snapshot_kondisi_barang)
        self.snapshot_tahun_perolehan = _snapshot_int(barang, "tahun_perolehan", self.snapshot_tahun_perolehan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.barang or '-'} ({self.volume})"


class PeminjamanBahanOperasional(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="bahan_operasional_items",
    )
    bahan = models.ForeignKey(
        BahanOperasional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    volume = models.PositiveIntegerField(default=1)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_kategori_barang = models.CharField(max_length=30, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("pengajuan", "bahan")
        ordering = ["bahan__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Item Bahan Operasional"
        verbose_name_plural = "Item Bahan Operasional"

    def sync_snapshot_from_master(self):
        bahan = self.bahan
        self.snapshot_nama_barang = _snapshot_text(bahan, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_kategori_barang = _snapshot_text(bahan, "kategori_barang", self.snapshot_kategori_barang)
        self.snapshot_satuan = _snapshot_text(bahan, "satuan", self.snapshot_satuan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.bahan or '-'} ({self.volume})"


class PengembalianBarangLaboratorium(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="pengembalian_lab_items",
    )
    barang = models.ForeignKey(
        BarangLaboratorium,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ReturnItemStatusChoices.choices,
        default=ReturnItemStatusChoices.DIKEMBALIKAN,
    )
    transfer_target = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_tipe_merek_barang = models.CharField(max_length=200, blank=True)
    snapshot_jenis_barang = models.CharField(max_length=150, blank=True)
    snapshot_status_barang = models.CharField(max_length=20, blank=True)
    snapshot_kode_aset_bmn = models.CharField(max_length=100, blank=True)
    snapshot_kode_laboratorium = models.CharField(max_length=100, blank=True)
    snapshot_volume = models.PositiveIntegerField(null=True, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)
    snapshot_kondisi_barang = models.CharField(max_length=30, blank=True)
    snapshot_tahun_perolehan = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("pengajuan", "barang")
        ordering = ["barang__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Pengembalian Peralatan Survei Lapangan"
        verbose_name_plural = "Pengembalian Peralatan Survei Lapangan"

    def sync_snapshot_from_master(self):
        barang = self.barang
        self.snapshot_nama_barang = _snapshot_text(barang, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_tipe_merek_barang = _snapshot_text(barang, "tipe_merek_barang", self.snapshot_tipe_merek_barang)
        self.snapshot_jenis_barang = _snapshot_text(barang, "jenis_barang", self.snapshot_jenis_barang)
        self.snapshot_status_barang = _snapshot_text(barang, "status_barang", self.snapshot_status_barang)
        self.snapshot_kode_aset_bmn = _snapshot_text(barang, "kode_aset_bmn", self.snapshot_kode_aset_bmn)
        self.snapshot_kode_laboratorium = _snapshot_text(barang, "kode_laboratorium", self.snapshot_kode_laboratorium)
        self.snapshot_volume = _snapshot_int(barang, "volume", self.snapshot_volume)
        self.snapshot_satuan = _snapshot_text(barang, "satuan", self.snapshot_satuan)
        self.snapshot_kondisi_barang = _snapshot_text(barang, "kondisi_barang", self.snapshot_kondisi_barang)
        self.snapshot_tahun_perolehan = _snapshot_int(barang, "tahun_perolehan", self.snapshot_tahun_perolehan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.barang or '-'} ({self.get_status_display()})"


class PengembalianBarangPenunjang(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="pengembalian_penunjang_items",
    )
    barang = models.ForeignKey(
        BarangPenunjangOperasional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    qty_dikembalikan = models.PositiveIntegerField(default=0)
    qty_rusak = models.PositiveIntegerField(default=0)
    qty_hilang = models.PositiveIntegerField(default=0)
    qty_transfer = models.PositiveIntegerField(default=0)
    transfer_target = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_tipe_merek_barang = models.CharField(max_length=200, blank=True)
    snapshot_kategori_barang = models.CharField(max_length=60, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("pengajuan", "barang")
        ordering = ["barang__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Pengembalian Barang Penunjang Lapangan"
        verbose_name_plural = "Pengembalian Barang Penunjang Lapangan"

    @property
    def total_processed(self):
        return self.qty_dikembalikan + self.qty_rusak + self.qty_hilang + self.qty_transfer

    def sync_snapshot_from_master(self):
        barang = self.barang
        self.snapshot_nama_barang = _snapshot_text(barang, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_tipe_merek_barang = _snapshot_text(barang, "tipe_merek_barang", self.snapshot_tipe_merek_barang)
        self.snapshot_kategori_barang = _snapshot_text(barang, "kategori_barang", self.snapshot_kategori_barang)
        self.snapshot_satuan = _snapshot_text(barang, "satuan", self.snapshot_satuan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.barang or '-'}"



class PengembalianPeralatanLaboratorium(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="pengembalian_peralatan_laboratorium_items",
    )
    barang = models.ForeignKey(
        PeralatanLaboratorium,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    qty_dikembalikan = models.PositiveIntegerField(default=0)
    qty_rusak = models.PositiveIntegerField(default=0)
    qty_hilang = models.PositiveIntegerField(default=0)
    qty_transfer = models.PositiveIntegerField(default=0)
    transfer_target = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_tipe_merek_barang = models.CharField(max_length=200, blank=True)
    snapshot_jenis_barang = models.CharField(max_length=150, blank=True)
    snapshot_status_barang = models.CharField(max_length=20, blank=True)
    snapshot_kode_aset_bmn = models.CharField(max_length=100, blank=True)
    snapshot_kode_laboratorium = models.CharField(max_length=100, blank=True)
    snapshot_volume = models.PositiveIntegerField(null=True, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)
    snapshot_kondisi_barang = models.CharField(max_length=30, blank=True)
    snapshot_tahun_perolehan = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("pengajuan", "barang")
        ordering = ["barang__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Pengembalian Peralatan Laboratorium"
        verbose_name_plural = "Pengembalian Peralatan Laboratorium"

    @property
    def total_processed(self):
        return self.qty_dikembalikan + self.qty_rusak + self.qty_hilang + self.qty_transfer

    def sync_snapshot_from_master(self):
        barang = self.barang
        self.snapshot_nama_barang = _snapshot_text(barang, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_tipe_merek_barang = _snapshot_text(barang, "tipe_merek_barang", self.snapshot_tipe_merek_barang)
        self.snapshot_jenis_barang = _snapshot_text(barang, "jenis_barang", self.snapshot_jenis_barang)
        self.snapshot_status_barang = _snapshot_text(barang, "status_barang", self.snapshot_status_barang)
        self.snapshot_kode_aset_bmn = _snapshot_text(barang, "kode_aset_bmn", self.snapshot_kode_aset_bmn)
        self.snapshot_kode_laboratorium = _snapshot_text(barang, "kode_laboratorium", self.snapshot_kode_laboratorium)
        self.snapshot_volume = _snapshot_int(barang, "volume", self.snapshot_volume)
        self.snapshot_satuan = _snapshot_text(barang, "satuan", self.snapshot_satuan)
        self.snapshot_kondisi_barang = _snapshot_text(barang, "kondisi_barang", self.snapshot_kondisi_barang)
        self.snapshot_tahun_perolehan = _snapshot_int(barang, "tahun_perolehan", self.snapshot_tahun_perolehan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.barang or '-'} ({self.total_processed})"


class PengembalianBahanOperasional(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="pengembalian_bahan_items",
    )
    bahan = models.ForeignKey(
        BahanOperasional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    qty_sisa = models.PositiveIntegerField(default=0)
    qty_transfer = models.PositiveIntegerField(default=0)
    transfer_target = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_kategori_barang = models.CharField(max_length=30, blank=True)
    snapshot_satuan = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("pengajuan", "bahan")
        ordering = ["bahan__nama_barang", "snapshot_nama_barang"]
        verbose_name = "Pengembalian Bahan Operasional"
        verbose_name_plural = "Pengembalian Bahan Operasional"

    @property
    def total_processed(self):
        return self.qty_sisa + self.qty_transfer

    def sync_snapshot_from_master(self):
        bahan = self.bahan
        self.snapshot_nama_barang = _snapshot_text(bahan, "nama_barang", self.snapshot_nama_barang)
        self.snapshot_kategori_barang = _snapshot_text(bahan, "kategori_barang", self.snapshot_kategori_barang)
        self.snapshot_satuan = _snapshot_text(bahan, "satuan", self.snapshot_satuan)

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pengajuan} - {self.snapshot_nama_barang or self.bahan or '-'} ({self.total_processed})"



class PeminjamanTimeline(models.Model):
    pengajuan = models.ForeignKey(
        PeminjamanRequest,
        on_delete=models.CASCADE,
        related_name="timeline_entries",
    )
    stage = models.CharField(max_length=50)
    action = models.CharField(max_length=100)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_peminjaman_actions",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "Riwayat Verifikasi Peminjaman"
        verbose_name_plural = "Riwayat Verifikasi Peminjaman"

    def __str__(self):
        return f"{self.pengajuan} - {self.action}"


def build_asal_peminjaman_maps(pengajuan):
    pengajuan_id = getattr(pengajuan, "pk", pengajuan)
    empty_maps = {"lab": {}, "penunjang": {}, "peralatan_lab": {}, "bahan": {}}
    if not pengajuan_id:
        return empty_maps

    lab_map = {}
    for item in (
        PengembalianBarangLaboratorium.objects.filter(
            transfer_target_id=pengajuan_id,
            status=ReturnItemStatusChoices.TRANSFER,
        )
        .select_related("pengajuan")
        .order_by("-updated_at", "-id")
    ):
        nomor = getattr(item.pengajuan, "nomor_pengajuan", "") or "-"
        lab_map[item.barang_id] = f"Transfer {nomor}"

    penunjang_map = {}
    for item in (
        PengembalianBarangPenunjang.objects.filter(
            transfer_target_id=pengajuan_id,
            qty_transfer__gt=0,
        )
        .select_related("pengajuan")
        .order_by("-updated_at", "-id")
    ):
        nomor = getattr(item.pengajuan, "nomor_pengajuan", "") or "-"
        source_map = penunjang_map.setdefault(item.barang_id, {})
        source_map[nomor] = source_map.get(nomor, 0) + (item.qty_transfer or 0)

    peralatan_lab_map = {}
    for item in (
        PengembalianPeralatanLaboratorium.objects.filter(
            transfer_target_id=pengajuan_id,
            qty_transfer__gt=0,
        )
        .select_related("pengajuan")
        .order_by("-updated_at", "-id")
    ):
        nomor = getattr(item.pengajuan, "nomor_pengajuan", "") or "-"
        source_map = peralatan_lab_map.setdefault(item.barang_id, {})
        source_map[nomor] = source_map.get(nomor, 0) + (item.qty_transfer or 0)

    bahan_map = {}
    for item in (
        PengembalianBahanOperasional.objects.filter(
            transfer_target_id=pengajuan_id,
            qty_transfer__gt=0,
        )
        .select_related("pengajuan")
        .order_by("-updated_at", "-id")
    ):
        nomor = getattr(item.pengajuan, "nomor_pengajuan", "") or "-"
        source_map = bahan_map.setdefault(item.bahan_id, {})
        source_map[nomor] = source_map.get(nomor, 0) + (item.qty_transfer or 0)

    return {"lab": lab_map, "penunjang": penunjang_map, "peralatan_lab": peralatan_lab_map, "bahan": bahan_map}


def resolve_asal_peminjaman_label(asal_maps, section, item_id, total_volume=None):
    section_map = (asal_maps or {}).get(section, {})
    source_data = section_map.get(item_id)
    if section == "lab":
        return source_data or "Laboratorium"

    if not source_data:
        return "Laboratorium"

    if isinstance(source_data, str):
        return source_data or "Laboratorium"

    transfer_entries = [
        (f"Transfer {nomor}", qty)
        for nomor, qty in sorted(source_data.items(), key=lambda entry: entry[0])
        if qty and qty > 0
    ]
    transfer_total = sum(qty for _, qty in transfer_entries)
    lab_qty = max((total_volume or 0) - transfer_total, 0)

    sources = []
    if lab_qty > 0:
        sources.append(("Laboratorium", lab_qty))
    sources.extend(transfer_entries)

    if not sources:
        return "Laboratorium"
    if len(sources) == 1:
        return sources[0][0]
    return ", ".join(f"{label} ({qty})" for label, qty in sources)
