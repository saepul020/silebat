from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.list_pagination import paginate_list
from apps.core.permissions import is_super_admin
from .forms import PendidikanForm
from .models import Pendidikan


def _pendidikan(user):
    queryset = Pendidikan.objects.select_related('user')
    return queryset if is_super_admin(user) else queryset.filter(user=user)


def _pendidikan_obj(request, pk):
    queryset = _pendidikan(request.user)
    if request.method == 'POST':
        queryset = queryset.select_for_update(of=('self',))
    return get_object_or_404(queryset, pk=pk)


@login_required
def daftar(request, import_context=None):
    context = paginate_list(request, _pendidikan(request.user), search_fields=(
        'tingkat', 'lembaga', 'jurusan', 'user__first_name', 'user__username',
    ))
    context['can_view_all'] = is_super_admin(request.user)
    context['import_context'] = import_context or {}
    return render(request, 'pengguna/pendidikan_list.html', context)


@login_required
@transaction.atomic
def form(request, pk=None):
    obj = _pendidikan_obj(request, pk) if pk is not None else None
    bound = PendidikanForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None, instance=obj,
    )
    if request.method == 'POST' and bound.is_valid():
        saved = bound.save(commit=False)
        if obj is None:
            saved.user = request.user
        saved.save()
        messages.success(request, 'Data pendidikan berhasil disimpan.')
        return redirect('pengguna:pendidikan_daftar')
    return render(request, 'pengguna/pendidikan_form.html', {
        'form': bound, 'obj': obj, 'page_title': 'Edit Pendidikan' if obj else 'Tambah Pendidikan',
    })


@login_required
@transaction.atomic
def hapus(request, pk):
    obj = _pendidikan_obj(request, pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Data pendidikan berhasil dihapus.')
        return redirect('pengguna:pendidikan_daftar')
    return render(request, 'pengguna/pendidikan_hapus.html', {'obj': obj})


@login_required
def dokumen(request, pk, jenis):
    if jenis not in ('ijazah', 'transkrip'):
        raise Http404
    obj = get_object_or_404(_pendidikan(request.user), pk=pk)
    field = getattr(obj, jenis)
    if not field:
        raise Http404('Dokumen belum tersedia.')
    try:
        file = field.open('rb')
    except FileNotFoundError:
        raise Http404('Dokumen tidak ditemukan.')
    return FileResponse(file, as_attachment=True)
