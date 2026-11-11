from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.list_pagination import paginate_list
from apps.core.navigation import get_next_url, redirect_next
from apps.core.permissions import is_super_admin, user_passes_access

from .forms import DokumentasiTVForm, KontenAlatTVForm, LandingPeralatanCardForm
from .models import LandingPeralatanCard, SlideDokumentasi
from .services import get_public_landing_context, invalidate_public_landing_cache


landing_manage_required = user_passes_access(
    is_super_admin,
    'Pengaturan konten hanya dapat diakses oleh Super Admin.',
)
EQUIPMENT_LIST_SEARCH_FIELDS = (
    "kategori_barang",
    "nama_barang",
    "jenis_barang",
    "merek_tipe_alat",
    "fungsi_alat",
    "metode_pengukuran",
    "spesifikasi_alat",
    "ringkasan_alat",
)


@login_required
@landing_manage_required
@require_http_methods(["GET", "POST"])
def dokumentasi_tv(request):
    if request.method == "POST" and request.POST.get("action") == "tambah":
        slide = SlideDokumentasi.objects.create()
        messages.success(request, "Slide dokumentasi baru berhasil ditambahkan.")
        return redirect(f"{reverse('landing:dokumentasi_tv')}#slide-{slide.pk}")
    if request.method == "POST" and request.POST.get("action", "simpan") != "simpan":
        return HttpResponseBadRequest("Aksi dokumentasi tidak valid.")
    target = None
    if request.method == "POST":
        raw_id = request.POST.get("slide_id", "")
        if not raw_id.isdecimal() or len(raw_id) > 19 or not 0 < int(raw_id) <= 9223372036854775807:
            return HttpResponseBadRequest("Slide dokumentasi tidak valid.")
        target = int(raw_id)
    slides = []
    bound = None
    for nomor, slide in enumerate(SlideDokumentasi.objects.prefetch_related("fotos"), start=1):
        form = DokumentasiTVForm(
            request.POST if target == slide.pk else None,
            request.FILES if target == slide.pk else None,
            slide=slide, prefix=f"slide-{slide.pk}",
        )
        slides.append({"slide": slide, "form": form, "nomor": nomor})
        if target == slide.pk:
            bound = form
    if target is not None and bound is None:
        raise Http404("Slide dokumentasi tidak ditemukan.")
    if bound and bound.is_valid():
        bound.save()
        messages.success(request, "Dokumentasi kegiatan TV berhasil disimpan.")
        return redirect(f"{reverse('landing:dokumentasi_tv')}#slide-{target}")
    return render(request, "landing/dokumentasi_tv.html", {"slides": slides})


@login_required
@landing_manage_required
@require_POST
def dokumentasi_delete(request, pk):
    slide = get_object_or_404(SlideDokumentasi, pk=pk)
    nomor = SlideDokumentasi.objects.filter(pk__lte=slide.pk).count()
    slide.delete()
    messages.success(request, f"Slide {nomor} dokumentasi berhasil dihapus.")
    return redirect("landing:dokumentasi_tv")


@login_required
@landing_manage_required
@require_http_methods(["GET", "POST"])
def konten_tv(request):
    form = KontenAlatTVForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Konten alat TV berhasil disimpan.")
        return redirect("landing:konten_tv")
    return render(request, "landing/konten_tv.html", {"form": form})


def public_home(request):
    context = {
        **get_public_landing_context(),
        "canonical_url": request.build_absolute_uri(request.path),
        "social_image_url": request.build_absolute_uri(static("assets/img/kegiatan-desktop.webp")),
    }
    return render(request, "landing/index.html", context)


def robots_txt(request):
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    content = f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    homepage_url = request.build_absolute_uri("/")
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{homepage_url}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>\n"
        "</urlset>\n"
    )
    return HttpResponse(content, content_type="application/xml; charset=utf-8")


@login_required
@landing_manage_required
def equipment_order_check(request):
    raw_urutan = str(request.GET.get("urutan", "")).strip()
    raw_exclude_pk = str(request.GET.get("exclude_pk", "")).strip()

    if not raw_urutan:
        return JsonResponse({"is_used": False, "message": ""})

    try:
        urutan = int(raw_urutan)
    except (TypeError, ValueError):
        return JsonResponse({"is_used": False, "message": ""})

    if urutan < 1:
        return JsonResponse({"is_used": False, "message": ""})

    queryset = LandingPeralatanCard.objects.filter(urutan=urutan)
    if raw_exclude_pk.isdigit():
        queryset = queryset.exclude(pk=int(raw_exclude_pk))

    is_used = queryset.exists()
    return JsonResponse({
        "is_used": is_used,
        "message": "Urutan tampil sudah digunakan oleh konten lain." if is_used else "",
    })


@login_required
@landing_manage_required
def equipment_list(request):
    queryset = LandingPeralatanCard.objects.prefetch_related("fotos").order_by(
        "urutan", "nama_barang", "id"
    )
    pagination_context = paginate_list(
        request,
        queryset,
        search_fields=EQUIPMENT_LIST_SEARCH_FIELDS,
    )
    context = {
        **pagination_context,
        "page_title": "Konten Peralatan Landing Page",
        "page_subtitle": "Kelola informasi peralatan laboratorium yang ditampilkan pada halaman landing page public.",
    }
    return render(request, "landing/peralatan_list.html", context)


@login_required
@landing_manage_required
def equipment_create(request):
    form = LandingPeralatanCardForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        invalidate_public_landing_cache()
        messages.success(request, "Konten peralatan landing page berhasil ditambahkan.")
        return redirect("landing:equipment_list")

    return render(
        request,
        "landing/peralatan_form.html",
        {
            "form": form,
            "page_title": "Tambah Konten Peralatan Landing Page",
            "page_subtitle": "Isi data peralatan yang akan tampil pada section Peralatan Survei di landing page public.",
            "submit_label": "Simpan Konten",
        },
    )


@login_required
@landing_manage_required
def equipment_update(request, pk):
    card = get_object_or_404(LandingPeralatanCard.objects.prefetch_related("fotos"), pk=pk)
    form = LandingPeralatanCardForm(request.POST or None, request.FILES or None, instance=card)
    if request.method == "POST" and form.is_valid():
        form.save()
        invalidate_public_landing_cache()
        messages.success(request, "Konten peralatan landing page berhasil diperbarui.")
        return redirect_next(request, "landing:equipment_list")

    return render(
        request,
        "landing/peralatan_form.html",
        {
            "form": form,
            "page_title": "Edit Konten Peralatan Landing Page",
            "page_subtitle": "Perbarui data peralatan yang tampil pada landing page public.",
            "submit_label": "Simpan Perubahan",
            "next_url": get_next_url(request),
        },
    )


@login_required
@landing_manage_required
def equipment_delete(request, pk):
    card = get_object_or_404(LandingPeralatanCard, pk=pk)
    if request.method == "POST":
        card.delete()
        invalidate_public_landing_cache()
        messages.success(request, "Konten peralatan landing page berhasil dihapus.")
    return redirect("landing:equipment_list")
