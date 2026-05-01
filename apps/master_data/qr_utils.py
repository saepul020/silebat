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
    return ContentFile(buffer.getvalue())


def get_master_qr_relative_path(instance):
    return f"{QR_UPLOAD_DIR}/{instance.get_qr_filename_prefix()}-{instance.pk}-{instance.qr_token}.png"


def master_qr_file_exists(instance):
    qr_file = getattr(instance, "qr_code", None)
    if not qr_file or not getattr(qr_file, "name", None):
        return False
    return qr_file.storage.exists(qr_file.name)


def ensure_master_qr_code(instance, *, force=False):
    """Ensure a master-data object has a physical QR PNG file and DB path.

    This intentionally does not rely on instance.save(), so it is safe to call
    from signals, list views, detail views, and maintenance commands without
    causing recursive post_save loops.
    """
    if not instance or not getattr(instance, "pk", None):
        return None
    if not hasattr(instance, "qr_code") or not hasattr(instance, "get_public_detail_url"):
        return None

    update_fields = {}

    if not getattr(instance, "qr_token", None):
        instance.qr_token = uuid4()
        update_fields["qr_token"] = instance.qr_token

    current_name = getattr(instance.qr_code, "name", "") or ""
    current_exists = bool(current_name and instance.qr_code.storage.exists(current_name))

    if current_exists and not force:
        return current_name

    relative_path = get_master_qr_relative_path(instance)
    storage = instance.qr_code.storage

    if force and current_name and storage.exists(current_name):
        storage.delete(current_name)

    if force and storage.exists(relative_path):
        storage.delete(relative_path)

    if not force and storage.exists(relative_path):
        saved_name = relative_path
    else:
        public_url = instance.get_public_detail_url()
        if not public_url or public_url == "#":
            return None

        content = _build_qr_png_content(public_url)
        saved_name = storage.save(relative_path, content)

    update_fields["qr_code"] = saved_name
    instance.qr_code.name = saved_name

    instance.__class__.objects.filter(pk=instance.pk).update(**update_fields)
    return saved_name


def ensure_master_qr_codes(instances, *, force=False):
    created_or_checked = 0
    for instance in instances:
        ensure_master_qr_code(instance, force=force)
        created_or_checked += 1
    return created_or_checked
