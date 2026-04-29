import re
from datetime import date, datetime, time

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Announcement

DATETIME_HELP_TEXT = "Gunakan format tanggal dan waktu yang sah. Contoh: 01 Januari 2026 08:30 atau 01/01/2026 08:30."

MONTH_LOOKUP = {
    "jan": 1,
    "januari": 1,
    "january": 1,
    "feb": 2,
    "februari": 2,
    "february": 2,
    "mar": 3,
    "maret": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "mei": 5,
    "may": 5,
    "jun": 6,
    "juni": 6,
    "june": 6,
    "jul": 7,
    "juli": 7,
    "july": 7,
    "agu": 8,
    "agustus": 8,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "okt": 10,
    "oktober": 10,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "des": 12,
    "desember": 12,
    "dec": 12,
    "december": 12,
}


class FlexibleDateTimeField(forms.DateTimeField):
    default_error_messages = {
        "invalid": DATETIME_HELP_TEXT,
    }

    def to_python(self, value):
        if value in self.empty_values:
            return None

        if isinstance(value, datetime):
            return self._ensure_timezone(value)

        if isinstance(value, date):
            return self._ensure_timezone(datetime.combine(value, time.min))

        raw_value = str(value or "").strip().replace(",", " ")
        if not raw_value:
            return None

        parsed = parse_datetime(raw_value)
        if parsed:
            return self._ensure_timezone(parsed)

        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M"):
            try:
                return self._ensure_timezone(datetime.strptime(raw_value, fmt))
            except ValueError:
                continue

        parsed = self._parse_text_datetime(raw_value)
        if parsed:
            return self._ensure_timezone(parsed)

        raise ValidationError(self.error_messages["invalid"], code="invalid")

    def _ensure_timezone(self, value):
        if value and timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value

    def _parse_text_datetime(self, value):
        match = re.match(
            r"^(?P<day>\d{1,2})\s+(?P<month>[A-Za-zÀ-ÿ.]+)\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})$",
            value,
            re.IGNORECASE,
        )
        if not match:
            return None

        month_key = (match.group("month") or "").lower().rstrip(".")
        month = MONTH_LOOKUP.get(month_key)
        if not month:
            return None

        try:
            return datetime(
                int(match.group("year")),
                month,
                int(match.group("day")),
                int(match.group("hour")),
                int(match.group("minute")),
            )
        except ValueError:
            return None


class AnnouncementForm(forms.ModelForm):
    publish_start_at = FlexibleDateTimeField(
        label="Mulai Ditampilkan",
        required=True,
        widget=forms.DateTimeInput(
            attrs={
                "class": "form-control date-input notif-datetime-input",
                "autocomplete": "off",
                "data-date-picker": "true",
                "data-notif-datetime": "start",
                "placeholder": "Masukan tanggal dan waktu sesuai format",
            },
            format="%d %b %Y %H:%M",
        ),
        error_messages={
            "required": "Mulai ditampilkan wajib diisi.",
            "invalid": DATETIME_HELP_TEXT,
        },
    )
    publish_end_at = FlexibleDateTimeField(
        label="Selesai Ditampilkan",
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                "class": "form-control date-input notif-datetime-input",
                "autocomplete": "off",
                "data-date-picker": "true",
                "data-requires-start-date": "true",
                "data-notif-datetime": "end",
                "placeholder": "Masukan tanggal dan waktu sesuai format",
            },
            format="%d %b %Y %H:%M",
        ),
        error_messages={"invalid": DATETIME_HELP_TEXT},
    )

    class Meta:
        model = Announcement
        fields = ["title", "message", "publish_start_at", "publish_end_at"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Contoh: Jadwal Maintenance Aplikasi",
                    "data-required-message": "Judul pengumuman wajib diisi.",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Tulis isi pengumuman yang akan dikirim ke seluruh user SILEBAT.",
                    "data-required-message": "Isi pengumuman wajib diisi.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].label = "Judul Pengumuman"
        self.fields["title"].error_messages.update({"required": "Judul pengumuman wajib diisi."})
        self.fields["message"].label = "Isi Pengumuman"
        self.fields["message"].error_messages.update({"required": "Isi pengumuman wajib diisi."})

    def clean(self):
        cleaned_data = super().clean()
        publish_start_at = cleaned_data.get("publish_start_at")
        publish_end_at = cleaned_data.get("publish_end_at")
        if publish_start_at and publish_end_at and publish_end_at < publish_start_at:
            self.add_error(
                "publish_end_at",
                "Selesai ditampilkan tidak boleh lebih awal dari mulai ditampilkan.",
            )
        return cleaned_data
