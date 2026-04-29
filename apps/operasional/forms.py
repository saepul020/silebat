from django import forms

from apps.core.file_cleanup import delete_file_if_unused
from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    apply_upload_widget_validation_attrs,
    build_max_upload_size_message,
    validate_uploaded_file,
)
from apps.pengguna.models import User

from .models import DataKopDokumen, InstansiKlien, LayananKegiatan, SurveiKegiatan, TimKegiatan

class OperasionalBaseForm(forms.ModelForm):
    required_message = "Kolom ini wajib diisi."

    def _apply_common_style(self):
        for name, field in self.fields.items():
            field.help_text = ""
            field.required = True
            field.error_messages["required"] = self.required_message
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css_class + " form-control").strip()
            field.widget.attrs["required"] = "required"
            field.widget.attrs["data-operasional-required"] = "true"
            if field.label:
                field.widget.attrs["data-placeholder-label"] = field.label


class TimKegiatanForm(OperasionalBaseForm):
    class Meta:
        model = TimKegiatan
        fields = ["nama_tim", "ketua_tim"]
        labels = {
            "nama_tim": "Nama Tim",
            "ketua_tim": "Ketua Tim",
        }
        widgets = {
            "nama_tim": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan nama tim kegiatan",
                    "autocomplete": "off",
                }
            ),
            "ketua_tim": forms.Select(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ketua_tim"].queryset = User.objects.order_by(
            "first_name", "username"
        )
        self.fields["ketua_tim"].required = True
        self.fields["ketua_tim"].empty_label = "Pilih ketua tim"
        self.fields["ketua_tim"].widget.attrs["data-placeholder-label"] = "Ketua Tim"
        self._apply_common_style()

    def clean_nama_tim(self):
        nama_tim = (self.cleaned_data.get("nama_tim") or "").strip()
        if not nama_tim:
            raise forms.ValidationError("Kolom ini wajib diisi.")

        qs = TimKegiatan.objects.filter(nama_tim__iexact=nama_tim)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Nama tim sudah digunakan.")
        return nama_tim


class LayananKegiatanForm(OperasionalBaseForm):
    class Meta:
        model = LayananKegiatan
        fields = ["jenis_layanan"]
        labels = {
            "jenis_layanan": "Jenis Layanan",
        }
        widgets = {
            "jenis_layanan": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan jenis layanan kegiatan",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_common_style()

    def clean_jenis_layanan(self):
        jenis_layanan = (self.cleaned_data.get("jenis_layanan") or "").strip()
        if not jenis_layanan:
            raise forms.ValidationError("Kolom ini wajib diisi.")

        qs = LayananKegiatan.objects.filter(jenis_layanan__iexact=jenis_layanan)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Jenis layanan sudah digunakan.")
        return jenis_layanan


class SurveiKegiatanForm(OperasionalBaseForm):
    class Meta:
        model = SurveiKegiatan
        fields = ["jenis_survei"]
        labels = {
            "jenis_survei": "Jenis Survei",
        }
        widgets = {
            "jenis_survei": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan jenis kegiatan survei",
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_common_style()

    def clean_jenis_survei(self):
        jenis_survei = (self.cleaned_data.get("jenis_survei") or "").strip()
        if not jenis_survei:
            raise forms.ValidationError("Kolom ini wajib diisi.")

        qs = SurveiKegiatan.objects.filter(jenis_survei__iexact=jenis_survei)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Jenis survei sudah digunakan.")
        return jenis_survei


class InstansiKlienForm(OperasionalBaseForm):
    class Meta:
        model = InstansiKlien
        fields = ["nama_instansi", "alamat_instansi", "organisasi"]
        labels = {
            "nama_instansi": "Nama Instansi",
            "alamat_instansi": "Alamat Instansi",
            "organisasi": "Organisasi",
        }
        widgets = {
            "nama_instansi": forms.TextInput(
                attrs={
                    "placeholder": "Masukkan nama instansi / klien",
                    "autocomplete": "off",
                }
            ),
            "alamat_instansi": forms.Textarea(
                attrs={
                    "placeholder": "Masukkan alamat instansi",
                    "rows": 3,
                }
            ),
            "organisasi": forms.Select(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisasi"].required = True
        existing_choices = list(self.fields["organisasi"].choices)
        if not existing_choices or existing_choices[0][0] != "":
            self.fields["organisasi"].choices = [("", "Pilih organisasi"), *existing_choices]
        self.fields["organisasi"].widget.attrs["data-placeholder-label"] = "Organisasi"
        self._apply_common_style()

    def clean_nama_instansi(self):
        nama_instansi = (self.cleaned_data.get("nama_instansi") or "").strip()
        if not nama_instansi:
            raise forms.ValidationError("Kolom ini wajib diisi.")

        qs = InstansiKlien.objects.filter(nama_instansi__iexact=nama_instansi)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Nama instansi sudah digunakan.")
        return nama_instansi


class DataKopDokumenForm(forms.ModelForm):
    required_message = "Kolom ini wajib diisi."

    class Meta:
        model = DataKopDokumen
        fields = ["kop_dokumen"]
        labels = {
            "kop_dokumen": "Kop Dokumen",
        }
        widgets = {
            "kop_dokumen": forms.FileInput(
                attrs={
                    "accept": ".jpg,.jpeg,.png",
                    "class": "input-file--proxy",
                    "data-inline-file-input": "true",
                    "data-inline-file-placeholder": "Pilih file",
                    "data-inline-file-extensions": "jpg,jpeg,png",
                    "data-inline-file-error": "Kop Dokumen hanya boleh berupa file JPG, JPEG, atau PNG.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kop_dokumen"].help_text = ""
        self.fields["kop_dokumen"].error_messages["required"] = self.required_message
        self.fields["kop_dokumen"].widget.attrs["data-placeholder-label"] = "Kop Dokumen"
        self.fields["kop_dokumen"].widget.attrs["data-inline-file-required-message"] = self.required_message
        self.fields["kop_dokumen"].required = not bool(getattr(self.instance, "pk", None) and getattr(self.instance, "kop_dokumen", None))
        apply_upload_widget_validation_attrs(
            self.fields["kop_dokumen"],
            allowed_extensions="jpg,jpeg,png",
            invalid_extension_message="Kop Dokumen hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Kop Dokumen"),
        )

    def clean_kop_dokumen(self):
        return validate_uploaded_file(
            self.cleaned_data.get("kop_dokumen"),
            allowed_extensions={".jpg", ".jpeg", ".png"},
            invalid_extension_message="Kop Dokumen hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Kop Dokumen"),
        )

    def clean(self):
        cleaned_data = super().clean()
        qs = DataKopDokumen.objects.all()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Data Kop Dokumen hanya boleh satu data.")

        uploaded = self.files.get(self.add_prefix("kop_dokumen"))
        existing = getattr(self.instance, "kop_dokumen", None)
        if (
            not uploaded
            and not getattr(existing, "name", "")
            and "kop_dokumen" not in self.errors
        ):
            self.add_error("kop_dokumen", self.required_message)
        return cleaned_data

    def save(self, commit=True):
        persisted_instance = None
        if self.instance.pk:
            persisted_instance = type(self.instance)._default_manager.filter(pk=self.instance.pk).first()

        old_kop_dokumen = getattr(persisted_instance, "kop_dokumen", None)
        new_kop_dokumen = self.files.get(self.add_prefix("kop_dokumen"))

        instance = super().save(commit=False)

        if new_kop_dokumen:
            instance.kop_dokumen = new_kop_dokumen
        elif persisted_instance is not None:
            instance.kop_dokumen = old_kop_dokumen

        if commit:
            instance.save()
            if new_kop_dokumen and old_kop_dokumen and getattr(old_kop_dokumen, "name", ""):
                delete_file_if_unused(
                    type(instance),
                    "kop_dokumen",
                    old_kop_dokumen,
                    exclude_pk=instance.pk,
                )
        return instance
