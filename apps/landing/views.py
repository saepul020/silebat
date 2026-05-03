from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.list_pagination import paginate_list
from apps.core.permissions import is_super_admin, user_passes_access

from .forms import LandingPeralatanCardForm
from .models import LandingPeralatanCard
from .services import get_public_landing_context


landing_manage_required = user_passes_access(
    is_super_admin,
    'Pengaturan landing page hanya dapat diakses oleh Super Admin.',
)


def public_home(request):
    return render(request, "landing/index.html", get_public_landing_context())


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
    queryset = LandingPeralatanCard.objects.order_by("urutan", "nama_barang", "id")
    pagination_context = paginate_list(request, queryset)
    context = {
        **pagination_context,
        "page_title": "Konten Peralatan Landing Page",
        "page_subtitle": "Kelola informasi peralatan laboratorium yang ditampilkan pada halaman landing page public.",
    }
    return render(request, "landing/manage_equipment_list.html", context)


@login_required
@landing_manage_required
def equipment_create(request):
    form = LandingPeralatanCardForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Konten peralatan landing page berhasil ditambahkan.")
        return redirect("landing:equipment_list")

    return render(
        request,
        "landing/manage_equipment_form.html",
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
    card = get_object_or_404(LandingPeralatanCard, pk=pk)
    form = LandingPeralatanCardForm(request.POST or None, request.FILES or None, instance=card)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Konten peralatan landing page berhasil diperbarui.")
        return redirect("landing:equipment_list")

    return render(
        request,
        "landing/manage_equipment_form.html",
        {
            "form": form,
            "page_title": "Edit Konten Peralatan Landing Page",
            "page_subtitle": "Perbarui data peralatan yang tampil pada landing page public.",
            "submit_label": "Simpan Perubahan",
        },
    )


@login_required
@landing_manage_required
def equipment_delete(request, pk):
    card = get_object_or_404(LandingPeralatanCard, pk=pk)
    if request.method == "POST":
        card.delete()
        messages.success(request, "Konten peralatan landing page berhasil dihapus.")
    return redirect("landing:equipment_list")
