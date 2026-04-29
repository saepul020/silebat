# Generated for SILEBAT: decouple laporan peminjaman from master_data.

import django.db.models.deletion
from django.db import migrations, models


LAB_SNAPSHOT_FIELDS = [
    "snapshot_nama_barang",
    "snapshot_tipe_merek_barang",
    "snapshot_jenis_barang",
    "snapshot_status_barang",
    "snapshot_kode_aset_bmn",
    "snapshot_kode_laboratorium",
    "snapshot_volume",
    "snapshot_satuan",
    "snapshot_kondisi_barang",
    "snapshot_tahun_perolehan",
]

PENUNJANG_SNAPSHOT_FIELDS = [
    "snapshot_nama_barang",
    "snapshot_tipe_merek_barang",
    "snapshot_kategori_barang",
    "snapshot_satuan",
]

BAHAN_SNAPSHOT_FIELDS = [
    "snapshot_nama_barang",
    "snapshot_kategori_barang",
    "snapshot_satuan",
]


def _text(value, default="-"):
    if value in (None, ""):
        return default
    return str(value)


def populate_item_snapshots(apps, schema_editor):
    def populate_lab(model_name, relation_name):
        Model = apps.get_model("peminjaman", model_name)
        rows = []
        for row in Model.objects.select_related(relation_name).all():
            source = getattr(row, relation_name, None)
            if source is None:
                continue
            row.snapshot_nama_barang = _text(getattr(source, "nama_barang", None))
            row.snapshot_tipe_merek_barang = _text(getattr(source, "tipe_merek_barang", None))
            row.snapshot_jenis_barang = _text(getattr(source, "jenis_barang", None))
            row.snapshot_status_barang = _text(getattr(source, "status_barang", None))
            row.snapshot_kode_aset_bmn = _text(getattr(source, "kode_aset_bmn", None))
            row.snapshot_kode_laboratorium = _text(getattr(source, "kode_laboratorium", None))
            row.snapshot_volume = getattr(source, "volume", None)
            row.snapshot_satuan = _text(getattr(source, "satuan", None))
            row.snapshot_kondisi_barang = _text(getattr(source, "kondisi_barang", None))
            row.snapshot_tahun_perolehan = getattr(source, "tahun_perolehan", None)
            rows.append(row)
        if rows:
            Model.objects.bulk_update(rows, LAB_SNAPSHOT_FIELDS)

    def populate_penunjang(model_name, relation_name):
        Model = apps.get_model("peminjaman", model_name)
        rows = []
        for row in Model.objects.select_related(relation_name).all():
            source = getattr(row, relation_name, None)
            if source is None:
                continue
            row.snapshot_nama_barang = _text(getattr(source, "nama_barang", None))
            row.snapshot_tipe_merek_barang = _text(getattr(source, "tipe_merek_barang", None))
            row.snapshot_kategori_barang = _text(getattr(source, "kategori_barang", None))
            row.snapshot_satuan = _text(getattr(source, "satuan", None))
            rows.append(row)
        if rows:
            Model.objects.bulk_update(rows, PENUNJANG_SNAPSHOT_FIELDS)

    def populate_bahan(model_name, relation_name):
        Model = apps.get_model("peminjaman", model_name)
        rows = []
        for row in Model.objects.select_related(relation_name).all():
            source = getattr(row, relation_name, None)
            if source is None:
                continue
            row.snapshot_nama_barang = _text(getattr(source, "nama_barang", None))
            row.snapshot_kategori_barang = _text(getattr(source, "kategori_barang", None))
            row.snapshot_satuan = _text(getattr(source, "satuan", None))
            rows.append(row)
        if rows:
            Model.objects.bulk_update(rows, BAHAN_SNAPSHOT_FIELDS)

    populate_lab("PeminjamanBarangLaboratorium", "barang")
    populate_lab("PengembalianBarangLaboratorium", "barang")
    populate_penunjang("PeminjamanBarangPenunjang", "barang")
    populate_penunjang("PengembalianBarangPenunjang", "barang")
    populate_bahan("PeminjamanBahanOperasional", "bahan")
    populate_bahan("PengembalianBahanOperasional", "bahan")


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0008_master_data_relabel_and_peralatan_lab"),
        ("peminjaman", "0012_update_item_verbose_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_nama_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_tipe_merek_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_jenis_barang",
            field=models.CharField(blank=True, default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_status_barang",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_kode_aset_bmn",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_kode_laboratorium",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_volume",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_satuan",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_kondisi_barang",
            field=models.CharField(blank=True, default="", max_length=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbaranglaboratorium",
            name="snapshot_tahun_perolehan",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_nama_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_tipe_merek_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_jenis_barang",
            field=models.CharField(blank=True, default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_status_barang",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_kode_aset_bmn",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_kode_laboratorium",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_volume",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_satuan",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_kondisi_barang",
            field=models.CharField(blank=True, default="", max_length=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbaranglaboratorium",
            name="snapshot_tahun_perolehan",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="peminjamanbarangpenunjang",
            name="snapshot_nama_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbarangpenunjang",
            name="snapshot_tipe_merek_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbarangpenunjang",
            name="snapshot_kategori_barang",
            field=models.CharField(blank=True, default="", max_length=60),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbarangpenunjang",
            name="snapshot_satuan",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbarangpenunjang",
            name="snapshot_nama_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbarangpenunjang",
            name="snapshot_tipe_merek_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbarangpenunjang",
            name="snapshot_kategori_barang",
            field=models.CharField(blank=True, default="", max_length=60),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbarangpenunjang",
            name="snapshot_satuan",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbahanoperasional",
            name="snapshot_nama_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbahanoperasional",
            name="snapshot_kategori_barang",
            field=models.CharField(blank=True, default="", max_length=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peminjamanbahanoperasional",
            name="snapshot_satuan",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbahanoperasional",
            name="snapshot_nama_barang",
            field=models.CharField(blank=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbahanoperasional",
            name="snapshot_kategori_barang",
            field=models.CharField(blank=True, default="", max_length=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pengembalianbahanoperasional",
            name="snapshot_satuan",
            field=models.CharField(blank=True, default="", max_length=20),
            preserve_default=False,
        ),
        migrations.RunPython(populate_item_snapshots, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="peminjamanbaranglaboratorium",
            name="barang",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="master_data.baranglaboratorium"),
        ),
        migrations.AlterField(
            model_name="pengembalianbaranglaboratorium",
            name="barang",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="master_data.baranglaboratorium"),
        ),
        migrations.AlterField(
            model_name="peminjamanbarangpenunjang",
            name="barang",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="master_data.barangpenunjangoperasional"),
        ),
        migrations.AlterField(
            model_name="pengembalianbarangpenunjang",
            name="barang",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="master_data.barangpenunjangoperasional"),
        ),
        migrations.AlterField(
            model_name="peminjamanbahanoperasional",
            name="bahan",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="master_data.bahanoperasional"),
        ),
        migrations.AlterField(
            model_name="pengembalianbahanoperasional",
            name="bahan",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="master_data.bahanoperasional"),
        ),
        migrations.AlterModelOptions(
            name="peminjamanbaranglaboratorium",
            options={
                "ordering": ["barang__nama_barang", "snapshot_nama_barang"],
                "verbose_name": "Item Peralatan Survei Lapangan",
                "verbose_name_plural": "Item Peralatan Survei Lapangan",
            },
        ),
        migrations.AlterModelOptions(
            name="pengembalianbaranglaboratorium",
            options={
                "ordering": ["barang__nama_barang", "snapshot_nama_barang"],
                "verbose_name": "Pengembalian Peralatan Survei Lapangan",
                "verbose_name_plural": "Pengembalian Peralatan Survei Lapangan",
            },
        ),
        migrations.AlterModelOptions(
            name="peminjamanbarangpenunjang",
            options={
                "ordering": ["barang__nama_barang", "snapshot_nama_barang"],
                "verbose_name": "Item Barang Penunjang Lapangan",
                "verbose_name_plural": "Item Barang Penunjang Lapangan",
            },
        ),
        migrations.AlterModelOptions(
            name="pengembalianbarangpenunjang",
            options={
                "ordering": ["barang__nama_barang", "snapshot_nama_barang"],
                "verbose_name": "Pengembalian Barang Penunjang Lapangan",
                "verbose_name_plural": "Pengembalian Barang Penunjang Lapangan",
            },
        ),
        migrations.AlterModelOptions(
            name="peminjamanbahanoperasional",
            options={
                "ordering": ["bahan__nama_barang", "snapshot_nama_barang"],
                "verbose_name": "Item Bahan Operasional",
                "verbose_name_plural": "Item Bahan Operasional",
            },
        ),
        migrations.AlterModelOptions(
            name="pengembalianbahanoperasional",
            options={
                "ordering": ["bahan__nama_barang", "snapshot_nama_barang"],
                "verbose_name": "Pengembalian Bahan Operasional",
                "verbose_name_plural": "Pengembalian Bahan Operasional",
            },
        ),
    ]
