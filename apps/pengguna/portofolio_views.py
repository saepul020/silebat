from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.list_pagination import paginate_list
from apps.core.permissions import is_super_admin
from .forms import PortofolioForm
from .models import Portofolio


def _portofolio(user):
    queryset = Portofolio.objects.select_related('user')
    return queryset if is_super_admin(user) else queryset.filter(user=user)


def _portofolio_obj(request, pk):
    queryset = _portofolio(request.user)
    if request.method == 'POST':
        queryset = queryset.select_for_update(of=('self',))
    return get_object_or_404(queryset, pk=pk)


@login_required
def daftar(request, import_context=None):
    context = paginate_list(request, _portofolio(request.user), search_fields=(
        'nama', 'lokasi', 'uraian', 'nomor_dokumen', 'user__first_name', 'user__username',
    ))
    context['can_view_all'] = is_super_admin(request.user)
    context['import_context'] = import_context or {}
    return render(request, 'pengguna/portofolio_list.html', context)


@login_required
@transaction.atomic
def form(request, pk=None):
    obj = _portofolio_obj(request, pk) if pk is not None else None
    bound = PortofolioForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None, instance=obj,
    )
    if request.method == 'POST' and bound.is_valid():
        saved = bound.save(commit=False)
        if obj is None:
            saved.user = request.user
        saved.save()
        messages.success(request, 'Portofolio proyek & kegiatan berhasil disimpan.')
        return redirect('pengguna:portofolio_daftar')
    return render(request, 'pengguna/portofolio_form.html', {
        'form': bound, 'obj': obj, 'page_title': 'Edit Portofolio Proyek & Kegiatan' if obj else 'Tambah Portofolio Proyek & Kegiatan',
        'doc_route': 'pengguna:portofolio_dokumen',
    })


@login_required
@transaction.atomic
def hapus(request, pk):
    obj = _portofolio_obj(request, pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Portofolio proyek & kegiatan berhasil dihapus.')
        return redirect('pengguna:portofolio_daftar')
    return render(request, 'pengguna/portofolio_hapus.html', {'obj': obj})


@login_required
def dokumen(request, pk, jenis):
    if jenis != 'dokumen':
        raise Http404
    obj = get_object_or_404(_portofolio(request.user), pk=pk)
    if not obj.dokumen:
        raise Http404('Dokumen belum tersedia.')
    try:
        file = obj.dokumen.open('rb')
    except FileNotFoundError:
        raise Http404('Dokumen tidak ditemukan.')
    return FileResponse(file, as_attachment=True)
