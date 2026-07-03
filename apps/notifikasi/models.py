from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationCategory(models.TextChoices):
    VERIFICATION = "verification", "Verifikasi"
    STATUS = "status", "Status"
    ANNOUNCEMENT = "announcement", "Pengumuman"
    SYSTEM = "system", "Sistem"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifikasi_items",
    )
    title = models.CharField(max_length=180)
    message = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM,
    )
    link_url = models.CharField(max_length=255, blank=True)
    source_pengajuan = models.ForeignKey(
        "peminjaman.PeminjamanRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifikasi_items",
    )
    source_pemeliharaan = models.ForeignKey(
        "pemeliharaan.PemeliharaanPengajuan",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifikasi_items",
    )
    dedupe_key = models.CharField(max_length=220, blank=True, db_index=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    visible_from = models.DateTimeField(default=timezone.now)
    visible_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "visible_from", "visible_until"]),
            models.Index(fields=["category", "-created_at"]),
        ]
        verbose_name = "Notifikasi"
        verbose_name_plural = "Notifikasi"

    def __str__(self):
        return f"{self.recipient} - {self.title}"

    @property
    def category_badge_class(self):
        return {
            NotificationCategory.VERIFICATION: "badge-warning",
            NotificationCategory.STATUS: "badge-success",
            NotificationCategory.ANNOUNCEMENT: "badge-primary",
            NotificationCategory.SYSTEM: "badge-secondary",
        }.get(self.category, "badge-secondary")

    @property
    def icon_class(self):
        return {
            NotificationCategory.VERIFICATION: "bi-clipboard-check",
            NotificationCategory.STATUS: "bi-check-circle",
            NotificationCategory.ANNOUNCEMENT: "bi-megaphone",
            NotificationCategory.SYSTEM: "bi-info-circle",
        }.get(self.category, "bi-bell")

    @property
    def is_visible_now(self):
        now = timezone.now()
        if self.visible_from and self.visible_from > now:
            return False
        if self.visible_until and self.visible_until < now:
            return False
        return True

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])


class Announcement(models.Model):
    title = models.CharField(max_length=180)
    message = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pengumuman_dibuat",
    )
    is_active = models.BooleanField(default=True)
    publish_start_at = models.DateTimeField(default=timezone.now)
    publish_end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-publish_start_at", "-id"]
        verbose_name = "Pengumuman"
        verbose_name_plural = "Pengumuman"

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        now = timezone.now()
        if self.publish_start_at and self.publish_start_at > now:
            return False
        if self.publish_end_at and self.publish_end_at < now:
            return False
        return True

    @property
    def publish_status_label(self):
        now = timezone.now()
        if self.publish_start_at and self.publish_start_at > now:
            return "Menunggu Tayang"
        if self.publish_end_at and self.publish_end_at < now:
            return "Selesai"
        return "Sedang Tayang"

    @property
    def publish_status_badge_class(self):
        status = self.publish_status_label
        if status == "Sedang Tayang":
            return "badge-success"
        if status == "Menunggu Tayang":
            return "badge-warning"
        return "badge-secondary"
