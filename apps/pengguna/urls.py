from django.urls import path
from . import drh_views, excel_views, karir_views, logbook_views, pendidikan_views, portofolio_views, views

app_name = 'pengguna'

urlpatterns = [
    path('sdm/pelatihan/<int:pk>/materi/', views.sdm_materi, name='sdm_materi'),
    path('sdm/logbook/<int:pk>/preview/', views.sdm_preview, name='sdm_preview'),
    path('logbook/', logbook_views.daftar, name='logbook_daftar'),
    path('logbook/tambah/', logbook_views.form, name='logbook_tambah'),
    path('logbook/preview/', logbook_views.preview_upload, name='logbook_upload'),
    path('logbook/<int:pk>/preview/', logbook_views.preview, name='logbook_preview'),
    path('logbook/<int:pk>/edit/', logbook_views.form, name='logbook_edit'),
    path('logbook/<int:pk>/hapus/', logbook_views.hapus, name='logbook_hapus'),
    path('logbook/<int:pk>/dokumen/', logbook_views.dokumen, name='logbook_dokumen'),
    path('', views.daftar_pengguna, name='daftar'),
    path('sdm/', views.dashboard_sdm, name='dashboard_sdm'),
    path('data/', views.data_pengguna, name='data'),
    path('data/drh/', drh_views.download, name='drh_download'),
    path('portofolio/', portofolio_views.daftar, name='portofolio_daftar'),
    path('portofolio/tambah/', portofolio_views.form, name='portofolio_tambah'),
    path('portofolio/<int:pk>/edit/', portofolio_views.form, name='portofolio_edit'),
    path('portofolio/<int:pk>/hapus/', portofolio_views.hapus, name='portofolio_hapus'),
    path('portofolio/<int:pk>/dokumen/<str:jenis>/', portofolio_views.dokumen, name='portofolio_dokumen'),
    path('karir/', karir_views.daftar, name='karir_daftar'),
    path('karir/tambah/', karir_views.form, name='karir_tambah'),
    path('karir/<int:pk>/edit/', karir_views.form, name='karir_edit'),
    path('karir/<int:pk>/hapus/', karir_views.hapus, name='karir_hapus'),
    path('karir/<int:pk>/dokumen/<str:jenis>/', karir_views.dokumen, name='karir_dokumen'),
    path('pendidikan/', pendidikan_views.daftar, name='pendidikan_daftar'),
    path('pendidikan/tambah/', pendidikan_views.form, name='pendidikan_tambah'),
    path('pendidikan/<int:pk>/edit/', pendidikan_views.form, name='pendidikan_edit'),
    path('pendidikan/<int:pk>/hapus/', pendidikan_views.hapus, name='pendidikan_hapus'),
    path('pendidikan/<int:pk>/dokumen/<str:jenis>/', pendidikan_views.dokumen, name='pendidikan_dokumen'),
    path('pelatihan/', views.daftar_pelatihan, name='pelatihan_daftar'),
    path('pelatihan/tambah/', views.tambah_pelatihan, name='pelatihan_tambah'),
    path('pelatihan/<int:pk>/', views.detail_pelatihan, name='pelatihan_detail'),
    path('pelatihan/<int:pk>/materi/', views.download_materi, name='materi_download'),
    path('pelatihan/<int:pk>/sertifikat/<int:peserta_pk>/', views.preview_sertifikat, name='sertifikat_preview'),
    path('pelatihan/<int:pk>/edit/', views.edit_pelatihan, name='pelatihan_edit'),
    path('pelatihan/<int:pk>/hapus/', views.hapus_pelatihan, name='pelatihan_hapus'),
    path('tambah/', views.tambah_pengguna, name='tambah'),
    path('import/', views.import_pengguna, name='import_pengguna'),
    path('export/', views.export_pengguna, name='export_pengguna'),
    path('import/download-format/', views.download_format_import_pengguna, name='download_format_import_pengguna'),
    path('<int:pk>/', views.detail_pengguna, name='detail'),
    path('<int:pk>/edit/', views.edit_pengguna, name='edit'),
    path('<int:pk>/hapus/', views.hapus_pengguna, name='hapus'),
]

for kind in ('pelatihan', 'pendidikan', 'karir', 'portofolio', 'logbook'):
    urlpatterns += [
        path(f'{kind}/export/', excel_views.export, {'kind': kind}, name=f'{kind}_export'),
        path(f'{kind}/import/', excel_views.import_data, {'kind': kind}, name=f'{kind}_import'),
        path(f'{kind}/import/download-format/', excel_views.format_import,
             {'kind': kind}, name=f'{kind}_format'),
    ]
