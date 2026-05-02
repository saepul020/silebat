from django.urls import path
from . import views

app_name = 'pengguna'

urlpatterns = [
    path('', views.daftar_pengguna, name='daftar'),
    path('tambah/', views.tambah_pengguna, name='tambah'),
    path('import/', views.import_pengguna, name='import_pengguna'),
    path('export/', views.export_pengguna, name='export_pengguna'),
    path('import/download-format/', views.download_format_import_pengguna, name='download_format_import_pengguna'),
    path('<int:pk>/', views.detail_pengguna, name='detail'),
    path('<int:pk>/edit/', views.edit_pengguna, name='edit'),
    path('<int:pk>/hapus/', views.hapus_pengguna, name='hapus'),
]