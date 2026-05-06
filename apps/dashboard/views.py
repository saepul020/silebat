from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce, ExtractYear, TruncMonth, Trim
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.permissions import get_role_name
from apps.operasional.models import InstansiKlien, LayananKegiatan, SurveiKegiatan, TimKegiatan
from apps.peminjaman.constants import PENGUKURAN_FIELD_CONFIG
from apps.peminjaman.models import PeminjamanRequest, ReturnStepChoices, StepChoices


MONTH_LABELS_ID = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mei",
    6: "Jun",
    7: "Jul",
    8: "Agu",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Des",
}

TIM_COLOR_PALETTE = [
    {"background": "rgba(16, 62, 111, 0.82)", "border": "rgba(16, 62, 111, 1)"},
    {"background": "rgba(100, 205, 209, 0.82)", "border": "rgba(100, 205, 209, 1)"},
    {"background": "rgba(184, 225, 242, 0.95)", "border": "rgba(16, 62, 111, 0.42)"},
    {"background": "rgba(255, 193, 7, 0.86)", "border": "rgba(255, 193, 7, 1)"},
    {"background": "rgba(16, 62, 111, 0.62)", "border": "rgba(16, 62, 111, 0.88)"},
    {"background": "rgba(220, 53, 69, 0.76)", "border": "rgba(220, 53, 69, 1)"},
]

LAYANAN_COLOR_PALETTE = [
    "rgba(16, 62, 111, 0.82)",
    "rgba(100, 205, 209, 0.82)",
    "rgba(184, 225, 242, 0.95)",
    "rgba(255, 193, 7, 0.86)",
    "rgba(16, 62, 111, 0.62)",
    "rgba(100, 205, 209, 0.62)",
    "rgba(184, 225, 242, 0.76)",
    "rgba(220, 53, 69, 0.76)",
]


SURVEI_COLOR_PALETTE = [
    "rgba(16, 62, 111, 0.82)",
    "rgba(100, 205, 209, 0.82)",
    "rgba(184, 225, 242, 0.95)",
    "rgba(255, 193, 7, 0.86)",
    "rgba(16, 62, 111, 0.64)",
    "rgba(100, 205, 209, 0.64)",
    "rgba(184, 225, 242, 0.78)",
    "rgba(220, 53, 69, 0.76)",
    "rgba(16, 62, 111, 0.50)",
    "rgba(100, 205, 209, 0.50)",
    "rgba(255, 193, 7, 0.62)",
    "rgba(220, 53, 69, 0.58)",
]

INSTANSI_COLOR_PALETTE = SURVEI_COLOR_PALETTE



def get_approved_peminjaman_queryset():
    return (
        PeminjamanRequest.objects.select_related(
            "tim_kegiatan",
            "layanan_kegiatan",
            "instansi_tujuan",
        )
        .filter(current_step=StepChoices.APPROVED)
        .annotate(dashboard_approved_at=Coalesce("pimpinan_at", "updated_at"))
    )



def get_active_peminjaman_queryset():
    return (
        PeminjamanRequest.objects.select_related(
            "peminjam",
            "layanan_kegiatan",
            "tim_kegiatan",
            "instansi_tujuan",
        )
        .prefetch_related(
            "barang_laboratorium_items__barang",
            "barang_penunjang_items__barang",
            "peralatan_laboratorium_items__barang",
            "bahan_operasional_items__bahan",
            "pengembalian_lab_items",
            "pengembalian_penunjang_items",
            "pengembalian_peralatan_laboratorium_items",
            "pengembalian_bahan_items",
        )
        .exclude(current_step=StepChoices.REJECTED)
        .exclude(return_current_step=ReturnStepChoices.COMPLETED)
        .order_by("-submitted_at", "-id")
    )

def get_pengukuran_lapangan_queryset(queryset):
    return queryset.filter(return_started_at__isnull=False)

def build_sum_rows_by_month(queryset, date_field, value_field, row_key):
    aggregated_rows = list(
        queryset.filter(**{f"{value_field}__isnull": False, f"{value_field}__gt": 0})
        .annotate(month=TruncMonth(date_field))
        .values("month")
        .annotate(total=Sum(value_field))
        .order_by("month")
    )
    return [
        {
            "year": row["month"].year,
            "month": row["month"].month,
            row_key: value_field,
            "total": int(row["total"] or 0),
        }
        for row in aggregated_rows
        if row.get("month")
    ]

def build_sum_rows_by_year(queryset, date_field, value_field, row_key):
    aggregated_rows = list(
        queryset.filter(**{f"{value_field}__isnull": False, f"{value_field}__gt": 0})
        .annotate(year=ExtractYear(date_field))
        .values("year")
        .annotate(total=Sum(value_field))
        .order_by("year")
    )
    return [
        {
            "year": int(row["year"]),
            row_key: value_field,
            "total": int(row["total"] or 0),
        }
        for row in aggregated_rows
        if row.get("year")
    ]

def build_count_rows_by_month(queryset, date_field):
    aggregated_rows = list(
        queryset.annotate(month=TruncMonth(date_field))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    return [
        {
            "year": row["month"].year,
            "month": row["month"].month,
            "total": int(row["total"] or 0),
        }
        for row in aggregated_rows
        if row.get("month")
    ]

def get_dashboard_greeting_period(current_time):
    hour = current_time.hour
    if 4 <= hour < 11:
        return "Pagi"
    if 11 <= hour < 15:
        return "Siang"
    if 15 <= hour < 18:
        return "Sore"
    return "Malam"


def build_dashboard_context(request=None, active_limit=None):
    approved_peminjaman_qs = get_approved_peminjaman_queryset()
    pengukuran_lapangan_qs = get_pengukuran_lapangan_queryset(approved_peminjaman_qs)
    now = timezone.localtime()
    current_year = now.year
    current_month = now.month

    completed_count = approved_peminjaman_qs.filter(
        return_current_step=ReturnStepChoices.COMPLETED,
    ).count()
    ongoing_count = approved_peminjaman_qs.exclude(
        return_current_step=ReturnStepChoices.COMPLETED,
    ).count()

    tim_list = list(TimKegiatan.objects.order_by("nama_tim").values("id", "nama_tim"))
    tim_month_rows = list(
        approved_peminjaman_qs.filter(tim_kegiatan__isnull=False)
        .annotate(month=TruncMonth("dashboard_approved_at"))
        .values("month", "tim_kegiatan_id")
        .annotate(total=Count("id"))
        .order_by("month", "tim_kegiatan__nama_tim")
    )

    tim_available_years = sorted(
        {
            row["month"].year
            for row in tim_month_rows
            if row.get("month")
        }
        | {current_year}
    )

    tim_chart = {
        "teams": [
            {
                "id": tim["id"],
                "label": tim["nama_tim"],
                "backgroundColor": TIM_COLOR_PALETTE[index % len(TIM_COLOR_PALETTE)]["background"],
                "borderColor": TIM_COLOR_PALETTE[index % len(TIM_COLOR_PALETTE)]["border"],
            }
            for index, tim in enumerate(tim_list)
        ],
        "rows": [
            {
                "year": row["month"].year,
                "month": row["month"].month,
                "timId": row["tim_kegiatan_id"],
                "total": row["total"],
            }
            for row in tim_month_rows
            if row.get("month") and row.get("tim_kegiatan_id")
        ],
        "availableYears": tim_available_years,
        "defaultYear": current_year,
        "defaultMonth": current_month,
    }

    layanan_list = list(
        LayananKegiatan.objects.order_by("jenis_layanan").values("id", "jenis_layanan")
    )
    layanan_year_rows = list(
        approved_peminjaman_qs.filter(layanan_kegiatan__isnull=False)
        .annotate(year=ExtractYear("dashboard_approved_at"))
        .values("year", "layanan_kegiatan_id")
        .annotate(total=Count("id"))
        .order_by("year", "layanan_kegiatan__jenis_layanan")
    )
    layanan_lainnya_rows = list(
        approved_peminjaman_qs.filter(layanan_kegiatan_lainnya__isnull=False)
        .annotate(
            year=ExtractYear("dashboard_approved_at"),
            layanan_lainnya_value=Trim("layanan_kegiatan_lainnya"),
        )
        .exclude(layanan_lainnya_value="")
        .values("year")
        .annotate(total=Count("id"))
        .order_by("year")
    )
    layanan_available_years = sorted(
        {
            int(row["year"])
            for row in [*layanan_year_rows, *layanan_lainnya_rows]
            if row.get("year")
        }
        | {current_year}
    )

    layanan_categories = [
        {
            "id": layanan["id"],
            "label": layanan["jenis_layanan"],
            "backgroundColor": LAYANAN_COLOR_PALETTE[index % len(LAYANAN_COLOR_PALETTE)],
        }
        for index, layanan in enumerate(layanan_list)
    ]
    layanan_lainnya_total = sum(int(row.get("total") or 0) for row in layanan_lainnya_rows)
    if layanan_lainnya_total:
        layanan_categories.append(
            {
                "id": "lainnya",
                "label": "Lainnya",
                "backgroundColor": LAYANAN_COLOR_PALETTE[len(layanan_categories) % len(LAYANAN_COLOR_PALETTE)],
            }
        )

    layanan_chart = {
        "categories": layanan_categories,
        "rows": [
            {
                "year": int(row["year"]),
                "layananId": row["layanan_kegiatan_id"],
                "total": row["total"],
            }
            for row in layanan_year_rows
            if row.get("year") and row.get("layanan_kegiatan_id")
        ]
        + [
            {
                "year": int(row["year"]),
                "layananId": "lainnya",
                "total": row["total"],
            }
            for row in layanan_lainnya_rows
            if row.get("year")
        ],
        "availableYears": layanan_available_years,
        "defaultYear": current_year,
    }

    survei_list = list(
        SurveiKegiatan.objects.order_by("jenis_survei").values("id", "jenis_survei")
    )
    survei_through_model = PeminjamanRequest._meta.get_field("kegiatan_survei").remote_field.through
    survei_rows = list(
        survei_through_model.objects.filter(
            peminjamanrequest__current_step=StepChoices.APPROVED,
        )
        .annotate(
            year=ExtractYear(
                Coalesce("peminjamanrequest__pimpinan_at", "peminjamanrequest__updated_at")
            )
        )
        .values("year", "surveikegiatan_id")
        .annotate(total=Count("id"))
        .order_by("year", "surveikegiatan__jenis_survei")
    )
    survei_lainnya_rows = list(
        approved_peminjaman_qs.filter(survei_lainnya__isnull=False)
        .annotate(
            year=ExtractYear("dashboard_approved_at"),
            survei_lainnya_value=Trim("survei_lainnya"),
        )
        .exclude(survei_lainnya_value="")
        .values("year")
        .annotate(total=Count("id"))
        .order_by("year")
    )
    survei_chart_categories = [
        {
            "id": survei["id"],
            "label": survei["jenis_survei"],
            "backgroundColor": SURVEI_COLOR_PALETTE[index % len(SURVEI_COLOR_PALETTE)],
        }
        for index, survei in enumerate(survei_list)
    ]
    survei_available_years = sorted(
        {
            int(row["year"])
            for row in survei_rows
            if row.get("year")
        }
        | {
            int(row["year"])
            for row in survei_lainnya_rows
            if row.get("year")
        }
        | {current_year}
    )
    survei_lainnya_total = sum(int(row.get("total") or 0) for row in survei_lainnya_rows)
    if survei_lainnya_total:
        survei_chart_categories.append(
            {
                "id": "lainnya",
                "label": "Lainnya",
                "backgroundColor": SURVEI_COLOR_PALETTE[len(survei_chart_categories) % len(SURVEI_COLOR_PALETTE)],
            }
        )

    survei_chart = {
        "categories": survei_chart_categories,
        "rows": [
            {
                "year": int(row["year"]),
                "surveiId": row["surveikegiatan_id"],
                "total": row["total"],
            }
            for row in survei_rows
            if row.get("year") and row.get("surveikegiatan_id")
        ]
        + [
            {
                "year": int(row["year"]),
                "surveiId": "lainnya",
                "total": row["total"],
            }
            for row in survei_lainnya_rows
            if row.get("year")
        ],
        "availableYears": survei_available_years,
        "defaultYear": current_year,
    }

    instansi_list = list(
        InstansiKlien.objects.order_by("nama_instansi").values("id", "nama_instansi")
    )
    instansi_rows = list(
        approved_peminjaman_qs.filter(instansi_tujuan__isnull=False)
        .annotate(year=ExtractYear("dashboard_approved_at"))
        .values("year", "instansi_tujuan_id")
        .annotate(total=Count("id"))
        .order_by("year", "instansi_tujuan__nama_instansi")
    )
    instansi_lainnya_rows = list(
        approved_peminjaman_qs.filter(instansi_tujuan_lainnya__isnull=False)
        .annotate(
            year=ExtractYear("dashboard_approved_at"),
            instansi_lainnya_value=Trim("instansi_tujuan_lainnya"),
        )
        .exclude(instansi_lainnya_value="")
        .values("year")
        .annotate(total=Count("id"))
        .order_by("year")
    )
    instansi_chart_categories = [
        {
            "id": instansi["id"],
            "label": instansi["nama_instansi"],
            "backgroundColor": INSTANSI_COLOR_PALETTE[index % len(INSTANSI_COLOR_PALETTE)],
        }
        for index, instansi in enumerate(instansi_list)
    ]
    instansi_available_years = sorted(
        {
            int(row["year"])
            for row in instansi_rows
            if row.get("year")
        }
        | {
            int(row["year"])
            for row in instansi_lainnya_rows
            if row.get("year")
        }
        | {current_year}
    )
    instansi_lainnya_total = sum(int(row.get("total") or 0) for row in instansi_lainnya_rows)
    if instansi_lainnya_total:
        instansi_chart_categories.append(
            {
                "id": "lainnya",
                "label": "Lainnya",
                "backgroundColor": INSTANSI_COLOR_PALETTE[len(instansi_chart_categories) % len(INSTANSI_COLOR_PALETTE)],
            }
        )

    instansi_chart = {
        "categories": instansi_chart_categories,
        "rows": [
            {
                "year": int(row["year"]),
                "instansiId": row["instansi_tujuan_id"],
                "total": row["total"],
            }
            for row in instansi_rows
            if row.get("year") and row.get("instansi_tujuan_id")
        ]
        + [
            {
                "year": int(row["year"]),
                "instansiId": "lainnya",
                "total": row["total"],
            }
            for row in instansi_lainnya_rows
            if row.get("year")
        ],
        "availableYears": instansi_available_years,
        "defaultYear": current_year,
    }

    pengukuran_available_years = {current_year}
    pengukuran_chart_rows = []
    pengukuran_year_rows = []
    pengukuran_chart_categories = []
    for index, field_config in enumerate(PENGUKURAN_FIELD_CONFIG):
        row_key = field_config["key"]
        monthly_rows = build_sum_rows_by_month(
            pengukuran_lapangan_qs,
            "return_started_at",
            row_key,
            "pengukuranKey",
        )
        year_rows = build_sum_rows_by_year(
            pengukuran_lapangan_qs,
            "return_started_at",
            row_key,
            "pengukuranKey",
        )
        pengukuran_chart_rows.extend(monthly_rows)
        pengukuran_year_rows.extend(year_rows)
        pengukuran_available_years.update(row["year"] for row in monthly_rows if row.get("year"))
        pengukuran_available_years.update(row["year"] for row in year_rows if row.get("year"))
        pengukuran_chart_categories.append(
            {
                "id": row_key,
                "label": field_config["label"],
                "backgroundColor": TIM_COLOR_PALETTE[index % len(TIM_COLOR_PALETTE)]["background"],
                "borderColor": TIM_COLOR_PALETTE[index % len(TIM_COLOR_PALETTE)]["border"],
            }
        )

    pengukuran_chart = {
        "categories": pengukuran_chart_categories,
        "rows": pengukuran_chart_rows,
        "yearRows": pengukuran_year_rows,
        "availableYears": sorted(pengukuran_available_years),
        "defaultYear": current_year,
        "defaultMonth": current_month,
    }

    approved_peminjaman_rows = build_count_rows_by_month(
        approved_peminjaman_qs,
        "dashboard_approved_at",
    )
    approved_peminjaman_available_years = sorted(
        {row["year"] for row in approved_peminjaman_rows if row.get("year")} | {current_year}
    )
    approved_peminjaman_chart = {
        "dataset": {
            "label": "Total Peminjaman Disetujui",
            "backgroundColor": "rgba(16, 62, 111, 0.82)",
            "borderColor": "rgba(16, 62, 111, 1)",
        },
        "rows": approved_peminjaman_rows,
        "availableYears": approved_peminjaman_available_years,
        "defaultYear": current_year,
        "defaultMonth": current_month,
    }

    active_peminjaman = get_active_peminjaman_queryset()
    if active_limit:
        active_peminjaman = active_peminjaman[:active_limit]

    if request is not None and request.user.is_authenticated:
        greeting_name = request.user.get_full_name() or request.user.username or get_role_name(request.user) or "Pengguna"
        greeting_time_source = request.user.last_login or now
    else:
        greeting_name = "Laboratorium"
        greeting_time_source = now
    greeting_period = get_dashboard_greeting_period(timezone.localtime(greeting_time_source))

    context = {
        "active_peminjaman": active_peminjaman,
        "dashboard_stats": {
            "completed_count": completed_count,
            "ongoing_count": ongoing_count,
            "total_count": completed_count + ongoing_count,
        },
        "tim_chart": tim_chart,
        "layanan_chart": layanan_chart,
        "pengukuran_chart": pengukuran_chart,
        "approved_peminjaman_chart": approved_peminjaman_chart,
        "survei_chart": survei_chart,
        "instansi_chart": instansi_chart,
        "month_choices": [
            {"value": month_number, "label": month_label}
            for month_number, month_label in MONTH_LABELS_ID.items()
        ],
        "dashboard_greeting_name": greeting_name,
        "dashboard_greeting_period": greeting_period,
        "display_generated_at": now,
    }
    return context


@login_required
def index(request):
    return render(request, "dashboard/index.html", build_dashboard_context(request))


def display(request, portal_slug):
    if portal_slug != settings.DASHBOARD_TV_SLUG:
        raise Http404("Halaman display tidak ditemukan.")

    context = build_dashboard_context(active_limit=8)
    context["tv_slug"] = portal_slug
    return render(request, "dashboard/display.html", context)


def display_active_data(request, portal_slug):
    if portal_slug != settings.DASHBOARD_TV_SLUG:
        raise Http404("Data display tidak ditemukan.")

    active_peminjaman = get_active_peminjaman_queryset()[:8]
    html = render_to_string(
        "dashboard/partials/display_active_rows.html",
        {"active_peminjaman": active_peminjaman},
        request=request,
    )
    response = JsonResponse({
        "html": html,
        "updatedAt": timezone.localtime().isoformat(),
    })
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response
