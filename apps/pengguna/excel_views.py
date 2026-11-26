from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.core.excel_utils import build_excel_response, build_import_template
from apps.core.import_utils import (
    json_response_or_none, load_import_worksheet, string_cell,
)
from apps.core.permissions import is_super_admin
from apps.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from .excel_data import EXCEL_DATA, excel_headers
from .models import User, get_sdm_users


def _config(kind):
    try:
        return EXCEL_DATA[kind]
    except KeyError as exc:
        raise Http404 from exc


def _queryset(kind, user):
    from . import karir_views, logbook_views, pendidikan_views, portofolio_views, views
    queries = {
        'pelatihan': views._get_pelatihan_queryset_for_user,
        'pendidikan': pendidikan_views._pendidikan, 'karir': karir_views._karir,
        'portofolio': portofolio_views._portofolio, 'logbook': logbook_views._logbook,
    }
    return queries[kind](user)


def _excel_value(value):
    if isinstance(value, list):
        value = '\n'.join(str(item) for item in value)
    if isinstance(value, bool):
        return 'Ya' if value else 'Tidak'
    # Keep text beginning with '=' as text in downloaded workbooks.
    if isinstance(value, str) and value.startswith('='):
        return "'" + value
    return value


@login_required
@require_GET
def export(request, kind):
    config = _config(kind)
    queryset = _queryset(kind, request.user)
    if config.get('participants'):
        queryset = queryset.prefetch_related('peserta__user')
    extra = [name for name, field in config['form'].base_fields.items()
             if isinstance(field, forms.FileField) or name == 'nomor_dokumen']
    rows = []
    for obj in queryset:
        row = [obj.user.username if obj.user else '']
        row.extend(_excel_value(getattr(obj, name)) for name in config['fields'])
        if config.get('participants'):
            row.append('; '.join(item.user.username for item in obj.peserta.all()))
        row.extend(_excel_value(str(getattr(obj, name) or '')) for name in extra)
        if config.get('certificate'):
            row.append('; '.join(
                f'{item.user.username}: {item.file_sertifikat.name}'
                for item in obj.peserta.all() if item.file_sertifikat
            ))
        rows.append(row)
    headers = excel_headers(config) + [config['form'].base_fields[name].label for name in extra]
    if config.get('certificate'):
        headers.append('Sertifikat Peserta')
    return build_excel_response(f'export_{kind}.xlsx', [{
        'title': kind.title(), 'headers': headers, 'rows': rows,
    }])


@login_required
@require_GET
def format_import(request, kind):
    config = _config(kind)
    admin = is_super_admin(request.user)
    owners = User.objects.all() if admin else User.objects.filter(pk=request.user.pk)
    users = list(owners.order_by('username').values_list('username', flat=True))
    participants = list(get_sdm_users().values_list('username', flat=True))
    sample = [users[0] if users else 'username_pengguna', *config['sample']]
    references = [('Username Pengguna', users)]
    if config.get('participants'):
        sample.append((participants[0] if participants else 'username_peserta') if admin else request.user.username)
        references.append(('Username Peserta (pisahkan dengan ;)', participants))
    form = config['form']()
    validations = {}
    for name in config['fields']:
        field = form.fields[name]
        choices = getattr(field, 'choices', ())
        if choices:
            values = [str(value) for value, _ in choices if value != '']
            references.append((field.label, values))
            if len(','.join(values)) <= 250:
                validations[field.label] = values
    if 'masih_bekerja' in config['fields']:
        validations[form.fields['masih_bekerja'].label] = ['Ya', 'Tidak']
    references.append(('Petunjuk', [
        'Tanggal: YYYY-MM-DD atau dd Mon yyyy. Masih Bekerja: Ya / Tidak.',
        'Pisahkan poin uraian dengan baris baru; pisahkan username peserta dengan titik koma (;).',
        'Data duplikat diperbolehkan; setiap baris akan dibuat sebagai data baru.',
        'Lampiran dan nomor dokumen dilengkapi melalui Edit Data setelah impor.',
        'Selain Super Admin, impor hanya untuk diri sendiri dan penginput wajib menjadi peserta kegiatan.',
    ]))
    return build_import_template(
        headers=excel_headers(config), sample=sample, references=references,
        validations=validations, worksheet_title=kind.title(), filename=f'format_import_{kind}.xlsx',
    )


def _read_rows(file, config):
    headers = excel_headers(config)
    worksheet, columns, aliases, errors = load_import_worksheet(
        file, headers, headers, max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
    )
    if errors:
        return [], errors
    rows = []
    try:
        for line, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            values = [string_cell(row[columns[aliases[header]]], date_to_iso=True)
                      if columns[aliases[header]] < len(row) else '' for header in headers]
            if not any(values):
                continue
            rows.append({'line': line, 'values': values})
            if len(rows) > 5000:
                return [], ['Maksimal 5000 baris data dalam satu kali import.']
    finally:
        worksheet.parent.close()
    if not rows:
        errors.append('File Excel tidak memiliki data untuk diimport.')
    return rows, errors


def _prepare_rows(rows, config, actor):
    """Validate again on save; repeated records are intentionally accepted."""
    users = dict(User.objects.values_list('username', 'pk'))
    admin = is_super_admin(actor)
    eligible = set(get_sdm_users().values_list('username', flat=True)) if config.get('participants') else set()
    ready, errors = [], []
    for row in rows:
        line, values = row['line'], row['values']
        username = values[0] or (actor.username if not admin else '')
        owner = users.get(username)
        if not admin and owner != actor.pk:
            errors.append(f'Baris {line}: Anda hanya dapat mengimpor data atas nama sendiri.')
            continue
        if owner is None:
            errors.append(f'Baris {line}: Username Pengguna wajib diisi dan harus terdaftar.')
            continue
        data = dict(zip(config['fields'], values[1:]))
        if 'masih_bekerja' in data:
            working = data['masih_bekerja'].lower()
            if working not in ('', 'ya', 'tidak', 'true', 'false', '1', '0'):
                errors.append(f'Baris {line}: Masih Bekerja harus Ya atau Tidak.')
                continue
            data['masih_bekerja'] = working in ('ya', 'true', '1')
        if config.get('points'):
            data['uraian'] = data['uraian'].splitlines()
        form = config['form'](data=data)
        # Excel imports contain tabular data; uploads remain required in the normal forms.
        for field in form.fields.values():
            if isinstance(field, forms.FileField):
                field.required = False
        valid = form.is_valid()
        for field, details in form.errors.items():
            label = form.fields[field].label if field in form.fields else 'Data'
            errors.extend(f'Baris {line}: {label}: {detail}' for detail in details)
        participants = []
        if config.get('participants'):
            names = list(dict.fromkeys(name.strip() for name in values[-1].split(';') if name.strip()))
            if not names and not admin:
                names = [actor.username]
            if not names or any(name not in eligible for name in names):
                errors.append(f'Baris {line}: Username Peserta wajib diisi dengan pengguna SDM terdaftar (pisahkan dengan ;).')
                valid = False
            else:
                participants = [users[name] for name in names]
                if not admin and actor.pk not in participants:
                    errors.append(f'Baris {line}: Penginput wajib menjadi peserta kegiatan.')
                    valid = False
        if valid:
            obj = form.save(commit=False)
            obj.user_id = owner
            ready.append((obj, participants))
    return ready, errors


def _reply(request, kind, payload, status=200):
    response = json_response_or_none(request, payload, status=status)
    if response is not None:
        return response
    if payload.get('saved') or payload.get('cancelled'):
        if payload.get('saved'):
            messages.success(request, payload['message'])
        return redirect(f'pengguna:{kind}_daftar')
    from . import karir_views, logbook_views, pendidikan_views, portofolio_views, views
    listing = {
        'pelatihan': views.daftar_pelatihan, 'pendidikan': pendidikan_views.daftar,
        'karir': karir_views.daftar, 'portofolio': portofolio_views.daftar, 'logbook': logbook_views.daftar,
    }[kind]
    return listing(request, import_context={'show_modal': True, **payload})


@login_required
@require_POST
def import_data(request, kind):
    config = _config(kind)
    key = f'sdm_import_{kind}_{request.user.pk}'
    action = request.POST.get('import_action')
    if action == 'cancel':
        request.session.pop(key, None)
        return _reply(request, kind, {'ok': True, 'cancelled': True})
    if action == 'validate':
        request.session.pop(key, None)
        rows, errors = _read_rows(request.FILES.get('file_import'), config)
        if not errors:
            _, errors = _prepare_rows(rows, config, request.user)
        if not errors:
            request.session[key] = rows
        return _reply(request, kind, {
            'ok': not errors, 'validated': not errors, 'can_save': bool(rows) and not errors,
            'total_rows': len(rows), 'errors': errors,
            'message': f'Validasi berhasil. {len(rows)} data siap disimpan.' if not errors else 'Validasi belum berhasil.',
        })
    if action == 'save':
        rows = request.session.pop(key, None)
        errors = []
        if not rows:
            errors = ['Data validasi tidak ditemukan. Lakukan Validasi Data terlebih dahulu.']
        else:
            try:
                with transaction.atomic():
                    ready, errors = _prepare_rows(rows, config, request.user)
                    if not errors:
                        for obj, participants in ready:
                            obj.save()
                            if config.get('participants'):
                                relation = config['relation']
                                config['participants'].objects.bulk_create([
                                    config['participants'](**{relation: obj, 'user_id': user_id})
                                    for user_id in participants
                                ])
            except IntegrityError:
                errors = ['Data relasi berubah selama penyimpanan. Lakukan Validasi Data kembali.']
        success = not errors
        return _reply(request, kind, {
            'ok': success, 'saved': success, 'can_save': False, 'errors': errors,
            'total_rows': len(rows) if success else 0,
            'message': f'{len(rows)} data berhasil diimport.' if success else 'Data belum dapat disimpan.',
            'redirect_url': reverse(f'pengguna:{kind}_daftar'),
        })
    return _reply(request, kind, {
        'ok': False, 'can_save': False, 'errors': ['Aksi import tidak dikenali.'],
    }, status=400)
