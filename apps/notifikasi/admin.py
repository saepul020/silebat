from django.contrib import admin

from .models import Announcement, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "category", "is_read", "created_at")
    list_filter = ("category", "is_read", "created_at")
    search_fields = ("title", "message", "recipient__username", "recipient__first_name", "recipient__last_name")
    readonly_fields = ("created_at", "updated_at", "read_at")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "publish_start_at", "publish_end_at", "created_by")
    list_filter = ("publish_start_at", "publish_end_at")
    search_fields = ("title", "message")
    readonly_fields = ("created_at", "updated_at")
