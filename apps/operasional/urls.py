from django.urls import path

from apps.core.permissions import app_access_required

from . import views

app_name = 'operasional'
operasional_guard = app_access_required('operasional')

urlpatterns = [
    path('', operasional_guard(views.index), name='index'),
    path('tim/', operasional_guard(views.data_tim), name='data_tim'),
    path('tim/tambah/', operasional_guard(views.tambah_tim), name='tambah_tim'),
    path('tim/<int:pk>/edit/', operasional_guard(views.edit_tim), name='edit_tim'),
    path('tim/<int:pk>/hapus/', operasional_guard(views.hapus_tim), name='hapus_tim'),
    path('layanan/', operasional_guard(views.data_layanan), name='data_layanan'),
    path('layanan/tambah/', operasional_guard(views.tambah_layanan), name='tambah_layanan'),
    path('layanan/<int:pk>/edit/', operasional_guard(views.edit_layanan), name='edit_layanan'),
    path('layanan/<int:pk>/hapus/', operasional_guard(views.hapus_layanan), name='hapus_layanan'),
    path('survei/', operasional_guard(views.data_survei), name='data_survei'),
    path('survei/tambah/', operasional_guard(views.tambah_survei), name='tambah_survei'),
    path('survei/<int:pk>/edit/', operasional_guard(views.edit_survei), name='edit_survei'),
    path('survei/<int:pk>/hapus/', operasional_guard(views.hapus_survei), name='hapus_survei'),
    path('instansi/', operasional_guard(views.data_instansi), name='data_instansi'),
    path('instansi/tambah/', operasional_guard(views.tambah_instansi), name='tambah_instansi'),
    path('instansi/import/', operasional_guard(views.import_instansi), name='import_instansi'),
    path('instansi/export/', operasional_guard(views.export_instansi), name='export_instansi'),
    path('instansi/import/download-format/', operasional_guard(views.download_format_import_instansi), name='download_format_import_instansi'),
    path('instansi/<int:pk>/edit/', operasional_guard(views.edit_instansi), name='edit_instansi'),
    path('instansi/<int:pk>/hapus/', operasional_guard(views.hapus_instansi), name='hapus_instansi'),
    path('kop-dokumen/', operasional_guard(views.data_kop_dokumen), name='data_kop_dokumen'),
    path('kop-dokumen/tambah/', operasional_guard(views.tambah_kop_dokumen), name='tambah_kop_dokumen'),
    path('kop-dokumen/<int:pk>/edit/', operasional_guard(views.edit_kop_dokumen), name='edit_kop_dokumen'),
]
