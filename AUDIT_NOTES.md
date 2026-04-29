# Audit dan Refactoring SILEBAT

Tanggal audit: 28 April 2026

## Ringkasan Perubahan Aman

1. Pagination list data pada app `master_data` sudah memakai helper global `apps.core.list_pagination.paginate_list`, sehingga konfigurasi `Show Entries`, pagination, dan query string tidak lagi diduplikasi di `master_data/views.py`.
2. Handler import Excel untuk `Data Peralatan Survei Lapangan` disatukan ke helper import global di `master_data/views.py`, sama seperti import data master lainnya.
3. Generator file format import Excel untuk `Data Peralatan Survei Lapangan` disatukan ke helper `_download_import_template`, sehingga logika workbook, referensi pilihan, dan validasi dropdown tidak lagi ditulis berulang.
4. Properti `sisa_volume` ganda pada model `BarangPenunjangOperasional` dihapus. Properti yang dipertahankan adalah versi yang memakai `volume_baik` dan `volume_pinjam_aktif`.
5. Class CSS yang terlalu panjang pada area chart, tabel pengembalian, tabel ringkasan, dan tabel operasional disederhanakan. Semua referensi pada HTML, CSS, dan JS ikut diperbarui.
6. Root warna global SILEBAT diperbarui menggunakan palet warna utama yang diminta dan semantic variable lama dipetakan ulang agar perubahan tetap kompatibel dengan style yang sudah berjalan.
7. Cache-busting query string static CSS/JS diperbarui ke `20260428-audit-refactor` agar browser tidak memakai cache lama setelah deploy.
8. Artefak Python cache (`__pycache__` dan `*.pyc`) dihapus dari paket project hasil akhir.

## File yang Diperbaiki

- `apps/master_data/views.py`
- `apps/master_data/models.py`
- `apps/dashboard/templates/dashboard/index.html`
- `apps/operasional/templates/operasional/data_instansi_list.html`
- `apps/operasional/templates/operasional/data_kop_dokumen_list.html`
- `apps/operasional/templates/operasional/data_tim_list.html`
- `apps/peminjaman/templates/peminjaman/pengembalian_form.html`
- `templates/base.html`
- `templates/registration/login.html`
- `static/css/style.css`
- `static/css/style_dashboard.css`
- `static/css/style_login.css`
- `static/css/style_navbar.css`
- `static/css/style_sidebar.css`
- `static/js/apps.js`

## File yang Dihapus

File program aktif tidak dihapus. Yang dibersihkan hanya artefak cache Python:

- seluruh folder `__pycache__`
- seluruh file `*.pyc`

Jumlah artefak cache yang dibersihkan dari ZIP awal: 96 file.

## Class yang Disederhanakan

- `dashboard-chart-area--scrollable` → `chart-area--scroll`
- `list-table--operasional-instansi` → `list-table--op-instansi`
- `detail-header-actions-grid--compact` → `detail-actions--compact`
- `table-mobile-scroll--return-penunjang` → `tbl-scroll--ret-penunjang`
- `table-mobile-scroll--return-bahan` → `tbl-scroll--ret-bahan`
- `table-mobile-scroll--return-support` → `tbl-scroll--ret-support`
- `table-mobile-scroll--summary-lab` → `tbl-scroll--sum-lab`
- `table-mobile-scroll--summary-support` → `tbl-scroll--sum-support`
- `table-mobile-scroll--summary-material` → `tbl-scroll--sum-material`

## Perubahan CSS/JS

- Tidak ditemukan inline/internal CSS di template aktif.
- Tidak ditemukan inline/internal JavaScript di template aktif.
- `style.css` menjadi pusat root variable warna dan semantic token.
- `style_dashboard.css`, `style_login.css`, `style_navbar.css`, dan `style_sidebar.css` diselaraskan agar memakai variable warna global.
- `apps.js` diperbarui hanya pada selector class yang namanya disederhanakan.
- Validasi sintaks JavaScript dilakukan dengan `node --check` untuk semua file JS di `static/js`.

## Penerapan Warna Baru

Root variable global yang diterapkan:

```css
:root {
  --color-primary-navy: #103e6f;
  --color-aqua-teal:    #64cdd1;
  --color-soft-blue:    #b8e1f2;
  --color-white:        #ffffff;
  --color-soft-gray:    #f0f4f6;
  --color-danger:       #dc3545;
  --color-warning:      #ffc107;
}
```

Button penolakan, pesan error, dan validasi gagal tetap memakai konsep merah. Button perbaikan tetap memakai konsep kuning/oranye profesional.

## Validasi Statis

- `python3 -S -m py_compile` berhasil untuk semua file Python di `apps/` dan `config/`.
- `node --check` berhasil untuk semua file JavaScript di `static/js/`.
- Scan template aktif tidak menemukan inline CSS/JS.
- Scan referensi class lama tidak menemukan class lama yang tertinggal untuk class yang disederhanakan.

## Catatan Risiko / Perlu Cek Manual

Environment audit tidak memiliki paket Django aktif, sehingga `python manage.py check` dan uji klik halaman secara runtime tidak bisa dijalankan di container ini. Setelah extract ZIP, lakukan validasi manual berikut di environment lokal:

1. Jalankan `python manage.py check`.
2. Login dan cek dashboard, navbar, sidebar.
3. Cek semua halaman list data yang memakai `Show Entries`.
4. Cek tambah/edit/detail/hapus data master.
5. Cek import Excel dan download format import.
6. Cek proses peminjaman, pengembalian, verifikasi, modal/pop-up, upload file, pagination, dan filter.

## Penyesuaian warna dashboard card - 2026-04-28

- Membedakan visual card `Peminjaman Selesai` dan `Peminjaman Berjalan` pada dashboard.
- `Peminjaman Selesai` menggunakan kombinasi terang `soft-blue` ke `aqua-teal` dengan teks navy.
- `Peminjaman Berjalan` menggunakan kombinasi navy ke aqua dengan teks putih.
- Perubahan hanya dilakukan pada `static/css/style_dashboard.css` dan cache static dashboard template.


## Fitur Download Chart Dashboard - 2026-04-28

- Menambahkan tombol aksi ikon `titik tiga vertikal` pada pojok kanan atas setiap card chart dashboard.
- Menyederhanakan pilihan download menjadi satu opsi: `Download JPG`.
- Hasil export Chart.js dibuat sebagai file JPG berkualitas tinggi dengan export canvas berskala 2x dan background putih.
- Judul chart ikut dirender pada bagian atas gambar hasil download.
- Berlaku untuk seluruh chart dashboard:
  - Rekap Peminjaman
  - Rekap Layanan Kegiatan
  - Rekap Data Pengukuran Lapangan
  - Rekap Tim Kegiatan
  - Rekap Kegiatan Survei
  - Instansi Tujuan Kegiatan
- Perubahan hanya dilakukan pada dashboard template, `static/css/style_dashboard.css`, dan `static/js/dashboard.js`.

## Penyesuaian Warna Hijau - 2026-04-28

- Menambahkan `--color-success: #198754` sebagai kategori warna hijau pada palette SILEBAT.
- Mengubah semantic variable `--success-bg`, `--success-text`, dan `--success-border` menjadi nuansa hijau.
- Mengubah card dashboard `Peminjaman Selesai` menjadi nuansa hijau tanpa mengubah class/struktur HTML.
- Status/ketersediaan yang memakai `badge-success`, termasuk nilai `Tersedia`, otomatis tampil dengan nuansa hijau.
- Warna `Peminjaman Berjalan`, warning/perbaikan, danger/penolakan, dan tema navy-aqua lain tetap dipertahankan.
- Cache static diperbarui ke `20260428-green-success-v1`.
