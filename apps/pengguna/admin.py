from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Role, User, UserProfile


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
