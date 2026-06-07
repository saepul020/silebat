from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Case, IntegerField, Value, When


DEFAULT_ROLE_NAMES = [
    "Super Admin",
    "User",
    "Admin Lab",
    "Teknisi Lab",
    "Kepala Lab",
    "Pimpinan",
]

ROLE_RENAME_MAP = {
    "Admin": "Admin Lab",
    "Petugas Laboratorium": "Teknisi Lab",
    "Peminjam": "User",
    "Approver": "Kepala Lab",
    "Pimpinan": "Pimpinan",
}

ROLE_DESCRIPTIONS = {
    "Super Admin": "Semua akses tanpa pengecualian.",
    "User": "Dashboard, Permintaan Peminjaman, Laporan Peminjaman, Dashboard SDM, Data Pelatihan, serta detail dan edit profil milik sendiri.",
    "Admin Lab": "Semua app kecuali Data Pengguna. Tetap dapat membuka Dashboard SDM, Data Pelatihan, serta detail dan edit profil milik sendiri.",
    "Teknisi Lab": "Semua app kecuali Data Pengguna. Tetap dapat membuka Dashboard SDM, Data Pelatihan, serta detail dan edit profil milik sendiri.",
    "Kepala Lab": "Dashboard, Verifikasi, Laporan, Data Master baca-saja, Dashboard SDM, Data Pelatihan, serta detail dan edit profil milik sendiri.",
    "Pimpinan": "Dashboard, Verifikasi, Laporan, Data Master baca-saja dan export, Dashboard SDM, Data Pelatihan, serta detail dan edit profil milik sendiri.",
}


class Role(models.Model):
    nama = models.CharField(max_length=100, unique=True)
    deskripsi = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["nama"]

    def __str__(self):
        return self.nama


def sync_default_roles():
    for nama in DEFAULT_ROLE_NAMES:
        role, created = Role.objects.get_or_create(
            nama=nama,
            defaults={
                "is_active": True,
                "deskripsi": ROLE_DESCRIPTIONS.get(nama),
            },
        )

        updated_fields = []

        if not role.is_active:
            role.is_active = True
            updated_fields.append("is_active")

        deskripsi_baru = ROLE_DESCRIPTIONS.get(nama)
        if role.deskripsi != deskripsi_baru:
            role.deskripsi = deskripsi_baru
            updated_fields.append("deskripsi")

        if updated_fields:
            role.save(update_fields=updated_fields)


def get_default_role_queryset():
    sync_default_roles()
    ordering = Case(
        *[
            When(nama=nama, then=Value(index))
            for index, nama in enumerate(DEFAULT_ROLE_NAMES)
        ],
        default=Value(len(DEFAULT_ROLE_NAMES)),
        output_field=IntegerField(),
    )
    return Role.objects.filter(nama__in=DEFAULT_ROLE_NAMES, is_active=True).order_by(
        ordering, "nama"
    )


class User(AbstractUser):
    nip = models.CharField(max_length=50, blank=True, null=True, unique=True)
    no_hp = models.CharField(max_length=20, blank=True, null=True, unique=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def safe_profile(self):
        profile = getattr(self, "profile", None)
        if profile is not None:
            return profile
        profile, _ = UserProfile.objects.get_or_create(user=self)
        return profile


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    foto_profil = models.ImageField(upload_to="profile/", blank=True, null=True)
    ttd_digital = models.ImageField(upload_to="ttd_digital/", blank=True, null=True)
    jabatan = models.CharField(max_length=100, blank=True, null=True)
    nama_tim = models.ForeignKey(
        "operasional.TimKegiatan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anggota_pengguna",
    )
    alamat = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Profil {self.user.get_full_name() or self.user.username}"


class Pelatihan(models.Model):
    TIPE_INTERNAL = "Pelatihan Internal"
    TIPE_EKSTERNAL = "Pelatihan Eksternal"
    TIPE_CHOICES = [
        (TIPE_INTERNAL, TIPE_INTERNAL),
        (TIPE_EKSTERNAL, TIPE_EKSTERNAL),
    ]

    JENIS_LABORATORIUM = "Laboratorium"
    JENIS_NON_LABORATORIUM = "Non-Laboratorium"
    JENIS_CHOICES = [
        (JENIS_LABORATORIUM, JENIS_LABORATORIUM),
        (JENIS_NON_LABORATORIUM, JENIS_NON_LABORATORIUM),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="data_pelatihan",
    )
    tipe_pelatihan = models.CharField(max_length=30, choices=TIPE_CHOICES)
    jenis_pelatihan = models.CharField(max_length=30, choices=JENIS_CHOICES)
    nama_pelatihan = models.CharField(max_length=255)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    lokasi_pelatihan = models.CharField(max_length=255)
    uraian_pelatihan = models.TextField(default="")
    file_sertifikat = models.FileField(
        upload_to="pengguna/pelatihan/sertifikat/",
        blank=True,
        null=True,
    )
    file_materi = models.FileField(
        upload_to="pengguna/pelatihan/materi/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-tanggal_mulai", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-tanggal_mulai"]),
            models.Index(fields=["tipe_pelatihan", "jenis_pelatihan"]),
        ]

    def __str__(self):
        return self.nama_pelatihan

    @property
    def periode_pelatihan(self):
        if self.tanggal_mulai == self.tanggal_selesai:
            return self.tanggal_mulai
        return f"{self.tanggal_mulai} - {self.tanggal_selesai}"
