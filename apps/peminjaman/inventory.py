from django.db.models import Sum

from apps.master_data.models import (
    BarangLaboratorium,
    BarangPenunjangOperasional,
    PeralatanLaboratorium,
)

from .models import (
    PeminjamanBarangLaboratorium,
    PeminjamanBarangPenunjang,
    PeminjamanPeralatanLaboratorium,
    ReturnStepChoices,
    StepChoices,
)


def _active_allocation_filter(queryset):
    return (
        queryset.filter(pengajuan__aset_sudah_dialokasikan=True)
        .exclude(pengajuan__current_step=StepChoices.REJECTED)
        .exclude(pengajuan__return_current_step=ReturnStepChoices.COMPLETED)
    )


def _sync_lab_items(item_ids=None):
    queryset = BarangLaboratorium.objects.all()
    if item_ids is not None:
        queryset = queryset.filter(id__in=item_ids)

    active_queryset = _active_allocation_filter(PeminjamanBarangLaboratorium.objects.all())
    if item_ids is not None:
        active_queryset = active_queryset.filter(barang_id__in=item_ids)
    active_ids = set(active_queryset.values_list("barang_id", flat=True))
    for item in queryset:
        expected = item.id in active_ids
        if item.sedang_dipinjam == expected:
            continue
        item.sedang_dipinjam = expected
        item.save(update_fields=["sedang_dipinjam", "ketersediaan", "updated_at"])


def _active_volume_map(model, field_name, item_ids=None):
    queryset = _active_allocation_filter(model.objects.all())
    if item_ids is not None:
        queryset = queryset.filter(**{f"{field_name}_id__in": item_ids})
    rows = queryset.values(f"{field_name}_id").annotate(total=Sum("volume"))
    return {row[f"{field_name}_id"]: row["total"] or 0 for row in rows}


def _sync_volume_items(model, active_model, field_name, item_ids=None):
    queryset = model.objects.all()
    if item_ids is not None:
        queryset = queryset.filter(id__in=item_ids)

    active_map = _active_volume_map(active_model, field_name, item_ids)
    for item in queryset:
        expected = active_map.get(item.id, 0)
        if item.volume_dipinjam == expected:
            continue
        item.volume_dipinjam = expected
        item.save(update_fields=["volume_dipinjam", "ketersediaan", "updated_at"])


def sync_active_inventory(*, lab_ids=None, penunjang_ids=None, peralatan_lab_ids=None):
    _sync_lab_items(lab_ids)
    _sync_volume_items(
        BarangPenunjangOperasional,
        PeminjamanBarangPenunjang,
        "barang",
        penunjang_ids,
    )
    _sync_volume_items(
        PeralatanLaboratorium,
        PeminjamanPeralatanLaboratorium,
        "barang",
        peralatan_lab_ids,
    )
