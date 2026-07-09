from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.contrib.staticfiles import finders
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


PX_PER_MM = 12
LABEL_WIDTH = 50 * PX_PER_MM
LABEL_HEIGHT = 20 * PX_PER_MM
LEFT_WIDTH = 30 * PX_PER_MM
HEADER_HEIGHT = 6 * PX_PER_MM
BODY_HEIGHT = 14 * PX_PER_MM
QR_SIZE = 19 * PX_PER_MM
LOGO_HEIGHT = 4 * PX_PER_MM
HEADER_PAD = int(0.7 * PX_PER_MM)
BODY_PAD_LEFT = int(1.5 * PX_PER_MM)
BODY_PAD_RIGHT = int(1 * PX_PER_MM)
BODY_PAD_TOP = int(1 * PX_PER_MM)
BODY_PAD_BOTTOM = int(0.8 * PX_PER_MM)
CODE_LABEL_WIDTH = 10 * PX_PER_MM
CODE_COLON_WIDTH = int(1 * PX_PER_MM)
CODE_GAP = int(0.3 * PX_PER_MM)
LABELS_PER_PAGE = 40
PDF_COLUMNS = 5
PDF_ROWS = 8
PDF_MARGIN_X_MM = 8
PDF_MARGIN_Y_MM = 8
PDF_LABEL_WIDTH_MM = 50
PDF_LABEL_HEIGHT_MM = 20
PDF_SMALL_SCALE = 0.75


@lru_cache(maxsize=24)
def _font(size, *, bold=False):
    candidates = []
    if Path("C:/Windows/Fonts").exists():
        candidates.extend(
            [
                "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/Arial.ttf",
            ]
        )
    candidates.extend(
        [
            "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf" if bold else "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )

    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _draw_text_top(draw, position, text, *, fill, font):
    try:
        draw.text(position, text, fill=fill, font=font, anchor="lt")
    except ValueError:
        draw.text(position, text, fill=fill, font=font)


def _truncate(draw, text, font, max_width):
    text = str(text or "-")
    if _text_size(draw, text, font)[0] <= max_width:
        return text

    marker = "..."
    while text and _text_size(draw, f"{text}{marker}", font)[0] > max_width:
        text = text[:-1]
    return f"{text}{marker}" if text else "-"


def _wrap_text(draw, text, font, max_width, max_lines):
    words = str(text or "-").split()
    if not words:
        return ["-"]

    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or _text_size(draw, candidate, font)[0] <= max_width:
            current = candidate
            continue

        lines.append(current)
        current = word
        if len(lines) == max_lines:
            break

    if len(lines) < max_lines and current:
        lines.append(current)

    lines = lines[:max_lines]
    if words and len(lines) == max_lines:
        used_words = " ".join(lines).split()
        if len(used_words) < len(words):
            lines[-1] = _truncate(draw, lines[-1], font, max_width)

    return [_truncate(draw, line, font, max_width) for line in (lines or ["-"])]


@lru_cache(maxsize=8)
def _asset_image(path, target_height, max_width):
    if not path:
        return None

    image = Image.open(path).convert("RGBA")
    image.thumbnail((max_width, target_height), Image.Resampling.LANCZOS)
    return image


def _paste_center(canvas, image, box):
    if image is None:
        return

    x1, y1, x2, y2 = box
    x = x1 + ((x2 - x1) - image.width) // 2
    y = y1 + ((y2 - y1) - image.height) // 2
    canvas.alpha_composite(image, (x, y))


def _load_qr(obj):
    qr_file = getattr(obj, "qr_code", None)
    if not qr_file:
        return None

    try:
        opened_file = qr_file.open("rb")
        image = Image.open(opened_file or qr_file).convert("RGBA")
        qr_file.close()
    except Exception:
        return None

    return ImageOps.contain(image, (QR_SIZE, QR_SIZE), Image.Resampling.NEAREST)


def build_label_png(obj, label_data):
    canvas = Image.new("RGBA", (LABEL_WIDTH, LABEL_HEIGHT), "white")
    draw = ImageDraw.Draw(canvas)

    black = "#241f1f"
    border_width = 1
    draw.rectangle(
        (0, 0, LABEL_WIDTH - 1, LABEL_HEIGHT - 1),
        outline=black,
        width=border_width,
    )
    draw.line((LEFT_WIDTH, 0, LEFT_WIDTH, LABEL_HEIGHT), fill=black, width=border_width)
    draw.line((0, HEADER_HEIGHT, LEFT_WIDTH, HEADER_HEIGHT), fill=black, width=border_width)

    logo_pu = _asset_image(finders.find("assets/img/logo-pu.png"), LOGO_HEIGHT, int(4.8 * PX_PER_MM))
    logo_col = int(5.2 * PX_PER_MM)
    _paste_center(canvas, logo_pu, (HEADER_PAD, 0, HEADER_PAD + logo_col, HEADER_HEIGHT))

    header_font = _font(15, bold=True)
    header_lines = ("KEMENTERIAN PEKERJAAN UMUM", "LABORATORIUM BALAI AIR TANAH")
    header_line_height = 18
    header_text_height = header_line_height * len(header_lines)
    y = (HEADER_HEIGHT - header_text_height) // 2
    header_x = HEADER_PAD + logo_col + int(0.4 * PX_PER_MM)
    max_header_width = LEFT_WIDTH - header_x - HEADER_PAD
    for line in header_lines:
        text = _truncate(draw, line, header_font, max_header_width)
        _draw_text_top(draw, (header_x, y), text, fill=black, font=header_font)
        y += header_line_height

    body_top = HEADER_HEIGHT + 1
    body_left = BODY_PAD_LEFT
    text_max_width = LEFT_WIDTH - body_left - BODY_PAD_RIGHT
    qr_x = LEFT_WIDTH + ((LABEL_WIDTH - LEFT_WIDTH - QR_SIZE) // 2)
    qr_y = (LABEL_HEIGHT - QR_SIZE) // 2

    fonts = {
        "name": _font(25, bold=True),
        "type": _font(21),
        "code": _font(21),
    }
    name_lines = _wrap_text(draw, label_data["nama_barang"], fonts["name"], text_max_width, 2)
    code_rows = [
        ("Kode BMN", label_data["kode_aset_bmn"], 22, 0),
        ("Kode Lab", label_data["kode_laboratorium"], 22, 0),
    ]
    body_content_height = BODY_HEIGHT - BODY_PAD_TOP - BODY_PAD_BOTTOM
    title_height = 25 * len(name_lines)
    total_text_height = title_height + 6 + 21 + 18 + 44
    text_y = body_top + BODY_PAD_TOP + max((body_content_height - total_text_height) // 2, 0)
    for line in name_lines:
        _draw_text_top(draw, (body_left, text_y), line, fill=black, font=fonts["name"])
        text_y += 25

    text_y += 6
    type_text = _truncate(draw, label_data["tipe_merek_barang"], fonts["type"], text_max_width)
    _draw_text_top(draw, (body_left, text_y), type_text, fill=black, font=fonts["type"])
    text_y += 39

    colon_x = body_left + CODE_LABEL_WIDTH
    value_x = colon_x + CODE_COLON_WIDTH + CODE_GAP
    value_max_width = text_max_width - CODE_LABEL_WIDTH - CODE_COLON_WIDTH - CODE_GAP
    for label, value, line_height, margin_bottom in code_rows:
        value_text = _truncate(draw, value, fonts["code"], value_max_width)
        _draw_text_top(draw, (body_left, text_y), label, fill=black, font=fonts["code"])
        _draw_text_top(draw, (colon_x, text_y), ":", fill=black, font=fonts["code"])
        _draw_text_top(draw, (value_x, text_y), value_text, fill=black, font=fonts["code"])
        text_y += line_height + margin_bottom

    qr_image = _load_qr(obj)
    if qr_image is not None:
        canvas.alpha_composite(qr_image, (qr_x, qr_y))
    else:
        dash_font = _font(24)
        dash_width, dash_height = _text_size(draw, "-", dash_font)
        draw.text(
            (qr_x + (QR_SIZE - dash_width) // 2, qr_y + (QR_SIZE - dash_height) // 2),
            "-",
            fill=black,
            font=dash_font,
        )

    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", dpi=(305, 305))
    output.seek(0)
    return output.getvalue()


def build_label_pdf(label_entries):
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=landscape(A4), pageCompression=0)
    page_width, page_height = landscape(A4)

    normal_width = PDF_LABEL_WIDTH_MM * mm
    normal_height = PDF_LABEL_HEIGHT_MM * mm
    margin_x = PDF_MARGIN_X_MM * mm
    margin_y = PDF_MARGIN_Y_MM * mm
    gap_x = (page_width - (2 * margin_x) - (PDF_COLUMNS * normal_width)) / (PDF_COLUMNS - 1)
    gap_y = (page_height - (2 * margin_y) - (PDF_ROWS * normal_height)) / (PDF_ROWS - 1)

    for index, entry in enumerate(label_entries):
        page_index = index % LABELS_PER_PAGE
        if index and page_index == 0:
            pdf.showPage()

        row = page_index // PDF_COLUMNS
        col = page_index % PDF_COLUMNS
        scale = PDF_SMALL_SCALE if entry.get("size") == "kecil" else 1
        label_width = normal_width * scale
        label_height = normal_height * scale
        slot_x = margin_x + (col * (normal_width + gap_x))
        slot_y = page_height - margin_y - ((row + 1) * normal_height) - (row * gap_y)
        x = slot_x + ((normal_width - label_width) / 2)
        y = slot_y + ((normal_height - label_height) / 2)

        image = ImageReader(BytesIO(entry["image"]))
        pdf.drawImage(
            image,
            x,
            y,
            width=label_width,
            height=label_height,
            mask="auto",
        )

    pdf.save()
    output.seek(0)
    return output.getvalue()
