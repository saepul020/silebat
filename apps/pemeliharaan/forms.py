from datetime import datetime, time

from django import forms
from django.db import transaction
from django.utils import timezone

from apps.peminjaman.forms import parse_flexible_date
from apps.core.upload_validation import (
    MAX_UPLOAD_SIZE_BYTES,
    build_max_upload_size_message,
    validate_uploaded_file,
)
from apps.master_data.models import BarangLaboratorium, KondisiBarangChoices

from .models import (
    ACTIVE_PEMELIHARAAN_STEPS,
    JenisFotoPemeliharaanChoices,
    KondisiPemeliharaanChoices,
    MAX_PEMELIHARAAN_PHOTOS,
    PemeliharaanFoto,
    PemeliharaanItem,
    PemeliharaanPengajuan,
    TindakanPerbaikanChoices,
)


DATE_TIME_INPUT_FORMATS = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]
MONTH_NAMES_SHORT_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def format_display_date(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        value = timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    return f"{value.day:02d} {MONTH_NAMES_SHORT_ID[value.month - 1]} {value.year}"


def date_to_end_of_day(value):
    parsed_date = parse_flexible_date(value)
    if not parsed_date:
        return None
    combined = datetime.combine(parsed_date, time(23, 59))
    return timezone.make_aware(combined, timezone.get_current_timezone())


def get_available_alat_queryset(instance=None):
    active_alat_ids = PemeliharaanPengajuan.objects.filter(
        current_step__in=ACTIVE_PEMELIHARAAN_STEPS,
        alat__isnull=False,
    )
    if instance and instance.pk:
        active_alat_ids = active_alat_ids.exclude(pk=instance.pk)

    return (
        BarangLaboratorium.objects.filter(sedang_dipinjam=False)
        .exclude(pk__in=active_alat_ids.values("alat_id"))
        .order_by("nama_barang", "kode_laboratorium")
    )


class PemeliharaanAlatChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        kode = obj.kode_laboratorium or "-"
        tipe = obj.tipe_merek_barang or "-"
        return f"{obj.nama_barang} ({kode}) - {tipe}"


class PemeliharaanForm(forms.Form):
    komponen_validasi = forms.CharField(required=False, widget=forms.HiddenInput())
    dokumentasi_pemeriksaan = forms.CharField(required=False, widget=forms.HiddenInput())
    pilih_alat = PemeliharaanAlatChoiceField(
        label="Pilih Alat",
        queryset=BarangLaboratorium.objects.none(),
        empty_label="Pilih alat",
    )
    tanggal_pemeriksaan = forms.CharField(
        label="Tanggal Pemeriksaan",
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "date-input",
                "placeholder": "Masukan tanggal sesuai format",
                "autocomplete": "off",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.actor = kwargs.pop("actor", None)
        self.instance = kwargs.pop("instance", None)
        self.tanggal_pemeriksaan_value = kwargs.pop("tanggal_pemeriksaan", None) or timezone.now()
        if self.instance and self.instance.pk:
            self.tanggal_pemeriksaan_value = self.instance.tanggal_pemeriksaan
        super().__init__(*args, **kwargs)
        self.cleaned_items = []
        self.pemeriksaan_files = []
        self.component_errors = {}
        self.fields["pilih_alat"].queryset = get_available_alat_queryset(self.instance)
        if self.instance and self.instance.alat_id:
            self.fields["pilih_alat"].initial = self.instance.alat
        self.fields["tanggal_pemeriksaan"].initial = format_display_date(self.tanggal_pemeriksaan_value)
        self._set_common_widget_style()
        self.fields["pilih_alat"].widget.attrs["data-preserve-placeholder"] = "true"
        self.fields["tanggal_pemeriksaan"].widget.attrs.update(
            {
                "readonly": "readonly",
                "aria-readonly": "true",
                "class": (
                    self.fields["tanggal_pemeriksaan"].widget.attrs.get("class", "")
                    + " is-readonly-field"
                ).strip(),
            }
        )

    def _set_common_widget_style(self):
        for field in self.fields.values():
            field.help_text = ""
            current_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (current_class + " form-control").strip()
            if field.required:
                field.error_messages["required"] = self._get_required_message(field)
                field.widget.attrs["required"] = "required"

    def _get_required_message(self, field):
        label = (field.label or "Kolom ini").strip()
        if isinstance(field.widget, forms.Select):
            return f"{label} wajib dipilih."
        return f"{label} wajib diisi."

    def _get_selected_alat(self):
        raw_value = self.data.get(self.add_prefix("pilih_alat")) if self.is_bound else None
        if not raw_value:
            return self.initial.get("pilih_alat") or getattr(self.instance, "alat", None)
        try:
            return self.fields["pilih_alat"].queryset.get(pk=raw_value)
        except (BarangLaboratorium.DoesNotExist, ValueError, TypeError):
            return None

    def _get_components(self, alat=None):
        alat = alat or self._get_selected_alat()
        values = getattr(alat, "komponen_pemeliharaan", None) or []
        if isinstance(values, str):
            values = [values]
        return [str(value or "").strip() for value in values if str(value or "").strip()]

    def _get_value(self, name, default=""):
        return str(self.data.get(name, default) or "").strip()

    def _get_files(self, name):
        return list(self.files.getlist(name)) if self.files else []

    def _add_component_error(self, index, message, *, area="komponen"):
        error_data = self.component_errors.setdefault(
            index,
            {"komponen": [], "perbaikan": []},
        )
        error_data.setdefault(area, []).append(message)

    def _validate_photos(
        self,
        field_name,
        label,
        *,
        required=True,
        existing_count=0,
        add_error,
    ):
        files = self._get_files(field_name)
        if required and not files:
            add_error(f"{label} wajib diupload.")
            return []
        if existing_count + len(files) > MAX_PEMELIHARAAN_PHOTOS:
            add_error(
                f"{label} maksimal {MAX_PEMELIHARAAN_PHOTOS} foto termasuk foto yang sudah tersimpan."
            )
            return []

        cleaned = []
        for file_obj in files:
            try:
                cleaned.append(
                    validate_uploaded_file(
                        file_obj,
                        allowed_extensions={".jpg", ".jpeg", ".png"},
                        invalid_extension_message=f"{label} hanya boleh berupa file JPG, JPEG, atau PNG.",
                        max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
                        max_size_message=build_max_upload_size_message(label),
                    )
                )
            except forms.ValidationError as exc:
                for message in exc.messages:
                    add_error(message)
        return cleaned

    def _existing_photo_queryset(self, jenis, component=None):
        if not self.instance or not self.instance.pk:
            return PemeliharaanFoto.objects.none()

        queryset = PemeliharaanFoto.objects.filter(
            item__pengajuan=self.instance,
            jenis=jenis,
        )
        if component is not None:
            queryset = queryset.filter(item__komponen=component)
        return queryset.order_by("urutan", "id")

    def _existing_photo_count(self, jenis, component=None):
        return self._existing_photo_queryset(jenis, component).count()

    def _existing_photo_data(self, jenis, component=None):
        photos = []
        for index, photo in enumerate(
            self._existing_photo_queryset(jenis, component),
            start=1,
        ):
            if not photo.foto:
                continue
            photos.append(
                {
                    "url": photo.foto.url,
                    "name": photo.foto.name.rsplit("/", 1)[-1],
                    "label": f"{photo.get_jenis_display()} {index}",
                }
            )
        return photos

    def _has_existing_item_photos(self, component, jenis):
        return self._existing_photo_count(jenis, component) > 0

    @property
    def existing_pemeriksaan_fotos(self):
        return self._existing_photo_data(JenisFotoPemeliharaanChoices.PEMERIKSAAN)

    def _parse_datetime(self, index, field_name, label):
        value = self._get_value(field_name)
        if not value:
            self._add_component_error(index, f"{label} wajib diisi.", area="perbaikan")
            return None

        try:
            field = forms.DateTimeField(input_formats=DATE_TIME_INPUT_FORMATS)
            return field.clean(value)
        except forms.ValidationError:
            try:
                return date_to_end_of_day(value)
            except (TypeError, ValueError, forms.ValidationError):
                self._add_component_error(
                    index,
                    f"{label} harus berupa tanggal yang valid.",
                    area="perbaikan",
                )
                return None

    def _build_bound_rows(self, components):
        rows = []
        for index, component in enumerate(components):
            condition = self._get_value(
                f"kondisi_{index}",
                KondisiPemeliharaanChoices.BAIK,
            )
            action = self._get_value(f"tindakan_{index}")
            rows.append(
                {
                    "index": index,
                    "komponen": component,
                    "kondisi": condition,
                    "tindakan": action,
                    "uraian_perbaikan": self._get_value(f"uraian_perbaikan_{index}"),
                    "tanggal_selesai_perbaikan": self._get_value(f"tanggal_selesai_perbaikan_{index}"),
                    "uraian_kerusakan": self._get_value(f"uraian_kerusakan_{index}"),
                    "existing_perbaikan_fotos": self._existing_photo_data(
                        JenisFotoPemeliharaanChoices.PERBAIKAN,
                        component,
                    ),
                    "existing_kerusakan_fotos": self._existing_photo_data(
                        JenisFotoPemeliharaanChoices.KERUSAKAN,
                        component,
                    ),
                    "errors": self.component_errors.get(index, {}).get("komponen", []),
                    "repair_errors": self.component_errors.get(index, {}).get("perbaikan", []),
                }
            )
        return rows

    def _build_instance_rows(self, components):
        item_map = {
            item.komponen: item
            for item in self.instance.items.all()
        } if self.instance and self.instance.pk else {}
        rows = []
        for index, component in enumerate(components):
            item = item_map.get(component)
            rows.append(
                {
                    "index": index,
                    "komponen": component,
                    "kondisi": getattr(item, "kondisi", "") if item else "",
                    "tindakan": getattr(item, "tindakan_perbaikan", "") if item else "",
                    "uraian_perbaikan": getattr(item, "uraian_perbaikan", "") if item else "",
                    "tanggal_selesai_perbaikan": format_display_date(item.tanggal_selesai_perbaikan)
                    if item and item.tanggal_selesai_perbaikan
                    else "",
                    "uraian_kerusakan": getattr(item, "uraian_kerusakan", "") if item else "",
                    "existing_perbaikan_fotos": self._existing_photo_data(
                        JenisFotoPemeliharaanChoices.PERBAIKAN,
                        component,
                    ),
                    "existing_kerusakan_fotos": self._existing_photo_data(
                        JenisFotoPemeliharaanChoices.KERUSAKAN,
                        component,
                    ),
                    "errors": self.component_errors.get(index, {}).get("komponen", []),
                    "repair_errors": self.component_errors.get(index, {}).get("perbaikan", []),
                }
            )
        return rows

    @property
    def component_rows(self):
        alat = self._get_selected_alat()
        components = self._get_components(alat)
        if not components:
            return []
        if self.is_bound:
            return self._build_bound_rows(components)
        if self.instance and self.instance.pk:
            return self._build_instance_rows(components)
        return [
            {
                "index": index,
                "komponen": component,
                "kondisi": "",
                "tindakan": "",
                "uraian_perbaikan": "",
                "tanggal_selesai_perbaikan": "",
                "uraian_kerusakan": "",
                "existing_perbaikan_fotos": [],
                "existing_kerusakan_fotos": [],
                "errors": [],
                "repair_errors": [],
            }
            for index, component in enumerate(components)
        ]

    @property
    def has_repair_rows(self):
        return any(
            row["kondisi"] == KondisiPemeliharaanChoices.PERLU_PERBAIKAN
            for row in self.component_rows
        )

    def clean(self):
        cleaned_data = super().clean()
        alat = cleaned_data.get("pilih_alat")
        if not alat:
            return cleaned_data

        components = self._get_components(alat)
        if not components:
            self.add_error(
                "pilih_alat",
                "Alat ini belum memiliki Komponen Pemeliharaan Rutin pada Data Master.",
            )
            return cleaned_data

        active_duplicate = PemeliharaanPengajuan.objects.filter(
            alat=alat,
            current_step__in=ACTIVE_PEMELIHARAAN_STEPS,
        )
        if self.instance and self.instance.pk:
            active_duplicate = active_duplicate.exclude(pk=self.instance.pk)
        if active_duplicate.exists():
            self.add_error(
                "pilih_alat",
                "Alat ini sedang memiliki pengajuan pemeliharaan aktif.",
            )
            return cleaned_data

        item_data = []
        condition_values = {choice[0] for choice in KondisiPemeliharaanChoices.choices}
        action_values = {choice[0] for choice in TindakanPerbaikanChoices.choices}
        pemeriksaan_errors = []
        existing_pemeriksaan_count = self._existing_photo_count(
            JenisFotoPemeliharaanChoices.PEMERIKSAAN
        )
        self.pemeriksaan_files = self._validate_photos(
            "dokumentasi_pemeriksaan",
            "Dokumentasi Pemeriksaan",
            required=existing_pemeriksaan_count == 0,
            existing_count=existing_pemeriksaan_count,
            add_error=pemeriksaan_errors.append,
        )
        for message in pemeriksaan_errors:
            self.add_error("dokumentasi_pemeriksaan", message)

        for index, component in enumerate(components):
            posted_component = self._get_value(f"komponen_{index}")
            if posted_component and posted_component != component:
                self._add_component_error(index, "Data komponen tidak sesuai dengan Data Master.")

            condition = self._get_value(f"kondisi_{index}")
            if condition not in condition_values:
                self._add_component_error(index, "Kondisi pemeliharaan wajib dipilih.")

            row = {
                "komponen": component,
                "kondisi": condition,
                "tindakan_perbaikan": "",
                "uraian_perbaikan": "",
                "tanggal_mulai_perbaikan": None,
                "tanggal_selesai_perbaikan": None,
                "perbaikan_files": [],
                "uraian_kerusakan": "",
                "kerusakan_files": [],
            }

            if condition == KondisiPemeliharaanChoices.PERLU_PERBAIKAN:
                action = self._get_value(f"tindakan_{index}")
                if action not in action_values:
                    self._add_component_error(
                        index,
                        "Tindakan perbaikan wajib dipilih.",
                        area="perbaikan",
                    )
                row["tindakan_perbaikan"] = action

                if action == TindakanPerbaikanChoices.MANDIRI:
                    uraian = self._get_value(f"uraian_perbaikan_{index}")
                    if not uraian:
                        self._add_component_error(
                            index,
                            "Uraian Perbaikan wajib diisi.",
                            area="perbaikan",
                        )
                    selesai = self._parse_datetime(
                        index,
                        f"tanggal_selesai_perbaikan_{index}",
                        "Tanggal selesai perbaikan",
                    )
                    if selesai and selesai < self.tanggal_pemeriksaan_value:
                        self._add_component_error(
                            index,
                            "Tanggal selesai perbaikan tidak boleh lebih awal dari tanggal pemeriksaan.",
                            area="perbaikan",
                        )
                    row.update(
                        {
                            "uraian_perbaikan": uraian,
                            "tanggal_mulai_perbaikan": self.tanggal_pemeriksaan_value,
                            "tanggal_selesai_perbaikan": selesai,
                            "perbaikan_files": self._validate_photos(
                                f"dokumentasi_perbaikan_{index}",
                                "Dokumentasi Perbaikan",
                                required=not self._has_existing_item_photos(
                                    component,
                                    JenisFotoPemeliharaanChoices.PERBAIKAN,
                                ),
                                existing_count=self._existing_photo_count(
                                    JenisFotoPemeliharaanChoices.PERBAIKAN,
                                    component,
                                ),
                                add_error=lambda message, row_index=index: self._add_component_error(
                                    row_index,
                                    message,
                                    area="perbaikan",
                                ),
                            ),
                        }
                    )
                elif action == TindakanPerbaikanChoices.EKSTERNAL:
                    uraian = self._get_value(f"uraian_kerusakan_{index}")
                    if not uraian:
                        self._add_component_error(
                            index,
                            "Uraian Kerusakan wajib diisi.",
                            area="perbaikan",
                        )
                    row.update(
                        {
                            "uraian_kerusakan": uraian,
                            "kerusakan_files": self._validate_photos(
                                f"dokumentasi_kerusakan_{index}",
                                "Dokumentasi Kerusakan",
                                required=not self._has_existing_item_photos(
                                    component,
                                    JenisFotoPemeliharaanChoices.KERUSAKAN,
                                ),
                                existing_count=self._existing_photo_count(
                                    JenisFotoPemeliharaanChoices.KERUSAKAN,
                                    component,
                                ),
                                add_error=lambda message, row_index=index: self._add_component_error(
                                    row_index,
                                    message,
                                    area="perbaikan",
                                ),
                            ),
                        }
                    )

            item_data.append(row)

        if self.component_errors:
            self.add_error("komponen_validasi", "Periksa kembali data komponen pemeriksaan.")

        self.cleaned_items = item_data
        return cleaned_data

    def save(self):
        alat = self.cleaned_data["pilih_alat"]
        with transaction.atomic():
            pengajuan = self.instance if self.instance and self.instance.pk else None
            old_alat = getattr(pengajuan, "alat", None)
            if pengajuan is None:
                pengajuan = PemeliharaanPengajuan.objects.create(
                    pemohon=self.actor,
                    alat=alat,
                    tanggal_pemeriksaan=self.tanggal_pemeriksaan_value,
                )
            else:
                old_kondisi_barang = pengajuan.kondisi_barang_sebelum
                old_tanggal_pemeliharaan = pengajuan.tanggal_pemeliharaan_sebelum
                old_tanggal_perbaikan = pengajuan.tanggal_perbaikan_sebelum
                old_master_awal_disimpan = pengajuan.master_awal_disimpan
                pengajuan.alat = alat
                pengajuan.tanggal_pemeriksaan = self.tanggal_pemeriksaan_value
                if old_alat and old_alat.pk != alat.pk:
                    pengajuan.kondisi_barang_sebelum = ""
                    pengajuan.tanggal_pemeliharaan_sebelum = None
                    pengajuan.tanggal_perbaikan_sebelum = None
                    pengajuan.master_awal_disimpan = False
                pengajuan.save(
                    update_fields=[
                        "alat",
                        "tanggal_pemeriksaan",
                        "snapshot_nama_barang",
                        "snapshot_kode_laboratorium",
                        "snapshot_tipe_merek_barang",
                        "snapshot_status_barang",
                        "kondisi_barang_sebelum",
                        "tanggal_pemeliharaan_sebelum",
                        "tanggal_perbaikan_sebelum",
                        "master_awal_disimpan",
                        "updated_at",
                    ]
                )

            item_map = {
                item.komponen: item
                for item in pengajuan.items.all()
            }
            used_components = set()
            for row in self.cleaned_items:
                item = item_map.get(row["komponen"])
                if item is None:
                    item = PemeliharaanItem(pengajuan=pengajuan, komponen=row["komponen"])
                item.kondisi = row["kondisi"]
                item.tindakan_perbaikan = row["tindakan_perbaikan"]
                item.uraian_perbaikan = row["uraian_perbaikan"]
                item.tanggal_mulai_perbaikan = row["tanggal_mulai_perbaikan"]
                item.tanggal_selesai_perbaikan = row["tanggal_selesai_perbaikan"]
                item.uraian_kerusakan = row["uraian_kerusakan"]
                item.save()
                used_components.add(row["komponen"])
                self._save_photos(
                    item,
                    JenisFotoPemeliharaanChoices.PERBAIKAN,
                    row["perbaikan_files"],
                )
                self._save_photos(
                    item,
                    JenisFotoPemeliharaanChoices.KERUSAKAN,
                    row["kerusakan_files"],
                )

            pengajuan.items.exclude(komponen__in=used_components).delete()
            first_item = pengajuan.items.order_by("id").first()
            if first_item and self.pemeriksaan_files:
                self._save_photos(
                    first_item,
                    JenisFotoPemeliharaanChoices.PEMERIKSAAN,
                    self.pemeriksaan_files,
                )

            pengajuan.tandai_alat_dalam_pemeliharaan()
            if old_alat and old_alat.pk != alat.pk:
                has_active_old = PemeliharaanPengajuan.objects.filter(
                    alat=old_alat,
                    current_step__in=ACTIVE_PEMELIHARAAN_STEPS,
                ).exclude(pk=pengajuan.pk).exists()
                if not has_active_old:
                    old_alat.kondisi_barang = old_kondisi_barang or KondisiBarangChoices.BAIK
                    update_fields = ["kondisi_barang", "updated_at"]
                    if old_master_awal_disimpan:
                        old_alat.tanggal_pemeliharaan = old_tanggal_pemeliharaan
                        old_alat.tanggal_perbaikan = old_tanggal_perbaikan
                        update_fields.extend(["tanggal_pemeliharaan", "tanggal_perbaikan"])
                    old_alat.save(update_fields=update_fields)
        return pengajuan

    def _save_photos(self, item, jenis, files):
        start_order = PemeliharaanFoto.objects.filter(item=item, jenis=jenis).count() + 1
        for order, file_obj in enumerate(files or [], start=start_order):
            PemeliharaanFoto.objects.create(
                item=item,
                jenis=jenis,
                foto=file_obj,
                urutan=order,
            )
