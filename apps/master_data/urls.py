from django.urls import path

from apps.core.permissions import app_access_required

from . import views

app_name = 'master_data'
master_data_guard = app_access_required('master_data')

urlpatterns = [
    path('public/peralatan-survei/<uuid:token>/', views.public_barang_laboratorium, name='public_barang_laboratorium'),
    path('public/barang-penunjang/<uuid:token>/', views.public_barang_penunjang, name='public_barang_penunjang'),
    path('public/bahan-operasional/<uuid:token>/', views.public_bahan_operasional, name='public_bahan_operasional'),
    path('public/fasilitas-ruangan/<uuid:token>/', views.public_fasilitas_ruangan, name='public_fasilitas_ruangan'),
    path('public/peralatan-laboratorium/<uuid:token>/', views.public_peralatan_laboratorium, name='public_peralatan_laboratorium'),

    path('', master_data_guard(views.index), name='index'),
    path('barang-laboratorium/', master_data_guard(views.data_barang_laboratorium), name='data_barang_laboratorium'),
    path('barang-laboratorium/tambah/', master_data_guard(views.tambah_barang_laboratorium), name='tambah_barang_laboratorium'),
    path('barang-laboratorium/import/', master_data_guard(views.import_barang_laboratorium), name='import_barang_laboratorium'),
    path('barang-laboratorium/import/download-format/', master_data_guard(views.download_format_import_barang_laboratorium), name='download_format_import_barang_laboratorium'),
    path('barang-laboratorium/<int:pk>/', master_data_guard(views.detail_barang_laboratorium), name='detail_barang_laboratorium'),
    path('barang-laboratorium/<int:pk>/edit/', master_data_guard(views.edit_barang_laboratorium), name='edit_barang_laboratorium'),
    path('barang-laboratorium/<int:pk>/hapus/', master_data_guard(views.hapus_barang_laboratorium), name='hapus_barang_laboratorium'),

    path('barang-penunjang/', master_data_guard(views.data_barang_penunjang), name='data_barang_penunjang'),
    path('barang-penunjang/tambah/', master_data_guard(views.tambah_barang_penunjang), name='tambah_barang_penunjang'),
    path('barang-penunjang/import/', master_data_guard(views.import_barang_penunjang), name='import_barang_penunjang'),
    path('barang-penunjang/import/download-format/', master_data_guard(views.download_format_import_barang_penunjang), name='download_format_import_barang_penunjang'),
    path('barang-penunjang/<int:pk>/edit/', master_data_guard(views.edit_barang_penunjang), name='edit_barang_penunjang'),
    path('barang-penunjang/<int:pk>/hapus/', master_data_guard(views.hapus_barang_penunjang), name='hapus_barang_penunjang'),

    path('bahan-operasional/', master_data_guard(views.data_bahan_operasional), name='data_bahan_operasional'),
    path('bahan-operasional/tambah/', master_data_guard(views.tambah_bahan_operasional), name='tambah_bahan_operasional'),
    path('bahan-operasional/import/', master_data_guard(views.import_bahan_operasional), name='import_bahan_operasional'),
    path('bahan-operasional/import/download-format/', master_data_guard(views.download_format_import_bahan_operasional), name='download_format_import_bahan_operasional'),
    path('bahan-operasional/<int:pk>/edit/', master_data_guard(views.edit_bahan_operasional), name='edit_bahan_operasional'),
    path('bahan-operasional/<int:pk>/hapus/', master_data_guard(views.hapus_bahan_operasional), name='hapus_bahan_operasional'),

    path('fasilitas-ruangan/', master_data_guard(views.data_fasilitas_ruangan), name='data_fasilitas_ruangan'),
    path('fasilitas-ruangan/tambah/', master_data_guard(views.tambah_fasilitas_ruangan), name='tambah_fasilitas_ruangan'),
    path('fasilitas-ruangan/import/', master_data_guard(views.import_fasilitas_ruangan), name='import_fasilitas_ruangan'),
    path('fasilitas-ruangan/import/download-format/', master_data_guard(views.download_format_import_fasilitas_ruangan), name='download_format_import_fasilitas_ruangan'),
    path('fasilitas-ruangan/<int:pk>/', master_data_guard(views.detail_fasilitas_ruangan), name='detail_fasilitas_ruangan'),
    path('fasilitas-ruangan/<int:pk>/edit/', master_data_guard(views.edit_fasilitas_ruangan), name='edit_fasilitas_ruangan'),
    path('fasilitas-ruangan/<int:pk>/hapus/', master_data_guard(views.hapus_fasilitas_ruangan), name='hapus_fasilitas_ruangan'),

    path('peralatan-laboratorium/', master_data_guard(views.data_peralatan_laboratorium), name='data_peralatan_laboratorium'),
    path('peralatan-laboratorium/tambah/', master_data_guard(views.tambah_peralatan_laboratorium), name='tambah_peralatan_laboratorium'),
    path('peralatan-laboratorium/import/', master_data_guard(views.import_peralatan_laboratorium), name='import_peralatan_laboratorium'),
    path('peralatan-laboratorium/import/download-format/', master_data_guard(views.download_format_import_peralatan_laboratorium), name='download_format_import_peralatan_laboratorium'),
    path('peralatan-laboratorium/<int:pk>/', master_data_guard(views.detail_peralatan_laboratorium), name='detail_peralatan_laboratorium'),
    path('peralatan-laboratorium/<int:pk>/edit/', master_data_guard(views.edit_peralatan_laboratorium), name='edit_peralatan_laboratorium'),
    path('peralatan-laboratorium/<int:pk>/hapus/', master_data_guard(views.hapus_peralatan_laboratorium), name='hapus_peralatan_laboratorium'),
]
