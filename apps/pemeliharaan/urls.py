from django.urls import path

from apps.core.permissions import app_access_required

from . import views


app_name = "pemeliharaan"
pemeliharaan_guard = app_access_required("pemeliharaan")

urlpatterns = [
    path("", pemeliharaan_guard(views.index), name="index"),
    path("list/", pemeliharaan_guard(views.daftar_pengajuan), name="list"),
    path("laporan/", pemeliharaan_guard(views.laporan_pemeliharaan), name="laporan"),
    path("laporan/<int:pk>/", pemeliharaan_guard(views.detail_laporan), name="laporan_detail"),
    path("laporan/<int:pk>/pdf/", pemeliharaan_guard(views.download_pdf), name="download_pdf"),
    path("tambah/", pemeliharaan_guard(views.tambah_pengajuan), name="tambah"),
    path("<int:pk>/edit/", pemeliharaan_guard(views.edit_pengajuan), name="edit"),
    path("<int:pk>/vendor/", pemeliharaan_guard(views.data_vendor), name="vendor"),
    path("<int:pk>/", pemeliharaan_guard(views.detail_pengajuan), name="detail"),
    path("<int:pk>/kirim/", pemeliharaan_guard(views.kirim_pengajuan), name="kirim"),
    path("<int:pk>/vendor/kirim/", pemeliharaan_guard(views.kirim_vendor), name="vendor_kirim"),
    path("<int:pk>/hapus/", pemeliharaan_guard(views.hapus_pengajuan), name="hapus"),
]
