from datetime import date, datetime
from io import BytesIO
import os
import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile

from apps.core.file_cleanup import delete_file_if_unused
from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    apply_upload_widget_validation_attrs,
    build_max_upload_size_message,
    validate_uploaded_file,
)
from apps.operasional.models import TimKegiatan


from .models import Pelatihan, User, UserProfile, get_default_role_queryset

try:
    from PIL import Image
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
    hapus_foto_profil = forms.BooleanField(required=False, widget=forms.HiddenInput())
    hapus_ttd_digital = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = UserProfile
        fields = [
            "role",
            "foto_profil",
            "ttd_digital",
            "jabatan",
            "nama_tim",
            "alamat",
        ]
        labels = {
            "role": "Peran",
            "foto_profil": "Foto Profil",
            "ttd_digital": "TTD Digital",
            "jabatan": "Jabatan",
            "nama_tim": "Divisi Tim Kegiatan",
            "alamat": "Alamat",
        }
        widgets = {
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

    def _crop_square_image(self, uploaded_file, filename_prefix="img"):
        if not uploaded_file or Image is None:
            return uploaded_file

        file_bytes = self._get_uploaded_file_bytes(uploaded_file)
        image = Image.open(BytesIO(file_bytes))

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if image.mode in ("LA", "P") else "RGB")

        width, height = image.size
        crop_size = min(width, height)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        image = image.crop((left, top, right, bottom))

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
        files_to_delete = []

        if self.cleaned_data.get("hapus_foto_profil"):
            profile.foto_profil = None
            if old_foto_profil and getattr(old_foto_profil, "name", ""):
                files_to_delete.append(old_foto_profil)
        elif new_foto_profil:
            profile.foto_profil = self._crop_square_image(
                new_foto_profil, filename_prefix="foto_profil"
            )
            if old_foto_profil and getattr(old_foto_profil, "name", ""):
                files_to_delete.append(old_foto_profil)
        elif persisted_profile is not None:
            profile.foto_profil = old_foto_profil

        if self.cleaned_data.get("hapus_ttd_digital"):
            profile.ttd_digital = None
            if old_ttd_digital and getattr(old_ttd_digital, "name", ""):
                files_to_delete.append(old_ttd_digital)
        elif new_ttd_digital:
            profile.ttd_digital = new_ttd_digital
            if old_ttd_digital and getattr(old_ttd_digital, "name", ""):
                files_to_delete.append(old_ttd_digital)
        elif persisted_profile is not None:
            profile.ttd_digital = old_ttd_digital

        if commit:
            profile.save()
            for existing_file in files_to_delete:
                delete_file_if_unused(
                    type(profile),
                    getattr(existing_file, "field", None).name
                    if getattr(existing_file, "field", None)
                    else "",
                    existing_file,
                    exclude_pk=profile.pk,
                )
        return profile


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
            "required": "Mulai tanggal pelatihan wajib diisi.",
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
            "required": "Selesai tanggal pelatihan wajib diisi.",
            "invalid": DATE_HELP_TEXT,
        },
    )

    class Meta:
        model = Pelatihan
        fields = [
            "tipe_pelatihan",
            "jenis_pelatihan",
            "nama_pelatihan",
            "tanggal_mulai",
            "tanggal_selesai",
            "lokasi_pelatihan",
            "uraian_pelatihan",
            "file_sertifikat",
            "file_materi",
        ]
        labels = {
            "tipe_pelatihan": "Tipe Pelatihan",
            "jenis_pelatihan": "Jenis Pelatihan",
            "nama_pelatihan": "Nama Pelatihan",
            "lokasi_pelatihan": "Lokasi Pelatihan",
            "uraian_pelatihan": "Uraian Pelatihan",
            "file_sertifikat": "File Sertifikat",
            "file_materi": "File Materi",
        }
        widgets = {
            "tipe_pelatihan": forms.Select(
                attrs={
                    "autocomplete": "off",
                    "data-training-type-field": "true",
                }
            ),
            "jenis_pelatihan": forms.Select(attrs={"autocomplete": "off"}),
            "nama_pelatihan": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan nama pelatihan",
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
                    "placeholder": "Masukkan uraian singkat pelatihan",
                    "rows": 4,
                    "autocomplete": "off",
                }
            ),
            "file_sertifikat": forms.FileInput(
                attrs={
                    "accept": ".jpg,.jpeg,.png,.pdf",
                    "class": "input-file--proxy",
                    "data-inline-file-input": "true",
                    "data-inline-file-placeholder": "Pilih file sertifikat",
                    "data-inline-file-extensions": "jpg,jpeg,png,pdf",
                    "data-inline-file-error": "File Sertifikat hanya boleh berupa file JPG, JPEG, PNG, atau PDF.",
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
            "tipe_pelatihan": {"required": "Tipe pelatihan wajib dipilih."},
            "jenis_pelatihan": {"required": "Jenis pelatihan wajib dipilih."},
            "nama_pelatihan": {"required": "Nama pelatihan wajib diisi."},
            "lokasi_pelatihan": {"required": "Lokasi pelatihan wajib diisi."},
            "uraian_pelatihan": {"required": "Uraian pelatihan wajib diisi."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.help_text = ""
            if field_name not in {"file_sertifikat", "file_materi"}:
                field.required = True
                field.widget.attrs["required"] = "required"

        self.fields["tipe_pelatihan"].choices = [("", "Pilih tipe pelatihan")] + list(
            Pelatihan.TIPE_CHOICES
        )
        self.fields["jenis_pelatihan"].choices = [("", "Pilih jenis pelatihan")] + list(
            Pelatihan.JENIS_CHOICES
        )
        self.fields["file_sertifikat"].required = False
        self.fields["file_materi"].required = False
        self.fields["file_sertifikat"].widget.attrs.pop("required", None)
        self.fields["file_materi"].widget.attrs.pop("required", None)

        apply_upload_widget_validation_attrs(
            self.fields["file_sertifikat"],
            allowed_extensions="jpg,jpeg,png,pdf",
            invalid_extension_message="File Sertifikat hanya boleh berupa file JPG, JPEG, PNG, atau PDF.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("File Sertifikat"),
        )
        apply_upload_widget_validation_attrs(
            self.fields["file_materi"],
            allowed_extensions="pdf,zip,rar",
            invalid_extension_message="File Materi hanya boleh berupa file PDF, ZIP, atau RAR.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("File Materi"),
        )

    def clean_file_sertifikat(self):
        return validate_uploaded_file(
            self.cleaned_data.get("file_sertifikat"),
            allowed_extensions={".jpg", ".jpeg", ".png", ".pdf"},
            invalid_extension_message="File Sertifikat hanya boleh berupa file JPG, JPEG, PNG, atau PDF.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("File Sertifikat"),
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
