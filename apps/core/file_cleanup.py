from __future__ import annotations

from typing import Iterable

from django.apps import apps
from django.db.models import FileField


def _resolve_file_name(file_or_name) -> str:
    if not file_or_name:
        return ""
    if hasattr(file_or_name, "name"):
        return getattr(file_or_name, "name", "") or ""
    return str(file_or_name or "")


def _resolve_storage(model, field_name: str, file_obj=None):
    storage = getattr(file_obj, "storage", None)
    if storage is not None:
        return storage
    field = model._meta.get_field(field_name)
    return getattr(field, "storage", None)


def delete_file_if_unused(
    model, field_name: str, file_or_name, *, exclude_pk=None, using=None, check_references=False,
) -> bool:
    file_name = _resolve_file_name(file_or_name)
    if not file_name:
        return False

    queryset = model._default_manager.using(using).filter(**{field_name: file_name})
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    if queryset.exists():
        return False

    storage = _resolve_storage(model, field_name, file_or_name)
    if storage is None:
        return False

    if check_references:
        for related_model in apps.get_models():
            for field in related_model._meta.concrete_fields:
                if not isinstance(field, FileField) or field.storage is not storage:
                    continue
                if related_model is model and field.name == field_name:
                    continue
                if related_model._base_manager.using(using).filter(**{field.name: file_name}).exists():
                    return False

    try:
        if storage.exists(file_name):
            storage.delete(file_name)
            return True
    except Exception:
        return False

    return False


def delete_instance_files(instance, field_names: Iterable[str]) -> None:
    model = type(instance)
    instance_pk = getattr(instance, "pk", None)
    for field_name in field_names:
        delete_file_if_unused(
            model,
            field_name,
            getattr(instance, field_name, None),
            exclude_pk=instance_pk,
        )
