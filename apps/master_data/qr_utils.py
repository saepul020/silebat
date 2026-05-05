from io import BytesIO
from uuid import uuid4

import qrcode
from django.core.files.base import ContentFile


QR_UPLOAD_DIR = "master_data/qr_code"


def _build_qr_png_content(public_url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(public_url)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ContentFile(buffer.getvalue())


def get_master_qr_relative_path(instance):
    return f"{QR_UPLOAD_DIR}/{instance.get_qr_filename_prefix()}-{instance.pk}-{instance.qr_token}.png"


def master_qr_file_exists(instance):
    qr_file = getattr(instance, "qr_code", None)
    if not qr_file or not getattr(qr_file, "name", None):
        return False
    return qr_file.storage.exists(qr_file.name)


def ensure_master_qr_code(instance, *, force=False, refresh_token=False):
    """Ensure a master-data object has a physical QR PNG file and DB path.

    The function intentionally updates the database with QuerySet.update() instead
    of instance.save(), so it can be called safely from post_save signals, list
    views, detail views, and maintenance commands without causing recursive
    signal loops.

    Args:
        instance: Master-data object that inherits QRCodeMixin.
        force: Rebuild the PNG even when the current file already exists.
        refresh_token: Generate a new token before rebuilding the QR. This is
            useful after changing PUBLIC_BASE_URL because it also changes the PNG
            filename and prevents browsers from showing a cached old QR image.
    """
    if not instance or not getattr(instance, "pk", None):
        return None
    if not hasattr(instance, "qr_code") or not hasattr(instance, "get_public_detail_url"):
        return None

    storage = instance.qr_code.storage
    current_name = getattr(instance.qr_code, "name", "") or ""
    current_exists = bool(current_name and storage.exists(current_name))

    should_rebuild = force or refresh_token or not current_exists
    if current_exists and not should_rebuild:
        return current_name

    if refresh_token or not getattr(instance, "qr_token", None):
        instance.qr_token = uuid4()

    relative_path = get_master_qr_relative_path(instance)

    # Clean stale/current files where possible. The database can still contain a
    # qr_code path even when the physical PNG was deleted manually, so each delete
    # is guarded by storage.exists().
    for old_name in {current_name, relative_path}:
        if old_name and storage.exists(old_name):
            storage.delete(old_name)

    public_url = instance.get_public_detail_url()
    if not public_url or public_url == "#":
        return None

    saved_name = storage.save(relative_path, _build_qr_png_content(public_url))

    instance.qr_code.name = saved_name
    instance.__class__.objects.filter(pk=instance.pk).update(
        qr_token=instance.qr_token,
        qr_code=saved_name,
    )
    return saved_name


def ensure_master_qr_codes(instances, *, force=False, refresh_token=False):
    created_or_checked = 0
    for instance in instances:
        ensure_master_qr_code(instance, force=force, refresh_token=refresh_token)
        created_or_checked += 1
    return created_or_checked
