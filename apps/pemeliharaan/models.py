from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.master_data.models import BarangLaboratorium, KondisiBarangChoices


MAX_PEMELIHARAAN_PHOTOS = 3


class KondisiPemeliharaanChoices(models.TextChoices):
    BAIK = "Baik", "Baik"
    PERLU_PERBAIKAN = "Perlu Perbaikan", "Perlu Perbaikan"


class TindakanPerbaikanChoices(models.TextChoices):
    MANDIRI = "Perbaikan Mandiri", "Perbaikan Mandiri"
    EKSTERNAL = "Perbaikan Eksternal", "Perbaikan Eksternal"


class StepPemeliharaanChoices(models.TextChoices):
    DRAFT = "draft", "Draft"
    KEPALA_LAB = "kepala_lab", "Verifikasi Pemeliharaan - Kepala Lab"
    PIMPINAN = "pimpinan", "Verifikasi Pemeliharaan - Pimpinan"
    SELESAI = "selesai", "Selesai"
    DIKEMBALIKAN = "dikembalikan", "Dikembalikan ke Pemohon"


ACTIVE_PEMELIHARAAN_STEPS = (
    StepPemeliharaanChoices.DRAFT,
    StepPemeliharaanChoices.KEPALA_LAB,
    StepPemeliharaanChoices.PIMPINAN,
    StepPemeliharaanChoices.DIKEMBALIKAN,
)


class KeputusanPemeliharaanChoices(models.TextChoices):
    PENDING = "pending", "Menunggu"
    APPROVED = "approved", "Disetujui"
    REVISION = "revision", "Dikembalikan"


class JenisFotoPemeliharaanChoices(models.TextChoices):
    PEMERIKSAAN = "pemeriksaan", "Dokumentasi Pemeriksaan"
    PERBAIKAN = "perbaikan", "Dokumentasi Perbaikan"
    KERUSAKAN = "kerusakan", "Dokumentasi Kerusakan"


def make_nomor_pemeliharaan(tanggal, pk):
    return f"PMH-{tanggal.strftime('%y%m%d')}-{pk:03d}"


class PemeliharaanPengajuan(models.Model):
    nomor_pengajuan = models.CharField(max_length=30, unique=True, blank=True)
    pemohon = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pengajuan_pemeliharaan",
    )
    alat = models.ForeignKey(
        BarangLaboratorium,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengajuan_pemeliharaan",
    )
    tanggal_pemeriksaan = models.DateTimeField(default=timezone.now)
    snapshot_nama_barang = models.CharField(max_length=200, blank=True)
    snapshot_kode_laboratorium = models.CharField(max_length=100, blank=True)
    snapshot_tipe_merek_barang = models.CharField(max_length=200, blank=True)
    kondisi_barang_sebelum = models.CharField(max_length=30, blank=True)
    current_step = models.CharField(
        max_length=30,
        choices=StepPemeliharaanChoices.choices,
        default=StepPemeliharaanChoices.DRAFT,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    kepala_lab_status = models.CharField(
        max_length=20,
        choices=KeputusanPemeliharaanChoices.choices,
        default=KeputusanPemeliharaanChoices.PENDING,
    )
    kepala_lab_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kepala_lab_pemeliharaan_processed",
    )
    kepala_lab_at = models.DateTimeField(null=True, blank=True)
    kepala_lab_note = models.TextField(blank=True)
    pimpinan_status = models.CharField(
        max_length=20,
        choices=KeputusanPemeliharaanChoices.choices,
        default=KeputusanPemeliharaanChoices.PENDING,
    )
    pimpinan_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pimpinan_pemeliharaan_processed",
    )
    pimpinan_at = models.DateTimeField(null=True, blank=True)
    pimpinan_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-tanggal_pemeriksaan", "-id"]
        verbose_name = "Pengajuan Pemeliharaan"
        verbose_name_plural = "Pengajuan Pemeliharaan"
        constraints = [
            models.UniqueConstraint(
                fields=["alat"],
                condition=models.Q(
                    alat__isnull=False,
                    current_step__in=ACTIVE_PEMELIHARAAN_STEPS,
                ),
                name="uq_pemeliharaan_alat_aktif",
            ),
        ]

    def __str__(self):
        return self.nomor_pengajuan or f"Pemeliharaan #{self.pk}"

    @property
    def alat_label(self):
        nama = self.snapshot_nama_barang or getattr(self.alat, "nama_barang", "") or "-"
        kode = self.snapshot_kode_laboratorium or getattr(self.alat, "kode_laboratorium", "") or "-"
        tipe = self.snapshot_tipe_merek_barang or getattr(self.alat, "tipe_merek_barang", "") or "-"
        return f"{nama} ({kode}) - {tipe}"

    @property
    def verifikasi_kind(self):
        return "pemeliharaan"

    @property
    def nama_pemohon(self):
        nama_lengkap = getattr(self.pemohon, "nama_lengkap", "") or ""
        if not nama_lengkap and hasattr(self.pemohon, "get_full_name"):
            nama_lengkap = self.pemohon.get_full_name()
        return nama_lengkap or self.pemohon.username

    @property
    def jenis_pengajuan_label(self):
        return "Pemeliharaan"

    @property
    def status_label(self):
        return self.get_current_step_display()

    @property
    def status_badge_class(self):
        return {
            StepPemeliharaanChoices.DRAFT: "badge-secondary",
            StepPemeliharaanChoices.KEPALA_LAB: "badge-warning",
            StepPemeliharaanChoices.PIMPINAN: "badge-warning",
            StepPemeliharaanChoices.SELESAI: "badge-success",
            StepPemeliharaanChoices.DIKEMBALIKAN: "badge-danger",
        }.get(self.current_step, "badge-secondary")

    @property
    def active_verification_label(self):
        return self.status_label

    @property
    def active_verification_badge_class(self):
        return self.status_badge_class

    @property
    def perlu_perbaikan(self):
        prefetched_items = getattr(self, "_prefetched_objects_cache", {}).get("items")
        if prefetched_items is not None:
            return any(
                item.kondisi == KondisiPemeliharaanChoices.PERLU_PERBAIKAN
                for item in prefetched_items
            )
        return self.items.filter(kondisi=KondisiPemeliharaanChoices.PERLU_PERBAIKAN).exists()

    @property
    def perlu_pimpinan(self):
        prefetched_items = getattr(self, "_prefetched_objects_cache", {}).get("items")
        if prefetched_items is not None:
            return any(
                item.tindakan_perbaikan == TindakanPerbaikanChoices.EKSTERNAL
                for item in prefetched_items
            )
        return self.items.filter(
            tindakan_perbaikan=TindakanPerbaikanChoices.EKSTERNAL
        ).exists()

    @property
    def alur_label(self):
        if self.perlu_pimpinan:
            return "Kepala Lab > Pimpinan > Selesai"
        return "Kepala Lab > Selesai"

    @property
    def kondisi_ringkas(self):
        return (
            KondisiPemeliharaanChoices.PERLU_PERBAIKAN
            if self.perlu_perbaikan
            else KondisiPemeliharaanChoices.BAIK
        )

    @property
    def is_draft_like(self):
        return self.current_step in {
            StepPemeliharaanChoices.DRAFT,
            StepPemeliharaanChoices.DIKEMBALIKAN,
        }

    @property
    def is_active_process(self):
        return self.current_step in ACTIVE_PEMELIHARAAN_STEPS

    def sync_snapshot_from_master(self):
        if not self.alat:
            return
        self.snapshot_nama_barang = self.alat.nama_barang or ""
        self.snapshot_kode_laboratorium = self.alat.kode_laboratorium or ""
        self.snapshot_tipe_merek_barang = self.alat.tipe_merek_barang or ""

    def add_timeline(self, stage, action, actor=None, note=""):
        return PemeliharaanTimeline.objects.create(
            pengajuan=self,
            stage=stage,
            action=action,
            actor=actor,
            note=note or "",
        )

    def tandai_alat_dalam_pemeliharaan(self):
        if not self.alat_id:
            return

        alat = self.alat
        update_self = []
        if not self.kondisi_barang_sebelum:
            self.kondisi_barang_sebelum = alat.kondisi_barang or KondisiBarangChoices.BAIK
            update_self.append("kondisi_barang_sebelum")

        if alat.kondisi_barang != KondisiBarangChoices.DALAM_PEMELIHARAAN:
            alat.kondisi_barang = KondisiBarangChoices.DALAM_PEMELIHARAAN
            alat.save(update_fields=["kondisi_barang", "updated_at"])

        if update_self and self.pk:
            self.save(update_fields=update_self)

    def pulihkan_kondisi_alat_jika_selesai(self, alat=None):
        alat = alat or self.alat
        if not alat:
            return

        has_active = PemeliharaanPengajuan.objects.filter(
            alat=alat,
            current_step__in=ACTIVE_PEMELIHARAAN_STEPS,
        ).exclude(pk=self.pk).exists()
        if has_active:
            return

        kondisi = self.kondisi_barang_sebelum or KondisiBarangChoices.BAIK
        if kondisi == KondisiBarangChoices.DALAM_PEMELIHARAAN:
            kondisi = KondisiBarangChoices.BAIK
        alat.kondisi_barang = kondisi
        alat.save(update_fields=["kondisi_barang", "updated_at"])

    def save(self, *args, **kwargs):
        self.sync_snapshot_from_master()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.nomor_pengajuan:
            local_date = timezone.localdate(self.tanggal_pemeriksaan or timezone.now())
            self.nomor_pengajuan = make_nomor_pemeliharaan(local_date, self.pk)
            super().save(update_fields=["nomor_pengajuan"])


class PemeliharaanItem(models.Model):
    pengajuan = models.ForeignKey(
        PemeliharaanPengajuan,
        on_delete=models.CASCADE,
        related_name="items",
    )
    komponen = models.CharField(max_length=100)
    kondisi = models.CharField(
        max_length=30,
        choices=KondisiPemeliharaanChoices.choices,
        default=KondisiPemeliharaanChoices.BAIK,
    )
    tindakan_perbaikan = models.CharField(
        max_length=30,
        choices=TindakanPerbaikanChoices.choices,
        blank=True,
    )
    uraian_perbaikan = models.TextField(blank=True)
    tanggal_mulai_perbaikan = models.DateTimeField(null=True, blank=True)
    tanggal_selesai_perbaikan = models.DateTimeField(null=True, blank=True)
    uraian_kerusakan = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Item Pemeliharaan"
        verbose_name_plural = "Item Pemeliharaan"

    def __str__(self):
        return f"{self.pengajuan} - {self.komponen}"

    @property
    def perlu_perbaikan(self):
        return self.kondisi == KondisiPemeliharaanChoices.PERLU_PERBAIKAN

    @property
    def is_mandiri(self):
        return self.tindakan_perbaikan == TindakanPerbaikanChoices.MANDIRI

    @property
    def is_eksternal(self):
        return self.tindakan_perbaikan == TindakanPerbaikanChoices.EKSTERNAL


class PemeliharaanFoto(models.Model):
    item = models.ForeignKey(
        PemeliharaanItem,
        on_delete=models.CASCADE,
        related_name="fotos",
    )
    jenis = models.CharField(
        max_length=20,
        choices=JenisFotoPemeliharaanChoices.choices,
    )
    foto = models.ImageField(upload_to="pemeliharaan/foto/")
    urutan = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["jenis", "urutan", "id"]
        verbose_name = "Foto Pemeliharaan"
        verbose_name_plural = "Foto Pemeliharaan"

    def __str__(self):
        return f"{self.item} - {self.get_jenis_display()} #{self.urutan}"


class PemeliharaanTimeline(models.Model):
    pengajuan = models.ForeignKey(
        PemeliharaanPengajuan,
        on_delete=models.CASCADE,
        related_name="timeline_entries",
    )
    stage = models.CharField(max_length=50)
    action = models.CharField(max_length=120)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_pemeliharaan_actions",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "Riwayat Verifikasi Pemeliharaan"
        verbose_name_plural = "Riwayat Verifikasi Pemeliharaan"

    def __str__(self):
        return f"{self.pengajuan} - {self.action}"
