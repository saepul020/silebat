from __future__ import annotations

from typing import Iterable

from django import forms

MAX_UPLOAD_SIZE_BYTES = 7 * 1024 * 1024
MAX_UPLOAD_SIZE_MB = 7


def build_max_upload_size_message(label: str | None = None) -> str:
    label_text = str(label or "File").strip() or "File"
    return f"Ukuran file {label_text} maksimal {MAX_UPLOAD_SIZE_MB} MB."


def validate_uploaded_file(
    uploaded_file,
    *,
    allowed_extensions: Iterable[str] | None = None,
    invalid_extension_message: str | None = None,
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
    max_size_message: str | None = None,
):
    if not uploaded_file:
        return uploaded_file

    if allowed_extensions:
        file_name = str(getattr(uploaded_file, "name", "") or "").strip().lower()
        if not file_name or "." not in file_name:
            raise forms.ValidationError(invalid_extension_message or "Format file tidak didukung.")

        extension = f".{file_name.split('.')[-1]}"
        if extension not in {str(ext).lower() for ext in allowed_extensions}:
            raise forms.ValidationError(invalid_extension_message or "Format file tidak didukung.")

    file_size = getattr(uploaded_file, "size", None)
    if file_size is not None and int(file_size) > int(max_size_bytes):
        raise forms.ValidationError(max_size_message or build_max_upload_size_message())

    return uploaded_file


def apply_upload_widget_validation_attrs(
    field,
    *,
    allowed_extensions: str | None = None,
    invalid_extension_message: str | None = None,
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
    max_size_message: str | None = None,
):
    if not field:
        return field

    attrs = field.widget.attrs
    attrs["data-inline-file-max-size"] = str(int(max_size_bytes))
    if max_size_message:
        attrs["data-inline-file-max-size-error"] = max_size_message
    if allowed_extensions:
        attrs["data-inline-file-extensions"] = allowed_extensions
    if invalid_extension_message:
        attrs["data-inline-file-error"] = invalid_extension_message
    return field
