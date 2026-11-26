from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone, translation
from django.utils.formats import date_format
from PIL import Image as PilImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, Image, KeepTogether, LongTable, PageTemplate, Paragraph, Spacer, TableStyle

from .models import Pelatihan, UserProfile
from .drh_data import get_drh_data


LEFT, RIGHT, TOP, BOTTOM = 25 * mm, 15 * mm, 20 * mm, 15 * mm
WIDTH = A4[0] - LEFT - RIGHT
PHOTO_WIDTH = 38 * mm
PHOTO_PADDING = 2 * mm
NAVY = colors.HexColor('#24364b')
STYLES = {
    'body': ParagraphStyle('DrhBody', fontName='Arial', fontSize=11, leading=15, spaceAfter=0),
    'justify': ParagraphStyle('DrhJustify', fontName='Arial', fontSize=11, leading=15, alignment=TA_JUSTIFY),
    'title': ParagraphStyle('DrhTitle', fontName='Arial-Bold', fontSize=16, leading=21,
                            textColor=NAVY, alignment=TA_CENTER, spaceAfter=7 * mm),
    'section': ParagraphStyle('DrhSection', fontName='Arial-Bold', fontSize=12, leading=16,
                              textColor=NAVY, spaceBefore=5 * mm, spaceAfter=3 * mm, keepWithNext=True),
    'label': ParagraphStyle('DrhLabel', fontName='Arial-Bold', fontSize=11, leading=15),
    'head': ParagraphStyle('DrhHead', fontName='Arial-Bold', fontSize=11, leading=15,
                           textColor=colors.white, alignment=TA_CENTER),
    'entry': ParagraphStyle('DrhEntry', fontName='Arial-Bold', fontSize=11, leading=15,
                            spaceBefore=3 * mm, spaceAfter=1 * mm, keepWithNext=True),
    'point': ParagraphStyle('DrhPoint', fontName='Arial', fontSize=11, leading=15, alignment=TA_JUSTIFY,
                            bulletFontName='Arial', leftIndent=10, bulletIndent=0, spaceAfter=3),
    'center': ParagraphStyle('DrhCenter', fontName='Arial', fontSize=11, leading=15, alignment=TA_CENTER),
    'sign': ParagraphStyle('DrhSign', fontName='Arial', fontSize=11, leading=15,
                           leftIndent=WIDTH - 75 * mm, alignment=TA_CENTER),
    'sign_name': ParagraphStyle('DrhSignName', fontName='Arial-Bold', fontSize=11, leading=15,
                                leftIndent=WIDTH - 75 * mm, alignment=TA_CENTER),
}


def _fonts():
    if {'Arial', 'Arial-Bold'} <= set(pdfmetrics.getRegisteredFontNames()):
        return
    roots = [Path(settings.DRH_FONT_DIR)] if settings.DRH_FONT_DIR else [
        Path('C:/Windows/Fonts'), Path('/usr/share/fonts/truetype/msttcorefonts'),
        Path('/usr/local/share/fonts'),
    ]
    for root in roots:
        if not root.is_dir():
            continue
        files = {file.name.lower(): file for file in root.iterdir() if file.is_file()}
        regular = files.get('arial.ttf')
        bold = files.get('arialbd.ttf') or files.get('arial_bold.ttf')
        if regular and bold:
            pdfmetrics.registerFont(TTFont('Arial', str(regular)))
            pdfmetrics.registerFont(TTFont('Arial-Bold', str(bold)))
            pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold')
            return
    raise ImproperlyConfigured('Font Arial belum tersedia. Atur DRH_FONT_DIR ke direktori arial.ttf dan arialbd.ttf.')


def _text(value, style='body'):
    value = str(value) if value not in (None, '') else '-'
    return Paragraph(escape(value).replace('\n', '<br/>'), STYLES[style])


def _date(value):
    return date_format(value, 'd M Y') if value else '-'


def _points(values):
    return [Paragraph(escape(str(value).strip()), STYLES['point'], bulletText='\u2022')
            for value in values if str(value).strip()] or [_text('-')]


def _table(headers, rows, weights, spans=(), center=(), justify=()):
    widths = [WIDTH * weight / sum(weights) for weight in weights]
    data = [[_text(header, 'head') for header in headers]]
    data.extend([
        [cell if isinstance(cell, (list, Flowable)) else _text(
            cell, 'center' if index in center else 'justify' if index in justify else 'body',
        ) for index, cell in enumerate(row)] for row in rows
    ])
    return LongTable(data, colWidths=widths, repeatRows=1, splitInRow=1, hAlign='LEFT', style=TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f6f9')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#d7dfe7')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        *[('SPAN', start, end) for start, end in spans],
    ]))


def _photo(field):
    if field:
        try:
            with field.open('rb') as source, PilImage.open(source) as original:
                picture = ImageOps.exif_transpose(original)
                picture.thumbnail((600, 800))
                rgba = picture.convert('RGBA')
                white = PilImage.new('RGB', rgba.size, 'white')
                white.paste(rgba, mask=rgba.getchannel('A'))
                buffer = BytesIO()
                white.save(buffer, format='PNG')
                buffer.seek(0)
                width = PHOTO_WIDTH - 2 * PHOTO_PADDING
                return Image(buffer, width=width,
                             height=width * white.height / white.width, hAlign='CENTER')
        except (OSError, ValueError, PilImage.DecompressionBombError):
            pass
    return _text('Foto Profil\nbelum tersedia', 'center')


def _personal(user, profile):
    with translation.override('id'):
        birth = ', '.join(part for part in (
            getattr(profile, 'tempat_lahir', ''),
            date_format(profile.tanggal_lahir, 'd F Y') if profile and profile.tanggal_lahir else '',
        ) if part)
    rows = [
        ('Nama Lengkap', user.get_full_name() or user.username),
        ('NIP / NIK', user.nip), ('Tempat, Tanggal Lahir', birth),
        ('Jenis Kelamin', profile.get_jenis_kelamin_display() if profile else ''),
        ('Email', user.email), ('Nomor Handphone', user.no_hp),
        ('Jabatan', getattr(profile, 'jabatan', '')),
    ]
    data = [[_text(label, 'label'), value, ''] for label, value in rows]
    data[0][2] = _photo(getattr(profile, 'foto_profil', None))
    data.append([_text('Alamat', 'label'), getattr(profile, 'alamat', ''), ''])
    table = _table(
        ['Keterangan', 'Data Pribadi', 'Foto Profil'], data,
        [45 * mm, WIDTH - 45 * mm - PHOTO_WIDTH, PHOTO_WIDTH], spans=[((2, 1), (2, len(data)))],
    )
    table.setStyle(TableStyle([
        ('BACKGROUND', (2, 1), (2, len(data)), colors.white),
        ('ALIGN', (2, 1), (2, len(data)), 'CENTER'),
        ('VALIGN', (2, 1), (2, len(data)), 'MIDDLE'),
        ('LEFTPADDING', (2, 1), (2, len(data)), PHOTO_PADDING),
        ('RIGHTPADDING', (2, 1), (2, len(data)), PHOTO_PADDING),
        ('TOPPADDING', (2, 1), (2, len(data)), PHOTO_PADDING),
        ('BOTTOMPADDING', (2, 1), (2, len(data)), PHOTO_PADDING),
    ]))
    return [table]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#d7dfe7'))
    canvas.line(LEFT, BOTTOM - 5 * mm, A4[0] - RIGHT, BOTTOM - 5 * mm)
    canvas.setFont('Arial', 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(LEFT, BOTTOM - 10 * mm, 'DAFTAR RIWAYAT HIDUP')
    canvas.drawRightString(A4[0] - RIGHT, BOTTOM - 10 * mm, f'Halaman {doc.page}')
    canvas.restoreState()


def build_drh(target, user, bagian, *, lokasi='Bandung', tanggal=None):
    _fonts()
    profile = UserProfile.objects.filter(user=user).first()
    data = {key: list(rows) for key, rows in get_drh_data(user).items() if key in bagian}
    story = [_text('DAFTAR RIWAYAT HIDUP', 'title')]
    number = 0

    def heading(title):
        nonlocal number
        story.append(_text(f'{chr(65 + number)}. {title}', 'section'))
        number += 1

    heading('Data Pribadi')
    story.extend(_personal(user, profile))
    if data.get('pendidikan'):
        heading('Data Pendidikan')
        story.append(_table(
            ['Tingkat Pendidikan', 'Lokasi Pendidikan', 'Nama Lembaga Pendidikan', 'Jurusan', 'Tahun Lulus'],
            [[row.tingkat, row.lokasi, row.lembaga, row.jurusan, row.tanggal_lulus.year]
             for row in data['pendidikan']], [1.3, 1.1, 2.1, 1.5, .8], center=(4,),
        ))
    if data.get('karir'):
        rows = []
        for row in data['karir']:
            end = 'Sekarang' if row.masih_bekerja else str(row.tanggal_selesai.year) if row.tanggal_selesai else '-'
            rows.append([
                row.perusahaan, row.jabatan, row.get_status_display(),
                f'{row.tanggal_mulai.year} - {end}', _points(row.uraian_poin),
            ])
        heading('Riwayat Karir')
        story.append(_table(
            ['Nama Perusahaan / Instansi', 'Jabatan / Posisi', 'Status', 'Periode Bekerja', 'Uraian Pekerjaan'],
            rows, [1.5, 1.55, 1.1, 1.2, 2.75], center=(3,),
        ))
    if data.get('pelatihan'):
        heading('Data Pelatihan / Diklat / Workshop / Seminar')
        subnumber = 0
        for category, _ in Pelatihan.KATEGORI_CHOICES:
            trainings = [row for row in data['pelatihan'] if row.kategori_kegiatan == category]
            if not trainings:
                continue
            roman = ('I', 'II', 'III', 'IV')[subnumber]
            subnumber += 1
            story.extend([_text(f'{roman}. {category}', 'entry'), _table(
                ['Nama Kegiatan', 'Waktu Pelaksanaan', 'Lokasi Kegiatan'],
                [[row.nama_pelatihan, f'{_date(row.tanggal_mulai)} - {_date(row.tanggal_selesai)}', row.lokasi_pelatihan]
                 for row in trainings], [2.4, 1.8, 1.3],
                center=(1,), justify=(0,),
            )])
    if data.get('portofolio'):
        heading('Portofolio Proyek & Kegiatan')
        story.append(_table(
            ['Nama Proyek', 'Lokasi Proyek (Instansi / Daerah)', 'Uraian Tugas', 'Tahun Kegiatan'],
            [[row.nama, row.lokasi, _points(row.uraian), row.tahun] for row in data['portofolio']],
            [1.5, 1.4, 2.5, 1.1], center=(3,), justify=(0,),
        ))
    name = user.get_full_name() or user.username
    with translation.override('id'):
        downloaded = date_format(tanggal or timezone.localdate(), 'j F Y')
    story.append(KeepTogether([
        Spacer(1, 8 * mm), _text(f'{lokasi}, {downloaded}', 'sign'),
        _text('Hormat saya,', 'sign'), Spacer(1, 23 * mm),
        _text(name, 'sign_name'), _text(f'NIP / NIK: {user.nip or "-"}', 'sign'),
    ]))
    doc = BaseDocTemplate(target, pagesize=A4, rightMargin=RIGHT, leftMargin=LEFT,
                          topMargin=TOP, bottomMargin=BOTTOM, title='DAFTAR RIWAYAT HIDUP', author=name)
    frame = Frame(LEFT, BOTTOM, doc.width, doc.height,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='DRH', frames=[frame], onPage=_footer))
    doc.build(story)
