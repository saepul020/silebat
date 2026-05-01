from django.urls import path

from . import views
from . import pengembalian_views
from . import import_riwayat

app_name = 'peminjaman'

urlpatterns = [
    path('', views.index, name='index'),
    path('list/', views.daftar_pengajuan, name='list'),
    path('tambah/', views.tambah_pengajuan, name='tambah'),
    path('<int:pk>/edit/', views.edit_pengajuan, name='edit'),
    path('<int:pk>/', views.detail_pengajuan, name='detail'),
    path('<int:pk>/pengembalian/', pengembalian_views.pengembalian_pengajuan, name='pengembalian'),
    path('<int:pk>/hapus/', views.hapus_pengajuan, name='hapus'),
    path('<int:pk>/pdf/', views.download_pdf, name='download_pdf'),
    path('<int:pk>/berita-acara/pdf/', views.download_berita_acara_pdf, name='download_berita_acara_pdf'),
    path('laporan/', views.laporan_peminjaman, name='laporan'),
    path('laporan/import-riwayat/', import_riwayat.import_riwayat_peminjaman, name='import_riwayat_peminjaman'),
    path('laporan/import-riwayat/download-format/', import_riwayat.download_format_import_riwayat_peminjaman, name='download_format_import_riwayat_peminjaman'),
    path('laporan/<int:pk>/', views.detail_laporan, name='laporan_detail'),
    path('laporan/<int:pk>/pdf/', views.download_laporan_pdf, name='download_laporan_pdf'),
]
