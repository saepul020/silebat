import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


BOT_REPLIES = {
    "peminjaman": "Untuk peminjaman alat, silakan login ke SILEBAT melalui menu Login. Pastikan akun Anda sudah terdaftar dan aktif.",
    "login": "Silakan klik tombol Login di navbar atau buka halaman /login/ untuk mengakses sistem SILEBAT.",
    "alat": "Laboratorium memiliki berbagai peralatan survei dan laboratorium. Informasi ringkas alat utama dapat dilihat pada section Peralatan Survei di halaman ini.",
    "geolistrik": "Kegiatan geolistrik dapat mencakup pengukuran 1D dan 2D untuk mendukung investigasi kondisi bawah permukaan dan potensi air tanah.",
    "kualitas air": "Layanan kualitas air tanah mendukung pemeriksaan parameter lapangan maupun laboratorium sesuai kebutuhan kegiatan teknis.",
    "kontak": "Anda dapat menghubungi Laboratorium Balai Air Tanah melalui informasi kontak pada bagian footer halaman ini.",
    "silebat": "SILEBAT adalah Sistem Informasi Laboratorium Balai Air Tanah untuk mendukung pengelolaan peminjaman alat, kegiatan survei, dan data laboratorium secara terintegrasi.",
    "jam": "Layanan laboratorium mengikuti jam kerja kantor. Untuk kepastian jadwal, silakan hubungi kontak resmi laboratorium.",
    "drone": "Informasi drone atau alat pemetaan udara dapat dilihat pada section Peralatan Survei jika kontennya sudah dikonfigurasi oleh Super Admin.",
}

DEFAULT_REPLY = "Terima kasih atas pertanyaan Anda. Untuk informasi lebih detail, silakan login ke SILEBAT atau hubungi kontak resmi Laboratorium Balai Air Tanah."


def resolve_reply(message):
    normalized_message = (message or "").strip().lower()
    if not normalized_message:
        return "Silakan ketik pertanyaan Anda terlebih dahulu."

    for keyword, reply in BOT_REPLIES.items():
        if keyword in normalized_message:
            return reply
    return DEFAULT_REPLY


@csrf_exempt
@require_POST
def reply(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    message = payload.get("message", "")
    return JsonResponse({"reply": resolve_reply(message)})
