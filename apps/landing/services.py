from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.master_data.models import BarangLaboratorium, KategoriBarangLaboratoriumChoices
from apps.peminjaman.constants import PENGUKURAN_FIELD_CONFIG
from apps.peminjaman.models import PeminjamanRequest, ReturnStepChoices, StepChoices

from .models import LandingPeralatanCard


LANDING_CONTEXT_CACHE_KEY = "public_landing_context_v4"
LANDING_CONTEXT_CACHE_TIMEOUT = 60

LANDING_PALETTE = [
    "#103e6f",
    "#1a5c9c",
    "#64cdd1",
    "#4dbec2",
    "#b8e1f2",
    "#2e8fa8",
    "#5b8db8",
    "#94c4e4",
    "#0c2d52",
    "#155e75",
]

CATEGORY_ICON_MAP = {
    KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA: "bi bi-camera-video-fill",
    KategoriBarangLaboratoriumChoices.DRONE: "bi bi-send-fill",
    KategoriBarangLaboratoriumChoices.GEOLISTRIK: "bi bi-lightning-charge-fill",
    KategoriBarangLaboratoriumChoices.INFILTRASI: "bi bi-water",
    KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN: "bi bi-moisture",
    KategoriBarangLaboratoriumChoices.LOGGING: "bi bi-reception-4",
    KategoriBarangLaboratoriumChoices.TOPOGRAFI_TS: "bi bi-crosshair",
    KategoriBarangLaboratoriumChoices.PENDUKUNG_SURVEI_LAPANGAN: "bi bi-box-seam-fill",
}


def invalidate_public_landing_cache():
    cache.delete(LANDING_CONTEXT_CACHE_KEY)


def get_approved_peminjaman_queryset():
    return PeminjamanRequest.objects.filter(current_step=StepChoices.APPROVED)


def build_chart_payload(labels, data):
    return {
        "labels": labels,
        "data": [int(value or 0) for value in data],
        "colors": [LANDING_PALETTE[index % len(LANDING_PALETTE)] for index, _ in enumerate(labels)],
    }


def get_landing_stats(approved_queryset, current_year):
    approved_this_year_filter = (
        Q(pimpinan_at__year=current_year)
        | (Q(pimpinan_at__isnull=True) & Q(updated_at__year=current_year))
    )
    stats = approved_queryset.aggregate(
        kegiatan_berjalan=Count(
            "id",
            filter=approved_this_year_filter & ~Q(return_current_step=ReturnStepChoices.COMPLETED),
        ),
        kegiatan_selesai=Count(
            "id",
            filter=Q(return_current_step=ReturnStepChoices.COMPLETED, return_completed_at__year=current_year),
        ),
        total_kegiatan_survei=Count("id", filter=Q(layanan_kegiatan__isnull=False)),
    )
    return {key: int(value or 0) for key, value in stats.items()}


def get_survei_chart_payload():
    through_model = PeminjamanRequest._meta.get_field("kegiatan_survei").remote_field.through
    rows = list(
        through_model.objects.filter(
            peminjamanrequest__current_step=StepChoices.APPROVED,
            surveikegiatan__isnull=False,
        )
        .values("surveikegiatan__jenis_survei")
        .annotate(total=Count("id"))
        .filter(total__gt=0)
        .order_by("surveikegiatan__jenis_survei")
    )
    return build_chart_payload(
        [row["surveikegiatan__jenis_survei"] or "-" for row in rows],
        [row["total"] for row in rows],
    )


def get_layanan_chart_payload(approved_queryset):
    rows = list(
        approved_queryset.filter(layanan_kegiatan__isnull=False)
        .values("layanan_kegiatan__jenis_layanan")
        .annotate(total=Count("id"))
        .filter(total__gt=0)
        .order_by("layanan_kegiatan__jenis_layanan")
    )
    return build_chart_payload(
        [row["layanan_kegiatan__jenis_layanan"] or "-" for row in rows],
        [row["total"] for row in rows],
    )


def get_instansi_chart_payload(approved_queryset):
    rows = list(
        approved_queryset.filter(instansi_tujuan__isnull=False)
        .exclude(instansi_tujuan__nama_instansi__iexact="Lainnya")
        .values("instansi_tujuan__nama_instansi")
        .annotate(total=Count("id"))
        .filter(total__gt=0)
        .order_by("instansi_tujuan__nama_instansi")
    )
    return build_chart_payload(
        [row["instansi_tujuan__nama_instansi"] or "-" for row in rows],
        [row["total"] for row in rows],
    )


def get_pengukuran_chart_payload(approved_queryset):
    pengukuran_queryset = approved_queryset.filter(return_started_at__isnull=False)
    aggregate_kwargs = {
        field_config["key"]: Sum(field_config["key"])
        for field_config in PENGUKURAN_FIELD_CONFIG
    }
    totals = pengukuran_queryset.aggregate(**aggregate_kwargs)
    labels = []
    data = []

    for field_config in PENGUKURAN_FIELD_CONFIG:
        total = totals.get(field_config["key"]) or 0
        if total <= 0:
            continue
        labels.append(field_config["label"])
        data.append(total)

    return build_chart_payload(labels, data)


def get_inventory_category_cards():
    choice_labels = dict(KategoriBarangLaboratoriumChoices.choices)
    rows = list(
        BarangLaboratorium.objects.exclude(kategori_barang__isnull=True)
        .exclude(kategori_barang="")
        .values("kategori_barang")
        .annotate(total=Count("id"))
        .filter(total__gt=0)
        .order_by("kategori_barang")
    )

    return [
        {
            "label": choice_labels.get(row["kategori_barang"], row["kategori_barang"] or "-"),
            "total": int(row["total"] or 0),
            "icon": CATEGORY_ICON_MAP.get(row["kategori_barang"], "bi bi-box-seam-fill"),
        }
        for row in rows
    ]


def get_equipment_cards():
    cards = (
        LandingPeralatanCard.objects.filter(is_active=True)
        .only(
            "kategori_barang",
            "nama_barang",
            "jenis_barang",
            "merek_tipe_alat",
            "fungsi_alat",
            "spesifikasi_alat",
            "ringkasan_alat",
            "foto_barang",
            "urutan",
        )
        .order_by("urutan", "nama_barang", "id")
    )
    return [
        {
            "kategori_barang_label": card.get_kategori_barang_display() or "Peralatan",
            "nama_barang": card.nama_barang or "-",
            "jenis_barang": card.jenis_barang or "-",
            "merek_tipe_alat": card.merek_tipe_alat or "-",
            "fungsi_alat": card.fungsi_alat or "-",
            "spesifikasi_alat": card.spesifikasi_alat or "-",
            "ringkasan_alat": card.ringkasan_alat or "-",
            "foto_url": card.foto_barang.url if card.foto_barang else "",
        }
        for card in cards
    ]


def build_public_landing_context():
    now = timezone.localtime()
    current_year = now.year
    approved_queryset = get_approved_peminjaman_queryset()
    landing_stats = get_landing_stats(approved_queryset, current_year)
    landing_stats["jumlah_peralatan_survei"] = BarangLaboratorium.objects.count()
    landing_stats["current_year"] = current_year

    return {
        "landing_stats": landing_stats,
        "landing_charts": {
            "survei": get_survei_chart_payload(),
            "layanan": get_layanan_chart_payload(approved_queryset),
            "pengukuran": get_pengukuran_chart_payload(approved_queryset),
            "instansi": get_instansi_chart_payload(approved_queryset),
        },
        "inventory_cards": get_inventory_category_cards(),
        "equipment_cards": get_equipment_cards(),
    }


def get_public_landing_context():
    cached_context = cache.get(LANDING_CONTEXT_CACHE_KEY)
    if cached_context is not None:
        return cached_context

    context = build_public_landing_context()
    cache.set(LANDING_CONTEXT_CACHE_KEY, context, LANDING_CONTEXT_CACHE_TIMEOUT)
    return context
