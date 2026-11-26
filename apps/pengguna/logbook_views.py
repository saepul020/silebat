from pathlib import Path

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.list_pagination import paginate_list
from apps.core.permissions import is_super_admin
from .forms import LogbookForm, LogbookPesertaSet
from .logbook_images import IMAGE_EXTENSIONS, preview_image
from .models import Logbook


def _logbook(user):
    queryset = Logbook.objects.select_related('user').prefetch_related('peserta__user')
    return queryset if is_super_admin(user) else queryset.filter(peserta__user=user)


def _obj(request, pk):
    queryset = _logbook(request.user)
    if request.method == 'POST':
        queryset = queryset.select_for_update(of=('self',))
    return get_object_or_404(queryset, pk=pk)


def _preview_url(obj):
    if obj and obj.dokumen and Path(obj.dokumen.name).suffix.lower().lstrip('.') in IMAGE_EXTENSIONS:
        return reverse('pengguna:logbook_preview', args=[obj.pk])
    return ''


@login_required
def daftar(request, import_context=None):
    context = paginate_list(request, _logbook(request.user), search_fields=(
        'uraian', 'user__username', 'user__first_name',
    ))
    context['can_view_all'] = is_super_admin(request.user)
    context['import_context'] = import_context or {}
    for item in context['items']:
        item.preview_url = _preview_url(item)
    return render(request, 'pengguna/logbook_list.html', context)


@login_required
@transaction.atomic
def form(request, pk=None):
    obj = _obj(request, pk) if pk is not None else None
    data = request.POST if request.method == 'POST' else None
    files = request.FILES if request.method == 'POST' else None
    bound = LogbookForm(data, files, instance=obj)
    peserta = LogbookPesertaSet(data, files, actor=request.user, kegiatan=obj)
    if request.method == 'POST':
        valid = bound.is_valid()
        if peserta.is_valid() and valid:
            saved = bound.save(commit=False)
            if obj is None:
                saved.user = request.user
            saved.save()
            peserta.save(saved)
            messages.success(request, 'Logbook harian berhasil disimpan.')
            return redirect('pengguna:logbook_daftar')
    return render(request, 'pengguna/logbook_form.html', {
        'form': bound, 'peserta': peserta, 'obj': obj,
        'page_title': 'Edit Logbook Harian' if obj else 'Tambah Logbook Harian',
        'preview_url': _preview_url(obj),
    })


@login_required
@transaction.atomic
def hapus(request, pk):
    obj = _obj(request, pk)
    if request.method == 'POST':
        if is_super_admin(request.user):
            obj.delete()
        else:
            obj.peserta.get(user=request.user).delete()
            if not obj.peserta.filter().exists():
                obj.delete()
        messages.success(request, 'Data logbook harian Anda berhasil dihapus.')
        return redirect('pengguna:logbook_daftar')
    return render(request, 'pengguna/logbook_hapus.html', {
        'obj': obj, 'can_view_all': is_super_admin(request.user),
    })


@login_required
def dokumen(request, pk):
    obj = _obj(request, pk)
    if not obj.dokumen:
        raise Http404('Dokumentasi belum tersedia.')
    try:
        file = obj.dokumen.open('rb')
    except FileNotFoundError:
        raise Http404('Dokumentasi tidak ditemukan.')
    return FileResponse(file, as_attachment=True)


def _preview(file):
    response = HttpResponse(preview_image(file), content_type='image/jpeg')
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_POST
def preview_upload(request):
    try:
        file = forms.FileField().clean(request.FILES.get('dokumen'))
        return _preview(file)
    except forms.ValidationError as error:
        return JsonResponse({'error': error.messages[0]}, status=400)


@login_required
def preview(request, pk):
    obj = _obj(request, pk)
    if not obj.dokumen:
        raise Http404('Dokumentasi belum tersedia.')
    try:
        with obj.dokumen.open('rb') as file:
            return _preview(file)
    except (FileNotFoundError, forms.ValidationError):
        raise Http404('Preview dokumentasi tidak tersedia.')
