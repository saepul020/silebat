from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboard.urls")),
    path("pengguna/", include("apps.pengguna.urls")),
    path("operasional/", include("apps.operasional.urls")),
    path("master-data/", include("apps.master_data.urls")),
    path("permintaan/", include("apps.peminjaman.urls")),
    path("verifikasi/", include("apps.verifikasi.urls")),
    path("notifikasi/", include("apps.notifikasi.urls")),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
