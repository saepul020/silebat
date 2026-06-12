from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from apps.operasional.models import DataKopDokumen


PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 1.5 * cm
RIGHT_MARGIN = 1.5 * cm
TOP_MARGIN = 1.5 * cm
KOP_TOP_MARGIN = 1 * cm
BOTTOM_MARGIN = 1.5 * cm
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
SIGN_WIDTH = 65 * mm
SIGN_GAP = CONTENT_WIDTH - (2 * SIGN_WIDTH)
SIGN_COL_WIDTHS = [SIGN_WIDTH, SIGN_GAP, SIGN_WIDTH]
PAIR_SIGN_GAP = 30 * mm
PAIR_SIGN_WIDTH = (CONTENT_WIDTH - PAIR_SIGN_GAP) / 2
PAIR_SIGN_COL_WIDTHS = [PAIR_SIGN_WIDTH, PAIR_SIGN_GAP, PAIR_SIGN_WIDTH]


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PdfTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=3 * mm,
        ),
        "section": ParagraphStyle(
            "PdfSection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#17365D"),
            spaceBefore=2 * mm,
            spaceAfter=1.5 * mm,
        ),
        "body": ParagraphStyle(
            "PdfBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "PdfSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            alignment=TA_LEFT,
        ),
        "small_center": ParagraphStyle(
            "PdfSmallCenter",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            alignment=TA_CENTER,
        ),
        "tiny": ParagraphStyle(
            "PdfTiny",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=5.5,
            leading=6.5,
            alignment=TA_LEFT,
        ),
        "tiny_center": ParagraphStyle(
            "PdfTinyCenter",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=5.5,
            leading=6.5,
            alignment=TA_CENTER,
        ),
        "label": ParagraphStyle(
            "PdfLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
        ),
        "colon": ParagraphStyle(
            "PdfColon",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),
        "head": ParagraphStyle(
            "PdfHead",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8.5,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "tiny_head": ParagraphStyle(
            "PdfTinyHead",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=5.5,
            leading=6.5,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "sign": ParagraphStyle(
            "PdfSign",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=8.5,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "sign_center": ParagraphStyle(
            "PdfSignCenter",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=8.5,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "sign_name": ParagraphStyle(
            "PdfSignName",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=8.5,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "sign_heading": ParagraphStyle(
            "PdfSignHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.black,
            spaceBefore=2 * mm,
            spaceAfter=1.5 * mm,
        ),
        "sign_heading_center": ParagraphStyle(
            "PdfSignHeadingCenter",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceBefore=0,
            spaceAfter=1.5 * mm,
        ),
    }


STYLES = _styles()
CENTER_HEADERS = {
    "no",
    "status barang",
    "kode aset bmn",
    "kode laboratorium",
    "volume",
    "satuan",
    "kondisi barang",
    "tahun perolehan",
    "volume dipinjam",
    "dipinjam",
    "dikembalikan",
    "rusak",
    "hilang",
    "transfer",
    "sisa",
    "jumlah",
}


def text(value, style="body"):
    value = "-" if value in (None, "") else str(value)
    value = escape(value).replace("\n", "<br/>")
    return Paragraph(value, STYLES[style])


def section(title):
    return Paragraph(escape(title), STYLES["section"])


class InfoGrid(Flowable):
    label_pad = 1.5 * mm
    label_ratio = 0.45
    colon_width = 3 * mm
    row_gap = 1.5 * mm

    def __init__(self, left_rows, right_rows, gap=8 * mm):
        super().__init__()
        self.left_rows = left_rows
        self.right_rows = right_rows
        self.gap = gap
        self._cols = []

    def _column(self, rows, width):
        items = []
        height = 0
        label_style = STYLES["label"]
        label_width = min(
            max(
                (
                    stringWidth(str(label), label_style.fontName, label_style.fontSize)
                    for label, _ in rows
                ),
                default=0,
            )
            + self.label_pad,
            width * self.label_ratio,
        )
        value_width = max(width - label_width - self.colon_width, 1)
        for label, value in rows:
            label_part = text(label, "label")
            colon_part = text(":", "colon")
            value_part = text(value)
            _, label_height = label_part.wrap(label_width, PAGE_HEIGHT)
            _, colon_height = colon_part.wrap(self.colon_width, PAGE_HEIGHT)
            _, value_height = value_part.wrap(value_width, PAGE_HEIGHT)
            row_height = max(label_height, colon_height, value_height)
            items.append(
                (
                    label_part,
                    label_height,
                    colon_part,
                    colon_height,
                    value_part,
                    value_height,
                    row_height,
                )
            )
            height += row_height + self.row_gap
        return items, max(height - self.row_gap, 0), label_width

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        col_width = (avail_width - self.gap) / 2
        left, left_height, left_label_width = self._column(self.left_rows, col_width)
        right, right_height, right_label_width = self._column(self.right_rows, col_width)
        self._cols = [(left, left_label_width), (right, right_label_width)]
        self.height = max(left_height, right_height)
        return self.width, self.height

    def draw(self):
        col_width = (self.width - self.gap) / 2
        for col_index, (items, label_width) in enumerate(self._cols):
            x = col_index * (col_width + self.gap)
            y = self.height
            for (
                label,
                label_height,
                colon,
                colon_height,
                value,
                value_height,
                row_height,
            ) in items:
                row_bottom = y - row_height
                label.drawOn(self.canv, x, row_bottom + row_height - label_height)
                colon.drawOn(
                    self.canv,
                    x + label_width,
                    row_bottom + row_height - colon_height,
                )
                value.drawOn(
                    self.canv,
                    x + label_width + self.colon_width,
                    row_bottom + row_height - value_height,
                )
                y = row_bottom - self.row_gap


def title_block(title, left_rows, right_rows):
    return [
        Paragraph(escape(title), STYLES["title"]),
        InfoGrid(left_rows, right_rows),
        Spacer(1, 3 * mm),
    ]


def info_table(rows, valign="TOP"):
    data = [[text(label, "label"), text(value)] for label, value in rows]
    table = Table(data, colWidths=[38 * mm, CONTENT_WIDTH - (38 * mm)], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), valign),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF3F8")),
                ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#9AAFC2")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C3CED8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _header_key(value):
    return str(value or "").strip().casefold().rstrip(".")


def _table_value(value):
    if isinstance(value, (int, float, Decimal)) and value == 0:
        return "-"
    if isinstance(value, str):
        stripped = value.strip()
        try:
            if stripped and Decimal(stripped) == 0:
                return "-"
        except InvalidOperation:
            pass
    return value


def data_table(headers, rows, weights=None, valign="TOP"):
    if not rows:
        rows = [["-"] + [""] * (len(headers) - 1)]
    weights = weights or [1] * len(headers)
    total = sum(weights)
    widths = [CONTENT_WIDTH * weight / total for weight in weights]
    compact = len(headers) > 8
    head_style = "tiny_head" if compact else "head"
    cell_style = "tiny" if compact else "small"
    center_style = "tiny_center" if compact else "small_center"
    center_cols = {
        index for index, header in enumerate(headers) if _header_key(header) in CENTER_HEADERS
    }
    padding = 1.5 if compact else 3
    data = [
        [text(header, head_style) for header in headers],
        *[
            [
                text(_table_value(value), center_style if index in center_cols else cell_style)
                for index, value in enumerate(row)
            ]
            for row in rows
        ],
    ]
    table = Table(
        data,
        colWidths=widths,
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), valign),
                ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FB")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#758A9D")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB8C4")),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ]
        )
    )
    return table


def _file_path(field):
    if not field or not getattr(field, "name", ""):
        return None
    try:
        path = Path(field.path)
    except (NotImplementedError, ValueError):
        return None
    return path if path.exists() else None


def _kop_path():
    kop = DataKopDokumen.objects.only("kop_dokumen").order_by("id").first()
    return _file_path(kop.kop_dokumen) if kop else None


def _image(path, max_width, max_height):
    width, height = ImageReader(str(path)).getSize()
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def kop_story(path):
    if not path:
        return []
    try:
        image = _image(path, CONTENT_WIDTH, 38 * mm)
    except Exception:
        return []
    image.hAlign = "CENTER"
    return [image, Spacer(1, 3 * mm)]


def _photo_cells(files, max_width, max_height):
    cells = []
    for field in files:
        path = _file_path(field)
        if not path:
            continue
        try:
            image = _image(path, max_width, max_height)
            image.hAlign = "CENTER"
        except Exception:
            continue
        cells.append(image)
    return cells


def photo_cell(files, width, max_height=14 * mm):
    column_count = 3
    cells = _photo_cells(
        files,
        min((width / column_count) - (2 * mm), 30 * mm),
        max_height,
    )[:column_count]
    if not cells:
        return text("-", "small_center")

    cells.extend([""] * (column_count - len(cells)))
    return Table(
        [cells[:column_count]],
        colWidths=[width / column_count] * column_count,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        ),
    )


def photo_grid(files, header=None):
    column_count = 3
    cell_width = CONTENT_WIDTH / column_count
    cells = _photo_cells(files, 44 * mm, 18 * mm)

    if not cells:
        return []

    rows = []
    if header:
        rows.append([text(header, "head"), "", ""])
    for index in range(0, len(cells), column_count):
        row = cells[index:index + column_count]
        row.extend([""] * (column_count - len(row)))
        rows.append(row)

    styles = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#758A9D")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB8C4")),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]
    if header:
        styles.extend(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
            ]
        )

    table = Table(
        rows,
        colWidths=[cell_width] * column_count,
        hAlign="LEFT",
        style=TableStyle(styles),
    )
    return [table]


class SignName(Flowable):
    def __init__(self, value, centered=False):
        super().__init__()
        self.value = " ".join(str(value or "-").split()) or "-"
        self.style = STYLES["sign_name"]
        self.font_size = self.style.fontSize
        self.centered = centered
        if centered:
            self.hAlign = "CENTER"

    def wrap(self, avail_width, avail_height):
        text_width = stringWidth(self.value, self.style.fontName, self.style.fontSize)
        scale = min(1, avail_width / text_width) if text_width else 1
        self.font_size = self.style.fontSize * scale
        self.width = avail_width if self.centered else min(text_width, avail_width)
        self.height = self.style.leading * scale
        return self.width, self.height

    def draw(self):
        self.canv.setFont(self.style.fontName, self.font_size)
        y = max((self.height - self.font_size) / 2, 0)
        if self.centered:
            self.canv.drawCentredString(self.width / 2, y, self.value)
        else:
            self.canv.drawString(0, y, self.value)

    def getPlainText(self):
        return self.value


def _signature_cell(title, user, centered=False):
    full_name = (user.get_full_name() or user.username) if user else "-"
    nip = getattr(user, "nip", "") if user else ""
    sign_style = "sign_center" if centered else "sign"
    content = [text(title, sign_style), Spacer(1, 1 * mm)]
    signature = None
    if user is not None:
        try:
            signature = _file_path(user.safe_profile.ttd_digital)
        except Exception:
            signature = None
    if signature:
        try:
            image = _image(signature, 35 * mm, 16 * mm)
            image.hAlign = "CENTER" if centered else "LEFT"
            content.append(image)
        except Exception:
            content.append(Spacer(1, 16 * mm))
    else:
        content.append(Spacer(1, 16 * mm))
    content.extend(
        [
            Spacer(1, 0.8 * mm),
            SignName(full_name, centered=centered),
            text(f"NIP/NIK: {nip or '-'}", sign_style),
        ]
    )
    return content


def _sign_table(left, right):
    return Table(
        [[left, "", right]],
        colWidths=SIGN_COL_WIDTHS,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def _center_sign_table(content):
    side_width = (CONTENT_WIDTH - SIGN_WIDTH) / 2
    return Table(
        [["", content, ""]],
        colWidths=[side_width, SIGN_WIDTH, side_width],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def _paired_sign_table(left, right):
    return Table(
        [[left, "", right]],
        colWidths=PAIR_SIGN_COL_WIDTHS,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def signature_block(date_text, first_signers, knowing_signers):
    story = [
        Spacer(1, 4 * mm),
        _sign_table("", text(date_text, "sign")),
        Spacer(1, 1 * mm),
        _sign_table(
            _signature_cell(*first_signers[0]),
            _signature_cell(*first_signers[1]),
        ),
        Spacer(1, 3 * mm),
        Paragraph("Mengetahui:", STYLES["sign_heading"]),
        _sign_table(
            _signature_cell(*knowing_signers[0]),
            _signature_cell(*knowing_signers[1]),
        ),
    ]
    return [KeepTogether(story)]


def signature_list(date_text, signers, centered=False, approval_label=None):
    date = text(date_text, "sign_center" if centered else "sign")
    story = [
        Spacer(1, 4 * mm),
        _paired_sign_table("", date) if centered else _sign_table("", date),
        Spacer(1, 1 * mm),
    ]
    for index in range(0, len(signers), 2):
        pair = signers[index:index + 2]
        left = _signature_cell(*pair[0], centered=centered)
        if len(pair) > 1:
            right = _signature_cell(*pair[1], centered=centered)
            table = _paired_sign_table(left, right) if centered else _sign_table(left, right)
        else:
            if approval_label:
                heading = Paragraph(escape(approval_label), STYLES["sign_heading_center"])
                story.append(_center_sign_table(heading))
            table = _center_sign_table(left) if centered else _sign_table(left, "")
        story.extend([table, Spacer(1, 3 * mm)])
    return [KeepTogether(story)]


class _PdfDoc(BaseDocTemplate):
    def __init__(self, target, title, has_kop):
        super().__init__(
            target,
            pagesize=A4,
            title=title,
            leftMargin=LEFT_MARGIN,
            rightMargin=RIGHT_MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN,
        )
        first_top = KOP_TOP_MARGIN if has_kop else TOP_MARGIN
        first = Frame(
            LEFT_MARGIN,
            BOTTOM_MARGIN,
            CONTENT_WIDTH,
            PAGE_HEIGHT - BOTTOM_MARGIN - first_top,
            id="first",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        later = Frame(
            LEFT_MARGIN,
            BOTTOM_MARGIN,
            CONTENT_WIDTH,
            PAGE_HEIGHT - BOTTOM_MARGIN - TOP_MARGIN,
            id="later",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(
            [
                PageTemplate(id="First", frames=[first], autoNextPageTemplate="Later"),
                PageTemplate(id="Later", frames=[later]),
            ]
        )


def build_pdf(target, title, story):
    kop = _kop_path()
    kop_items = kop_story(kop)
    doc = _PdfDoc(target, title, bool(kop_items))
    doc.build([*kop_items, *story])


def _append_table(story, title, headers, rows, weights=None):
    story.extend([section(title), data_table(headers, rows, weights)])


def _item_value(item, snapshot, relation, field):
    value = getattr(item, snapshot, None)
    if value not in (None, ""):
        return value
    master = getattr(item, relation, None)
    return getattr(master, field, None) or "-"


def _peminjam_rows(nama, nip, telepon, email, alamat):
    return [
        ("Nama", nama),
        ("NIP / NIK", nip),
        ("Nomor Telepon", telepon),
        ("Email", email),
        ("Alamat", alamat),
    ]


def _dokumen_rows(nomor, tanggal_label, tanggal, pengembalian, selesai):
    return [
        ("Nomor Pengajuan", nomor),
        (tanggal_label, tanggal),
        ("Tanggal Pengembalian", pengembalian),
        ("Pengembalian Selesai", selesai),
    ]


def render_pengajuan_pdf(target, obj, format_date, ketua_title):
    survei = [item.jenis_survei for item in obj.kegiatan_survei.all()]
    if obj.survei_lainnya:
        survei.append(f"Lainnya: {obj.survei_lainnya}")
    story = title_block(
        "FORMULIR PENGAJUAN PEMINJAMAN",
        _peminjam_rows(
            obj.nama_peminjam,
            obj.nip_peminjam,
            obj.no_hp_peminjam,
            obj.email_peminjam,
            obj.alamat_peminjam,
        ),
        _dokumen_rows(
            obj.nomor_pengajuan,
            "Tanggal Peminjaman",
            format_date(obj.submitted_at),
            format_date(obj.return_started_at),
            format_date(obj.return_completed_at),
        ),
    )
    story.extend(
        [
            section("A. Data Kegiatan"),
            info_table(
                [
                    ("Layanan Kegiatan", obj.layanan_kegiatan_label),
                    ("Kegiatan Survei", ", ".join(survei) or "-"),
                    ("Tim Kegiatan Pelaksana", getattr(obj.tim_kegiatan, "nama_tim", "-")),
                    (
                        "Instansi Tujuan Kegiatan",
                        getattr(obj.instansi_tujuan, "nama_instansi", obj.instansi_tujuan_lainnya or "-"),
                    ),
                    (
                        "Waktu Kegiatan",
                        f"{format_date(obj.tanggal_mulai)} s/d {format_date(obj.tanggal_selesai)}",
                    ),
                    ("Total Hari", f"{obj.total_hari} hari"),
                ]
            ),
        ]
    )
    _append_table(
        story,
        "B. Data Peralatan Survei Lapangan yang Dipinjam",
        [
            "No.",
            "Nama Barang",
            "Tipe / Merek",
            "Jenis Barang",
            "Status Barang",
            "Kode Aset BMN",
            "Kode Laboratorium",
            "Volume",
            "Satuan",
            "Kondisi Barang",
            "Tahun Perolehan",
        ],
        [
            [
                index,
                _item_value(item, "snapshot_nama_barang", "barang", "nama_barang"),
                _item_value(item, "snapshot_tipe_merek_barang", "barang", "tipe_merek_barang"),
                _item_value(item, "snapshot_jenis_barang", "barang", "jenis_barang"),
                _item_value(item, "snapshot_status_barang", "barang", "status_barang"),
                _item_value(item, "snapshot_kode_aset_bmn", "barang", "kode_aset_bmn"),
                _item_value(item, "snapshot_kode_laboratorium", "barang", "kode_laboratorium"),
                _item_value(item, "snapshot_volume", "barang", "volume"),
                _item_value(item, "snapshot_satuan", "barang", "satuan"),
                _item_value(item, "snapshot_kondisi_barang", "barang", "kondisi_barang"),
                _item_value(item, "snapshot_tahun_perolehan", "barang", "tahun_perolehan"),
            ]
            for index, item in enumerate(obj.barang_laboratorium_items.all(), start=1)
        ],
        [0.4, 1.8, 1.5, 1.2, 1, 1.1, 1.1, 0.7, 0.7, 1, 0.8],
    )
    _append_table(
        story,
        "C. Data Barang Penunjang Lapangan yang Dipinjam",
        ["No.", "Nama Barang", "Tipe / Merek", "Kategori Barang", "Volume", "Satuan"],
        [
            [
                index,
                _item_value(item, "snapshot_nama_barang", "barang", "nama_barang"),
                _item_value(item, "snapshot_tipe_merek_barang", "barang", "tipe_merek_barang"),
                _item_value(item, "snapshot_kategori_barang", "barang", "kategori_barang"),
                item.volume,
                _item_value(item, "snapshot_satuan", "barang", "satuan"),
            ]
            for index, item in enumerate(obj.barang_penunjang_items.all(), start=1)
        ],
        [0.5, 2.2, 1.8, 1.5, 0.8, 0.9],
    )
    _append_table(
        story,
        "D. Data Bahan Operasional yang Dipinjam",
        ["No.", "Nama Barang", "Volume", "Satuan"],
        [
            [
                index,
                _item_value(item, "snapshot_nama_barang", "bahan", "nama_barang"),
                item.volume,
                _item_value(item, "snapshot_satuan", "bahan", "satuan"),
            ]
            for index, item in enumerate(obj.bahan_operasional_items.all(), start=1)
        ],
        [0.5, 3.5, 1, 1],
    )
    _append_table(
        story,
        "E. Data Peralatan Laboratorium yang Dipinjam",
        [
            "No.",
            "Nama Barang",
            "Tipe / Merek",
            "Jenis Barang",
            "Status Barang",
            "Kode Aset BMN",
            "Kode Laboratorium",
            "Volume Dipinjam",
            "Satuan",
            "Kondisi Barang",
            "Tahun Perolehan",
        ],
        [
            [
                index,
                _item_value(item, "snapshot_nama_barang", "barang", "nama_barang"),
                _item_value(item, "snapshot_tipe_merek_barang", "barang", "tipe_merek_barang"),
                _item_value(item, "snapshot_jenis_barang", "barang", "jenis_barang"),
                _item_value(item, "snapshot_status_barang", "barang", "status_barang"),
                _item_value(item, "snapshot_kode_aset_bmn", "barang", "kode_aset_bmn"),
                _item_value(item, "snapshot_kode_laboratorium", "barang", "kode_laboratorium"),
                item.volume,
                _item_value(item, "snapshot_satuan", "barang", "satuan"),
                _item_value(item, "snapshot_kondisi_barang", "barang", "kondisi_barang"),
                _item_value(item, "snapshot_tahun_perolehan", "barang", "tahun_perolehan"),
            ]
            for index, item in enumerate(obj.peralatan_laboratorium_items.all(), start=1)
        ],
        [0.4, 1.8, 1.5, 1.2, 1, 1.1, 1.1, 0.8, 0.7, 1, 0.8],
    )
    story.extend(
        signature_block(
            f"Bandung, {format_date(obj.submitted_at)}",
            [("Peminjam,", obj.peminjam), ("Petugas Laboratorium,", obj.teknisi_lab_by)],
            [("Kepala Laboratorium,", obj.get_kepala_lab_signer()), (ketua_title, obj.get_pimpinan_signer())],
        )
    )
    build_pdf(target, obj.nomor_pengajuan, story)


def render_laporan_pdf(target, obj, report, format_date, teknisi):
    peminjam = report.get("peminjam", {})
    kegiatan = report.get("kegiatan", {})
    items = report.get("items", {})
    story = title_block(
        "LAPORAN DETAIL PEMINJAMAN DAN PENGEMBALIAN",
        _peminjam_rows(
            peminjam.get("nama", "-"),
            peminjam.get("nip", "-"),
            peminjam.get("nomor_telepon", "-"),
            peminjam.get("email", "-"),
            peminjam.get("alamat", "-"),
        ),
        _dokumen_rows(
            report.get("nomor_pengajuan", obj.nomor_pengajuan),
            "Tanggal Peminjaman",
            report.get("submitted_at", "-"),
            report.get("return_started_at", "-"),
            report.get("return_completed_at", "-"),
        ),
    )
    story.extend(
        [
            section("A. Data Kegiatan"),
            info_table(
                [
                    ("Layanan Kegiatan", kegiatan.get("layanan_kegiatan", "-")),
                    ("Kegiatan Survei", ", ".join(kegiatan.get("kegiatan_survei", []) or []) or "-"),
                    ("Tim Kegiatan", kegiatan.get("tim_kegiatan", "-")),
                    ("Instansi Tujuan", kegiatan.get("instansi_tujuan", "-")),
                    ("Mulai Tanggal", kegiatan.get("mulai_tanggal", "-")),
                    ("Selesai Tanggal", kegiatan.get("selesai_tanggal", "-")),
                    ("Total Hari", f"{kegiatan.get('total_hari', '-')} hari"),
                ]
            ),
        ]
    )
    _append_table(
        story,
        "B. Data Peralatan Survei Lapangan",
        [
            "No.",
            "Nama Barang",
            "Tipe / Merek",
            "Jenis Barang",
            "Status Barang",
            "Kode Aset BMN",
            "Kode Laboratorium",
            "Volume",
            "Satuan",
            "Kondisi Barang",
            "Tahun Perolehan",
            "Asal Peminjaman",
            "Status Pengembalian",
            "Tujuan Transfer",
            "Catatan Pengembalian",
        ],
        [
            [
                index,
                item.get("nama_barang", "-"),
                item.get("tipe_merek_barang", "-"),
                item.get("jenis_barang", "-"),
                item.get("status_barang", "-"),
                item.get("kode_aset_bmn", "-"),
                item.get("kode_laboratorium", "-"),
                item.get("volume", "-"),
                item.get("satuan", "-"),
                item.get("kondisi_barang", "-"),
                item.get("tahun_perolehan", "-"),
                item.get("asal_peminjaman", "-"),
                item.get("status_pengembalian", "-"),
                item.get("tujuan_transfer", "-"),
                item.get("catatan_pengembalian", "-"),
            ]
            for index, item in enumerate(items.get("lab", []), start=1)
        ],
        [0.35, 1.5, 1.2, 1, 0.9, 1, 1, 0.6, 0.6, 0.9, 0.7, 1.2, 1.1, 1.2, 1.5],
    )
    _append_table(
        story,
        "C. Data Barang Penunjang Lapangan",
        [
            "No.",
            "Nama Barang",
            "Tipe / Merek",
            "Kategori Barang",
            "Volume Dipinjam",
            "Satuan",
            "Asal Peminjaman",
            "Dikembalikan",
            "Rusak",
            "Hilang",
            "Transfer",
            "Tujuan Transfer",
            "Catatan Pengembalian",
        ],
        [
            [
                index,
                item.get("nama_barang", "-"),
                item.get("tipe_merek_barang", "-"),
                item.get("kategori_barang", "-"),
                item.get("volume_dipinjam", "-"),
                item.get("satuan", "-"),
                item.get("asal_peminjaman", "-"),
                item.get("qty_dikembalikan", 0),
                item.get("qty_rusak", 0),
                item.get("qty_hilang", 0),
                item.get("qty_transfer", 0),
                item.get("tujuan_transfer", "-"),
                item.get("catatan_pengembalian", "-"),
            ]
            for index, item in enumerate(items.get("penunjang", []), start=1)
        ],
        [0.35, 1.5, 1.2, 1.1, 0.8, 0.6, 1.2, 0.7, 0.6, 0.6, 0.6, 1.2, 1.5],
    )
    _append_table(
        story,
        "D. Data Bahan Operasional",
        [
            "No.",
            "Nama Barang",
            "Volume Dipinjam",
            "Satuan",
            "Asal Peminjaman",
            "Sisa",
            "Transfer",
            "Tujuan Transfer",
            "Catatan Pengembalian",
        ],
        [
            [
                index,
                item.get("nama_barang", "-"),
                item.get("volume_dipinjam", "-"),
                item.get("satuan", "-"),
                item.get("asal_peminjaman", "-"),
                item.get("qty_sisa", 0),
                item.get("qty_transfer", 0),
                item.get("tujuan_transfer", "-"),
                item.get("catatan_pengembalian", "-"),
            ]
            for index, item in enumerate(items.get("bahan", []), start=1)
        ],
        [0.4, 1.8, 0.9, 0.7, 1.4, 0.7, 0.7, 1.4, 1.8],
    )
    _append_table(
        story,
        "E. Data Peralatan Laboratorium",
        [
            "No.",
            "Nama Barang",
            "Tipe / Merek",
            "Jenis Barang",
            "Status Barang",
            "Kode Aset BMN",
            "Kode Laboratorium",
            "Volume Dipinjam",
            "Satuan",
            "Kondisi Barang",
            "Tahun Perolehan",
            "Asal Peminjaman",
            "Dikembalikan",
            "Rusak",
            "Hilang",
            "Transfer",
            "Tujuan Transfer",
            "Catatan Pengembalian",
        ],
        [
            [
                index,
                item.get("nama_barang", "-"),
                item.get("tipe_merek_barang", "-"),
                item.get("jenis_barang", "-"),
                item.get("status_barang", "-"),
                item.get("kode_aset_bmn", "-"),
                item.get("kode_laboratorium", "-"),
                item.get("volume_dipinjam", "-"),
                item.get("satuan", "-"),
                item.get("kondisi_barang", "-"),
                item.get("tahun_perolehan", "-"),
                item.get("asal_peminjaman", "-"),
                item.get("qty_dikembalikan", 0),
                item.get("qty_rusak", 0),
                item.get("qty_hilang", 0),
                item.get("qty_transfer", 0),
                item.get("tujuan_transfer", "-"),
                item.get("catatan_pengembalian", "-"),
            ]
            for index, item in enumerate(items.get("peralatan_lab", []), start=1)
        ],
        [0.3, 1.4, 1.1, 0.9, 0.8, 0.9, 0.9, 0.7, 0.5, 0.8, 0.6, 1, 0.6, 0.5, 0.5, 0.5, 1, 1.3],
    )
    _append_table(
        story,
        "F. Data Pengukuran",
        ["No.", "Data Pengukuran", "Jumlah"],
        [
            [index, item.get("label", "-"), item.get("display", "-")]
            for index, item in enumerate(report.get("pengukuran", []) or [], start=1)
        ],
        [0.5, 3, 2],
    )
    story.extend(
        signature_block(
            f"Bandung, {format_date(obj.return_completed_at)}",
            [("Peminjam,", obj.peminjam), ("Teknisi Laboratorium,", teknisi)],
            [
                ("Kepala Laboratorium,", obj.get_kepala_lab_signer()),
                ("Ketua Tim Layanan Teknis,", obj.get_return_pimpinan_signer()),
            ],
        )
    )
    build_pdf(target, f"Laporan {obj.nomor_pengajuan}", story)


def render_berita_acara_pdf(target, obj, sections, format_date, teknisi):
    survei = [item.jenis_survei for item in obj.kegiatan_survei.all()]
    if obj.survei_lainnya:
        survei.append(f"Lainnya: {obj.survei_lainnya}")
    story = title_block(
        "BERITA ACARA PENGEMBALIAN BARANG RUSAK / HILANG",
        _peminjam_rows(
            obj.nama_peminjam,
            obj.nip_peminjam,
            obj.no_hp_peminjam,
            obj.email_peminjam,
            obj.alamat_peminjam,
        ),
        _dokumen_rows(
            obj.nomor_pengajuan,
            "Tanggal Peminjaman",
            format_date(obj.submitted_at),
            format_date(obj.return_started_at),
            format_date(obj.return_completed_at),
        ),
    )
    story.extend(
        [
            section("A. Data Kegiatan"),
            info_table(
                [
                    ("Layanan Kegiatan", obj.layanan_kegiatan_label),
                    ("Kegiatan Survei", ", ".join(survei) or "-"),
                    ("Tim Kegiatan", getattr(obj.tim_kegiatan, "nama_tim", "-")),
                    (
                        "Instansi Tujuan",
                        getattr(obj.instansi_tujuan, "nama_instansi", obj.instansi_tujuan_lainnya or "-"),
                    ),
                    (
                        "Periode Peminjaman",
                        f"{format_date(obj.tanggal_mulai)} s/d {format_date(obj.tanggal_selesai)}",
                    ),
                    ("Total Hari", f"{obj.total_hari} hari"),
                ]
            ),
        ]
    )
    headers = [
        "No.",
        "Nama Barang",
        "Jenis",
        "Jumlah",
        "Kode Laboratorium",
        "Catatan Pengembalian",
    ]
    weights = [0.4, 1.8, 1.4, 0.9, 1.4, 2.1]
    _append_table(
        story,
        "B. Daftar Barang Rusak",
        headers,
        [
            [
                index,
                item["nama"],
                item["jenis"],
                item["jumlah"],
                item["kode_laboratorium"],
                item["catatan_pengembalian"],
            ]
            for index, item in enumerate(sections["rusak"], start=1)
        ],
        weights,
    )
    _append_table(
        story,
        "C. Daftar Barang Hilang",
        headers,
        [
            [
                index,
                item["nama"],
                item["jenis"],
                item["jumlah"],
                item["kode_laboratorium"],
                item["catatan_pengembalian"],
            ]
            for index, item in enumerate(sections["hilang"], start=1)
        ],
        weights,
    )
    _append_table(
        story,
        "D. Keterangan",
        ["No.", "Keterangan"],
        [
            [
                1,
                "Dokumen ini diterbitkan secara otomatis pada akhir proses pengembalian untuk mencatat barang dengan status rusak atau hilang.",
            ],
            [
                2,
                "Barang yang dikembalikan dalam kondisi baik atau ditransfer ke pengajuan lain tidak dimasukkan ke dalam berita acara ini.",
            ],
        ],
        [0.5, 6],
    )
    story.extend(
        signature_block(
            f"Bandung, {format_date(obj.return_completed_at)}",
            [("Peminjam,", obj.peminjam), ("Teknisi Laboratorium,", teknisi)],
            [
                ("Kepala Laboratorium,", obj.get_kepala_lab_signer()),
                ("Ketua Tim Layanan Teknis,", obj.get_return_pimpinan_signer()),
            ],
        )
    )
    build_pdf(target, f"Berita Acara {obj.nomor_pengajuan}", story)
