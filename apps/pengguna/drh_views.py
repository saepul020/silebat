from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest
from django.utils.text import slugify
from django.views.decorators.http import require_GET

from .drh_pdf import build_drh
from .forms import DrhForm


@login_required
@require_GET
def download(request):
    form = DrhForm(request.GET, user=request.user)
    if not form.is_valid():
        return HttpResponseBadRequest(
            ' '.join(f'{form.fields[key].label}: {" ".join(errors)}' for key, errors in form.errors.items()),
            content_type='text/plain; charset=utf-8',
        )
    output = BytesIO()
    try:
        build_drh(output, request.user, set(form.cleaned_data['bagian']),
                  lokasi=form.cleaned_data['lokasi'], tanggal=form.cleaned_data['tanggal'])
    except ImproperlyConfigured:
        return HttpResponse(
            'Font Arial untuk DRH belum tersedia pada server. Hubungi administrator.',
            status=503, content_type='text/plain; charset=utf-8',
        )
    output.seek(0)
    name = slugify(request.user.get_full_name() or request.user.username) or 'pengguna'
    response = FileResponse(output, as_attachment=True, filename=f'DRH-{name}.pdf')
    response['Cache-Control'] = 'private, no-store'
    return response
