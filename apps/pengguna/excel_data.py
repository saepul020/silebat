"""Definisi kolom Excel untuk data SDM; validasi domain memakai form existing."""

from .forms import KarirForm, LogbookForm, PelatihanForm, PendidikanForm, PortofolioForm
from .models import PesertaLogbook, PesertaPelatihan


EXCEL_DATA = {
    'pelatihan': {
        'form': PelatihanForm,
        'fields': ('kategori_kegiatan', 'tipe_pelatihan', 'jenis_pelatihan', 'nama_pelatihan',
                   'tanggal_mulai', 'tanggal_selesai', 'lokasi_pelatihan', 'uraian_pelatihan'),
        'sample': ('Pelatihan', 'Pelatihan Internal', 'Laboratorium', 'Analisis Sampel',
                   '01 Jan 2020', '02 Jan 2020', 'Bandung', 'Pengujian sampel laboratorium.'),
        'participants': PesertaPelatihan,
        'relation': 'pelatihan',
        'certificate': True,
    },
    'pendidikan': {
        'form': PendidikanForm,
        'fields': ('tingkat', 'lokasi', 'lembaga', 'jurusan', 'tanggal_lulus', 'jenis_nilai', 'nilai'),
        'sample': ('Sarjana (S1)', 'Dalam Negeri', 'Universitas Contoh', 'Kimia',
                   '01 Jan 2020', 'IPK', '3.50'),
    },
    'karir': {
        'form': KarirForm,
        'points': True,
        'fields': ('perusahaan', 'jabatan', 'status', 'tanggal_mulai', 'tanggal_selesai',
                   'masih_bekerja', 'uraian'),
        'sample': ('Instansi Contoh', 'Analis', 'Karyawan Tetap', '01 Jan 2020',
                   '31 Des 2021', 'Tidak', 'Analisis sampel\nMenyusun laporan'),
    },
    'portofolio': {
        'form': PortofolioForm,
        'points': True,
        'fields': ('nama', 'lokasi', 'uraian', 'tahun'),
        'sample': ('Proyek Contoh', 'Bandung', 'Analisis sampel\nMenyusun laporan', '2020'),
    },
    'logbook': {
        'form': LogbookForm,
        'fields': ('lingkup', 'tanggal', 'uraian'),
        'sample': ('Laboratorium', '01 Jan 2020', 'Pengujian sampel harian.'),
        'participants': PesertaLogbook,
        'relation': 'logbook',
    },
}


def excel_headers(config):
    headers = ['Username Pengguna']
    headers.extend(config['form'].base_fields[name].label or name for name in config['fields'])
    if config.get('participants'):
        headers.append('Username Peserta')
    return headers
