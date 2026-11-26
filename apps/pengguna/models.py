from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Case, F, IntegerField, Q, Value, When


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
    JENIS_KELAMIN_CHOICES = [('Laki-Laki', 'Laki-Laki'), ('Perempuan', 'Perempuan')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    tempat_lahir = models.CharField(max_length=100, blank=True)
    tanggal_lahir = models.DateField(blank=True, null=True)
    jenis_kelamin = models.CharField(max_length=10, choices=JENIS_KELAMIN_CHOICES, blank=True)
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


class Logbook(models.Model):
    LINGKUP_CHOICES = [(value, value) for value in (
        'Dukungan Manajemen', 'Laboratorium', 'Layanan Teknis', 'Pengembangan Penerapan',
    )]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logbook_input')
    lingkup = models.CharField('Lingkup Kegiatan', max_length=30, choices=LINGKUP_CHOICES)
    tanggal = models.DateField()
    uraian = models.TextField()
    dokumen = models.FileField(upload_to='pengguna/logbook/', blank=True)
    peserta_user = models.ManyToManyField(User, through='PesertaLogbook', related_name='logbook_diikuti')

    class Meta:
        ordering = ['-tanggal', '-pk']

    def __str__(self):
        return f'Logbook {self.tanggal}'


class PesertaLogbook(models.Model):
    logbook = models.ForeignKey(Logbook, on_delete=models.CASCADE, related_name='peserta')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='peserta_logbook')

    class Meta:
        ordering = ['pk']
        constraints = [models.UniqueConstraint(fields=['logbook', 'user'], name='logbook_user_unik')]


class Portofolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portofolio')
    nama = models.CharField(max_length=255)
    lokasi = models.CharField(max_length=255)
    uraian = models.JSONField(default=list)
    tahun = models.PositiveSmallIntegerField()
    dokumen = models.FileField(upload_to='pengguna/portofolio/', blank=True)
    nomor_dokumen = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-tahun', '-pk']

    def __str__(self):
        return self.nama


class RiwayatKarir(models.Model):
    STATUS_CHOICES = [(value, value) for value in ('Karyawan Tetap', 'Kontrak', 'Magang', 'Part-time', 'Freelance')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='riwayat_karir')
    perusahaan = models.CharField(max_length=255)
    jabatan = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField(blank=True, null=True)
    masih_bekerja = models.BooleanField(default=False)
    uraian = models.TextField()
    dokumen = models.FileField(upload_to='pengguna/karir/', blank=True)
    nomor_dokumen = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-tanggal_mulai', '-pk']
        constraints = [models.CheckConstraint(
            condition=(
                Q(masih_bekerja=True, tanggal_selesai__isnull=True)
                | (Q(masih_bekerja=False, tanggal_selesai__isnull=False)
                   & Q(tanggal_selesai__gte=F('tanggal_mulai')))
            ), name='karir_tanggal_urut',
        )]

    def __str__(self):
        return f'{self.jabatan} - {self.perusahaan}'

    @property
    def uraian_poin(self):
        return [line for line in self.uraian.splitlines() if line.strip()]


class Pendidikan(models.Model):
    TINGKAT_CHOICES = [(value, value) for value in (
        'SD / Sederajat', 'SMP / Sederajat', 'SMA / SMK / Sederajat',
        'Diploma I (D1)', 'Diploma II (D2)', 'Diploma III (D3)', 'Diploma IV (D4)',
        'Sarjana (S1)', 'Magister (S2)', 'Doktor (S3)',
    )]
    LOKASI_CHOICES = [('Dalam Negeri', 'Dalam Negeri'), ('Luar Negeri', 'Luar Negeri')]
    NILAI_CHOICES = [(value, value) for value in ('IPK', 'GPA', 'Nilai Rata-Rata Ijazah', 'Nilai US/UN')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pendidikan')
    tingkat = models.CharField(max_length=30, choices=TINGKAT_CHOICES)
    lokasi = models.CharField(max_length=15, choices=LOKASI_CHOICES)
    lembaga = models.CharField(max_length=255)
    jurusan = models.CharField(max_length=255, blank=True)
    tanggal_lulus = models.DateField()
    jenis_nilai = models.CharField(max_length=30, choices=NILAI_CHOICES)
    nilai = models.DecimalField(max_digits=7, decimal_places=2)
    ijazah = models.FileField(upload_to='pengguna/pendidikan/ijazah/')
    transkrip = models.FileField(upload_to='pengguna/pendidikan/transkrip/')

    class Meta:
        ordering = ['-tanggal_lulus', '-pk']

    def __str__(self):
        return f'{self.tingkat} - {self.lembaga}'


class Pelatihan(models.Model):
    KATEGORI_CHOICES = [(value, value) for value in ('Diklat', 'Pelatihan', 'Seminar', 'Workshop')]

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

    # Penginput disimpan sebagai atribusi; akses pelatihan mengikuti relasi peserta.
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="data_pelatihan",
        null=True,
        blank=True,
    )
    kategori_kegiatan = models.CharField(max_length=20, choices=KATEGORI_CHOICES)
    tipe_pelatihan = models.CharField(max_length=30, choices=TIPE_CHOICES)
    jenis_pelatihan = models.CharField(max_length=30, choices=JENIS_CHOICES)
    nama_pelatihan = models.CharField(max_length=255)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    lokasi_pelatihan = models.CharField(max_length=255)
    uraian_pelatihan = models.TextField(default="")
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


class PesertaPelatihan(models.Model):
    pelatihan = models.ForeignKey(Pelatihan, on_delete=models.CASCADE, related_name="peserta")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pelatihan_diikuti")
    file_sertifikat = models.FileField(
        upload_to="pengguna/pelatihan/sertifikat/", blank=True, null=True,
    )

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(fields=["pelatihan", "user"], name="pelatihan_user_unik"),
        ]

    def __str__(self):
        return self.user.get_full_name() or self.user.username


def get_sdm_users():
    return (
        User.objects.select_related("profile", "profile__role")
        .exclude(profile__role__nama="Super Admin")
        .order_by("first_name", "username")
    )
