from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

ROLE_SUPER_ADMIN = "Super Admin"
ROLE_USER = "User"
ROLE_ADMIN_LAB = "Admin Lab"
ROLE_TEKNISI_LAB = "Teknisi Lab"
ROLE_KEPALA_LAB = "Kepala Lab"
ROLE_PIMPINAN = "Pimpinan"

FULL_LAB_ACCESS_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN_LAB, ROLE_TEKNISI_LAB}
MASTER_DATA_VIEW_ROLES = FULL_LAB_ACCESS_ROLES | {ROLE_KEPALA_LAB, ROLE_PIMPINAN}
MASTER_DATA_EXPORT_ROLES = FULL_LAB_ACCESS_ROLES | {ROLE_PIMPINAN}
VERIFICATION_ROLES = {
    ROLE_SUPER_ADMIN,
    ROLE_USER,
    ROLE_ADMIN_LAB,
    ROLE_TEKNISI_LAB,
    ROLE_KEPALA_LAB,
    ROLE_PIMPINAN,
}
REPORT_VERIFICATION_ROLES = VERIFICATION_ROLES


def get_role_name(user):
    if not getattr(user, "is_authenticated", False):
        return None

    try:
        role = user.safe_profile.role
    except Exception:  # pragma: no cover
        role = None

    return getattr(role, "nama", None)


def is_super_admin(user):
    return get_role_name(user) == ROLE_SUPER_ADMIN


def can_access_master_data(user):
    return get_role_name(user) in MASTER_DATA_VIEW_ROLES


def can_manage_master_data(user):
    return get_role_name(user) in FULL_LAB_ACCESS_ROLES


def can_import_master_data(user):
    return is_super_admin(user)


def can_export_master_data(user):
    return get_role_name(user) in MASTER_DATA_EXPORT_ROLES


def can_access_operasional(user):
    return is_super_admin(user)


def can_access_pengguna_app(user):
    return is_super_admin(user)


def can_access_peminjaman_app(user):
    return get_role_name(user) in VERIFICATION_ROLES


def can_access_pemeliharaan_app(user):
    return get_role_name(user) in VERIFICATION_ROLES


def can_access_verifikasi_app(user):
    return get_role_name(user) in VERIFICATION_ROLES


def can_view_user_detail(user, target_user):
    return can_access_pengguna_app(user) or (
        getattr(user, "is_authenticated", False) and user.pk == target_user.pk
    )


def can_edit_user(user, target_user):
    return can_view_user_detail(user, target_user)


def deny_access(request, message):
    messages.error(request, message)
    return redirect("dashboard:index")


def user_passes_access(test_func, message):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not getattr(request.user, "is_authenticated", False):
                return redirect_to_login(request.get_full_path())
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return deny_access(request, message)

        return _wrapped

    return decorator


def app_access_required(app_name):
    if app_name == "master_data":
        return user_passes_access(
            can_access_master_data,
            'Anda tidak memiliki akses ke app "Master Data".',
        )

    if app_name == "operasional":
        return user_passes_access(
            can_access_operasional,
            'App "Manajemen Operasional" hanya dapat diakses oleh Super Admin.',
        )

    if app_name == "pengguna":
        return user_passes_access(
            can_access_pengguna_app,
            'App "Pengguna" hanya dapat diakses oleh Super Admin.',
        )

    if app_name == "peminjaman":
        return user_passes_access(
            can_access_peminjaman_app,
            'Anda tidak memiliki akses ke app "Permintaan".',
        )

    if app_name == "pemeliharaan":
        return user_passes_access(
            can_access_pemeliharaan_app,
            'Anda tidak memiliki akses ke app "Pemeliharaan".',
        )

    if app_name == "verifikasi":
        return user_passes_access(
            can_access_verifikasi_app,
            'Anda tidak memiliki akses ke app "Verifikasi".',
        )

    raise ValueError(f"Unknown app_name: {app_name}")


def build_role_access(user):
    role_name = get_role_name(user)
    is_authenticated = getattr(user, "is_authenticated", False)

    return {
        "role_name": role_name,
        "is_super_admin": role_name == ROLE_SUPER_ADMIN,
        "can_manage_user_app": role_name == ROLE_SUPER_ADMIN,
        "show_dashboard": is_authenticated,
        "show_permintaan": role_name in VERIFICATION_ROLES,
        "show_permintaan_all_items": role_name in FULL_LAB_ACCESS_ROLES,
        "show_permintaan_peminjaman_only": role_name == ROLE_USER,
        "show_pemeliharaan": role_name in VERIFICATION_ROLES,
        "show_verifikasi": role_name in VERIFICATION_ROLES,
        "show_laporan": role_name in REPORT_VERIFICATION_ROLES,
        "show_laporan_all_items": role_name in REPORT_VERIFICATION_ROLES - {ROLE_USER},
        "show_laporan_peminjaman_only": role_name == ROLE_USER,
        "show_master_data": role_name in MASTER_DATA_VIEW_ROLES,
        "can_manage_master_data": role_name in FULL_LAB_ACCESS_ROLES,
        "can_import_master_data": role_name == ROLE_SUPER_ADMIN,
        "can_export_master_data": role_name in MASTER_DATA_EXPORT_ROLES,
        "show_operasional": role_name == ROLE_SUPER_ADMIN,
        "show_pengguna": is_authenticated,
        "show_pengguna_menu": is_authenticated,
        "show_data_pengguna": role_name == ROLE_SUPER_ADMIN,
    }
