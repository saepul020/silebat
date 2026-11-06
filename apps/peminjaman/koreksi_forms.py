from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.forms import BaseModelFormSet, modelformset_factory
from django.utils import timezone

from apps.master_data.models import BarangLaboratorium
from apps.core.upload_validation import apply_upload_widget_validation_attrs, validate_uploaded_file

from .forms import DateInput, FlexibleDateField
from .models import PeminjamanBarangLaboratorium, PeminjamanRequest


IDENTITAS_FIELDS = (
    "nama_peminjam", "no_hp_peminjam", "email_peminjam", "nip_peminjam", "alamat_peminjam",
)
KEGIATAN_FIELDS = (
    "layanan_kegiatan", "layanan_kegiatan_lainnya", "tim_kegiatan", "kegiatan_survei",
    "survei_lainnya", "instansi_tujuan", "instansi_tujuan_lainnya", "tanggal_mulai", "tanggal_selesai", "berkas_pendukung",
)
PENGUKURAN_FIELDS = tuple(key for key, _ in PeminjamanRequest().pengukuran_fields)
RIWAYAT_FIELDS = ("pimpinan_at", "return_started_at", "return_completed_at")
ALAT_FIELDS = (
    "nama_barang", "tipe_merek_barang", "jenis_barang", "status_barang", "kode_aset_bmn",
    "kode_laboratorium", "volume", "satuan", "kondisi_barang", "tahun_perolehan",
)
CHOICE_PAIRS = (
    ("layanan_kegiatan", "layanan_kegiatan_lainnya"), ("instansi_tujuan", "instansi_tujuan_lainnya"),
)
DATE_LIMITS = {
    "tanggal_selesai": ("tanggal_mulai",),
    "tanggal_persetujuan": ("tanggal_mulai",),
    "tanggal_pengembalian": ("tanggal_selesai",),
    "tanggal_selesai_pengembalian": ("tanggal_selesai", "tanggal_pengembalian"),
}


class KoreksiUpload(forms.ClearableFileInput):
    template_name = "peminjaman/partials/koreksi_upload.html"


class KoreksiLaporanForm(forms.ModelForm):
    tanggal_mulai = FlexibleDateField(label="Mulai Tanggal", widget=DateInput())
    tanggal_selesai = FlexibleDateField(label="Selesai Tanggal", widget=DateInput())
    tanggal_persetujuan = FlexibleDateField(label="Tanggal Persetujuan", widget=DateInput())
    tanggal_pengembalian = FlexibleDateField(label="Tanggal Mulai Pengembalian", widget=DateInput())
    tanggal_selesai_pengembalian = FlexibleDateField(label="Tanggal Pengembalian Selesai", widget=DateInput())
    versi = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = PeminjamanRequest
        fields = ("peminjam", *KEGIATAN_FIELDS, *PENGUKURAN_FIELDS)
        labels = {
            "peminjam": "Akun Peminjam",
            "layanan_kegiatan": "Layanan Kegiatan", "layanan_kegiatan_lainnya": "Layanan Kegiatan Lainnya",
            "tim_kegiatan": "Tim Kegiatan", "kegiatan_survei": "Kegiatan Survei",
            "survei_lainnya": "Kegiatan Survei Lainnya", "instansi_tujuan": "Instansi Tujuan",
            "instansi_tujuan_lainnya": "Instansi Tujuan Lainnya", "berkas_pendukung": "Berkas Pendukung (PDF, maksimal 7 MB)",
            **dict(PeminjamanRequest().pengukuran_fields),
        }
        widgets = {
            "kegiatan_survei": forms.CheckboxSelectMultiple(attrs={"class": "survey-choice-input"}),
            "berkas_pendukung": KoreksiUpload(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.previous = {
            name: getattr(self.instance, name) for name in self.Meta.fields if name != "kegiatan_survei"
        }
        self.previous["kegiatan_survei"] = self.instance.kegiatan_survei.all()
        self.pending_fields = set()
        self.fields["peminjam"].queryset = get_user_model().objects.select_related("profile").filter(
            Q(is_active=True) | Q(pk=self.instance.peminjam_id)
        ).order_by("first_name", "username")
        for name, attr in zip(
            ("tanggal_persetujuan", "tanggal_pengembalian", "tanggal_selesai_pengembalian"), RIWAYAT_FIELDS,
        ):
            value = getattr(self.instance, attr)
            self.previous[name] = timezone.localtime(value).date() if value else None
        self.initial["versi"] = self.instance.updated_at.isoformat()
        for name, field in self.fields.items():
            if name != "versi":
                field.required = False
                if name != "berkas_pendukung":
                    self.initial[name] = None
            if isinstance(field, FlexibleDateField):
                field.widget.attrs["class"] = "date-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "select-input"
            elif name != "kegiatan_survei":
                field.widget.attrs["class"] = "text-input"
            if isinstance(field, FlexibleDateField):
                field.widget.attrs["data-maint-date-picker"] = "true"
                field.widget.attrs["data-koreksi-previous"] = self.previous[name].isoformat() if self.previous[name] else ""
            if name in PENGUKURAN_FIELDS:
                field.widget.attrs["min"] = 0
        for name, sources in DATE_LIMITS.items():
            self.fields[name].widget.attrs.update({
                "data-maint-min-source": f"koreksi-date-{self[sources[-1]].id_for_label}",
                "data-koreksi-min-sources": " ".join(self[source].id_for_label for source in sources),
            })
        for selected, manual in CHOICE_PAIRS:
            self.fields[selected].widget.attrs["data-koreksi-other"] = self[manual].id_for_label
        file_field = self.fields["berkas_pendukung"]
        file_field.widget.attrs.update({
            "accept": ".pdf,application/pdf", "class": "input-file input-file--proxy",
            "data-inline-file-input": "true", "data-inline-file-placeholder": "Pilih file PDF",
        })
        apply_upload_widget_validation_attrs(
            file_field, allowed_extensions="pdf", invalid_extension_message="Berkas pendukung harus berupa PDF.",
        )
        for name in ("peminjam", "layanan_kegiatan", "tim_kegiatan", "instansi_tujuan"):
            self.fields[name].empty_label = f"Pilih {self.fields[name].label.lower()}"
        report = self.instance.report_snapshot or {}
        kegiatan = report.get("kegiatan", {})
        for name in ("layanan_kegiatan", "tim_kegiatan", "instansi_tujuan"):
            if not getattr(self.instance, f"{name}_id") and kegiatan.get(name):
                self.fields[name].help_text = f"Nilai historis: {kegiatan[name]}. Pilih master untuk menghubungkan ke grafik."

    def clean_berkas_pendukung(self):
        if not self.files.get(self.add_prefix("berkas_pendukung")):
            return self.cleaned_data.get("berkas_pendukung")
        return validate_uploaded_file(
            self.cleaned_data.get("berkas_pendukung"), allowed_extensions={".pdf"},
            invalid_extension_message="Berkas pendukung harus berupa PDF.",
        )

    def clean(self):
        data = super().clean()
        for name, field in self.fields.items():
            if name == "versi":
                continue
            raw = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(name))
            if raw not in field.empty_values and (name in self.errors or data.get(name) not in field.empty_values):
                self.pending_fields.add(name)
            elif name not in self.errors:
                data[name] = self.previous[name]
        for rel, manual in CHOICE_PAIRS:
            selected, other = rel in self.pending_fields, manual in self.pending_fields
            if selected and other:
                message = "Pilih data dari daftar atau isi lainnya, bukan keduanya."
                self.add_error(rel, message)
                self.add_error(manual, message)
            elif selected:
                data[manual] = ""
            elif other:
                data[rel] = None
        for name, sources in DATE_LIMITS.items():
            if not self.pending_fields.intersection((name, *sources)):
                continue
            value = data.get(name)
            bounds = [data[source] for source in sources if data.get(source)]
            if value and bounds and value < max(bounds):
                labels = " dan ".join(self.fields[source].label for source in sources)
                self.add_error(name, f"{self.fields[name].label} tidak boleh sebelum {labels}.")
        approval, returned = data.get("tanggal_persetujuan"), data.get("tanggal_pengembalian")
        if self.pending_fields.intersection(("tanggal_persetujuan", "tanggal_pengembalian")) and approval and returned and approval > returned:
            self.add_error("tanggal_persetujuan", "Tanggal persetujuan tidak boleh setelah tanggal pengembalian.")
        return data


class KoreksiAlatForm(forms.ModelForm):
    class Meta:
        model = PeminjamanBarangLaboratorium
        fields = ("barang",)
        labels = {"barang": "Peralatan Survei Lapangan"}

    def __init__(self, *args, **kwargs):
        alat_choices = kwargs.pop("alat_choices", None)
        super().__init__(*args, **kwargs)
        self.old_barang_id = self.instance.barang_id
        self.replace_master = False
        self.initial["barang"] = None
        self.fields["barang"].queryset = BarangLaboratorium.objects.order_by("nama_barang", "kode_laboratorium")
        if alat_choices is not None:
            self.fields["barang"].choices = alat_choices
        self.fields["barang"].widget.attrs["class"] = "select-input"
        self.fields["barang"].widget.attrs["data-previous-barang"] = self.old_barang_id or ""

    def clean(self):
        data = super().clean()
        self.replace_master = bool(data.get("barang"))
        if not self.replace_master and self.instance.pk and "barang" not in self.errors:
            data["barang"] = self.instance.barang
        return data


class BaseKoreksiAlatFormSet(BaseModelFormSet):
    def __init__(self, *args, protected_ids=(), **kwargs):
        self.protected_ids = set(protected_ids)
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        expected = set(self.get_queryset().values_list("pk", flat=True))
        submitted = [f.cleaned_data.get("id") for f in self.initial_forms]
        if self.initial_form_count() != len(expected) or {obj.pk for obj in submitted if obj} != expected or len(submitted) != len(expected):
            raise forms.ValidationError("Daftar alat berubah atau tidak valid. Muat ulang halaman koreksi.")
        selected = set()
        for form in self.forms:
            if not form.cleaned_data:
                continue
            data = form.cleaned_data
            barang = data.get("barang")
            barang_id = barang.pk if barang else None
            if form.instance.pk in self.protected_ids and (
                data.get("DELETE") or barang_id != form.old_barang_id
            ):
                raise forms.ValidationError(
                    "Relasi alat rusak, hilang, atau terkait transfer harus dipertahankan. "
                    "Penggantian/penghapusan relasi alat memerlukan rekonsiliasi stok dan transfer."
                )
            if data.get("DELETE"):
                continue
            if barang_id and barang_id in selected:
                raise forms.ValidationError("Master alat yang sama tidak boleh dipilih lebih dari sekali.")
            if barang_id:
                selected.add(barang_id)


KoreksiAlatFormSet = modelformset_factory(
    PeminjamanBarangLaboratorium, form=KoreksiAlatForm, formset=BaseKoreksiAlatFormSet,
    extra=0, can_delete=True, max_num=200, validate_max=True, absolute_max=400,
)
