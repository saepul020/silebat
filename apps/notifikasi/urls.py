from django.urls import path

from . import views

app_name = "notifikasi"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/baca/", views.baca_notifikasi, name="baca"),
    path("tandai-semua-dibaca/", views.tandai_semua_dibaca, name="tandai_semua_dibaca"),
    path("pengumuman/tambah/", views.tambah_pengumuman, name="tambah_pengumuman"),
    path("pengumuman/riwayat/", views.riwayat_pengumuman, name="riwayat_pengumuman"),
    path("pengumuman/<int:pk>/edit/", views.edit_pengumuman, name="edit_pengumuman"),
    path("pengumuman/<int:pk>/hapus/", views.hapus_pengumuman, name="hapus_pengumuman"),
]
