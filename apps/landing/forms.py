from django import forms

from apps.core.file_cleanup import delete_file_if_unused
from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    apply_upload_widget_validation_attrs,
    build_max_upload_size_message,
    validate_uploaded_file,
)
from apps.master_data.models import BarangLaboratorium, KategoriBarangLaboratoriumChoices

from .models import LandingPeralatanCard


class LandingPeralatanCardForm(forms.ModelForm):
    hapus_foto_barang = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = LandingPeralatanCard
        fields = [
            "kategori_barang",
            "nama_barang",
            "jenis_barang",
            "merek_tipe_alat",
            "fungsi_alat",
            "spesifikasi_alat",
            "ringkasan_alat",
            "foto_barang",
            "urutan",
            "is_active",
        ]
        widgets = {
            "ringkasan_alat": forms.Textarea(attrs={"rows": 4}),
            "spesifikasi_alat": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._files_to_delete_after_save = []
        self._set_common_widget_style()
        self._setup_category_choices()
        self._setup_upload_field()
        self._set_input_attrs()
        self.fields["is_active"].widget.attrs["class"] = "landing-visible-checkbox"
        self.fields["is_active"].label = "Tampilkan"

    def _set_common_widget_style(self):
        for field in self.fields.values():
            field.help_text = ""
            widget = field.widget
            existing_class = widget.attrs.get("class", "")
            widget.attrs["class"] = (existing_class + " form-control").strip()
            if field.required and not isinstance(widget, forms.FileInput):
                field.error_messages["required"] = self._get_required_message(field)
                widget.attrs["required"] = "required"

    def _get_required_message(self, field):
        label = (field.label or "Kolom ini").strip()
        if isinstance(field.widget, forms.Select):
            return f"{label} wajib dipilih."
        return f"{label} wajib diisi."

    def _setup_category_choices(self):
        choice_labels = dict(KategoriBarangLaboratoriumChoices.choices)
        used_categories = (
            BarangLaboratorium.objects.exclude(kategori_barang__isnull=True)
            .exclude(kategori_barang="")
            .values_list("kategori_barang", flat=True)
            .distinct()
            .order_by("kategori_barang")
        )
        category_choices = [
            (value, choice_labels.get(value, value))
            for value in used_categories
            if value
        ]
        selected_value = (
            self.data.get(self.add_prefix("kategori_barang"))
            if self.is_bound
            else getattr(self.instance, "kategori_barang", "")
        )
        if selected_value and selected_value not in {value for value, _ in category_choices}:
            category_choices.append((selected_value, choice_labels.get(selected_value, selected_value)))

        self.fields["kategori_barang"].choices = [("", "Pilih kategori barang"), *category_choices]
        self.fields["kategori_barang"].widget.attrs.update({"data-preserve-placeholder": "true"})

    def _setup_upload_field(self):
        self.fields["foto_barang"].required = False
        self.fields["foto_barang"].widget = forms.FileInput(
            attrs={
                "accept": ".jpg,.jpeg,.png",
                "class": "input-file--proxy",
                "data-inline-file-input": "true",
                "data-inline-file-placeholder": "Pilih file",
                "data-inline-file-extensions": "jpg,jpeg,png",
                "data-inline-file-error": "Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
            }
        )
        apply_upload_widget_validation_attrs(
            self.fields["foto_barang"],
            allowed_extensions="jpg,jpeg,png",
            invalid_extension_message="Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Foto Barang"),
        )

    def _set_input_attrs(self):
        attrs_map = {
            "nama_barang": {"placeholder": "Masukkan nama barang", "autocomplete": "off"},
            "jenis_barang": {"placeholder": "Masukkan jenis barang", "autocomplete": "off"},
            "merek_tipe_alat": {"placeholder": "Masukkan merek / tipe alat", "autocomplete": "off"},
            "fungsi_alat": {"placeholder": "Masukkan fungsi alat", "autocomplete": "off"},
            "spesifikasi_alat": {"placeholder": "Masukkan spesifikasi alat", "rows": 3},
            "ringkasan_alat": {"placeholder": "Masukkan ringkasan alat", "rows": 4},
            "urutan": {"placeholder": "Contoh: 1", "min": "1", "inputmode": "numeric"},
        }
        for field_name, attrs in attrs_map.items():
            self.fields[field_name].widget.attrs.update(attrs)

    def _get_persisted_instance(self):
        if not getattr(self.instance, "pk", None):
            return None
        return type(self.instance)._default_manager.filter(pk=self.instance.pk).first()

    def _get_uploaded_file_from_request(self, field_name):
        return self.files.get(self.add_prefix(field_name))

    def _queue_file_for_delete(self, file_obj):
        file_name = getattr(file_obj, "name", "")
        if not file_name:
            return
        queued_names = {getattr(item, "name", "") for item in self._files_to_delete_after_save}
        if file_name not in queued_names:
            self._files_to_delete_after_save.append(file_obj)

    def _delete_queued_files(self):
        instance_pk = getattr(self.instance, "pk", None)
        for file_obj in self._files_to_delete_after_save:
            delete_file_if_unused(
                self._meta.model,
                "foto_barang",
                file_obj,
                exclude_pk=instance_pk,
            )
        self._files_to_delete_after_save = []

    def clean_foto_barang(self):
        return validate_uploaded_file(
            self.cleaned_data.get("foto_barang"),
            allowed_extensions={".jpg", ".jpeg", ".png"},
            invalid_extension_message="Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Foto Barang"),
        )

    def clean_urutan(self):
        urutan = self.cleaned_data.get("urutan")
        if urutan is None:
            return urutan
        if urutan < 1:
            raise forms.ValidationError("Urutan tampil minimal 1.")
        queryset = LandingPeralatanCard.objects.filter(urutan=urutan)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Urutan tampil sudah digunakan oleh konten lain.")
        return urutan

    def save(self, commit=True):
        persisted_instance = self._get_persisted_instance()
        old_foto_barang = getattr(persisted_instance, "foto_barang", None)
        new_foto_barang = self._get_uploaded_file_from_request("foto_barang")

        instance = super().save(commit=False)
        self._files_to_delete_after_save = []

        if self.cleaned_data.get("hapus_foto_barang"):
            instance.foto_barang = None
            self._queue_file_for_delete(old_foto_barang)
        elif new_foto_barang:
            instance.foto_barang = new_foto_barang
            self._queue_file_for_delete(old_foto_barang)
        elif persisted_instance is not None:
            instance.foto_barang = old_foto_barang

        if commit:
            instance.save()
            self.save_m2m()
            self._delete_queued_files()

        return instance
