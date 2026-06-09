from django import forms
from django.db import transaction

from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    apply_upload_widget_validation_attrs,
    build_max_upload_size_message,
    validate_uploaded_file,
)
from apps.master_data.models import BarangLaboratorium, KategoriBarangLaboratoriumChoices

from .models import MAX_EQUIPMENT_PHOTOS, LandingPeralatanCard, LandingPeralatanFoto


class MultiImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiImageField(forms.ImageField):
    widget = MultiImageInput

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        cleaned = []
        errors = []
        for file_obj in files:
            try:
                cleaned.append(super().clean(file_obj, initial))
            except forms.ValidationError as exc:
                errors.extend(exc.error_list)
        if errors:
            raise forms.ValidationError(errors)
        return cleaned


class LandingPeralatanCardForm(forms.ModelForm):
    foto_barang = MultiImageField(required=False, label="Upload Foto Barang")
    hapus_foto_ids = forms.MultipleChoiceField(required=False)

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
            "urutan",
            "is_active",
        ]
        widgets = {
            "ringkasan_alat": forms.Textarea(attrs={"rows": 4}),
            "spesifikasi_alat": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_common_widget_style()
        self._setup_category_choices()
        self._setup_upload_field()
        self._setup_existing_photos()
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
        self.fields["foto_barang"].widget = MultiImageInput(
            attrs={
                "accept": ".jpg,.jpeg,.png",
                "class": "landing-gallery-input",
                "multiple": "multiple",
                "data-gallery-input": "true",
            }
        )
        apply_upload_widget_validation_attrs(
            self.fields["foto_barang"],
            allowed_extensions="jpg,jpeg,png",
            invalid_extension_message="Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Foto Barang"),
        )

    def _setup_existing_photos(self):
        photos = list(self.instance.fotos.all()) if getattr(self.instance, "pk", None) else []
        self.existing_photos = photos
        self.deleted_photo_ids = (
            set(self.data.getlist(self.add_prefix("hapus_foto_ids"))) if self.is_bound else set()
        )
        self.fields["hapus_foto_ids"].choices = [
            (str(photo.pk), str(photo.pk)) for photo in photos
        ]

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

    def clean_foto_barang(self):
        files = self.cleaned_data.get("foto_barang") or []
        if len(files) > MAX_EQUIPMENT_PHOTOS:
            raise forms.ValidationError(
                f"Maksimal {MAX_EQUIPMENT_PHOTOS} foto dapat diupload untuk satu konten."
            )
        return [
            validate_uploaded_file(
                file_obj,
                allowed_extensions={".jpg", ".jpeg", ".png"},
                invalid_extension_message="Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
                max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
                max_size_message=build_max_upload_size_message("Foto Barang"),
            )
            for file_obj in files
        ]

    def clean_hapus_foto_ids(self):
        return [int(photo_id) for photo_id in self.cleaned_data.get("hapus_foto_ids") or []]

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        existing_count = len(self.existing_photos)
        delete_count = len(cleaned_data.get("hapus_foto_ids") or [])
        upload_count = len(cleaned_data.get("foto_barang") or [])
        total = existing_count - delete_count + upload_count
        if total > MAX_EQUIPMENT_PHOTOS:
            self.add_error(
                "foto_barang",
                (
                    f"Total foto maksimal {MAX_EQUIPMENT_PHOTOS}. "
                    f"Hapus foto lama atau kurangi jumlah foto baru yang dipilih."
                ),
            )
        return cleaned_data

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
        if not commit:
            return super().save(commit=False)

        with transaction.atomic():
            instance = super().save(commit=True)
            delete_ids = self.cleaned_data.get("hapus_foto_ids") or []
            if delete_ids:
                instance.fotos.filter(pk__in=delete_ids).delete()

            remaining = list(instance.fotos.order_by("urutan", "id"))
            for order, photo in enumerate(remaining, start=1):
                if photo.urutan != order:
                    LandingPeralatanFoto.objects.filter(pk=photo.pk).update(urutan=order)

            next_order = len(remaining) + 1
            for index, file_obj in enumerate(self.cleaned_data.get("foto_barang") or []):
                LandingPeralatanFoto.objects.create(
                    card=instance,
                    foto=file_obj,
                    urutan=next_order + index,
                )
        return instance
