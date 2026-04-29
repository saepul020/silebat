from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class StatusBarangChoices(models.TextChoices):
    BMN = "BMN", "BMN"
    NON_BMN = "Non BMN", "Non BMN"


class SatuanAsetChoices(models.TextChoices):
    BUAH = "Buah", "Buah"
    UNIT = "Unit", "Unit"
    SET = "Set", "Set"


class KondisiBarangChoices(models.TextChoices):
    BAIK = "Baik", "Baik"
    DALAM_PEMELIHARAAN = "Dalam Pemeliharaan", "Dalam Pemeliharaan"
    DALAM_PERBAIKAN = "Dalam Perbaikan", "Dalam Perbaikan"
    RUSAK = "Rusak", "Rusak"
    HILANG = "Hilang", "Hilang"


class KetersediaanChoices(models.TextChoices):
    TERSEDIA = "Tersedia", "Tersedia"
    TIDAK_TERSEDIA = "Tidak Tersedia", "Tidak Tersedia"


class KategoriBarangPenunjangChoices(models.TextChoices):
    ALAT_SURVEI = (
        "Penunjang Operasional Alat Survei",
        "Penunjang Operasional Alat Survei",
    )
    LAPANGAN = "Penunjang Operasional Lapangan", "Penunjang Operasional Lapangan"
    K3 = (
        "Penunjang Operasional K3 dan Pelindung",
        "Penunjang Operasional K3 dan Pelindung",
    )


class KategoriBarangLaboratoriumChoices(models.TextChoices):
    BOREHOLE_CAMERA = "Borehole Camera", "Borehole Camera"
    DRONE = "Drone", "Drone"
    GEOLISTRIK = "Geolistrik", "Geolistrik"
    INFILTRASI = "Infiltrasi", "Infiltrasi"
    INSTRUMEN_KEAIRAN = "Instrumen Keairan", "Instrumen Keairan"
    LOGGING = "Logging", "Logging"
    TOPOGRAFI_TS = "Topografi (TS)", "Topografi (TS)"
    PENDUKUNG_SURVEI_LAPANGAN = (
        "Pendukung Survei Lapangan",
        "Pendukung Survei Lapangan",
    )


class KategoriBahanOperasionalChoices(models.TextChoices):
    BAHAN_LABORATORIUM = "Bahan Laboratorium", "Bahan Laboratorium"
    BAHAN_LAPANGAN = "Bahan Lapangan", "Bahan Lapangan"
    SUKU_CADANG = "Suku Cadang", "Suku Cadang"


class KategoriSaranaPrasaranaChoices(models.TextChoices):
    FASILITAS_RUANGAN = "Fasilitas Ruangan", "Fasilitas Ruangan"
    FASILITAS_LAINNYA = "Fasilitas Lainnya", "Fasilitas Lainnya"


class SatuanBahanChoices(models.TextChoices):
    BUAH = "Buah", "Buah"
    PAK = "Pak", "Pak"
    ROL = "Rol", "Rol"
    SET = "Set", "Set"
    BOX = "Box", "Box"
    BOTOL = "Botol", "Botol"
    JIRIGEN = "Jirigen", "Jirigen"
    METER = "Meter", "Meter"


class StatusStokBahanChoices(models.TextChoices):
    BAIK = "Baik", "Baik"
    CUKUP = "Cukup", "Cukup"
    KURANG = "Kurang", "Kurang"
    HABIS = "Habis", "Habis"


class AssetBaseModel(models.Model):
    lock_volume_to_one = True

    nama_barang = models.CharField(max_length=200)
    tipe_merek_barang = models.CharField(max_length=200)
    jenis_barang = models.CharField(max_length=150)
    status_barang = models.CharField(max_length=20, choices=StatusBarangChoices.choices)
    kode_aset_bmn = models.CharField(max_length=100, null=True, blank=True)
    kode_laboratorium = models.CharField(max_length=100)
    volume = models.PositiveIntegerField(default=1)
    satuan = models.CharField(
        max_length=20, choices=SatuanAsetChoices.choices, default=SatuanAsetChoices.UNIT
    )
    ketersediaan = models.CharField(
        max_length=20,
        choices=KetersediaanChoices.choices,
        default=KetersediaanChoices.TERSEDIA,
        editable=False,
    )
    tahun_perolehan = models.PositiveIntegerField(null=True, blank=True)
    kondisi_barang = models.CharField(
        max_length=30,
        choices=KondisiBarangChoices.choices,
        default=KondisiBarangChoices.BAIK,
    )
    lokasi_barang = models.CharField(max_length=200)
    foto_barang = models.ImageField(
        upload_to="master_data/foto_barang/", blank=True, null=True
    )
    tanggal_pemeliharaan = models.DateField(null=True, blank=True)
    tanggal_perbaikan = models.DateField(null=True, blank=True)
    catatan = models.TextField(blank=True)
    sedang_dipinjam = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["nama_barang"]

    def _sync_locked_volume_by_condition(self):
        if not getattr(self, "lock_volume_to_one", True):
            if self.volume is None:
                self.volume = 0
            return

        kondisi = self.kondisi_barang or KondisiBarangChoices.BAIK
        self.volume = 0 if kondisi == KondisiBarangChoices.HILANG else 1

    def clean(self):
        super().clean()
        self._sync_locked_volume_by_condition()
        if self.status_barang != StatusBarangChoices.BMN:
            self.kode_aset_bmn = None
        if self.status_barang == StatusBarangChoices.BMN and not self.kode_aset_bmn:
            raise ValidationError(
                {
                    "kode_aset_bmn": "Kode Aset BMN wajib diisi untuk barang berstatus BMN."
                }
            )

    def sync_ketersediaan(self):
        self.kondisi_barang = self.kondisi_barang or KondisiBarangChoices.BAIK
        self.sedang_dipinjam = bool(self.sedang_dipinjam)
        is_tersedia = (
            self.kondisi_barang == KondisiBarangChoices.BAIK
            and not self.sedang_dipinjam
        )
        self.ketersediaan = (
            KetersediaanChoices.TERSEDIA
            if is_tersedia
            else KetersediaanChoices.TIDAK_TERSEDIA
        )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")

        self._sync_locked_volume_by_condition()
        if self.status_barang != StatusBarangChoices.BMN:
            self.kode_aset_bmn = None
        if self.sedang_dipinjam is None:
            self.sedang_dipinjam = False
        self.sync_ketersediaan()

        if update_fields is not None:
            extra_fields = {"volume", "ketersediaan", "updated_at"}
            if self.status_barang != StatusBarangChoices.BMN:
                extra_fields.add("kode_aset_bmn")
            kwargs["update_fields"] = set(update_fields).union(extra_fields)

        super().save(*args, **kwargs)

    @property
    def status_badge_class(self):
        return (
            "badge-success"
            if self.ketersediaan == KetersediaanChoices.TERSEDIA
            else "badge-danger"
        )


class BarangLaboratorium(AssetBaseModel):
    kategori_barang = models.CharField(
        max_length=40,
        choices=KategoriBarangLaboratoriumChoices.choices,
        null=True,
    )
    ik_alat = models.FileField(
        upload_to="master_data/ik_alat/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf"])],
    )

    class Meta(AssetBaseModel.Meta):
        verbose_name = "Data Peralatan Survei Lapangan"
        verbose_name_plural = "Data Peralatan Survei Lapangan"
        constraints = [
            models.UniqueConstraint(
                Lower("kode_laboratorium"),
                name="uq_survei_kode_lab_ci",
            ),
            models.UniqueConstraint(
                Lower("kode_aset_bmn"),
                name="uq_survei_kode_bmn_ci",
            ),
        ]

    def __str__(self):
        return self.nama_barang


class BarangPenunjangOperasional(models.Model):
    nama_barang = models.CharField(max_length=200)
    tipe_merek_barang = models.CharField(max_length=200)
    volume = models.PositiveIntegerField(default=1, validators=[MinValueValidator(0)])
    volume_rusak = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    satuan = models.CharField(
        max_length=20, choices=SatuanAsetChoices.choices, default=SatuanAsetChoices.UNIT
    )
    kategori_barang = models.CharField(
        max_length=60, choices=KategoriBarangPenunjangChoices.choices
    )
    volume_dipinjam = models.PositiveIntegerField(default=0)
    ketersediaan = models.CharField(
        max_length=20,
        choices=KetersediaanChoices.choices,
        default=KetersediaanChoices.TERSEDIA,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nama_barang"]
        verbose_name = "Data Barang Penunjang Lapangan"
        verbose_name_plural = "Data Barang Penunjang Lapangan"
        constraints = [
            models.UniqueConstraint(
                Lower("nama_barang"),
                name="uq_penunjang_nama_ci",
            ),
        ]

    def __str__(self):
        return self.nama_barang

    @property
    def volume_baik(self):
        return self.volume or 0

    @property
    def volume_pinjam_aktif(self):
        return getattr(self, "volume_dipinjam", 0) or 0

    @property
    def sisa_volume(self):
        return max((self.volume_baik or 0) - self.volume_pinjam_aktif, 0)

    @property
    def total_volume(self):
        return (self.volume or 0) + (self.volume_rusak or 0)

    @property
    def status_badge_class(self):
        return (
            "badge-success"
            if self.ketersediaan == KetersediaanChoices.TERSEDIA
            else "badge-danger"
        )

    def sync_ketersediaan(self):
        if self.volume is None:
            self.volume = 0
        if self.volume_rusak is None:
            self.volume_rusak = 0
        if self.volume_dipinjam is None:
            self.volume_dipinjam = 0
        self.ketersediaan = (
            KetersediaanChoices.TERSEDIA
            if self.sisa_volume > 0
            else KetersediaanChoices.TIDAK_TERSEDIA
        )

    def save(self, *args, **kwargs):
        self.sync_ketersediaan()
        super().save(*args, **kwargs)


class BahanOperasional(models.Model):
    nama_barang = models.CharField(max_length=200)
    kategori_barang = models.CharField(
        max_length=30,
        choices=KategoriBahanOperasionalChoices.choices,
        default=KategoriBahanOperasionalChoices.BAHAN_LAPANGAN,
    )
    volume = models.PositiveIntegerField(default=0)
    satuan = models.CharField(max_length=20, choices=SatuanBahanChoices.choices)
    stok_minimum = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    ketersediaan = models.CharField(
        max_length=10,
        choices=StatusStokBahanChoices.choices,
        default=StatusStokBahanChoices.HABIS,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nama_barang"]
        verbose_name = "Data Bahan Operasional"
        verbose_name_plural = "Data Bahan Operasional"
        constraints = [
            models.UniqueConstraint(
                Lower("nama_barang"),
                name="uq_bahan_nama_ci",
            ),
        ]

    def __str__(self):
        return self.nama_barang

    @property
    def status_badge_class(self):
        return {
            StatusStokBahanChoices.BAIK: "badge-primary",
            StatusStokBahanChoices.CUKUP: "badge-success",
            StatusStokBahanChoices.KURANG: "badge-warning",
            StatusStokBahanChoices.HABIS: "badge-danger",
        }.get(self.ketersediaan, "badge-secondary")

    def sync_ketersediaan(self):
        if self.volume == 0:
            self.ketersediaan = StatusStokBahanChoices.HABIS
            return

        if self.volume <= self.stok_minimum:
            self.ketersediaan = StatusStokBahanChoices.KURANG
            return

        if self.volume >= self.stok_minimum * 3:
            self.ketersediaan = StatusStokBahanChoices.BAIK
            return

        self.ketersediaan = StatusStokBahanChoices.CUKUP

    def save(self, *args, **kwargs):
        self.sync_ketersediaan()
        super().save(*args, **kwargs)


class VolumeBaikAssetMixin(models.Model):
    lock_volume_to_one = False

    volume_rusak = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        abstract = True

    @property
    def volume_baik(self):
        return self.volume or 0

    @property
    def volume_pinjam_aktif(self):
        return getattr(self, "volume_dipinjam", 0) or 0

    @property
    def sisa_volume(self):
        return max((self.volume_baik or 0) - self.volume_pinjam_aktif, 0)

    @property
    def total_volume(self):
        return (self.volume or 0) + (self.volume_rusak or 0)

    def _sync_bmn_volume_by_condition(self):
        if self.status_barang != StatusBarangChoices.BMN:
            return

        kondisi = self.kondisi_barang or KondisiBarangChoices.BAIK
        if kondisi == KondisiBarangChoices.BAIK:
            self.volume = 1
            self.volume_rusak = 0
        elif kondisi == KondisiBarangChoices.HILANG:
            self.volume = 0
            self.volume_rusak = 0
        else:
            self.volume = 0
            self.volume_rusak = 1

    def clean(self):
        super().clean()

        if self.status_barang == StatusBarangChoices.BMN:
            self._sync_bmn_volume_by_condition()
            return

        if self.volume is None:
            self.volume = 0
        if self.volume_rusak is None:
            self.volume_rusak = 0
        self.kode_aset_bmn = None
        self.kondisi_barang = KondisiBarangChoices.BAIK

    def sync_ketersediaan(self):
        if self.status_barang == StatusBarangChoices.BMN:
            self._sync_bmn_volume_by_condition()
            if hasattr(self, "volume_dipinjam"):
                self.sedang_dipinjam = self.volume_pinjam_aktif > 0
            return super().sync_ketersediaan()

        if self.volume is None:
            self.volume = 0
        if self.volume_rusak is None:
            self.volume_rusak = 0
        if hasattr(self, "volume_dipinjam") and self.volume_dipinjam is None:
            self.volume_dipinjam = 0
        self.sedang_dipinjam = self.volume_pinjam_aktif > 0
        self.kondisi_barang = KondisiBarangChoices.BAIK
        self.ketersediaan = (
            KetersediaanChoices.TERSEDIA
            if self.sisa_volume > 0
            else KetersediaanChoices.TIDAK_TERSEDIA
        )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")

        if self.status_barang == StatusBarangChoices.BMN:
            self._sync_bmn_volume_by_condition()
        else:
            if self.volume is None:
                self.volume = 0
            if self.volume_rusak is None:
                self.volume_rusak = 0
            if hasattr(self, "volume_dipinjam") and self.volume_dipinjam is None:
                self.volume_dipinjam = 0
            self.kode_aset_bmn = None
            self.kondisi_barang = KondisiBarangChoices.BAIK

        if self.sedang_dipinjam is None:
            self.sedang_dipinjam = False
        self.sync_ketersediaan()

        if update_fields is not None:
            extra_fields = {
                "volume",
                "volume_rusak",
                "kondisi_barang",
                "ketersediaan",
                "updated_at",
            }
            if hasattr(self, "volume_dipinjam"):
                extra_fields.add("volume_dipinjam")
                extra_fields.add("sedang_dipinjam")
            if self.status_barang != StatusBarangChoices.BMN:
                extra_fields.add("kode_aset_bmn")
            kwargs["update_fields"] = set(update_fields).union(extra_fields)

        super(AssetBaseModel, self).save(*args, **kwargs)


class FasilitasRuangan(VolumeBaikAssetMixin, AssetBaseModel):
    kategori_barang = models.CharField(
        max_length=30,
        choices=KategoriSaranaPrasaranaChoices.choices,
        default=KategoriSaranaPrasaranaChoices.FASILITAS_RUANGAN,
    )

    class Meta(AssetBaseModel.Meta):
        verbose_name = "Data Sarana Prasarana Ruangan"
        verbose_name_plural = "Data Sarana Prasarana Ruangan"

    def __str__(self):
        return self.nama_barang


class PeralatanLaboratorium(VolumeBaikAssetMixin, AssetBaseModel):
    volume_dipinjam = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta(AssetBaseModel.Meta):
        verbose_name = "Data Peralatan Laboratorium"
        verbose_name_plural = "Data Peralatan Laboratorium"
        constraints = [
            models.UniqueConstraint(
                Lower("kode_laboratorium"),
                name="uq_perlab_kode_lab_ci",
            ),
            models.UniqueConstraint(
                Lower("kode_aset_bmn"),
                name="uq_perlab_kode_bmn_ci",
            ),
        ]

    def __str__(self):
        return self.nama_barang
