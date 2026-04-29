from datetime import date, datetime
import re

from django import forms
from django.core.exceptions import ValidationError

from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    apply_upload_widget_validation_attrs,
    build_max_upload_size_message,
    validate_uploaded_file,
)
from apps.operasional.models import (
    InstansiKlien,
    LayananKegiatan,
    SurveiKegiatan,
    TimKegiatan,
)

from .models import PeminjamanRequest


DATE_INPUT_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"]
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
DATE_HELP_TEXT = "Gunakan salah satu format: 01 Januari 2026, 01/01/2026, 01-01-2026, atau 01 Jan 2026."


def parse_flexible_date(value):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    raw_value = str(value).strip()
    if not raw_value:
        return None

    normalized_value = re.sub(r"\s+", " ", raw_value)

    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(normalized_value, fmt).date()
        except ValueError:
            continue

    month_name_match = re.fullmatch(
        r"(\d{1,2})\s+([A-Za-zÀ-ÿ.]+)\s+(\d{4})", normalized_value
    )
    if month_name_match:
        day = int(month_name_match.group(1))
        month_key = month_name_match.group(2).strip().lower().rstrip(".")
        year = int(month_name_match.group(3))
        month = MONTH_LOOKUP.get(month_key)
        if month:
            return date(year, month, day)

    numeric_match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", normalized_value)
    if numeric_match:
        day = int(numeric_match.group(1))
        month = int(numeric_match.group(2))
        year = int(numeric_match.group(3))
        return date(year, month, day)

    iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", normalized_value)
    if iso_match:
        year = int(iso_match.group(1))
        month = int(iso_match.group(2))
        day = int(iso_match.group(3))
        return date(year, month, day)

    raise ValueError("invalid date format")


class DateInput(forms.DateInput):
    input_type = "text"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("format", "%d %b %Y")
        attrs = kwargs.setdefault("attrs", {})
        attrs.setdefault(
            "placeholder",
            "Masukan tanggal sesuai format",
        )
        attrs.setdefault("autocomplete", "off")
        super().__init__(*args, **kwargs)


class FlexibleDateField(forms.DateField):
    default_error_messages = {
        "invalid": DATE_HELP_TEXT,
    }

    def to_python(self, value):
        if value in self.empty_values:
            return None

        if isinstance(value, date):
            if isinstance(value, datetime):
                return value.date()
            return value

        try:
            return parse_flexible_date(value)
        except (TypeError, ValueError):
            raise ValidationError(self.error_messages["invalid"], code="invalid")


class PeminjamanRequestForm(forms.ModelForm):
    tanggal_mulai = FlexibleDateField(
        input_formats=DATE_INPUT_FORMATS,
        widget=DateInput(),
        label="Mulai Tanggal",
        error_messages={
            "required": "Mulai tanggal wajib diisi.",
            "invalid": DATE_HELP_TEXT,
        },
    )
    tanggal_selesai = FlexibleDateField(
        input_formats=DATE_INPUT_FORMATS,
        widget=DateInput(),
        label="Selesai Tanggal",
        error_messages={
            "required": "Selesai tanggal wajib diisi.",
            "invalid": DATE_HELP_TEXT,
        },
    )
    kegiatan_survei = forms.ModelMultipleChoiceField(
        queryset=SurveiKegiatan.objects.order_by("jenis_survei"),
        required=False,
        label="Kegiatan Survei",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "survey-choice-input"}),
    )
    gunakan_survei_lainnya = forms.BooleanField(
        required=False,
        label="Lainnya",
    )
    gunakan_instansi_lainnya = forms.BooleanField(
        required=False,
        label="Instansi tujuan di luar daftar",
    )

    class Meta:
        model = PeminjamanRequest
        fields = [
            "layanan_kegiatan",
            "kegiatan_survei",
            "survei_lainnya",
            "tim_kegiatan",
            "berkas_pendukung",
            "instansi_tujuan",
            "instansi_tujuan_lainnya",
            "tanggal_mulai",
            "tanggal_selesai",
        ]
        labels = {
            "layanan_kegiatan": "Layanan Kegiatan",
            "survei_lainnya": "Kegiatan Survei Lainnya",
            "tim_kegiatan": "Tim Kegiatan Pelaksana",
            "berkas_pendukung": "Berkas Pendukung (opsional)",
            "instansi_tujuan": "Instansi Tujuan Kegiatan",
            "instansi_tujuan_lainnya": "Instansi Tujuan Lainnya",
        }
        widgets = {
            "survei_lainnya": forms.TextInput(
                attrs={
                    "placeholder": "Isi manual jika kegiatan survei tidak ada pada daftar."
                }
            ),
            "instansi_tujuan_lainnya": forms.TextInput(
                attrs={
                    "placeholder": "Isi manual jika instansi tujuan tidak ada pada daftar."
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["layanan_kegiatan"].queryset = LayananKegiatan.objects.order_by(
            "jenis_layanan"
        )
        self.fields["tim_kegiatan"].queryset = TimKegiatan.objects.order_by("nama_tim")
        self.fields["instansi_tujuan"].queryset = InstansiKlien.objects.order_by(
            "nama_instansi"
        )

        self.fields["layanan_kegiatan"].empty_label = "Pilih layanan kegiatan"
        self.fields["tim_kegiatan"].empty_label = "Pilih tim kegiatan"
        self.fields["instansi_tujuan"].empty_label = "Pilih instansi tujuan"

        self.fields["gunakan_survei_lainnya"].widget.attrs.update(
            {"class": "toggle-input"}
        )
        self.fields["gunakan_instansi_lainnya"].widget.attrs.update(
            {"class": "toggle-input"}
        )

        self.fields["layanan_kegiatan"].widget.attrs.update({"class": "select-input"})
        self.fields["tim_kegiatan"].widget.attrs.update({"class": "select-input"})
        self.fields["instansi_tujuan"].widget.attrs.update({"class": "select-input"})
        self.fields["berkas_pendukung"].widget = forms.FileInput(
            attrs={
                "accept": ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png",
                "data-inline-file-extensions": "pdf,jpg,jpeg,png",
                "data-inline-file-error": "Berkas pendukung hanya boleh berupa file PDF, JPG, JPEG, atau PNG.",
                "class": "input-file input-file--proxy",
                "data-inline-file-input": "true",
                "data-inline-file-placeholder": "Dokumen Permintaan Pengukuran/SPT",
            }
        )
        self.fields["tanggal_mulai"].widget.attrs.update(
            {
                "class": "date-input",
                "data-date-display": "true",
                "data-date-picker": "true",
            }
        )
        self.fields["tanggal_selesai"].widget.attrs.update(
            {
                "class": "date-input",
                "data-date-display": "true",
                "data-date-picker": "true",
                "data-requires-start-date": "true",
            }
        )

        self.fields["survei_lainnya"].widget.attrs.update(
            {"autocomplete": "off", "class": "text-input"}
        )
        self.fields["instansi_tujuan_lainnya"].widget.attrs.update(
            {"autocomplete": "off", "class": "text-input"}
        )

        self.fields["berkas_pendukung"].required = False
        self.fields["berkas_pendukung"].help_text = ""
        self.fields["berkas_pendukung"].error_messages.update(
            {"invalid": "Berkas pendukung hanya boleh berupa file PDF, JPG, JPEG, atau PNG."}
        )
        apply_upload_widget_validation_attrs(
            self.fields["berkas_pendukung"],
            allowed_extensions="pdf,jpg,jpeg,png",
            invalid_extension_message="Berkas pendukung hanya boleh berupa file PDF, JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Berkas Pendukung"),
        )

        self.fields["layanan_kegiatan"].required = True
        self.fields["layanan_kegiatan"].error_messages.update(
            {"required": "Layanan kegiatan wajib dipilih."}
        )
        self.fields["tim_kegiatan"].required = True
        self.fields["tim_kegiatan"].error_messages.update(
            {"required": "Tim kegiatan pelaksana wajib dipilih."}
        )
        self.fields["tanggal_mulai"].required = True
        self.fields["tanggal_selesai"].required = True

        if self.instance and self.instance.pk and not self.is_bound:
            self.fields["gunakan_survei_lainnya"].initial = bool(
                (self.instance.survei_lainnya or "").strip()
            )
            self.fields["gunakan_instansi_lainnya"].initial = bool(
                (self.instance.instansi_tujuan_lainnya or "").strip()
                and not self.instance.instansi_tujuan_id
            )

    def clean_berkas_pendukung(self):
        return validate_uploaded_file(
            self.cleaned_data.get("berkas_pendukung"),
            allowed_extensions={".pdf", ".jpg", ".jpeg", ".png"},
            invalid_extension_message="Berkas pendukung hanya boleh berupa file PDF, JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Berkas Pendukung"),
        )

    def clean(self):
        cleaned_data = super().clean()
        tanggal_mulai = cleaned_data.get("tanggal_mulai")
        tanggal_selesai = cleaned_data.get("tanggal_selesai")
        layanan_kegiatan = cleaned_data.get("layanan_kegiatan")
        tim_kegiatan = cleaned_data.get("tim_kegiatan")

        if not layanan_kegiatan:
            self.add_error("layanan_kegiatan", "Layanan kegiatan wajib dipilih.")
        if not tim_kegiatan:
            self.add_error("tim_kegiatan", "Tim kegiatan pelaksana wajib dipilih.")
        if not tanggal_mulai:
            self.add_error("tanggal_mulai", "Mulai tanggal wajib diisi.")
        if not tanggal_selesai:
            self.add_error("tanggal_selesai", "Selesai tanggal wajib diisi.")
        if tanggal_mulai and tanggal_selesai and tanggal_selesai < tanggal_mulai:
            self.add_error(
                "tanggal_selesai",
                "Tanggal selesai tidak boleh lebih awal dari tanggal mulai.",
            )

        gunakan_survei_lainnya = cleaned_data.get("gunakan_survei_lainnya")
        survei_lainnya = (cleaned_data.get("survei_lainnya") or "").strip()
        kegiatan_survei = cleaned_data.get("kegiatan_survei")
        if not kegiatan_survei and not survei_lainnya:
            self.add_error(
                "kegiatan_survei",
                "Pilih minimal satu kegiatan survei atau isi survei lainnya.",
            )
        if gunakan_survei_lainnya and not survei_lainnya:
            self.add_error("survei_lainnya", "Silakan isi kegiatan survei lainnya.")

        gunakan_instansi_lainnya = cleaned_data.get("gunakan_instansi_lainnya")
        instansi_tujuan = cleaned_data.get("instansi_tujuan")
        instansi_tujuan_lainnya = (
            cleaned_data.get("instansi_tujuan_lainnya") or ""
        ).strip()
        if not instansi_tujuan and not instansi_tujuan_lainnya:
            self.add_error(
                "instansi_tujuan", "Pilih instansi tujuan atau isi instansi lainnya."
            )
        if gunakan_instansi_lainnya and not instansi_tujuan_lainnya:
            self.add_error(
                "instansi_tujuan_lainnya", "Silakan isi instansi tujuan lainnya."
            )
        if instansi_tujuan and (gunakan_instansi_lainnya or instansi_tujuan_lainnya):
            self.add_error(
                "instansi_tujuan",
                "Pilih salah satu: instansi dari daftar atau isi instansi lainnya.",
            )
            self.add_error(
                "instansi_tujuan_lainnya",
                "Kosongkan kolom instansi lainnya jika sudah memilih dari daftar.",
            )

        return cleaned_data


class VerifikasiAksiForm(forms.Form):
    aksi = forms.ChoiceField(choices=[])
    catatan = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Tulis alasan / catatan verifikasi di sini.",
            }
        ),
        label="Catatan / Alasan",
    )

    def __init__(self, *args, action_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["aksi"].choices = action_choices or []
