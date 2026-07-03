from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.permissions import (
    ROLE_ADMIN_LAB,
    ROLE_KEPALA_LAB,
    ROLE_PIMPINAN,
    ROLE_SUPER_ADMIN,
    ROLE_TEKNISI_LAB,
)
from apps.operasional.models import TIM_LAYANAN_TEKNIS_NAME, TimKegiatan
from apps.peminjaman.models import DecisionChoices, ReturnStepChoices, StepChoices
from apps.pemeliharaan.models import StepPemeliharaanChoices

from .models import Announcement, Notification, NotificationCategory

User = get_user_model()

# Aturan masa tampil notifikasi status transaksi final.
# Berlaku untuk:
# - Peminjaman/Pemeliharaan Disetujui
# - Peminjaman/Pemeliharaan Ditolak
# - Pengembalian Selesai
#
# Durasi tampil:
# - Dropdown navbar: 1 x 24 jam.
# - Halaman Notifikasi: 7 x 24 jam.
TRANSACTION_STATUS_DROPDOWN_DURATION = timedelta(days=1)
TRANSACTION_STATUS_PAGE_DURATION = timedelta(days=7)


def _active_users():
    return User.objects.filter(is_active=True).select_related("profile", "profile__role")


def _transaction_status_notification_q():
    return (
        Q(category=NotificationCategory.STATUS)
        & (
            (
                Q(dedupe_key__startswith="peminjaman:")
                & (
                    Q(dedupe_key__endswith=f":status:{StepChoices.APPROVED.value}")
                    | Q(dedupe_key__endswith=f":status:{StepChoices.REJECTED.value}")
                )
            )
            | (
                Q(dedupe_key__startswith="pengembalian:")
                & Q(dedupe_key__endswith=":status:completed")
            )
            | (
                Q(dedupe_key__startswith="pemeliharaan:")
                & (
                    Q(dedupe_key__endswith=f":status:{StepPemeliharaanChoices.SELESAI.value}")
                    | Q(dedupe_key__endswith=f":status:{StepPemeliharaanChoices.DITOLAK.value}")
                )
            )
        )
    )


def _status_surface_duration(surface):
    return (
        TRANSACTION_STATUS_DROPDOWN_DURATION
        if surface == "dropdown"
        else TRANSACTION_STATUS_PAGE_DURATION
    )


def visible_notifications(queryset=None, *, surface="page"):
    now = timezone.now()
    base_queryset = queryset if queryset is not None else Notification.objects.all()
    queryset = base_queryset.filter(
        Q(visible_from__isnull=True) | Q(visible_from__lte=now),
        Q(visible_until__isnull=True) | Q(visible_until__gte=now),
    )

    # Khusus notifikasi status transaksi final:
    # - Peminjaman/Pemeliharaan Disetujui, Peminjaman/Pemeliharaan Ditolak,
    #   dan Pengembalian Selesai
    #   tampil di dropdown navbar selama 1 x 24 jam;
    # - tetap bisa dilihat di halaman Notifikasi selama 7 x 24 jam.
    # Pengumuman tidak dibatasi aturan ini dan tetap mengikuti publish_start_at/publish_end_at.
    duration = _status_surface_duration(surface)
    cutoff = now - duration
    return queryset.filter(
        ~_transaction_status_notification_q()
        | Q(visible_from__gte=cutoff)
        | Q(visible_from__isnull=True, created_at__gte=cutoff)
    )


def _users_by_role(role_name):
    return _active_users().filter(profile__role__nama=role_name)


def _merge_users(*querysets_or_users):
    user_map = {}
    for item in querysets_or_users:
        if item is None:
            continue
        if hasattr(item, "all"):
            iterator = item
        elif isinstance(item, (list, tuple, set)):
            iterator = item
        else:
            iterator = [item]
        for user in iterator:
            if user and getattr(user, "pk", None):
                user_map[user.pk] = user
    return list(user_map.values())


def _super_admin_users():
    return _users_by_role(ROLE_SUPER_ADMIN)


def _get_return_pimpinan_user():
    target_team = (
        TimKegiatan.objects.filter(nama_tim__iexact=TIM_LAYANAN_TEKNIS_NAME)
        .select_related("ketua_tim")
        .order_by("id")
        .first()
    )
    if target_team and target_team.ketua_tim_id:
        return target_team.ketua_tim

    fallback_team = (
        TimKegiatan.objects.filter(nama_tim__icontains="Layanan Teknis")
        .select_related("ketua_tim")
        .order_by("id")
        .first()
    )
    if fallback_team and fallback_team.ketua_tim_id:
        return fallback_team.ketua_tim
    return None


def _verification_recipients(pengajuan):
    if _is_pemeliharaan(pengajuan):
        step = pengajuan.current_step
        if step == StepPemeliharaanChoices.KEPALA_LAB:
            return _merge_users(_users_by_role(ROLE_KEPALA_LAB), _super_admin_users())
        if step == StepPemeliharaanChoices.PIMPINAN:
            return _merge_users(_get_return_pimpinan_user(), _super_admin_users())
        if step == StepPemeliharaanChoices.DIKEMBALIKAN:
            return _merge_users(pengajuan.pemohon)
        return []

    if pengajuan.return_current_step not in {ReturnStepChoices.NONE, ReturnStepChoices.COMPLETED}:
        step = pengajuan.return_current_step
        if step in {
            ReturnStepChoices.TEKNISI_VERIFICATION,
            ReturnStepChoices.TEKNISI_BA,
            ReturnStepChoices.TEKNISI_TRANSFER,
        }:
            return _merge_users(_users_by_role(ROLE_TEKNISI_LAB), _super_admin_users())
        if step == ReturnStepChoices.USER_VERIFICATION:
            return _merge_users(pengajuan.peminjam)
        if step in {ReturnStepChoices.KEPALA_BA, ReturnStepChoices.KEPALA_TRANSFER}:
            return _merge_users(_users_by_role(ROLE_KEPALA_LAB), _super_admin_users())
        if step in {ReturnStepChoices.PIMPINAN_BA, ReturnStepChoices.PIMPINAN_TRANSFER}:
            return _merge_users(_get_return_pimpinan_user(), _super_admin_users())
        return []

    step = pengajuan.current_step
    if step == StepChoices.ADMIN_LAB:
        return _merge_users(_users_by_role(ROLE_ADMIN_LAB), _super_admin_users())
    if step == StepChoices.TEKNISI_LAB:
        return _merge_users(_users_by_role(ROLE_TEKNISI_LAB), _super_admin_users())
    if step == StepChoices.KEPALA_LAB:
        return _merge_users(_users_by_role(ROLE_KEPALA_LAB), _super_admin_users())
    if step == StepChoices.PIMPINAN:
        ketua_tim = getattr(getattr(pengajuan, "tim_kegiatan", None), "ketua_tim", None)
        fallback_pimpinan = [] if ketua_tim else _users_by_role(ROLE_PIMPINAN)
        return _merge_users(ketua_tim, fallback_pimpinan, _super_admin_users())
    return []


REVISION_ACTIONS = {"perbaiki", "tidak_sesuai"}
CONTINUATION_ACTIONS = {"setujui", "selesai", "sesuai"}


def _is_active_pengembalian(pengajuan):
    if not hasattr(pengajuan, "return_current_step"):
        return False
    return pengajuan.return_current_step not in {
        ReturnStepChoices.NONE,
        ReturnStepChoices.COMPLETED,
    }


def _is_pemeliharaan(pengajuan):
    return getattr(pengajuan, "verifikasi_kind", "") == "pemeliharaan"


def _is_active_pemeliharaan(pengajuan):
    return _is_pemeliharaan(pengajuan) and pengajuan.current_step in {
        StepPemeliharaanChoices.KEPALA_LAB,
        StepPemeliharaanChoices.PIMPINAN,
        StepPemeliharaanChoices.DIKEMBALIKAN,
    }


def _source_filter(pengajuan):
    if _is_pemeliharaan(pengajuan):
        return {"source_pemeliharaan": pengajuan}
    return {"source_pengajuan": pengajuan}


def _source_defaults(pengajuan):
    if _is_pemeliharaan(pengajuan):
        return {"source_pemeliharaan": pengajuan}
    return {"source_pengajuan": pengajuan}


def _verification_link(pengajuan):
    if _is_pemeliharaan(pengajuan):
        if pengajuan.current_step == StepPemeliharaanChoices.DIKEMBALIKAN:
            return reverse("pemeliharaan:detail", args=[pengajuan.pk])
        return reverse("verifikasi:detail_pemeliharaan", args=[pengajuan.pk])
    return reverse("verifikasi:detail", args=[pengajuan.pk])


def _status_link(pengajuan):
    if _is_pemeliharaan(pengajuan):
        return reverse("pemeliharaan:detail", args=[pengajuan.pk])
    return reverse("peminjaman:detail", args=[pengajuan.pk])


def _safe_user_label(user):
    if not user:
        return "Sistem"
    name = ""
    if hasattr(user, "get_full_name"):
        name = user.get_full_name()
    if not name:
        name = getattr(user, "username", "User")
    role = getattr(getattr(user, "safe_profile", None), "role", None)
    role_name = getattr(role, "nama", "") if role else ""
    return f"{name} ({role_name})" if role_name else name


def _short_note(note, max_length=170):
    note = (note or "").strip()
    if not note:
        return ""
    if len(note) <= max_length:
        return note
    return f"{note[:max_length].rstrip()}..."


def _is_revision_followup(pengajuan, source_action=None):
    if source_action in REVISION_ACTIONS:
        return True

    if _is_pemeliharaan(pengajuan):
        return pengajuan.current_step == StepPemeliharaanChoices.DIKEMBALIKAN

    if _is_active_pengembalian(pengajuan):
        return (
            pengajuan.return_current_step == ReturnStepChoices.TEKNISI_VERIFICATION
            and pengajuan.return_user_verification_status == DecisionChoices.MISMATCH
        )

    return (
        pengajuan.current_step == StepChoices.TEKNISI_LAB
        and (
            pengajuan.kepala_lab_status == DecisionChoices.REVISION
            or pengajuan.pimpinan_status == DecisionChoices.REVISION
        )
    )


def _is_continuation_followup(source_action=None):
    return source_action in CONTINUATION_ACTIONS


def _verification_flow_key(pengajuan, source_action=None):
    if _is_revision_followup(pengajuan, source_action):
        return "revision"
    if _is_continuation_followup(source_action):
        return "continuation"
    return "pending"


def _verification_title(pengajuan, source_action=None):
    nomor = pengajuan.nomor_pengajuan or ""
    if _is_pemeliharaan(pengajuan):
        flow_key = _verification_flow_key(pengajuan, source_action)
        if flow_key == "revision":
            prefix = "Perbaikan Pemeliharaan"
        elif flow_key == "continuation":
            prefix = "Lanjutan Verifikasi Pemeliharaan"
        else:
            prefix = "Verifikasi Pemeliharaan"
        return f"{prefix} {nomor}".strip()

    is_return = _is_active_pengembalian(pengajuan)
    flow_key = _verification_flow_key(pengajuan, source_action)

    if flow_key == "revision":
        prefix = "Perbaikan Pengembalian" if is_return else "Perbaikan Peminjaman"
    elif flow_key == "continuation":
        prefix = "Lanjutan Verifikasi Pengembalian" if is_return else "Lanjutan Verifikasi Peminjaman"
    else:
        prefix = "Verifikasi Pengembalian" if is_return else "Verifikasi Peminjaman"
    return f"{prefix} {nomor}".strip()


def _verification_message(pengajuan, actor=None, source_action=None, action_note=""):
    nomor = pengajuan.nomor_pengajuan or f"#{pengajuan.pk}"
    if _is_pemeliharaan(pengajuan):
        nama = pengajuan.nama_pemohon
        step_label = pengajuan.get_current_step_display()
        actor_label = _safe_user_label(actor)
        note = _short_note(action_note)
        note_text = f" Catatan: {note}" if note else ""

        if _is_revision_followup(pengajuan, source_action):
            return (
                f"Jenis tindak lanjut: Perbaikan. Proses pemeliharaan {nomor} dari {nama} "
                f"dikembalikan oleh {actor_label} untuk diperbaiki. "
                f"Silakan cek catatan perbaikan dan tindak lanjuti pada tahap {step_label}."
                f"{note_text}"
            )

        if _is_continuation_followup(source_action):
            action_label = {
                "setujui": "telah disetujui",
                "selesai": "telah dilanjutkan",
                "sesuai": "telah dinyatakan sesuai",
            }.get(source_action, "telah dilanjutkan")
            return (
                f"Jenis tindak lanjut: Lanjutan proses. Proses pemeliharaan {nomor} dari {nama} "
                f"{action_label} oleh {actor_label}. Menunggu tindak lanjut pada tahap {step_label}."
                f"{note_text}"
            )

        return f"Pemeliharaan {nomor} dari {nama} menunggu proses {step_label}."

    nama = (
        pengajuan.nama_peminjam
        or getattr(pengajuan.peminjam, "get_full_name", lambda: "")()
        or getattr(pengajuan.peminjam, "username", "User")
    )
    is_return = _is_active_pengembalian(pengajuan)
    step_label = (
        pengajuan.get_return_current_step_display()
        if is_return
        else pengajuan.get_current_step_display()
    )
    actor_label = _safe_user_label(actor)
    note = _short_note(action_note)
    note_text = f" Catatan: {note}" if note else ""

    if _is_revision_followup(pengajuan, source_action):
        process_label = "pengembalian" if is_return else "peminjaman"
        return (
            f"Jenis tindak lanjut: Perbaikan. Proses {process_label} {nomor} dari {nama} "
            f"dikembalikan oleh {actor_label} untuk diperbaiki. "
            f"Silakan cek catatan perbaikan/ketidaksesuaian dan tindak lanjuti pada tahap {step_label}."
            f"{note_text}"
        )

    if _is_continuation_followup(source_action):
        process_label = "pengembalian" if is_return else "peminjaman"
        action_label = {
            "setujui": "telah disetujui",
            "selesai": "telah dilanjutkan",
            "sesuai": "telah dinyatakan sesuai",
        }.get(source_action, "telah dilanjutkan")
        return (
            f"Jenis tindak lanjut: Lanjutan proses. Proses {process_label} {nomor} dari {nama} "
            f"{action_label} oleh {actor_label}. Menunggu tindak lanjut pada tahap {step_label}."
            f"{note_text}"
        )

    if is_return:
        return f"Pengembalian {nomor} dari {nama} menunggu proses {step_label}."
    return f"Peminjaman {nomor} dari {nama} menunggu proses {step_label}."


def _verification_dedupe_key(pengajuan, source_action=None):
    flow_key = _verification_flow_key(pengajuan, source_action)
    if _is_pemeliharaan(pengajuan):
        return f"pemeliharaan:{pengajuan.pk}:step:{pengajuan.current_step}:flow:{flow_key}"
    if _is_active_pengembalian(pengajuan):
        return f"pengembalian:{pengajuan.pk}:step:{pengajuan.return_current_step}:flow:{flow_key}"
    return f"peminjaman:{pengajuan.pk}:step:{pengajuan.current_step}:flow:{flow_key}"


def _verification_step_key_prefix(pengajuan):
    if _is_pemeliharaan(pengajuan):
        return f"pemeliharaan:{pengajuan.pk}:step:{pengajuan.current_step}:flow:"
    if _is_active_pengembalian(pengajuan):
        return f"pengembalian:{pengajuan.pk}:step:{pengajuan.return_current_step}:flow:"
    return f"peminjaman:{pengajuan.pk}:step:{pengajuan.current_step}:flow:"


def _has_visible_current_step_notification(recipient, pengajuan):
    """Cegah notifikasi verifikasi generik muncul ganda pada tahap yang sama."""
    if recipient is None or not getattr(recipient, "pk", None):
        return False

    step_key_prefix = _verification_step_key_prefix(pengajuan)
    queryset = visible_notifications(
        Notification.objects.filter(
            recipient=recipient,
            category=NotificationCategory.VERIFICATION,
            dedupe_key__startswith=step_key_prefix,
            **_source_filter(pengajuan),
        )
    )

    if not queryset.exists():
        return False

    pending_key = f"{step_key_prefix}pending"
    has_followup_notification = queryset.exclude(dedupe_key=pending_key).exists()
    if has_followup_notification:
        queryset.filter(dedupe_key=pending_key).delete()
    return True


def _create_or_update_notification(
    recipient,
    *,
    title,
    message,
    category,
    link_url="",
    source_pengajuan=None,
    source_pemeliharaan=None,
    dedupe_key="",
    visible_from=None,
    visible_until=None,
):
    if recipient is None or not getattr(recipient, "pk", None):
        return None

    defaults = {
        "title": title,
        "message": message,
        "category": category,
        "link_url": link_url or "",
        "source_pengajuan": source_pengajuan,
        "source_pemeliharaan": source_pemeliharaan,
        "visible_from": visible_from or timezone.now(),
        "visible_until": visible_until,
        "is_read": False,
        "read_at": None,
    }

    if dedupe_key:
        existing = Notification.objects.filter(recipient=recipient, dedupe_key=dedupe_key).order_by("id")
        notification = existing.first()
        if notification:
            for field, value in defaults.items():
                setattr(notification, field, value)
            notification.save(update_fields=[*defaults.keys(), "updated_at"])
            if existing.count() > 1:
                existing.exclude(pk=notification.pk).delete()
            return notification

    return Notification.objects.create(recipient=recipient, dedupe_key=dedupe_key or "", **defaults)


def close_open_verification_notifications(pengajuan):
    now = timezone.now()
    expired_at = now - timedelta(seconds=1)
    Notification.objects.filter(
        category=NotificationCategory.VERIFICATION,
        **_source_filter(pengajuan),
    ).update(
        is_read=True,
        read_at=now,
        visible_until=expired_at,
        updated_at=now,
    )


def sync_transaction_notifications(
    pengajuan,
    actor=None,
    source_action=None,
    previous_current_step=None,
    previous_return_step=None,
    action_note="",
):
    """Sinkronisasi notifikasi setiap kali tahap transaksi berpindah."""
    if not pengajuan or not getattr(pengajuan, "pk", None):
        return

    with transaction.atomic():
        close_open_verification_notifications(pengajuan)

        if _is_pemeliharaan(pengajuan):
            if _is_active_pemeliharaan(pengajuan):
                for recipient in _verification_recipients(pengajuan):
                    _create_or_update_notification(
                        recipient,
                        title=_verification_title(pengajuan, source_action),
                        message=_verification_message(
                            pengajuan,
                            actor=actor,
                            source_action=source_action,
                            action_note=action_note,
                        ),
                        category=NotificationCategory.VERIFICATION,
                        link_url=_verification_link(pengajuan),
                        dedupe_key=_verification_dedupe_key(pengajuan, source_action),
                        **_source_defaults(pengajuan),
                    )
                return

            if pengajuan.current_step in {
                StepPemeliharaanChoices.SELESAI,
                StepPemeliharaanChoices.DITOLAK,
            }:
                status_label = pengajuan.get_current_step_display()
                nomor = pengajuan.nomor_pengajuan or f"#{pengajuan.pk}"
                status_visible_from = timezone.now()
                _create_or_update_notification(
                    pengajuan.pemohon,
                    title=f"Pemeliharaan {status_label}",
                    message=f"Proses pemeliharaan {nomor} telah {status_label.lower()}.",
                    category=NotificationCategory.STATUS,
                    link_url=_status_link(pengajuan),
                    dedupe_key=f"pemeliharaan:{pengajuan.pk}:status:{pengajuan.current_step}",
                    visible_from=status_visible_from,
                    visible_until=status_visible_from + TRANSACTION_STATUS_PAGE_DURATION,
                    **_source_defaults(pengajuan),
                )
            return

        is_active_pengembalian = _is_active_pengembalian(pengajuan)
        is_active_peminjaman = pengajuan.current_step not in {
            StepChoices.APPROVED,
            StepChoices.REJECTED,
        }

        if is_active_pengembalian or (not is_active_pengembalian and is_active_peminjaman):
            for recipient in _verification_recipients(pengajuan):
                _create_or_update_notification(
                    recipient,
                    title=_verification_title(pengajuan, source_action),
                    message=_verification_message(
                        pengajuan,
                        actor=actor,
                        source_action=source_action,
                        action_note=action_note,
                    ),
                    category=NotificationCategory.VERIFICATION,
                    link_url=_verification_link(pengajuan),
                    dedupe_key=_verification_dedupe_key(pengajuan, source_action),
                    **_source_defaults(pengajuan),
                )
            return

        if (
            pengajuan.current_step in {StepChoices.APPROVED, StepChoices.REJECTED}
            and pengajuan.return_current_step == ReturnStepChoices.NONE
        ):
            status_label = pengajuan.get_current_step_display()
            nomor = pengajuan.nomor_pengajuan or f"#{pengajuan.pk}"
            title = f"Peminjaman {status_label}"
            message = f"Proses peminjaman {nomor} telah {status_label.lower()}."
            status_visible_from = timezone.now()
            _create_or_update_notification(
                pengajuan.peminjam,
                title=title,
                message=message,
                category=NotificationCategory.STATUS,
                link_url=_status_link(pengajuan),
                dedupe_key=f"peminjaman:{pengajuan.pk}:status:{pengajuan.current_step}",
                visible_from=status_visible_from,
                visible_until=status_visible_from + TRANSACTION_STATUS_PAGE_DURATION,
                **_source_defaults(pengajuan),
            )

        if pengajuan.return_current_step == ReturnStepChoices.COMPLETED:
            nomor = pengajuan.nomor_pengajuan or f"#{pengajuan.pk}"
            status_visible_from = timezone.now()
            _create_or_update_notification(
                pengajuan.peminjam,
                title="Pengembalian Selesai",
                message=f"Proses pengembalian {nomor} telah selesai/disetujui.",
                category=NotificationCategory.STATUS,
                link_url=reverse("peminjaman:pengembalian", args=[pengajuan.pk]),
                dedupe_key=f"pengembalian:{pengajuan.pk}:status:completed",
                visible_from=status_visible_from,
                visible_until=status_visible_from + TRANSACTION_STATUS_PAGE_DURATION,
                **_source_defaults(pengajuan),
            )


def publish_announcement_to_users(announcement):
    if not announcement or not announcement.is_active:
        return 0

    counter = 0
    for user in _active_users():
        _create_or_update_notification(
            user,
            title=announcement.title,
            message=announcement.message,
            category=NotificationCategory.ANNOUNCEMENT,
            link_url=reverse("notifikasi:index"),
            visible_from=announcement.publish_start_at or timezone.now(),
            visible_until=announcement.publish_end_at,
            dedupe_key=f"announcement:{announcement.pk}:user:{user.pk}",
        )
        counter += 1
    return counter



def ensure_user_pending_notifications(user):
    if not getattr(user, "is_authenticated", False):
        return

    from apps.peminjaman.models import PeminjamanRequest
    from apps.pemeliharaan.models import PemeliharaanPengajuan

    active_queryset = PeminjamanRequest.objects.select_related(
        "peminjam", "tim_kegiatan", "tim_kegiatan__ketua_tim"
    ).filter(
        Q(return_current_step__in=[
            ReturnStepChoices.TEKNISI_VERIFICATION,
            ReturnStepChoices.USER_VERIFICATION,
            ReturnStepChoices.TEKNISI_BA,
            ReturnStepChoices.KEPALA_BA,
            ReturnStepChoices.PIMPINAN_BA,
            ReturnStepChoices.TEKNISI_TRANSFER,
            ReturnStepChoices.KEPALA_TRANSFER,
            ReturnStepChoices.PIMPINAN_TRANSFER,
        ])
        | Q(current_step__in=[
            StepChoices.ADMIN_LAB,
            StepChoices.TEKNISI_LAB,
            StepChoices.KEPALA_LAB,
            StepChoices.PIMPINAN,
        ])
    ).distinct()

    for pengajuan in active_queryset[:75]:
        recipients = _verification_recipients(pengajuan)
        if not any(getattr(recipient, "pk", None) == user.pk for recipient in recipients):
            continue
        if _has_visible_current_step_notification(user, pengajuan):
            continue

        dedupe_key = _verification_dedupe_key(pengajuan)
        _create_or_update_notification(
            user,
            title=_verification_title(pengajuan),
            message=_verification_message(pengajuan),
            category=NotificationCategory.VERIFICATION,
            link_url=_verification_link(pengajuan),
            dedupe_key=dedupe_key,
            **_source_defaults(pengajuan),
        )

    pemeliharaan_queryset = PemeliharaanPengajuan.objects.select_related(
        "pemohon", "alat"
    ).filter(
        current_step__in=[
            StepPemeliharaanChoices.KEPALA_LAB,
            StepPemeliharaanChoices.PIMPINAN,
            StepPemeliharaanChoices.DIKEMBALIKAN,
        ]
    ).distinct()

    for pengajuan in pemeliharaan_queryset[:75]:
        recipients = _verification_recipients(pengajuan)
        if not any(getattr(recipient, "pk", None) == user.pk for recipient in recipients):
            continue
        if _has_visible_current_step_notification(user, pengajuan):
            continue

        dedupe_key = _verification_dedupe_key(pengajuan)
        _create_or_update_notification(
            user,
            title=_verification_title(pengajuan),
            message=_verification_message(pengajuan),
            category=NotificationCategory.VERIFICATION,
            link_url=_verification_link(pengajuan),
            dedupe_key=dedupe_key,
            **_source_defaults(pengajuan),
        )

def get_navbar_notifications(user, limit=5):
    if not getattr(user, "is_authenticated", False):
        return {
            "notification_unread_count": 0,
            "notification_recent_items": [],
        }
    ensure_user_pending_notifications(user)
    qs = visible_notifications(Notification.objects.filter(recipient=user), surface="dropdown")
    return {
        "notification_unread_count": qs.filter(is_read=False).count(),
        "notification_recent_items": list(qs.order_by("-visible_from", "-created_at", "-id")[:limit]),
    }


def mark_all_as_read(user):
    now = timezone.now()
    return visible_notifications(Notification.objects.filter(recipient=user, is_read=False)).update(
        is_read=True,
        read_at=now,
        updated_at=now,
    )
