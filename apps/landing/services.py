import logging

from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Count, Q, Sum
from django.db.utils import InterfaceError, OperationalError, ProgrammingError
from django.utils import timezone

from apps.master_data.models import BarangLaboratorium, KategoriBarangLaboratoriumChoices, KondisiBarangChoices
from apps.peminjaman.constants import PENGUKURAN_FIELD_CONFIG
from apps.peminjaman.models import PeminjamanRequest, ReturnStepChoices, StepChoices

from .models import TV_SLOT_COUNT, TV_SLIDE_COUNT, DokumentasiTV, KontenAlatTV, LandingPeralatanCard


def get_tv_documentation():
    slides = {}
    for slot in DokumentasiTV.objects.all():
        if slot.foto:
            slides.setdefault(slot.slide_id, {})[slot.nomor] = slot.foto
    return [
        {
            "id": slide_id,
            "slots": [{"nomor": nomor, "foto": photos.get(nomor)} for nomor in range(1, TV_SLOT_COUNT + 1)],
        }
        for slide_id, photos in slides.items()
    ]


def get_tv_slides():
    slots = {
        slot.nomor: {"alat": slot.alat, "judul_barang": slot.judul_barang}
        for slot in KontenAlatTV.objects.select_related("alat")
    }
    return [
        {"nomor": slide + 1, "slots": [
            {"nomor": kolom, **slots.get(slide * TV_SLOT_COUNT + kolom, {"alat": None, "judul_barang": ""})}
            for kolom in range(1, TV_SLOT_COUNT + 1)
        ]}
        for slide in range(TV_SLIDE_COUNT)
    ]


logger = logging.getLogger(__name__)

LANDING_CONTEXT_CACHE_KEY = "public_landing_context_v9"
LANDING_CONTEXT_CACHE_TIMEOUT = 60
LANDING_FALLBACK_CACHE_TIMEOUT = 10
DEFAULT_EQUIPMENT_CATEGORY = KategoriBarangLaboratoriumChoices.GEOLISTRIK

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

CATEGORY_IMG_MAP = {
    KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA: "assets/img/borehole.webp",
    KategoriBarangLaboratoriumChoices.DRONE: "assets/img/drone.webp",
    KategoriBarangLaboratoriumChoices.GEOLISTRIK: "assets/img/geolistrik.webp",
    KategoriBarangLaboratoriumChoices.INFILTRASI: "assets/img/infiltrometer.webp",
    KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN: "assets/img/kualitas-air.webp",
    KategoriBarangLaboratoriumChoices.LOGGING: "assets/img/logging.webp",
    KategoriBarangLaboratoriumChoices.TOPOGRAFI_TS: "assets/img/total-station.webp",
    KategoriBarangLaboratoriumChoices.PENDUKUNG_SURVEI_LAPANGAN: "assets/img/pendukung-survei.webp",
}

TV_INVENTORY_CATEGORIES = (
    KategoriBarangLaboratoriumChoices.BOREHOLE_CAMERA,
    KategoriBarangLaboratoriumChoices.DRONE,
    KategoriBarangLaboratoriumChoices.GEOLISTRIK,
    KategoriBarangLaboratoriumChoices.INFILTRASI,
    KategoriBarangLaboratoriumChoices.INSTRUMEN_KEAIRAN,
    KategoriBarangLaboratoriumChoices.LOGGING,
)


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


def get_empty_chart_payload():
    return build_chart_payload([], [])


def get_empty_public_landing_context():
    current_year = timezone.localtime().year
    return {
        "landing_stats": {
            "kegiatan_berjalan": 0,
            "kegiatan_selesai": 0,
            "total_kegiatan_survei": 0,
            "jumlah_peralatan_survei": 0,
            "current_year": current_year,
        },
        "landing_charts": {
            "survei": get_empty_chart_payload(),
            "layanan": get_empty_chart_payload(),
            "pengukuran": get_empty_chart_payload(),
            "instansi": get_empty_chart_payload(),
        },
        "inventory_cards": [],
        "equipment_cards": [],
        "equipment_filters": [],
        "default_equipment_filter": DEFAULT_EQUIPMENT_CATEGORY,
        "landing_data_unavailable": True,
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


def get_inventory_category_cards(categories=None, include_conditions=False):
    choice_labels = dict(KategoriBarangLaboratoriumChoices.choices)
    queryset = BarangLaboratorium.objects.exclude(kategori_barang__isnull=True).exclude(kategori_barang="")
    if categories is not None:
        queryset = queryset.filter(kategori_barang__in=categories)
    aggregates = {"total": Count("id")}
    if include_conditions:
        aggregates.update(
            baik=Count("id", filter=Q(kondisi_barang=KondisiBarangChoices.BAIK)),
            rusak=Count("id", filter=Q(kondisi_barang=KondisiBarangChoices.RUSAK)),
        )
    rows = list(
        queryset.values("kategori_barang")
        .annotate(**aggregates)
        .filter(total__gt=0)
        .order_by("kategori_barang")
    )
    counts = {row["kategori_barang"]: row for row in rows}

    return [
        {
            "label": choice_labels.get(category, category or "-"),
            **{field: int(counts.get(category, {}).get(field) or 0) for field in aggregates},
            "img": CATEGORY_IMG_MAP.get(category, ""),
        }
        for category in (categories if categories is not None else counts)
    ]


def get_tv_inventory_cards():
    return get_inventory_category_cards(TV_INVENTORY_CATEGORIES, include_conditions=True)


def split_spec_points(value):
    text = str(value or "").replace(";", "\n")
    return [item.strip() for item in text.splitlines() if item.strip()]


def get_equipment_filters():
    return [
        {"value": value, "label": label}
        for value, label in KategoriBarangLaboratoriumChoices.choices
    ]


def get_equipment_cards():
    cards = (
        LandingPeralatanCard.objects.filter(is_active=True)
        .prefetch_related("fotos")
        .only(
            "kategori_barang",
            "nama_barang",
            "jenis_barang",
            "merek_tipe_alat",
            "fungsi_alat",
            "metode_pengukuran",
            "spesifikasi_alat",
            "ringkasan_alat",
            "urutan",
        )
        .order_by("urutan", "nama_barang", "id")
    )
    return [
        {
            "kategori_barang": card.kategori_barang or "",
            "kategori_barang_label": card.get_kategori_barang_display() or "Peralatan",
            "nama_barang": card.nama_barang or "-",
            "jenis_barang": card.jenis_barang or "-",
            "merek_tipe_alat": card.merek_tipe_alat or "-",
            "fungsi_alat": card.fungsi_alat or "-",
            "metode_pengukuran": card.metode_pengukuran or "",
            "spesifikasi_items": split_spec_points(card.spesifikasi_alat),
            "ringkasan_alat": card.ringkasan_alat or "-",
            "foto_urls": [photo.foto.url for photo in card.fotos.all() if photo.foto],
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
        "equipment_filters": get_equipment_filters(),
        "default_equipment_filter": DEFAULT_EQUIPMENT_CATEGORY,
    }


def get_public_landing_context():
    cached_context = cache.get(LANDING_CONTEXT_CACHE_KEY)
    if cached_context is not None:
        return cached_context

    try:
        context = build_public_landing_context()
    except (DatabaseError, InterfaceError, OperationalError, ProgrammingError):
        logger.exception("Data landing publik belum tersedia atau database tidak dapat diakses.")
        context = get_empty_public_landing_context()
        cache.set(LANDING_CONTEXT_CACHE_KEY, context, LANDING_FALLBACK_CACHE_TIMEOUT)
        return context

    cache.set(LANDING_CONTEXT_CACHE_KEY, context, LANDING_CONTEXT_CACHE_TIMEOUT)
    return context
