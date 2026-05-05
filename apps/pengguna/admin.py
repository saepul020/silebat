from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Pelatihan, Role, User, UserProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Tambahan', {'fields': ('nip', 'no_hp')}),
    )
    list_display = ('username', 'first_name', 'email', 'nip', 'no_hp', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'email', 'nip', 'no_hp')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nama', 'is_active')
    search_fields = ('nama',)
    list_filter = ('is_active',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'jabatan', 'nama_tim')
    search_fields = ('user__username', 'user__first_name', 'jabatan', 'nama_tim__nama_tim')
    list_select_related = ('user', 'role', 'nama_tim')


@admin.register(Pelatihan)
class PelatihanAdmin(admin.ModelAdmin):
    list_display = (
        'nama_pelatihan',
        'user',
        'tipe_pelatihan',
        'jenis_pelatihan',
        'tanggal_mulai',
        'tanggal_selesai',
    )
    list_filter = ('tipe_pelatihan', 'jenis_pelatihan')
    search_fields = ('nama_pelatihan', 'lokasi_pelatihan', 'uraian_pelatihan', 'user__username', 'user__first_name')
    list_select_related = ('user',)
