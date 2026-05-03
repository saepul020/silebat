from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.dashboard.views import PENGUKURAN_FIELD_CONFIG
from apps.master_data.models import BarangLaboratorium, KategoriBarangLaboratoriumChoices
from apps.peminjaman.models import PeminjamanRequest, ReturnStepChoices, StepChoices

from .models import LandingPeralatanCard


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


def get_approved_peminjaman_queryset():
    return PeminjamanRequest.objects.filter(current_step=StepChoices.APPROVED).annotate(
        landing_approved_at=Coalesce("pimpinan_at", "updated_at")
    )


def build_chart_payload(labels, data):
    return {
        "labels": labels,
        "data": [int(value or 0) for value in data],
        "colors": [LANDING_PALETTE[index % len(LANDING_PALETTE)] for index, _ in enumerate(labels)],
    }


def get_survei_chart_payload(approved_queryset):
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


def get_pengukuran_chart_payload(approved_queryset):
    pengukuran_queryset = approved_queryset.filter(return_started_at__isnull=False)
    labels = []
    data = []

    for field_config in PENGUKURAN_FIELD_CONFIG:
        total = pengukuran_queryset.aggregate(total=Sum(field_config["key"]))["total"] or 0
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
    return LandingPeralatanCard.objects.filter(is_active=True).order_by(
        "urutan", "nama_barang", "id"
    )


def get_public_landing_context():
    now = timezone.localtime()
    current_year = now.year
    approved_queryset = get_approved_peminjaman_queryset()

    ongoing_count = approved_queryset.filter(landing_approved_at__year=current_year).exclude(
        return_current_step=ReturnStepChoices.COMPLETED
    ).count()
    completed_count = approved_queryset.filter(
        return_current_step=ReturnStepChoices.COMPLETED,
        return_completed_at__year=current_year,
    ).count()
    total_kegiatan_survei = approved_queryset.filter(layanan_kegiatan__isnull=False).count()
    total_peralatan_survei = BarangLaboratorium.objects.count()

    return {
        "landing_stats": {
            "kegiatan_berjalan": ongoing_count,
            "kegiatan_selesai": completed_count,
            "total_kegiatan_survei": total_kegiatan_survei,
            "jumlah_peralatan_survei": total_peralatan_survei,
            "current_year": current_year,
        },
        "landing_charts": {
            "survei": get_survei_chart_payload(approved_queryset),
            "layanan": get_layanan_chart_payload(approved_queryset),
            "pengukuran": get_pengukuran_chart_payload(approved_queryset),
        },
        "inventory_cards": get_inventory_category_cards(),
        "equipment_cards": get_equipment_cards(),
    }
