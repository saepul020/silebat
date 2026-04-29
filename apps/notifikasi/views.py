from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.list_pagination import paginate_list
from apps.core.permissions import ROLE_SUPER_ADMIN, deny_access, get_role_name

from .forms import AnnouncementForm
from .models import Announcement, Notification, NotificationCategory
from .services import mark_all_as_read, publish_announcement_to_users, visible_notifications


@login_required
def index(request):
    queryset = visible_notifications(Notification.objects.filter(recipient=request.user)).order_by("-visible_from", "-created_at", "-id")
    filter_status = (request.GET.get("status") or "").strip()
    if filter_status == "belum-dibaca":
        queryset = queryset.filter(is_read=False)
    elif filter_status == "sudah-dibaca":
        queryset = queryset.filter(is_read=True)

    pagination_context = paginate_list(request, queryset)
    context = {
        "items": pagination_context["items"],
        "filter_status": filter_status,
        "page_title": "Notifikasi",
        "page_subtitle": "Pusat informasi verifikasi, status peminjaman/pengembalian, dan pengumuman SILEBAT.",
        "can_create_announcement": get_role_name(request.user) == ROLE_SUPER_ADMIN,
    }
    context.update(pagination_context)
    return render(request, "notifikasi/notifikasi_list.html", context)


@login_required
def baca_notifikasi(request, pk):
    obj = get_object_or_404(visible_notifications(Notification.objects.filter(recipient=request.user)), pk=pk)
    obj.mark_as_read()
    if obj.link_url:
        return redirect(obj.link_url)
    return redirect("notifikasi:index")


@login_required
def tandai_semua_dibaca(request):
    if request.method != "POST":
        return redirect("notifikasi:index")
    total = mark_all_as_read(request.user)
    messages.success(request, f"{total} notifikasi berhasil ditandai sudah dibaca.")
    return redirect("notifikasi:index")


@login_required
def tambah_pengumuman(request):
    if get_role_name(request.user) != ROLE_SUPER_ADMIN:
        return deny_access(request, "Hanya Super Admin yang dapat membuat pengumuman.")

    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.is_active = True
            announcement.save()
            total_user = publish_announcement_to_users(announcement)
            messages.success(
                request,
                f"Pengumuman berhasil dibuat dan disiapkan untuk {total_user} user aktif sesuai jadwal tampil.",
            )
            return redirect("notifikasi:riwayat_pengumuman")
    else:
        form = AnnouncementForm()

    return render(
        request,
        "notifikasi/pengumuman_form.html",
        {
            "form": form,
            "page_title": "Tambah Pengumuman",
            "page_subtitle": "Buat pengumuman yang akan muncul sebagai notifikasi untuk seluruh user SILEBAT.",
            "submit_label": "Kirim Pengumuman",
            "submit_icon": "bi-send",
            "is_edit_mode": False,
        },
    )


@login_required
def edit_pengumuman(request, pk):
    if get_role_name(request.user) != ROLE_SUPER_ADMIN:
        return deny_access(request, "Hanya Super Admin yang dapat mengubah pengumuman.")

    announcement = get_object_or_404(Announcement, pk=pk)

    if request.method == "POST":
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            updated_announcement = form.save(commit=False)
            updated_announcement.is_active = True
            updated_announcement.save()
            total_user = publish_announcement_to_users(updated_announcement)
            messages.success(
                request,
                f'Pengumuman "{updated_announcement.title}" berhasil diperbarui dan disinkronkan kembali untuk {total_user} user aktif sesuai jadwal tampil.',
            )
            return redirect("notifikasi:riwayat_pengumuman")
    else:
        form = AnnouncementForm(instance=announcement)

    return render(
        request,
        "notifikasi/pengumuman_form.html",
        {
            "form": form,
            "page_title": "Edit Pengumuman",
            "page_subtitle": "Ubah isi atau jadwal pengumuman. Jika masa tayang sudah selesai, perbarui tanggal selesai agar pengumuman aktif kembali.",
            "submit_label": "Simpan Pengumuman",
            "submit_icon": "bi-save",
            "is_edit_mode": True,
            "announcement": announcement,
        },
    )


@login_required
def riwayat_pengumuman(request):
    if get_role_name(request.user) != ROLE_SUPER_ADMIN:
        return deny_access(request, "Hanya Super Admin yang dapat melihat riwayat pengumuman.")

    now = timezone.now()
    queryset = Announcement.objects.select_related("created_by").order_by("-publish_start_at", "-id")
    filter_status = (request.GET.get("status") or "").strip()

    if filter_status == "menunggu":
        queryset = queryset.filter(publish_start_at__gt=now)
    elif filter_status == "tayang":
        queryset = queryset.filter(
            Q(publish_start_at__isnull=True) | Q(publish_start_at__lte=now),
            Q(publish_end_at__isnull=True) | Q(publish_end_at__gte=now),
        )
    elif filter_status == "selesai":
        queryset = queryset.filter(publish_end_at__lt=now)

    pagination_context = paginate_list(request, queryset)
    items = pagination_context["items"]

    for item in items:
        notif_qs = Notification.objects.filter(
            category=NotificationCategory.ANNOUNCEMENT,
            dedupe_key__startswith=f"announcement:{item.pk}:user:",
        )
        item.notification_total = notif_qs.count()
        item.notification_read = notif_qs.filter(is_read=True).count()
        item.notification_unread = max(item.notification_total - item.notification_read, 0)

    context = {
        "items": items,
        "filter_status": filter_status,
        "page_title": "Riwayat Pengumuman",
        "page_subtitle": "Kelola seluruh histori notifikasi pengumuman yang pernah dibuat dan dikirim kepada user SILEBAT.",
    }
    context.update(pagination_context)
    return render(request, "notifikasi/riwayat_pengumuman.html", context)


@login_required
def hapus_pengumuman(request, pk):
    if get_role_name(request.user) != ROLE_SUPER_ADMIN:
        return deny_access(request, "Hanya Super Admin yang dapat menghapus pengumuman.")

    if request.method != "POST":
        return redirect("notifikasi:riwayat_pengumuman")

    announcement = get_object_or_404(Announcement, pk=pk)
    title = announcement.title

    with transaction.atomic():
        deleted_notifications, _ = Notification.objects.filter(
            category=NotificationCategory.ANNOUNCEMENT,
            dedupe_key__startswith=f"announcement:{announcement.pk}:user:",
        ).delete()
        announcement.delete()

    messages.success(
        request,
        f'Pengumuman "{title}" berhasil dihapus beserta {deleted_notifications} notifikasi terkait.',
    )
    return redirect("notifikasi:riwayat_pengumuman")
