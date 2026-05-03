from django.urls import path

from . import views

app_name = "landing"

urlpatterns = [
    path("", views.public_home, name="home"),
    path("landing/peralatan/", views.equipment_list, name="equipment_list"),
    path("landing/peralatan/cek-urutan/", views.equipment_order_check, name="equipment_order_check"),
    path("landing/peralatan/tambah/", views.equipment_create, name="equipment_create"),
    path("landing/peralatan/<int:pk>/edit/", views.equipment_update, name="equipment_update"),
    path("landing/peralatan/<int:pk>/hapus/", views.equipment_delete, name="equipment_delete"),
]
