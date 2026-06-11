from django.urls import path

from . import views

app_name = 'verifikasi'

urlpatterns = [
    path('', views.index, name='index'),
    path('pemeliharaan/<int:pk>/', views.detail_pemeliharaan, name='detail_pemeliharaan'),
    path('<int:pk>/', views.detail, name='detail'),
]
