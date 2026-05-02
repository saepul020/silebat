from django import forms

from apps.core.file_cleanup import delete_file_if_unused
from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    apply_upload_widget_validation_attrs,
    build_max_upload_size_message,
    validate_uploaded_file,
)

from .models import (
    BahanOperasional,
    BarangLaboratorium,
    BarangPenunjangOperasional,
    FasilitasRuangan,
    PeralatanLaboratorium,
    KategoriBarangLaboratoriumChoices,
    KetersediaanChoices,
    KondisiBarangChoices,
    StatusBarangChoices,
)


class BaseMasterDataForm(forms.ModelForm):
    required_message = "Kolom ini wajib diisi."

    def _get_required_message(self, field):
        label = (field.label or "").strip() or "Kolom ini"
        if isinstance(field.widget, forms.Select):
            return f"{label} wajib dipilih."
        return f"{label} wajib diisi."

    def _set_required_state(self, field_names, required=True):
        for field_name in field_names:
            field = self.fields.get(field_name)
            if not field:
                continue

            field.required = required
            if required:
                field.error_messages["required"] = self._get_required_message(field)
                if not field.disabled:
                    field.widget.attrs["required"] = "required"
            else:
                field.widget.attrs.pop("required", None)

    def _set_placeholder_choice(self, field_name, placeholder_text=None):
        field = self.fields.get(field_name)
        if not field or not isinstance(field.widget, forms.Select):
            return

        placeholder_text = (
            placeholder_text or f"Pilih {(field.label or field_name).strip().lower()}"
        )
        choices = list(field.choices)
        if not choices or choices[0][0] != "":
            field.choices = [("", placeholder_text), *choices]
        else:
            choices[0] = ("", placeholder_text)
            field.choices = choices

    def _set_common_widget_style(self):
        for name, field in self.fields.items():
            field.help_text = ""
            widget = field.widget
            css_class = widget.attrs.get("class", "")
            widget.attrs["class"] = (css_class + " form-control").strip()
            if field.required:
                field.error_messages["required"] = self._get_required_message(field)
                if not field.disabled:
                    widget.attrs["required"] = "required"

    def _set_input_attrs(self, mapping):
        for field_name, attrs in mapping.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update(attrs)

    def _validate_case_insensitive_unique(self, model, field_name, value, message):
        value = (value or "").strip()
        if not value:
            return value

        qs = model.objects.filter(**{f"{field_name}__iexact": value})
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(message)
        return value


class AssetBaseForm(BaseMasterDataForm):
    ketersediaan_info = forms.CharField(
        label="Ketersediaan", required=False, disabled=True
    )
    tanggal_pemeliharaan_info = forms.DateField(
        label="Tanggal Pemeliharaan", required=False, disabled=True
    )
    tanggal_perbaikan_info = forms.DateField(
        label="Tanggal Perbaikan", required=False, disabled=True
    )
    hapus_foto_barang = forms.BooleanField(required=False, widget=forms.HiddenInput())
    hapus_ik_alat = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        fields = [
            "status_barang",
            "nama_barang",
            "tipe_merek_barang",
            "jenis_barang",
            "kode_aset_bmn",
            "kode_laboratorium",
            "volume",
            "satuan",
            "tahun_perolehan",
            "kondisi_barang",
            "lokasi_barang",
            "foto_barang",
            "ik_alat",
            "catatan",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._files_to_delete_after_save = []
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
        self.fields["ik_alat"].widget = forms.FileInput(
            attrs={
                "accept": ".pdf,application/pdf",
                "class": "input-file--proxy",
                "data-inline-file-input": "true",
                "data-inline-file-placeholder": "Pilih file",
                "data-inline-file-extensions": "pdf",
                "data-inline-file-error": "IK Alat hanya boleh berupa file PDF.",
            }
        )
        self._set_common_widget_style()
        self._set_placeholder_choice("status_barang", "Pilih status barang")
        self._set_placeholder_choice("satuan", "Pilih satuan")
        self._set_placeholder_choice("kondisi_barang", "Pilih kondisi barang")
        self._set_input_attrs(
            {
                "nama_barang": {
                    "placeholder": "Masukkan nama barang",
                    "autocomplete": "off",
                    "data-status-dependent": "true",
                },
                "tipe_merek_barang": {
                    "placeholder": "Masukkan tipe / merek barang",
                    "autocomplete": "off",
                    "data-status-dependent": "true",
                },
                "jenis_barang": {
                    "placeholder": "Masukkan jenis barang",
                    "autocomplete": "off",
                    "data-status-dependent": "true",
                },
                "kode_aset_bmn": {
                    "placeholder": "Masukkan kode aset BMN",
                    "autocomplete": "off",
                    "data-bmn-code-field": "true",
                    "data-status-dependent": "true",
                },
                "kode_laboratorium": {
                    "placeholder": "Masukkan kode laboratorium",
                    "autocomplete": "off",
                    "data-status-dependent": "true",
                },
                "volume": {"min": "0", "data-status-dependent": "true"},
                "satuan": {"data-status-dependent": "true"},
                "tahun_perolehan": {
                    "placeholder": "Contoh: 2026",
                    "min": "1900",
                    "data-status-dependent": "true",
                },
                "kondisi_barang": {"data-status-dependent": "true"},
                "lokasi_barang": {
                    "placeholder": "Masukkan lokasi barang",
                    "autocomplete": "off",
                    "data-status-dependent": "true",
                },
                "foto_barang": {
                    "accept": ".jpg,.jpeg,.png",
                    "class": "input-file--proxy",
                    "data-inline-file-input": "true",
                    "data-inline-file-placeholder": "Pilih file",
                    "data-inline-file-extensions": "jpg,jpeg,png",
                    "data-inline-file-error": "Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
                    "data-status-dependent": "true",
                },
                "ik_alat": {
                    "accept": ".pdf,application/pdf",
                    "class": "input-file--proxy",
                    "data-inline-file-input": "true",
                    "data-inline-file-placeholder": "Pilih file",
                    "data-inline-file-extensions": "pdf",
                    "data-inline-file-error": "IK Alat hanya boleh berupa file PDF.",
                    "data-status-dependent": "true",
                },
                "catatan": {
                    "placeholder": "Tambahkan catatan bila diperlukan",
                    "rows": 4,
                    "data-status-dependent": "true",
                },
                "status_barang": {"data-status-field": "true"},
            }
        )
        apply_upload_widget_validation_attrs(
            self.fields["foto_barang"],
            allowed_extensions="jpg,jpeg,png",
            invalid_extension_message="Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Foto Barang"),
        )
        apply_upload_widget_validation_attrs(
            self.fields["ik_alat"],
            allowed_extensions="pdf",
            invalid_extension_message="IK Alat hanya boleh berupa file PDF.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("IK Alat"),
        )
        self.fields["volume"].disabled = True
        self.fields["volume"].required = False
        self.fields["volume"].widget.attrs.pop("required", None)
        self.fields["volume"].widget.attrs.update(
            {
                "readonly": "readonly",
                "aria-readonly": "true",
                "data-volume-locked": "true",
                "class": (
                    self.fields["volume"].widget.attrs.get("class", "")
                    + " is-readonly-field"
                ).strip(),
                "title": "Volume otomatis diisi sistem berdasarkan Kondisi Barang.",
            }
        )
        self.fields["volume"].initial = self._get_locked_volume_value()
        self.fields["ketersediaan_info"].initial = self._get_ketersediaan_value()
        self.fields["tanggal_pemeliharaan_info"].initial = getattr(
            self.instance, "tanggal_pemeliharaan", None
        )
        self.fields["tanggal_perbaikan_info"].initial = getattr(
            self.instance, "tanggal_perbaikan", None
        )
        if not getattr(self.instance, "pk", None):
            self._set_required_state(["tahun_perolehan"])
        self.fields["tahun_perolehan"].error_messages.setdefault(
            "invalid", "Tahun perolehan harus berupa angka yang valid."
        )
        self._sync_bmn_field_requirements()

    def _get_locked_volume_value(self, kondisi_barang=None):
        kondisi = (
            kondisi_barang
            or self.data.get(self.add_prefix("kondisi_barang"))
            or self.initial.get("kondisi_barang")
            or getattr(self.instance, "kondisi_barang", None)
            or KondisiBarangChoices.BAIK
        )
        return 0 if str(kondisi).strip() == KondisiBarangChoices.HILANG else 1

    def _get_ketersediaan_value(self):
        if getattr(self.instance, "pk", None):
            return self.instance.ketersediaan

        kondisi = (
            self.data.get("kondisi_barang")
            or self.initial.get("kondisi_barang")
            or "Baik"
        )
        return (
            KetersediaanChoices.TERSEDIA
            if kondisi == "Baik"
            else KetersediaanChoices.TIDAK_TERSEDIA
        )

    def _get_status_barang_value(self):
        if self.is_bound:
            return (self.data.get(self.add_prefix("status_barang")) or "").strip()

        initial_value = self.initial.get("status_barang")
        if initial_value:
            return str(initial_value).strip()

        if getattr(self.instance, "status_barang", None):
            return str(self.instance.status_barang).strip()

        return ""

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

        queued_names = {
            getattr(queued_file, "name", "")
            for queued_file in self._files_to_delete_after_save
        }
        if file_name not in queued_names:
            self._files_to_delete_after_save.append(file_obj)

    def _delete_queued_files(self):
        model = self._meta.model
        instance_pk = getattr(self.instance, "pk", None)
        for file_obj in self._files_to_delete_after_save:
            field_name = getattr(getattr(file_obj, "field", None), "name", "")
            if field_name:
                delete_file_if_unused(
                    model,
                    field_name,
                    file_obj,
                    exclude_pk=instance_pk,
                )
        self._files_to_delete_after_save = []

    def _sync_bmn_field_requirements(self):
        field = self.fields.get("kode_aset_bmn")
        if not field:
            return

        is_bmn = self._get_status_barang_value() == StatusBarangChoices.BMN
        field.required = is_bmn
        if is_bmn:
            field.error_messages["required"] = self._get_required_message(field)
            field.widget.attrs["required"] = "required"
        else:
            field.widget.attrs.pop("required", None)

    def clean_foto_barang(self):
        return validate_uploaded_file(
            self.cleaned_data.get("foto_barang"),
            allowed_extensions={".jpg", ".jpeg", ".png"},
            invalid_extension_message="Foto Barang hanya boleh berupa file JPG, JPEG, atau PNG.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("Foto Barang"),
        )

    def clean_ik_alat(self):
        return validate_uploaded_file(
            self.cleaned_data.get("ik_alat"),
            allowed_extensions={".pdf"},
            invalid_extension_message="IK Alat hanya boleh berupa file PDF.",
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
            max_size_message=build_max_upload_size_message("IK Alat"),
        )

    def clean_status_barang(self):
        return (self.cleaned_data.get("status_barang") or "").strip()

    def _validate_asset_code_unique(self, field_name, value, message):
        value = (value or "").strip()
        if not value:
            return value

        # Sesuai aturan validasi terbaru, duplikasi kode hanya dicegah
        # pada Data Peralatan Survei Lapangan dan Data Peralatan Laboratorium.
        # Data aset lain boleh memiliki nilai field yang sama.
        model = self._meta.model
        if model not in (BarangLaboratorium, PeralatanLaboratorium):
            return value

        qs = model.objects.filter(**{f"{field_name}__iexact": value})
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(message)

        return value

    def clean_kode_aset_bmn(self):
        value = (self.cleaned_data.get("kode_aset_bmn") or "").strip()
        if not value:
            return None
        return self._validate_asset_code_unique(
            "kode_aset_bmn",
            value,
            "Kode Aset BMN sudah digunakan.",
        )

    def clean_kode_laboratorium(self):
        return self._validate_asset_code_unique(
            "kode_laboratorium",
            self.cleaned_data.get("kode_laboratorium"),
            "Kode laboratorium sudah digunakan.",
        )

    def clean(self):
        cleaned_data = super().clean()
        if getattr(self._meta.model, "lock_volume_to_one", True):
            cleaned_data["volume"] = self._get_locked_volume_value(
                cleaned_data.get("kondisi_barang")
            )
        status_barang = cleaned_data.get("status_barang")
        kode_aset_bmn = cleaned_data.get("kode_aset_bmn")

        if status_barang == StatusBarangChoices.BMN and not kode_aset_bmn:
            self.add_error(
                "kode_aset_bmn", "Kode Aset BMN wajib diisi untuk barang berstatus BMN."
            )
        elif status_barang != StatusBarangChoices.BMN:
            cleaned_data["kode_aset_bmn"] = None

        return cleaned_data

    def save(self, commit=True):
        persisted_instance = self._get_persisted_instance()
        old_foto_barang = getattr(persisted_instance, "foto_barang", None)
        old_ik_alat = getattr(persisted_instance, "ik_alat", None)
        new_foto_barang = self._get_uploaded_file_from_request("foto_barang")
        new_ik_alat = self._get_uploaded_file_from_request("ik_alat")

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

        if self.cleaned_data.get("hapus_ik_alat"):
            instance.ik_alat = None
            self._queue_file_for_delete(old_ik_alat)
        elif new_ik_alat:
            instance.ik_alat = new_ik_alat
            self._queue_file_for_delete(old_ik_alat)
        elif persisted_instance is not None:
            instance.ik_alat = old_ik_alat

        if instance.status_barang != StatusBarangChoices.BMN:
            instance.kode_aset_bmn = None

        if not getattr(instance, "kondisi_barang", None):
            instance.kondisi_barang = "Baik"

        if not getattr(instance, "pk", None):
            instance.sedang_dipinjam = False

        if commit:
            instance.save()
            self.save_m2m()
            self._delete_queued_files()

        return instance


class BarangLaboratoriumForm(AssetBaseForm):
    class Meta(AssetBaseForm.Meta):
        model = BarangLaboratorium
        fields = AssetBaseForm.Meta.fields + ["kategori_barang"]
        labels = {
            "status_barang": "Status Barang",
            "nama_barang": "Nama Barang",
            "tipe_merek_barang": "Tipe / Merek Barang",
            "jenis_barang": "Jenis Barang",
            "kode_aset_bmn": "Kode Aset BMN",
            "kode_laboratorium": "Kode Laboratorium",
            "volume": "Volume",
            "satuan": "Satuan",
            "tahun_perolehan": "Tahun Perolehan",
            "kondisi_barang": "Kondisi Barang",
            "lokasi_barang": "Lokasi Barang",
            "kategori_barang": "Kategori Barang",
            "foto_barang": "Foto Barang",
            "ik_alat": "IK Alat (PDF)",
            "catatan": "Catatan",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kategori_barang"].widget = forms.Select(
            choices=self.fields["kategori_barang"].choices
        )
        self.fields["kategori_barang"].widget.attrs["data-status-dependent"] = "true"
        self.fields["kategori_barang"].widget.attrs["class"] = "form-control"
        self.fields["kategori_barang"].widget.attrs["required"] = "required"
        self.fields["kategori_barang"].choices = [
            ("", "Pilih kategori barang"),
            *KategoriBarangLaboratoriumChoices.choices,
        ]


class VolumeBaikAssetFormMixin:
    total_volume_info = forms.IntegerField(
        label="Total Volume", required=False, disabled=True, min_value=0
    )

    def _get_kondisi_barang_value(self):
        if self.is_bound:
            return (self.data.get(self.add_prefix("kondisi_barang")) or "").strip()

        initial_value = self.initial.get("kondisi_barang")
        if initial_value:
            return str(initial_value).strip()

        if getattr(self.instance, "kondisi_barang", None):
            return str(self.instance.kondisi_barang).strip()

        return KondisiBarangChoices.BAIK

    def _get_bmn_volume_values(self, kondisi_barang=None):
        kondisi = (
            kondisi_barang
            or self._get_kondisi_barang_value()
            or KondisiBarangChoices.BAIK
        ).strip()
        if kondisi == KondisiBarangChoices.BAIK:
            return 1, 0
        if kondisi == KondisiBarangChoices.HILANG:
            return 0, 0
        return 0, 1

    def _force_bound_bmn_volume_data(self, volume_baik, volume_rusak):
        if not self.is_bound:
            return

        mutable_data = self.data.copy()
        mutable_data[self.add_prefix("volume")] = str(volume_baik)
        mutable_data[self.add_prefix("volume_rusak")] = str(volume_rusak)
        mutable_data[self.add_prefix("total_volume_info")] = str(
            (volume_baik or 0) + (volume_rusak or 0)
        )
        self.data = mutable_data

    def _setup_volume_baik_fields(self):
        status_barang = self._get_status_barang_value()
        is_bmn = status_barang == StatusBarangChoices.BMN
        is_non_bmn = status_barang == StatusBarangChoices.NON_BMN

        volume_field = self.fields["volume"]
        volume_field.label = "Volume Baik"
        volume_field.disabled = False
        volume_field.required = not is_bmn
        volume_field.widget.attrs.pop("disabled", None)
        volume_field.widget.attrs.pop("data-volume-locked", None)
        volume_field.widget.attrs.pop("readonly", None)
        volume_field.widget.attrs.pop("aria-readonly", None)
        volume_field.widget.attrs["class"] = " ".join(
            class_name
            for class_name in volume_field.widget.attrs.get("class", "").split()
            if class_name != "is-readonly-field"
        )
        volume_field.widget.attrs.update(
            {
                "min": "0",
                "data-volume-baik-field": "true",
                "data-bmn-auto-volume-field": "true",
            }
        )
        volume_field.error_messages.setdefault("required", "Volume baik wajib diisi.")
        volume_field.error_messages.setdefault(
            "invalid", "Volume baik harus berupa angka yang valid."
        )
        volume_field.error_messages.setdefault("min_value", "Volume baik minimal 0.")

        volume_rusak_field = self.fields["volume_rusak"]
        volume_rusak_field.required = is_non_bmn
        volume_rusak_field.widget.attrs.update(
            {
                "min": "0",
                "data-volume-rusak-field": "true",
                "data-bmn-auto-volume-field": "true",
            }
        )
        volume_rusak_field.error_messages.setdefault(
            "required", "Volume rusak wajib diisi."
        )
        volume_rusak_field.error_messages.setdefault(
            "invalid", "Volume rusak harus berupa angka yang valid."
        )
        volume_rusak_field.error_messages.setdefault(
            "min_value", "Volume rusak minimal 0."
        )

        if is_non_bmn:
            volume_field.widget.attrs["required"] = "required"
            volume_rusak_field.widget.attrs["required"] = "required"
            for field in (volume_field, volume_rusak_field):
                field.disabled = False
                field.widget.attrs.pop("disabled", None)
                field.widget.attrs.pop("readonly", None)
                field.widget.attrs.pop("aria-readonly", None)
                field.widget.attrs.pop("max", None)
                field.widget.attrs.pop("title", None)
                field.widget.attrs["class"] = " ".join(
                    class_name
                    for class_name in field.widget.attrs.get("class", "").split()
                    if class_name != "is-readonly-field"
                )
        elif is_bmn:
            volume_baik, volume_rusak = self._get_bmn_volume_values()
            self._force_bound_bmn_volume_data(volume_baik, volume_rusak)
            volume_field.initial = volume_baik
            volume_rusak_field.initial = volume_rusak
            for field in (volume_field, volume_rusak_field):
                field.disabled = False
                field.widget.attrs.pop("disabled", None)
                field.widget.attrs.pop("required", None)
                field.widget.attrs.update(
                    {
                        "readonly": "readonly",
                        "aria-readonly": "true",
                        "max": "1",
                        "title": "Otomatis diisi sistem berdasarkan Kondisi Barang.",
                    }
                )
                current_class = field.widget.attrs.get("class", "")
                if "is-readonly-field" not in current_class.split():
                    field.widget.attrs["class"] = (
                        current_class + " is-readonly-field"
                    ).strip()
        else:
            for field in (volume_field, volume_rusak_field):
                field.disabled = False
                field.widget.attrs.pop("disabled", None)
                field.widget.attrs.pop("required", None)
                field.widget.attrs.pop("readonly", None)
                field.widget.attrs.pop("aria-readonly", None)
                field.widget.attrs.pop("max", None)
                field.widget.attrs.pop("title", None)
                field.widget.attrs["class"] = " ".join(
                    class_name
                    for class_name in field.widget.attrs.get("class", "").split()
                    if class_name != "is-readonly-field"
                )

        total_volume_field = self.fields["total_volume_info"]
        total_volume_field.widget.attrs.update(
            {
                "data-total-volume-field": "true",
                "min": "0",
            }
        )
        if is_bmn:
            volume_baik, volume_rusak = self._get_bmn_volume_values()
            total_volume_field.widget.attrs.update({"min": "0", "max": "1"})
            total_volume_field.initial = (volume_baik or 0) + (volume_rusak or 0)
        else:
            total_volume_field.widget.attrs.pop("max", None)
            total_volume_field.initial = getattr(self.instance, "total_volume", 0)

        kondisi_field = self.fields["kondisi_barang"]
        kondisi_field.widget.attrs["data-bmn-only"] = "true"
        kondisi_field.required = is_bmn
        if is_bmn:
            kondisi_field.widget.attrs["required"] = "required"
        else:
            kondisi_field.widget.attrs.pop("required", None)

    def clean(self):
        cleaned_data = super().clean()
        status_barang = (
            cleaned_data.get("status_barang") or self._get_status_barang_value()
        )

        if not status_barang:
            return cleaned_data

        if status_barang == StatusBarangChoices.BMN:
            kondisi_barang = cleaned_data.get("kondisi_barang")
            if not kondisi_barang:
                self.add_error("kondisi_barang", "Kondisi Barang wajib dipilih.")
                return cleaned_data

            volume_baik, volume_rusak = self._get_bmn_volume_values(kondisi_barang)
            cleaned_data["volume"] = volume_baik
            cleaned_data["volume_rusak"] = volume_rusak
            return cleaned_data

        if status_barang != StatusBarangChoices.NON_BMN:
            return cleaned_data

        volume = cleaned_data.get("volume")
        if volume is None:
            self.add_error("volume", "Volume baik wajib diisi.")
        elif volume < 0:
            self.add_error("volume", "Volume baik minimal 0.")

        volume_rusak = cleaned_data.get("volume_rusak")
        if volume_rusak is None:
            self.add_error("volume_rusak", "Volume rusak wajib diisi.")
        elif volume_rusak < 0:
            self.add_error("volume_rusak", "Volume rusak minimal 0.")

        cleaned_data["kode_aset_bmn"] = None
        cleaned_data["kondisi_barang"] = KondisiBarangChoices.BAIK
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.status_barang == StatusBarangChoices.BMN:
            volume_baik, volume_rusak = self._get_bmn_volume_values(
                instance.kondisi_barang
            )
            instance.volume = volume_baik
            instance.volume_rusak = volume_rusak
        else:
            instance.kode_aset_bmn = None
            instance.kondisi_barang = KondisiBarangChoices.BAIK
            if instance.volume is None:
                instance.volume = 0
            if instance.volume_rusak is None:
                instance.volume_rusak = 0

        if commit:
            instance.save()
            self.save_m2m()
            self._delete_queued_files()

        return instance


class FasilitasRuanganForm(VolumeBaikAssetFormMixin, AssetBaseForm):
    total_volume_info = forms.IntegerField(
        label="Total Volume", required=False, disabled=True, min_value=0
    )

    class Meta(AssetBaseForm.Meta):
        model = FasilitasRuangan
        fields = AssetBaseForm.Meta.fields + [
            "volume_rusak",
            "total_volume_info",
            "kategori_barang",
        ]
        labels = {
            "status_barang": "Status Barang",
            "nama_barang": "Nama Barang",
            "tipe_merek_barang": "Tipe / Merek Barang",
            "jenis_barang": "Jenis Barang",
            "kode_aset_bmn": "Kode Aset BMN",
            "kode_laboratorium": "Kode Laboratorium",
            "volume": "Volume Baik",
            "volume_rusak": "Volume Rusak",
            "satuan": "Satuan",
            "tahun_perolehan": "Tahun Perolehan",
            "kondisi_barang": "Kondisi Barang",
            "lokasi_barang": "Lokasi Barang",
            "kategori_barang": "Kategori Barang",
            "foto_barang": "Foto Barang",
            "ik_alat": "IK Alat (PDF)",
            "catatan": "Catatan",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_placeholder_choice("kategori_barang", "Pilih kategori barang")
        self.fields["kategori_barang"].widget.attrs["data-status-dependent"] = "true"
        self._setup_volume_baik_fields()


class PeralatanLaboratoriumForm(VolumeBaikAssetFormMixin, AssetBaseForm):
    total_volume_info = forms.IntegerField(
        label="Total Volume", required=False, disabled=True, min_value=0
    )

    class Meta(AssetBaseForm.Meta):
        model = PeralatanLaboratorium
        fields = AssetBaseForm.Meta.fields + ["volume_rusak", "total_volume_info"]
        labels = {
            "status_barang": "Status Barang",
            "nama_barang": "Nama Barang",
            "tipe_merek_barang": "Tipe / Merek Barang",
            "jenis_barang": "Jenis Barang",
            "kode_aset_bmn": "Kode Aset BMN",
            "kode_laboratorium": "Kode Laboratorium",
            "volume": "Volume Baik",
            "volume_rusak": "Volume Rusak",
            "satuan": "Satuan",
            "tahun_perolehan": "Tahun Perolehan",
            "kondisi_barang": "Kondisi Barang",
            "lokasi_barang": "Lokasi Barang",
            "foto_barang": "Foto Barang",
            "ik_alat": "IK Alat (PDF)",
            "catatan": "Catatan",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_volume_baik_fields()


class BarangPenunjangOperasionalForm(BaseMasterDataForm):
    total_volume_info = forms.IntegerField(
        label="Total Volume", required=False, disabled=True, min_value=0
    )
    ketersediaan_info = forms.CharField(
        label="Ketersediaan", required=False, disabled=True
    )

    class Meta:
        model = BarangPenunjangOperasional
        fields = [
            "nama_barang",
            "tipe_merek_barang",
            "volume",
            "volume_rusak",
            "satuan",
            "kategori_barang",
        ]
        labels = {
            "nama_barang": "Nama Barang",
            "tipe_merek_barang": "Tipe / Merek Barang",
            "volume": "Volume Baik",
            "volume_rusak": "Volume Rusak",
            "satuan": "Satuan",
            "kategori_barang": "Kategori Barang",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_common_widget_style()
        self._set_placeholder_choice("satuan", "Pilih satuan")
        self._set_placeholder_choice("kategori_barang", "Pilih kategori barang")
        self._set_input_attrs(
            {
                "nama_barang": {
                    "placeholder": "Masukkan nama barang",
                    "autocomplete": "off",
                },
                "tipe_merek_barang": {
                    "placeholder": "Masukkan tipe / merek barang",
                    "autocomplete": "off",
                },
                "volume": {"min": "0", "data-volume-baik-field": "true"},
                "volume_rusak": {"min": "0", "data-volume-rusak-field": "true"},
            }
        )
        self.fields["total_volume_info"].widget.attrs["data-total-volume-field"] = (
            "true"
        )
        self.fields["total_volume_info"].initial = getattr(
            self.instance, "total_volume", 0
        )
        self.fields["ketersediaan_info"].initial = getattr(
            self.instance, "ketersediaan", KetersediaanChoices.TERSEDIA
        )
        self.fields["volume"].error_messages.setdefault(
            "invalid", "Volume baik harus berupa angka yang valid."
        )
        self.fields["volume"].error_messages.setdefault(
            "min_value", "Volume baik minimal 0."
        )
        self.fields["volume_rusak"].error_messages.setdefault(
            "invalid", "Volume rusak harus berupa angka yang valid."
        )
        self.fields["volume_rusak"].error_messages.setdefault(
            "min_value", "Volume rusak minimal 0."
        )

    def clean_nama_barang(self):
        return self._validate_case_insensitive_unique(
            BarangPenunjangOperasional,
            "nama_barang",
            self.cleaned_data.get("nama_barang"),
            "Nama barang sudah digunakan.",
        )

    def clean(self):
        cleaned_data = super().clean()
        volume_baik = cleaned_data.get("volume") or 0
        volume_dipinjam = getattr(self.instance, "volume_dipinjam", 0) or 0
        if volume_baik < volume_dipinjam:
            self.add_error(
                "volume",
                f"Volume baik tidak boleh lebih kecil dari jumlah yang sedang dipinjam ({volume_dipinjam}).",
            )
        return cleaned_data


class BahanOperasionalForm(BaseMasterDataForm):
    ketersediaan_info = forms.CharField(
        label="Ketersediaan", required=False, disabled=True
    )

    class Meta:
        model = BahanOperasional
        fields = ["nama_barang", "kategori_barang", "volume", "satuan", "stok_minimum"]
        labels = {
            "nama_barang": "Nama Barang",
            "kategori_barang": "Kategori Barang",
            "volume": "Volume",
            "satuan": "Satuan",
            "stok_minimum": "Stok Minimum",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_common_widget_style()
        self._set_placeholder_choice("kategori_barang", "Pilih kategori barang")
        self._set_placeholder_choice("satuan", "Pilih satuan")
        self._set_input_attrs(
            {
                "nama_barang": {
                    "placeholder": "Masukkan nama bahan operasional",
                    "autocomplete": "off",
                },
                "volume": {"min": "0"},
                "stok_minimum": {"min": "1"},
            }
        )
        self.fields["ketersediaan_info"].initial = getattr(
            self.instance, "ketersediaan", "Habis"
        )
        self.fields["volume"].error_messages.setdefault(
            "invalid", "Volume harus berupa angka yang valid."
        )
        self.fields["stok_minimum"].error_messages.setdefault(
            "invalid", "Stok minimum harus berupa angka yang valid."
        )
        self.fields["stok_minimum"].error_messages.setdefault(
            "min_value", "Stok minimum minimal 1."
        )

    def clean_nama_barang(self):
        return self._validate_case_insensitive_unique(
            BahanOperasional,
            "nama_barang",
            self.cleaned_data.get("nama_barang"),
            "Nama barang sudah digunakan.",
        )
