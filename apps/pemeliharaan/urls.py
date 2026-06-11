from django.urls import path

from apps.core.permissions import app_access_required

from . import views


app_name = "pemeliharaan"
pemeliharaan_guard = app_access_required("pemeliharaan")

urlpatterns = [
    path("", pemeliharaan_guard(views.index), name="index"),
    path("list/", pemeliharaan_guard(views.daftar_pengajuan), name="list"),
    path("tambah/", pemeliharaan_guard(views.tambah_pengajuan), name="tambah"),
    path("<int:pk>/edit/", pemeliharaan_guard(views.edit_pengajuan), name="edit"),
    path("<int:pk>/", pemeliharaan_guard(views.detail_pengajuan), name="detail"),
    path("<int:pk>/kirim/", pemeliharaan_guard(views.kirim_pengajuan), name="kirim"),
    path("<int:pk>/hapus/", pemeliharaan_guard(views.hapus_pengajuan), name="hapus"),
]
