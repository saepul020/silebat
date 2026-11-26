from datetime import date, datetime
from io import BytesIO
import os
import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import is_super_admin
from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    apply_upload_widget_validation_attrs,
    build_max_upload_size_message,
    validate_uploaded_file,
)
from apps.operasional.models import TimKegiatan


from .models import Logbook, PesertaLogbook, Pendidikan, Pelatihan, PesertaPelatihan, Portofolio, RiwayatKarir, User, UserProfile, get_default_role_queryset, get_sdm_users
from .logbook_images import IMAGE_ERROR, read_image
from .drh_data import get_drh_data

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    Image = None


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
        attrs.setdefault("placeholder", "Masukan tanggal sesuai format")
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
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")


def _clean_digit_only_field(value, label):
    value = (value or "").strip()
    if not value:
        return None

    if not value.isdigit():
        raise forms.ValidationError(f"{label} hanya boleh berisi angka.")

    return value


def _apply_digit_only_attrs(field):
    field.widget.attrs.update(
        {
            "inputmode": "numeric",
            "pattern": "[0-9]*",
            "data-digits-only": "true",
            "title": f"{field.label} hanya boleh berisi angka.",
        }
    )


class UserForm(UserCreationForm):
    nama_lengkap = forms.CharField(
        required=True,
        label="Nama Lengkap dan Gelar",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Contoh: Dr. Suyadi, Ph.D.",
                "autocomplete": "off",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Masukkan email",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "nama_lengkap",
            "email",
            "nip",
            "no_hp",
            "password1",
            "password2",
        ]
        labels = {
            "username": "Username",
            "nip": "NIP / NIK",
            "no_hp": "Nomor HP",
        }
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan username",
                    "autocomplete": "off",
                }
            ),
            "nip": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan NIP",
                    "autocomplete": "off",
                }
            ),
            "no_hp": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan nomor HP",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_messages = {
            "username": "Username wajib diisi.",
            "nama_lengkap": "Nama lengkap dan gelar wajib diisi.",
            "email": "Email wajib diisi.",
            "nip": "NIP / NIK wajib diisi.",
            "no_hp": "Nomor HP wajib diisi.",
            "password1": "Kata sandi wajib diisi.",
            "password2": "Konfirmasi kata sandi wajib diisi.",
        }

        for field_name, message in required_messages.items():
            if field_name in self.fields:
                self.fields[field_name].required = True
                self.fields[field_name].error_messages["required"] = message
                self.fields[field_name].widget.attrs["required"] = "required"

        self.fields["username"].help_text = ""
        self.fields["nama_lengkap"].help_text = ""
        self.fields["email"].help_text = ""
        self.fields["nip"].help_text = ""
        self.fields["no_hp"].help_text = ""
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""

        self.fields["password1"].label = "Kata Sandi"
        self.fields["password2"].label = "Konfirmasi Kata Sandi"

        self.fields["password1"].widget.attrs.update(
            {
                "placeholder": "Masukkan kata sandi",
                "autocomplete": "new-password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "placeholder": "Ulangi kata sandi",
                "autocomplete": "new-password",
            }
        )

        _apply_digit_only_attrs(self.fields["nip"])
        _apply_digit_only_attrs(self.fields["no_hp"])

        if self.instance and self.instance.pk:
            self.fields["nama_lengkap"].initial = self.instance.get_full_name()

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        qs = User.objects.filter(username__iexact=username)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if username and qs.exists():
            raise forms.ValidationError("Username sudah digunakan.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        qs = User.objects.filter(email__iexact=email)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if email and qs.exists():
            raise forms.ValidationError("Email sudah digunakan.")
        return email

    def clean_nip(self):
        nip = _clean_digit_only_field(self.cleaned_data.get("nip"), "NIP / NIK")
        if not nip:
            return None

        qs = User.objects.filter(nip__iexact=nip)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("NIP sudah digunakan.")
        return nip

    def clean_no_hp(self):
        no_hp = _clean_digit_only_field(self.cleaned_data.get("no_hp"), "Nomor HP")
        if not no_hp:
            return None

        qs = User.objects.filter(no_hp__iexact=no_hp)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Nomor HP sudah digunakan.")
        return no_hp

    def clean_nama_lengkap(self):
        nama_lengkap = (self.cleaned_data.get("nama_lengkap") or "").strip()
        if not nama_lengkap:
            raise forms.ValidationError("Nama lengkap wajib diisi.")
        return " ".join(nama_lengkap.split())

    def validate_password_for_user(self, user, password_field_name="password2"):
        """
        Validasi password bawaan Django tetap dipakai, tetapi pesan error
        kekuatan password ditampilkan pada field Kata Sandi dan Konfirmasi
        Kata Sandi supaya perilakunya konsisten di UI.
        """
        password = self.cleaned_data.get(password_field_name)
        if not password:
            return

        try:
            password_validation.validate_password(password, user)
        except forms.ValidationError as error:
            self.add_error("password1", error)
            self.add_error("password2", error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["nama_lengkap"]
        user.last_name = ""

        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    nama_lengkap = forms.CharField(
        required=True,
        label="Nama Lengkap dan Gelar",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Contoh: Dr. Andi Saputra, S.T., M.T.",
                "autocomplete": "off",
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Masukkan email",
                "autocomplete": "off",
            }
        ),
    )

    password_lama = forms.CharField(
        required=False,
        label="Password Lama",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Masukkan password lama",
                "autocomplete": "new-password",
                "readonly": "readonly",
                "data-unlock-readonly": "true",
            }
        ),
    )

    password_baru1 = forms.CharField(
        required=False,
        label="Password Baru",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Masukkan password baru",
                "autocomplete": "new-password",
                "readonly": "readonly",
                "data-unlock-readonly": "true",
            }
        ),
    )

    password_baru2 = forms.CharField(
        required=False,
        label="Konfirmasi Password Baru",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Ulangi password baru",
                "autocomplete": "new-password",
                "readonly": "readonly",
                "data-unlock-readonly": "true",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "nama_lengkap",
            "email",
            "nip",
            "no_hp",
        ]
        labels = {
            "username": "Username",
            "nip": "NIP / NIK",
            "no_hp": "Nomor HP",
        }
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan username",
                    "autocomplete": "off",
                }
            ),
            "nip": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan NIP",
                    "autocomplete": "off",
                }
            ),
            "no_hp": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan nomor HP",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.allow_username_edit = kwargs.pop("allow_username_edit", False)
        super().__init__(*args, **kwargs)

        self.fields["username"].help_text = ""
        self.fields["nama_lengkap"].help_text = ""
        self.fields["email"].help_text = ""
        self.fields["nip"].help_text = ""
        self.fields["no_hp"].help_text = ""
        self.fields["password_lama"].help_text = ""
        self.fields["password_baru1"].help_text = ""
        self.fields["password_baru2"].help_text = ""

        if self.instance and self.instance.pk:
            self.fields["nama_lengkap"].initial = self.instance.get_full_name()

        _apply_digit_only_attrs(self.fields["nip"])
        _apply_digit_only_attrs(self.fields["no_hp"])

        if not self.allow_username_edit:
            self.fields["username"].disabled = True
            self.fields["username"].widget.attrs.update(
                {
                    "readonly": "readonly",
                    "aria-readonly": "true",
                }
            )
            self.fields[
                "username"
            ].help_text = "Username hanya dapat diubah oleh Super Admin."

    def clean_username(self):
        if not self.allow_username_edit and self.instance.pk:
            return self.instance.username

        username = (self.cleaned_data.get("username") or "").strip()
        qs = User.objects.filter(username__iexact=username)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if username and qs.exists():
            raise forms.ValidationError("Username sudah digunakan.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        qs = User.objects.filter(email__iexact=email)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if email and qs.exists():
            raise forms.ValidationError("Email sudah digunakan.")
        return email

    def clean_nip(self):
        nip = _clean_digit_only_field(self.cleaned_data.get("nip"), "NIP / NIK")
        if not nip:
            return None

        qs = User.objects.filter(nip__iexact=nip)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("NIP sudah digunakan.")
        return nip

    def clean_no_hp(self):
        no_hp = _clean_digit_only_field(self.cleaned_data.get("no_hp"), "Nomor HP")
        if not no_hp:
            return None

        qs = User.objects.filter(no_hp__iexact=no_hp)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Nomor HP sudah digunakan.")
        return no_hp

    def clean_nama_lengkap(self):
        nama_lengkap = (self.cleaned_data.get("nama_lengkap") or "").strip()
        if not nama_lengkap:
            raise forms.ValidationError("Nama lengkap wajib diisi.")
        return " ".join(nama_lengkap.split())

    def clean(self):
        cleaned_data = super().clean()

        password_lama = cleaned_data.get("password_lama")
        password_baru1 = cleaned_data.get("password_baru1")
        password_baru2 = cleaned_data.get("password_baru2")

        ingin_ganti_password = bool(password_lama or password_baru1 or password_baru2)

        if ingin_ganti_password:
            if not password_lama:
                self.add_error("password_lama", "Password lama wajib diisi.")
            elif not self.instance.check_password(password_lama):
                self.add_error("password_lama", "Password lama tidak sesuai.")

            if not password_baru1:
                self.add_error("password_baru1", "Password baru wajib diisi.")

            if not password_baru2:
                self.add_error(
                    "password_baru2", "Konfirmasi password baru wajib diisi."
                )

            if password_baru1 and password_baru2 and password_baru1 != password_baru2:
                self.add_error("password_baru2", "Konfirmasi password baru tidak sama.")

            if password_baru1:
                try:
                    password_validation.validate_password(password_baru1, self.instance)
                except forms.ValidationError as error:
                    self.add_error("password_baru1", error)
                    self.add_error("password_baru2", error)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["nama_lengkap"]
        user.last_name = ""

        password_baru1 = self.cleaned_data.get("password_baru1")
        if password_baru1:
            user.set_password(password_baru1)

        if commit:
            user.save()
        return user

    def password_changed(self):
        return bool(self.cleaned_data.get("password_baru1"))


class UserProfileForm(forms.ModelForm):
    tanggal_lahir = FlexibleDateField(
        label='Tanggal Lahir', required=False,
        widget=DateInput(attrs={'class': 'date-input', 'data-user-date-picker': 'true'}),
    )
    hapus_foto_profil = forms.BooleanField(required=False, widget=forms.HiddenInput())
    hapus_ttd_digital = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = UserProfile
        fields = [
            "role",
            "tempat_lahir",
            "tanggal_lahir",
            "jenis_kelamin",
            "foto_profil",
            "ttd_digital",
            "jabatan",
            "nama_tim",
            "alamat",
        ]
        labels = {
            "role": "Peran",
            "tempat_lahir": "Tempat Lahir",
            "jenis_kelamin": "Jenis Kelamin",
            "foto_profil": "Foto Profil",
            "ttd_digital": "TTD Digital",
            "jabatan": "Jabatan",
            "nama_tim": "Divisi Tim Kegiatan",
            "alamat": "Alamat",
        }
        widgets = {
            "tempat_lahir": forms.TextInput(attrs={"placeholder": "Masukkan tempat lahir"}),
            "foto_profil": forms.FileInput(
                attrs={
                    "accept": ".jpg,.jpeg,.png",
                    "class": "input-file--proxy",
                    "data-preview-target": "foto-profil-preview",
                    "data-inline-file-input": "true",
                    "data-inline-file-placeholder": "Pilih file",
                    "data-inline-file-extensions": "jpg,jpeg,png",
                    "data-inline-file-error": "Foto Profil hanya boleh berupa file JPG, JPEG, atau PNG.",
                }
            ),
            "ttd_digital": forms.FileInput(
                attrs={
                    "accept": ".jpg,.jpeg,.png",
                    "class": "input-file--proxy",
                    "data-preview-target": "ttd-digital-preview",
                    "data-inline-file-input": "true",
                    "data-inline-file-placeholder": "Pilih file",
                    "data-inline-file-extensions": "jpg,jpeg,png",
                    "data-inline-file-error": "TTD Digital hanya boleh berupa file JPG, JPEG, atau PNG.",
                }
            ),
            "jabatan": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan jabatan",
                    "autocomplete": "off",
                }
            ),
            "nama_tim": forms.Select(
                attrs={
                    "autocomplete": "off",
                }
            ),
            "alamat": forms.Textarea(
                attrs={
                    "placeholder": "Masukkan alamat",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.allow_role_edit = kwargs.pop("allow_role_edit", False)
        self.require_role = kwargs.pop("require_role", False)
        super().__init__(*args, **kwargs)

        for field_name in self.fields:
            self.fields[field_name].help_text = ""

        self.fields["role"].queryset = get_default_role_queryset()
        self.fields['jenis_kelamin'].choices = [('', 'Pilih jenis kelamin')] + UserProfile.JENIS_KELAMIN_CHOICES
        self.fields["role"].empty_label = "Pilih role pengguna"
        self.fields["role"].required = self.require_role
        self.fields["role"].error_messages["required"] = "Peran wajib dipilih."
        if self.require_role:
            self.fields["role"].widget.attrs["required"] = "required"
        else:
            self.fields["role"].widget.attrs.pop("required", None)

        if not self.allow_role_edit:
            self.fields["role"].disabled = True
            self.fields["role"].help_text = "Role hanya dapat diubah oleh Super Admin."

        self.fields["nama_tim"].queryset = TimKegiatan.objects.select_related(
            "ketua_tim"
        ).order_by("nama_tim")
        self.fields["nama_tim"].empty_label = "Pilih divisi tim kegiatan"

        self.fields["foto_profil"].widget.attrs.update(
            {
                "accept": ".jpg,.jpeg,.png",
                "class": "input-file--proxy",
                "data-preview-target": "foto-profil-preview",
                "data-inline-file-input": "true",
                "data-inline-file-placeholder": "Pilih file",
                "data-inline-file-extensions": "jpg,jpeg,png",
                "data-inline-file-error": "Foto Profil hanya boleh berupa file JPG, JPEG, atau PNG.",
            }
        )
        self.fields["ttd_digital"].widget.attrs.update(
            {
                "accept": ".jpg,.jpeg,.png",
                "class": "input-file--proxy",
                "data-preview-target": "ttd-digital-preview",
                "data-inline-file-input": "true",
                "data-inline-file-placeholder": "Pilih file",
                "data-inline-file-extensions": "jpg,jpeg,png",
                "data-inline-file-error": "TTD Digital hanya boleh berupa file JPG, JPEG, atau PNG.",
            }
        )

        apply_upload_widget_validation_attrs(
            self.fields["foto_profil"],
            allowed_extensions="jpg,jpeg,png",
            invalid_extension_message="Foto Profil hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Foto Profil"),
        )
        apply_upload_widget_validation_attrs(
            self.fields["ttd_digital"],
            allowed_extensions="jpg,jpeg,png",
            invalid_extension_message="TTD Digital hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("TTD Digital"),
        )

    def clean_foto_profil(self):
        return validate_uploaded_file(
            self.cleaned_data.get("foto_profil"),
            allowed_extensions={".jpg", ".jpeg", ".png"},
            invalid_extension_message="Foto Profil hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Foto Profil"),
        )

    def clean_ttd_digital(self):
        return validate_uploaded_file(
            self.cleaned_data.get("ttd_digital"),
            allowed_extensions={".jpg", ".jpeg", ".png"},
            invalid_extension_message="TTD Digital hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("TTD Digital"),
        )

    def clean_role(self):
        if not self.allow_role_edit and self.instance.pk:
            return self.instance.role

        role = self.cleaned_data.get("role")
        if self.require_role and not role:
            raise forms.ValidationError("Peran wajib dipilih.")
        return role

    def _get_uploaded_file_bytes(self, uploaded_file):
        if not uploaded_file:
            return b""

        if hasattr(uploaded_file, "open"):
            try:
                uploaded_file.open("rb")
            except TypeError:
                uploaded_file.open()
            except Exception:
                pass

        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        try:
            file_bytes = uploaded_file.read()
        except ValueError:
            file_obj = getattr(uploaded_file, "file", None)
            if file_obj and hasattr(file_obj, "seek"):
                file_obj.seek(0)
                file_bytes = file_obj.read()
            else:
                raise

        if hasattr(uploaded_file, "seek"):
            try:
                uploaded_file.seek(0)
            except Exception:
                pass

        return file_bytes

    def _crop_profile_image(self, uploaded_file, filename_prefix="img"):
        if not uploaded_file or Image is None:
            return uploaded_file

        file_bytes = self._get_uploaded_file_bytes(uploaded_file)
        image = Image.open(BytesIO(file_bytes))

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if image.mode in ("LA", "P") else "RGB")

        width, height = image.size
        scale = max(1, min(width // 2, height // 3))
        image = ImageOps.fit(image, (2 * scale, 3 * scale))

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".png"

        output = BytesIO()
        save_format = "PNG" if ext == ".png" else "WEBP" if ext == ".webp" else "JPEG"

        if save_format == "JPEG" and image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background

        if save_format == "JPEG" and image.mode != "RGB":
            image = image.convert("RGB")

        image.save(output, format=save_format, quality=95, optimize=True)
        output.seek(0)

        safe_name = f"{filename_prefix}{ext}"
        return ContentFile(output.read(), name=safe_name)

    def _get_uploaded_file_from_request(self, field_name):
        return self.files.get(self.add_prefix(field_name))

    def save(self, commit=True):
        persisted_profile = None
        if self.instance.pk:
            persisted_profile = (
                type(self.instance)._default_manager.filter(pk=self.instance.pk).first()
            )

        old_foto_profil = getattr(persisted_profile, "foto_profil", None)
        old_ttd_digital = getattr(persisted_profile, "ttd_digital", None)

        new_foto_profil = self._get_uploaded_file_from_request("foto_profil")
        new_ttd_digital = self._get_uploaded_file_from_request("ttd_digital")

        profile = super().save(commit=False)

        if self.cleaned_data.get("hapus_foto_profil"):
            profile.foto_profil = None
        elif new_foto_profil:
            profile.foto_profil = self._crop_profile_image(
                new_foto_profil, filename_prefix="foto_profil"
            )
        elif persisted_profile is not None:
            profile.foto_profil = old_foto_profil

        if self.cleaned_data.get("hapus_ttd_digital"):
            profile.ttd_digital = None
        elif new_ttd_digital:
            profile.ttd_digital = new_ttd_digital
        elif persisted_profile is not None:
            profile.ttd_digital = old_ttd_digital

        if commit:
            profile.save()
        return profile


def _require_fields(form, choices, files):
    for name, field in form.fields.items():
        field.required = True
        action = 'dipilih' if name in choices else 'diunggah' if name in files else 'diisi'
        message = f'{field.label} wajib {action}.'
        field.error_messages['required'] = message
        field.widget.attrs['data-required-message'] = message


def _document_fields(form, names):
    for name in names:
        field = form.fields[name]
        field.widget.attrs.update({
            'accept': '.jpg,.jpeg,.png,.pdf', 'class': 'input-file--proxy',
            'data-inline-file-input': 'true', 'data-inline-file-skip-required': 'true',
            'data-inline-file-placeholder': 'Pilih file ' + field.label.lower(),
            'data-has-file': str(bool(getattr(form.instance, name, None))).lower(),
        })
        field.help_text = 'JPG, JPEG, PNG, atau PDF. Maksimal 7 MB.'
        apply_upload_widget_validation_attrs(
            field, allowed_extensions='jpg,jpeg,png,pdf',
            invalid_extension_message=f'{field.label} harus berupa JPG, JPEG, PNG, atau PDF.',
            max_size_message=build_max_upload_size_message(field.label),
        )


def _clean_documents(form, cleaned, names):
    for name in names:
        if name not in cleaned or form.add_prefix(name) not in form.files:
            continue
        try:
            validate_uploaded_file(
                cleaned[name], allowed_extensions={'.jpg', '.jpeg', '.png', '.pdf'},
                invalid_extension_message=f'{form.fields[name].label} harus berupa JPG, JPEG, PNG, atau PDF.',
                max_size_message=build_max_upload_size_message(form.fields[name].label),
            )
        except forms.ValidationError as error:
            form.add_error(name, error)


def _document_number(form):
    _document_fields(form, ('dokumen',))
    has_document = bool(form.files.get(form.add_prefix('dokumen')) or form.instance.dokumen)
    form.fields['dokumen'].required = False
    form.fields['nomor_dokumen'].required = has_document
    if not has_document:
        form.fields['nomor_dokumen'].widget.attrs.update({'disabled': True, 'aria-disabled': 'true'})


def _clean_support(form, cleaned):
    _clean_documents(form, cleaned, ('dokumen',))
    if not cleaned.get('dokumen'):
        cleaned['nomor_dokumen'] = ''


class PoinWidget(forms.Widget):
    template_name = 'pengguna/poin_input.html'

    def value_from_datadict(self, data, files, name):
        if hasattr(data, 'getlist'):
            return data.getlist(name)
        value = data.get(name, [])
        return value if isinstance(value, list) else [value]

    def id_for_label(self, id_):
        return id_ + '_0' if id_ else ''

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['rows'] = value if isinstance(value, list) and value else ['']
        context['widget']['row_label'] = self.attrs.get('data-point-label', 'Tugas')
        context['widget']['field_label'] = self.attrs.get('data-point-name', 'uraian tugas')
        return context


class PoinField(forms.Field):
    widget = PoinWidget

    def __init__(self, *args, row_label='Tugas', **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({'data-point-label': row_label, 'data-point-name': self.label.lower()})

    def to_python(self, value):
        if value in self.empty_values:
            return []
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise forms.ValidationError(f'{self.label} harus berupa daftar poin teks.')
        return [item.strip() for item in value]

    def validate(self, value):
        super().validate(value)
        if any(not item for item in value):
            raise forms.ValidationError(f'Setiap poin {self.label.lower()} wajib diisi.')
        if any(len(item) > 1000 for item in value):
            raise forms.ValidationError(f'Setiap poin {self.label.lower()} maksimal 1000 karakter.')


class PortofolioForm(forms.ModelForm):
    uraian = PoinField(label='Uraian Tugas')
    tahun = forms.TypedChoiceField(label='Tahun Kegiatan', coerce=int)

    class Meta:
        model = Portofolio
        fields = ['nama', 'lokasi', 'uraian', 'tahun', 'dokumen', 'nomor_dokumen']
        labels = {
            'nama': 'Nama Proyek', 'lokasi': 'Lokasi Proyek (Instansi / Daerah)',
            'dokumen': 'Dokumen Pendukung', 'nomor_dokumen': 'Nomor Dokumen',
        }
        widgets = {
            'nama': forms.Textarea(attrs={'placeholder': 'Masukkan nama proyek', 'rows': 3}),
            'lokasi': forms.TextInput(attrs={'placeholder': 'Masukkan instansi / daerah proyek'}),
            'dokumen': forms.FileInput(),
            'nomor_dokumen': forms.TextInput(attrs={'placeholder': 'Masukkan nomor dokumen'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _require_fields(self, ('tahun',), ('dokumen',))
        _document_number(self)
        self.fields['tahun'].choices = [('', 'Pilih tahun kegiatan')] + [
            (year, str(year)) for year in range(timezone.localdate().year, 1899, -1)
        ]

    def clean(self):
        cleaned = super().clean()
        _clean_support(self, cleaned)
        return cleaned


class KarirForm(forms.ModelForm):
    uraian = PoinField(label='Uraian Tugas')

    tanggal_mulai = FlexibleDateField(
        label='Tanggal Mulai', widget=DateInput(attrs={
            'class': 'date-input', 'data-user-date-picker': 'true', 'data-user-start-date': 'true',
        }),
    )
    tanggal_selesai = FlexibleDateField(
        label='Tanggal Selesai', widget=DateInput(attrs={
            'class': 'date-input', 'data-user-date-picker': 'true', 'data-user-end-date': 'true',
        }),
    )

    class Meta:
        model = RiwayatKarir
        fields = ['perusahaan', 'jabatan', 'status', 'tanggal_mulai', 'tanggal_selesai',
                  'masih_bekerja', 'uraian', 'dokumen', 'nomor_dokumen']
        labels = {
            'perusahaan': 'Nama Perusahaan / Instansi', 'jabatan': 'Jabatan / Posisi',
            'status': 'Status',
            'dokumen': 'Dokumen Pendukung', 'nomor_dokumen': 'Nomor Dokumen',
            'masih_bekerja': 'Masih Bekerja',
        }
        widgets = {
            'perusahaan': forms.TextInput(attrs={'placeholder': 'Masukkan nama perusahaan / instansi'}),
            'jabatan': forms.TextInput(attrs={'placeholder': 'Masukkan jabatan / posisi'}),
            'dokumen': forms.FileInput(),
            'nomor_dokumen': forms.TextInput(attrs={'placeholder': 'Masukkan nomor dokumen'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and isinstance(self.initial.get('uraian'), str):
            self.initial['uraian'] = [line for line in self.initial['uraian'].splitlines() if line.strip()]
        _require_fields(self, ('status',), ('dokumen',))
        self.fields['masih_bekerja'].required = False
        self.fields['masih_bekerja'].widget.attrs.pop('data-required-message', None)
        working = bool(self['masih_bekerja'].value())
        self.fields['tanggal_selesai'].required = not working
        if self['tanggal_selesai'].value() and not working:
            self.fields['masih_bekerja'].widget.attrs.update({'disabled': True, 'aria-disabled': 'true'})
        _document_number(self)
        self.fields['status'].choices = [('', 'Pilih status')] + RiwayatKarir.STATUS_CHOICES
        try:
            has_start = bool(parse_flexible_date(self['tanggal_mulai'].value()))
        except (ValueError, TypeError):
            has_start = False
        if not has_start or working:
            self.fields['tanggal_selesai'].widget.attrs.update({'disabled': True, 'aria-disabled': 'true'})

    def clean_uraian(self):
        return '\n'.join(self.cleaned_data['uraian'])

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('tanggal_mulai'), cleaned.get('tanggal_selesai')
        if cleaned.get('masih_bekerja') and end:
            self.add_error('tanggal_selesai', 'Kosongkan tanggal selesai jika masih bekerja.')
        elif start and end and end < start:
            self.add_error('tanggal_selesai', 'Tanggal selesai tidak boleh lebih awal dari tanggal mulai.')
        _clean_support(self, cleaned)
        return cleaned


class PendidikanForm(forms.ModelForm):
    NILAI_BATAS = {'IPK': 4, 'GPA': 100, 'Nilai Rata-Rata Ijazah': 100, 'Nilai US/UN': 100}
    TANPA_JURUSAN = ('SD / Sederajat', 'SMP / Sederajat')

    tanggal_lulus = FlexibleDateField(
        label='Tanggal Kelulusan',
        widget=DateInput(attrs={'class': 'date-input', 'data-user-date-picker': 'true'}),
    )
    nilai = forms.DecimalField(
        label='Nilai Akhir', min_value=0, max_digits=7, decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Masukkan nilai akhir'}),
    )

    class Meta:
        model = Pendidikan
        fields = ['tingkat', 'lokasi', 'lembaga', 'jurusan', 'tanggal_lulus',
                  'jenis_nilai', 'nilai', 'ijazah', 'transkrip']
        labels = {
            'tingkat': 'Tingkat Pendidikan', 'lokasi': 'Lokasi Pendidikan',
            'lembaga': 'Nama Lembaga Pendidikan', 'jurusan': 'Jurusan',
            'jenis_nilai': 'Jenis Nilai', 'ijazah': 'Ijazah', 'transkrip': 'Transkrip',
        }
        widgets = {
            'lembaga': forms.TextInput(attrs={'placeholder': 'Masukkan nama lembaga pendidikan'}),
            'jurusan': forms.TextInput(attrs={'placeholder': 'Masukkan jurusan'}),
            'ijazah': forms.FileInput(), 'transkrip': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _require_fields(self, ('tingkat', 'lokasi', 'jenis_nilai'), ('ijazah', 'transkrip'))
        self.lock_fields = self['tingkat'].value() not in dict(Pendidikan.TINGKAT_CHOICES)
        self.hide_jurusan = self['tingkat'].value() in self.TANPA_JURUSAN
        self.fields['jurusan'].required = not self.hide_jurusan
        self.fields['jurusan'].disabled = self.hide_jurusan
        batas = self.NILAI_BATAS.get(self['jenis_nilai'].value())
        if batas is not None:
            self.fields['nilai'].widget.attrs['max'] = batas
        for name, choices in (
            ('tingkat', Pendidikan.TINGKAT_CHOICES), ('lokasi', Pendidikan.LOKASI_CHOICES),
            ('jenis_nilai', Pendidikan.NILAI_CHOICES),
        ):
            self.fields[name].choices = [('', 'Pilih ' + self.fields[name].label.lower())] + choices
        _document_fields(self, ('ijazah', 'transkrip'))
        for name, field in self.fields.items():
            if name == 'tingkat':
                continue
            locked = self.lock_fields or field.disabled or (name == 'nilai' and batas is None)
            field.widget.attrs['aria-disabled'] = str(locked).lower()
            if locked:
                field.widget.attrs['disabled'] = True

    def clean_jurusan(self):
        return '' if self.hide_jurusan else self.cleaned_data['jurusan']

    def clean_tanggal_lulus(self):
        value = self.cleaned_data['tanggal_lulus']
        if value > timezone.localdate():
            raise forms.ValidationError('Tanggal kelulusan tidak boleh di masa depan.')
        return value

    def clean(self):
        cleaned = super().clean()
        jenis = cleaned.get('jenis_nilai')
        nilai = cleaned.get('nilai')
        batas = self.NILAI_BATAS.get(jenis)
        if nilai is not None and batas is not None and nilai > batas:
            self.add_error('nilai', f'Nilai {jenis} harus berada pada rentang 0.00–{batas:.2f}.')
        _clean_documents(self, cleaned, ('ijazah', 'transkrip'))
        return cleaned


class PelatihanForm(forms.ModelForm):
    tanggal_mulai = FlexibleDateField(
        input_formats=DATE_INPUT_FORMATS,
        widget=DateInput(
            attrs={
                "data-training-date-picker": "true",
                "data-training-start-date": "true",
                "placeholder": "Pilih mulai tanggal",
            }
        ),
        label="Mulai Tanggal",
        error_messages={
            "required": "Mulai tanggal kegiatan wajib diisi.",
            "invalid": DATE_HELP_TEXT,
        },
    )
    tanggal_selesai = FlexibleDateField(
        input_formats=DATE_INPUT_FORMATS,
        widget=DateInput(
            attrs={
                "data-training-date-picker": "true",
                "data-training-end-date": "true",
                "placeholder": "Pilih selesai tanggal",
            }
        ),
        label="Selesai Tanggal",
        error_messages={
            "required": "Selesai tanggal kegiatan wajib diisi.",
            "invalid": DATE_HELP_TEXT,
        },
    )

    class Meta:
        model = Pelatihan
        fields = [
            "kategori_kegiatan",
            "tipe_pelatihan",
            "jenis_pelatihan",
            "nama_pelatihan",
            "tanggal_mulai",
            "tanggal_selesai",
            "lokasi_pelatihan",
            "uraian_pelatihan",
            "file_materi",
        ]
        labels = {
            "kategori_kegiatan": "Kategori Kegiatan",
            "tipe_pelatihan": "Tipe Kegiatan",
            "jenis_pelatihan": "Jenis Kegiatan",
            "nama_pelatihan": "Nama Kegiatan",
            "lokasi_pelatihan": "Lokasi Kegiatan",
            "uraian_pelatihan": "Uraian Kegiatan",
            "file_materi": "File Materi",
        }
        widgets = {
            "kategori_kegiatan": forms.Select(attrs={
                "autocomplete": "off",
                "data-training-category-field": "true",
            }),
            "tipe_pelatihan": forms.Select(
                attrs={
                    "autocomplete": "off",
                    "data-training-type-field": "true",
                }
            ),
            "jenis_pelatihan": forms.Select(attrs={"autocomplete": "off"}),
            "nama_pelatihan": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan nama kegiatan",
                    "autocomplete": "off",
                }
            ),
            "lokasi_pelatihan": forms.TextInput(
                attrs={
                    "placeholder": "Contoh: Bandung - Bintek SDA",
                    "autocomplete": "off",
                }
            ),
            "uraian_pelatihan": forms.Textarea(
                attrs={
                    "placeholder": "Masukkan uraian singkat kegiatan",
                    "rows": 4,
                    "autocomplete": "off",
                }
            ),
            "file_materi": forms.FileInput(
                attrs={
                    "accept": ".pdf,.zip,.rar",
                    "class": "input-file--proxy",
                    "data-inline-file-input": "true",
                    "data-inline-file-placeholder": "Pilih file materi",
                    "data-inline-file-extensions": "pdf,zip,rar",
                    "data-inline-file-error": "File Materi hanya boleh berupa file PDF, ZIP, atau RAR.",
                }
            ),
        }
        error_messages = {
            "kategori_kegiatan": {
                "required": "Kategori kegiatan wajib dipilih.",
                "invalid_choice": "Pilih kategori kegiatan yang tersedia.",
            },
            "tipe_pelatihan": {"required": "Tipe kegiatan wajib dipilih."},
            "jenis_pelatihan": {"required": "Jenis kegiatan wajib dipilih."},
            "nama_pelatihan": {"required": "Nama kegiatan wajib diisi."},
            "lokasi_pelatihan": {"required": "Lokasi kegiatan wajib diisi."},
            "uraian_pelatihan": {"required": "Uraian kegiatan wajib diisi."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.help_text = ""
            if field_name != "file_materi":
                field.required = True
                field.widget.attrs["required"] = "required"

        self.fields["kategori_kegiatan"].choices = [("", "Pilih kategori kegiatan")] + Pelatihan.KATEGORI_CHOICES
        if self["kategori_kegiatan"].value() not in dict(Pelatihan.KATEGORI_CHOICES):
            self.fields["tipe_pelatihan"].widget.attrs.update(disabled=True, **{"aria-disabled": "true"})

        self.fields["tipe_pelatihan"].choices = [("", "Pilih tipe kegiatan")] + [
            (value, label.replace("Pelatihan", "Kegiatan")) for value, label in Pelatihan.TIPE_CHOICES
        ]
        self.fields["jenis_pelatihan"].choices = [("", "Pilih jenis kegiatan")] + list(
            Pelatihan.JENIS_CHOICES
        )
        self.fields["file_materi"].required = False
        self.fields["file_materi"].widget.attrs.pop("required", None)

        apply_upload_widget_validation_attrs(
            self.fields["file_materi"],
            allowed_extensions="pdf,zip,rar",
            invalid_extension_message="File Materi hanya boleh berupa file PDF, ZIP, atau RAR.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("File Materi"),
        )

    def clean_file_materi(self):
        return validate_uploaded_file(
            self.cleaned_data.get("file_materi"),
            allowed_extensions={".pdf", ".zip", ".rar"},
            invalid_extension_message="File Materi hanya boleh berupa file PDF, ZIP, atau RAR.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("File Materi"),
        )

    def clean(self):
        cleaned_data = super().clean()
        tanggal_mulai = cleaned_data.get("tanggal_mulai")
        tanggal_selesai = cleaned_data.get("tanggal_selesai")

        if tanggal_mulai and tanggal_selesai and tanggal_selesai < tanggal_mulai:
            self.add_error(
                "tanggal_selesai",
                "Selesai tanggal tidak boleh lebih awal dari mulai tanggal.",
            )

        return cleaned_data


class SertifikatField(forms.FileField):
    def clean(self, data, initial=None):
        if data is initial and initial:
            return initial
        file = super().clean(data, initial)
        if file is initial:
            return file
        return validate_uploaded_file(
            file,
            allowed_extensions={".jpg", ".jpeg", ".png", ".pdf"},
            invalid_extension_message="File Sertifikat hanya boleh berupa file JPG, JPEG, PNG, atau PDF.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("File Sertifikat"),
        )


class PesertaAdminForm(forms.ModelForm):
    class Meta:
        model = PesertaPelatihan
        fields = ["user", "file_sertifikat"]
        field_classes = {"file_sertifikat": SertifikatField}


class PesertaNamaForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(), label="Nama Peserta", empty_label="Pilih user",
    )

    def __init__(self, *args, users, can_remove=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = users
        self.locked = bool(self.initial.get("user"))
        self.removable = not self.initial.get("primary") and (not self.locked or can_remove)
        self.fields["user"].disabled = self.locked
        for field in self.fields.values():
            if field.disabled:
                field.widget.attrs["data-training-locked"] = "true"


class PesertaForm(PesertaNamaForm):
    file_sertifikat = SertifikatField(
        required=False, label="File Sertifikat",
        widget=forms.FileInput(attrs={
            "accept": ".jpg,.jpeg,.png,.pdf",
            "class": "input-file--proxy",
            "data-inline-file-input": "true",
            "data-inline-file-placeholder": "Pilih file sertifikat",
            "data-inline-file-extensions": "jpg,jpeg,png,pdf",
            "data-inline-file-error": "File Sertifikat hanya boleh berupa file JPG, JPEG, PNG, atau PDF.",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_upload_widget_validation_attrs(
            self.fields["file_sertifikat"], allowed_extensions="jpg,jpeg,png,pdf",
            invalid_extension_message="File Sertifikat hanya boleh berupa file JPG, JPEG, PNG, atau PDF.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("File Sertifikat"),
        )


class BaseKegiatanSet(forms.BaseFormSet):
    def __init__(self, *args, actor, kegiatan=None, **kwargs):
        is_admin = is_super_admin(actor)
        self.can_delete = bool(kegiatan and is_admin)
        self.rows = list(kegiatan.peserta.select_related("user")) if kegiatan else []
        self.rows.sort(key=lambda row: row.user_id != actor.pk)
        if kegiatan:
            initial = [
                {"user": row.user_id, "file_sertifikat": getattr(row, "file_sertifikat", None)}
                for row in self.rows
            ]
        else:
            initial = [{"primary": True}]
            if not is_admin:
                initial[0]["user"] = actor.pk
        self.expected_initial = len(initial)
        users = get_sdm_users()
        users = User.objects.filter(
            Q(pk__in=users.values("pk")) | Q(pk__in=[item["user"] for item in initial if item.get("user")])
        ).order_by("first_name", "username")
        super().__init__(
            *args, initial=initial, prefix="peserta",
            form_kwargs={"users": users, "can_remove": self.can_delete}, **kwargs,
        )

    def clean(self):
        super().clean()
        if self.initial_form_count() != self.expected_initial or self.total_form_count() < self.expected_initial:
            raise forms.ValidationError("Data peserta berubah. Muat ulang halaman dan coba kembali.")
        if any(self.errors):
            return
        seen = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            user = form.cleaned_data.get("user")
            if not user:
                continue
            if user.pk in seen:
                form.add_error("user", "Peserta yang sama hanya boleh dipilih satu kali.")
            seen.add(user.pk)
        if not seen:
            raise forms.ValidationError("Minimal satu peserta kegiatan wajib diisi.")



class BasePesertaSet(BaseKegiatanSet):
    def __init__(self, *args, pelatihan=None, **kwargs):
        super().__init__(*args, kegiatan=pelatihan, **kwargs)

    def save(self, pelatihan):
        for index, form in enumerate(self.forms):
            if self.can_delete and self._should_delete_form(form):
                if index < len(self.rows):
                    self.rows[index].delete()
                continue
            user = form.cleaned_data.get("user")
            if not user:
                continue
            if index < len(self.rows):
                row = self.rows[index]
                if "file_sertifikat" not in form.changed_data:
                    continue
                row.file_sertifikat = form.cleaned_data["file_sertifikat"]
                row.save(update_fields=["file_sertifikat"])
            else:
                PesertaPelatihan.objects.create(
                    pelatihan=pelatihan, user=user,
                    file_sertifikat=form.cleaned_data.get("file_sertifikat"),
                )


PesertaFormSet = forms.formset_factory(PesertaForm, formset=BasePesertaSet, extra=0, can_delete=True)


class LogbookImageField(forms.FileField):
    def clean(self, data, initial=None):
        file = super().clean(data, initial)
        if data:
            with read_image(file):
                pass
        return file


class LogbookForm(forms.ModelForm):
    dokumen = LogbookImageField(label='Dokumentasi Kegiatan', widget=forms.FileInput())
    tanggal = FlexibleDateField(
        label='Tanggal Pelaksanaan',
        widget=DateInput(attrs={'class': 'date-input', 'data-user-date-picker': 'true'}),
    )

    class Meta:
        model = Logbook
        fields = ['lingkup', 'tanggal', 'uraian', 'dokumen']
        labels = {'uraian': 'Uraian Kegiatan'}
        widgets = {
            'uraian': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Masukkan uraian kegiatan'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault('tanggal', timezone.localdate())
        self.fields['lingkup'].choices = [('', 'Pilih lingkup kegiatan')] + Logbook.LINGKUP_CHOICES
        self.lock_fields = self['lingkup'].value() not in dict(Logbook.LINGKUP_CHOICES)
        _require_fields(self, (), ('dokumen',))
        field = self.fields['dokumen']
        extensions = 'jpg,jpeg,png,heic,heif'
        field.widget.attrs.update({
            'accept': '.jpg,.jpeg,.png,.heic,.heif,image/heic,image/heif',
            'class': 'input-file--proxy', 'data-inline-file-input': 'true',
            'data-inline-file-skip-required': 'true',
            'data-inline-file-placeholder': 'Pilih gambar dokumentasi',
            'data-has-file': str(bool(self.instance.dokumen)).lower(),
        })
        apply_upload_widget_validation_attrs(field, allowed_extensions=extensions,
            invalid_extension_message=IMAGE_ERROR,
            max_size_message=build_max_upload_size_message(field.label))


class LogbookNamaForm(PesertaNamaForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].widget.attrs.update({
            'required': True, 'data-required-message': 'Nama peserta wajib dipilih.',
        })


class BaseLogbookSet(BaseKegiatanSet):
    def _construct_form(self, i, **kwargs):
        kwargs['empty_permitted'] = False
        return super()._construct_form(i, **kwargs)

    def save(self, logbook):
        for index, form in enumerate(self.forms):
            if self.can_delete and self._should_delete_form(form):
                if index < len(self.rows):
                    self.rows[index].delete()
                continue
            user = form.cleaned_data.get('user')
            if user and index >= len(self.rows):
                PesertaLogbook.objects.create(logbook=logbook, user=user)


LogbookPesertaSet = forms.formset_factory(LogbookNamaForm, formset=BaseLogbookSet, extra=0, can_delete=True)


class DrhChoices(forms.CheckboxSelectMultiple):
    locked = frozenset()

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value in self.locked:
            option['attrs']['disabled'] = True
            option['attrs']['aria-disabled'] = 'true'
            option['attrs'].pop('checked', None)
            option['selected'] = False
        return option


class DrhForm(forms.Form):
    BAGIAN = (
        ('pendidikan', 'Data Pendidikan'),
        ('karir', 'Riwayat Karir'),
        ('pelatihan', 'Data Pelatihan / Diklat / Workshop / Seminar'),
        ('portofolio', 'Portofolio Proyek & Kegiatan'),
    )
    bagian = forms.MultipleChoiceField(
        label='Pilih data yang akan dimuat', choices=BAGIAN, required=False, widget=DrhChoices,
    )
    lokasi = forms.CharField(label='Lokasi DRH', max_length=100, initial='Bandung', widget=forms.TextInput(
        attrs={'data-required-message': 'Lokasi DRH wajib diisi.'},
    ))
    tanggal = FlexibleDateField(label='Tanggal DRH', initial=timezone.localdate, widget=DateInput(attrs={
        'class': 'date-input', 'data-user-date-picker': 'true',
        'data-required-message': 'Tanggal DRH wajib diisi.',
    }))

    def __init__(self, data=None, *args, user, **kwargs):
        if data is not None:
            data = data.copy()
            data.setdefault('lokasi', 'Bandung')
            data.setdefault('tanggal', timezone.localdate().isoformat())
        super().__init__(data, *args, **kwargs)
        self.available = {key for key, rows in get_drh_data(user).items() if rows.exists()}
        self.fields['bagian'].widget.locked = {key for key, _ in self.BAGIAN} - self.available
        self.initial.setdefault('bagian', [key for key, _ in self.BAGIAN if key in self.available])

    def clean_bagian(self):
        return [key for key in self.cleaned_data['bagian'] if key in self.available]

    def clean_lokasi(self):
        return ' '.join(self.cleaned_data['lokasi'].split())
