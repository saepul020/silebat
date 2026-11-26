from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.list_pagination import paginate_list
from apps.core.permissions import is_super_admin
from .forms import KarirForm
from .models import RiwayatKarir


def _karir(user):
    queryset = RiwayatKarir.objects.select_related('user')
    return queryset if is_super_admin(user) else queryset.filter(user=user)


def _karir_obj(request, pk):
    queryset = _karir(request.user)
    if request.method == 'POST':
        queryset = queryset.select_for_update(of=('self',))
    return get_object_or_404(queryset, pk=pk)


@login_required
def daftar(request, import_context=None):
    context = paginate_list(request, _karir(request.user), search_fields=(
        'perusahaan', 'jabatan', 'status', 'uraian', 'nomor_dokumen', 'user__first_name', 'user__username',
    ))
    context['can_view_all'] = is_super_admin(request.user)
    context['import_context'] = import_context or {}
    return render(request, 'pengguna/karir_list.html', context)


@login_required
@transaction.atomic
def form(request, pk=None):
    obj = _karir_obj(request, pk) if pk is not None else None
    bound = KarirForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None, instance=obj,
    )
    if request.method == 'POST' and bound.is_valid():
        saved = bound.save(commit=False)
        if obj is None:
            saved.user = request.user
        saved.save()
        messages.success(request, 'Riwayat karir berhasil disimpan.')
        return redirect('pengguna:karir_daftar')
    return render(request, 'pengguna/karir_form.html', {
        'form': bound, 'obj': obj, 'page_title': 'Edit Riwayat Karir' if obj else 'Tambah Riwayat Karir',
        'doc_route': 'pengguna:karir_dokumen',
    })


@login_required
@transaction.atomic
def hapus(request, pk):
    obj = _karir_obj(request, pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Riwayat karir berhasil dihapus.')
        return redirect('pengguna:karir_daftar')
    return render(request, 'pengguna/karir_hapus.html', {'obj': obj})


@login_required
def dokumen(request, pk, jenis):
    if jenis != 'dokumen':
        raise Http404
    obj = get_object_or_404(_karir(request.user), pk=pk)
    if not obj.dokumen:
        raise Http404('Dokumen belum tersedia.')
    try:
        file = obj.dokumen.open('rb')
    except FileNotFoundError:
        raise Http404('Dokumen tidak ditemukan.')
    return FileResponse(file, as_attachment=True)
