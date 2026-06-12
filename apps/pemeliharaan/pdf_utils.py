from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Spacer, Table, TableStyle

from apps.core.permissions import ROLE_KEPALA_LAB, ROLE_PIMPINAN
from apps.operasional.models import TIM_LAYANAN_TEKNIS_NAME, TimKegiatan
from apps.pengguna.models import User
from apps.peminjaman.pdf_utils import (
    CONTENT_WIDTH,
    build_pdf,
    data_table,
    info_table,
    photo_cell,
    photo_grid,
    section,
    signature_list,
    text,
    title_block,
)

from .models import JenisFotoPemeliharaanChoices, TindakanPerbaikanChoices


TABLE_GAP = 3 * mm


def _user_name(user):
    if not user:
        return "-"
    return user.get_full_name() or user.username


def _role_signer(role_name, jabatan=None):
    users = User.objects.filter(is_active=True, profile__role__nama=role_name)
    if jabatan:
        users = users.filter(profile__jabatan__icontains=jabatan)
    return (
        users
        .select_related("profile")
        .order_by("id")
        .first()
    )


def _ketua_layanan_teknis():
    teams = (
        TimKegiatan.objects.filter(nama_tim__iexact=TIM_LAYANAN_TEKNIS_NAME)
        .select_related("ketua_tim", "ketua_tim__profile")
        .order_by("id")
    )
    team = teams.first()
    if team is None:
        team = (
            TimKegiatan.objects.filter(nama_tim__icontains="Layanan Teknis")
            .select_related("ketua_tim", "ketua_tim__profile")
            .order_by("id")
            .first()
        )
    if team and team.ketua_tim_id and team.ketua_tim.is_active:
        return team.ketua_tim
    return _role_signer(ROLE_PIMPINAN, "Layanan Teknis")


def _signers(obj):
    return [
        ("Pelaksana Pemeliharaan,", obj.pemohon),
        ("Kepala Laboratorium,", _role_signer(ROLE_KEPALA_LAB)),
        ("Ketua Tim Layanan Teknis,", _ketua_layanan_teknis()),
    ]


def _photos(items, jenis):
    photos = []
    for item in items:
        for photo in item.fotos.all():
            if photo.jenis == jenis:
                photos.append(photo.foto)
    return photos


def _repair_table(title, items, jenis, format_date):
    is_mandiri = jenis == JenisFotoPemeliharaanChoices.PERBAIKAN
    if is_mandiri:
        headers = [
            "No.",
            "Komponen",
            "Uraian Perbaikan",
            "Tanggal Selesai",
            "Dokumentasi Perbaikan",
        ]
        weights = [0.45, 1.25, 2.5, 1.15, 2.2]
    else:
        headers = ["No.", "Komponen", "Uraian Kerusakan", "Dokumentasi Kerusakan"]
        weights = [0.45, 1.35, 3, 2.4]

    total = sum(weights)
    widths = [CONTENT_WIDTH * weight / total for weight in weights]
    rows = [
        [text(title, "head"), *([""] * (len(headers) - 1))],
        [text(header, "head") for header in headers],
    ]
    for index, item in enumerate(items, start=1):
        documentation = photo_cell(_photos([item], jenis), widths[-1])
        row = [
            text(index, "small_center"),
            text(item.komponen, "small"),
            text(item.uraian_perbaikan if is_mandiri else item.uraian_kerusakan, "small"),
        ]
        if is_mandiri:
            row.append(text(format_date(item.tanggal_selesai_perbaikan), "small_center"))
        row.append(documentation)
        rows.append(row)

    table = Table(
        rows,
        colWidths=widths,
        repeatRows=2,
        splitByRow=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#17365D")),
                ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, colors.HexColor("#F5F8FB")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#758A9D")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB8C4")),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return [table]


def render_pemeliharaan_pdf(target, obj, format_date):
    items = list(obj.items.all())
    story = title_block(
        "LAPORAN PENGAJUAN PEMELIHARAAN",
        [
            ("Pelaksana Pemeliharaan", _user_name(obj.pemohon)),
            ("Jabatan", obj.jabatan_pelaksana),
            ("Tanggal Pemeriksaan", format_date(obj.tanggal_pemeriksaan)),
            ("Tanggal Kirim", format_date(obj.submitted_at)),
        ],
        [
            ("Nomor Pengajuan", obj.nomor_pengajuan),
            ("Hasil Proses", obj.hasil_label),
            ("Proses Selesai", format_date(obj.selesai_at)),
            ("Kondisi Awal Barang", obj.kondisi_barang_sebelum or "-"),
        ],
    )
    story.extend(
        [
            section("A. Data Barang"),
            info_table(
                [
                    ("Nama Barang", obj.snapshot_nama_barang or "-"),
                    ("Tipe / Merek Barang", obj.snapshot_tipe_merek_barang or "-"),
                    ("Kode Laboratorium", obj.snapshot_kode_laboratorium or "-"),
                    ("Status Barang", obj.status_barang_label),
                ],
                valign="MIDDLE",
            ),
        ]
    )
    story.extend(
        [
            section("B. Pemeriksaan Komponen"),
            data_table(
                ["No.", "Komponen", "Kondisi"],
                [
                    [index, item.komponen, item.kondisi]
                    for index, item in enumerate(items, start=1)
                ],
                [0.6, 3, 1.5],
                valign="MIDDLE",
            ),
        ]
    )
    examination_photos = _photos(items, JenisFotoPemeliharaanChoices.PEMERIKSAAN)
    if examination_photos:
        story.append(Spacer(1, TABLE_GAP))
        story.extend(
            photo_grid(examination_photos, header="Dokumentasi Pemeriksaan")
        )

    mandiri_items = [
        item for item in items
        if item.perlu_perbaikan
        and item.tindakan_perbaikan == TindakanPerbaikanChoices.MANDIRI
    ]
    eksternal_items = [
        item for item in items
        if item.perlu_perbaikan
        and item.tindakan_perbaikan == TindakanPerbaikanChoices.EKSTERNAL
    ]
    if mandiri_items or eksternal_items:
        story.append(section("C. Tindak Lanjut Perbaikan"))
    if mandiri_items:
        story.extend(
            _repair_table(
                "Perbaikan Mandiri",
                mandiri_items,
                JenisFotoPemeliharaanChoices.PERBAIKAN,
                format_date,
            )
        )
    if eksternal_items:
        if mandiri_items:
            story.append(Spacer(1, TABLE_GAP))
        story.extend(
            _repair_table(
                "Perbaikan Eksternal",
                eksternal_items,
                JenisFotoPemeliharaanChoices.KERUSAKAN,
                format_date,
            )
        )
    story.extend(
        signature_list(
            f"Bandung, {format_date(obj.selesai_at)}",
            _signers(obj),
            centered=True,
            approval_label="Menyetujui:",
        )
    )
    build_pdf(target, f"Laporan Pemeliharaan {obj.nomor_pengajuan}", story)
