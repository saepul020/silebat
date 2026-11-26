from .models import Pelatihan


def get_drh_data(user):
    return {
        'pendidikan': user.pendidikan.all(),
        'karir': user.riwayat_karir.all(),
        'pelatihan': Pelatihan.objects.filter(peserta__user=user).order_by('-tanggal_mulai', '-pk'),
        'portofolio': user.portofolio.all(),
    }
