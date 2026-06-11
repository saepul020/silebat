# AGENT.MD

Panduan kerja untuk agent/developer yang mengubah project Django SILEBAT.

## Ringkasan Project

SILEBAT adalah aplikasi Django untuk layanan laboratorium, inventaris, permintaan peminjaman, verifikasi, pengembalian, notifikasi, dashboard, landing page, dan manajemen SDM.

Stack utama:

- Python 3.12
- Django 6.0.x
- PostgreSQL
- Gunicorn, Nginx, Docker Compose
- Target runtime: local development, Docker demo, dan Oracle VPS publish
- Static/media lokal melalui `static/`, `staticfiles/`, dan `media/`

Konfigurasi penting:

- Settings utama: `config/settings.py`
- URL utama: `config/urls.py`
- Custom user model: `apps.pengguna.User`
- Time zone: `Asia/Jakarta`
- Bahasa: `id-id`
- Login URL: `/login/`
- Redirect login: `/dashboard/`
- Static sumber: `static/`
- Static hasil deploy: `staticfiles/`

## Baseline Audit Terakhir

Audit penamaan terakhir sudah menyeragamkan 40+ nama template, CSS, JS, aset, template tag, dan management command dengan nama singkat maksimal dua kata inti. Istilah teknis yang umum dipakai di frontend/backend digunakan apa adanya, sedangkan istilah domain SILEBAT tetap memakai bahasa Indonesia.

Baseline yang harus dijaga:

- Template domain memakai nama Indonesia ringkas, misalnya `instansi_list.html`, `pengajuan_detail.html`, dan `pengembalian_form.html`.
- CSS/JS layout memakai istilah teknis ringkas, misalnya `base.css`, `sidebar.css`, `sidebar.js`, `navbar.css`, dan `navbar.js`.
- Command QR memakai istilah teknis ringkas, misalnya `refresh_qr`.
- Helper pengembalian duplikatif sudah digabung menjadi `get_step_pengembalian`.
- Konstanta import sudah disingkat menjadi pola seperti `HEADER_IMPOR_PERALATAN` dan `HEADER_WAJIB_PERALATAN`.
- Selector dashboard sudah disingkat dan mengikuti BEM, misalnya `dashboard-chart`, `dashboard-chart__area`, dan `item-modal__trigger`.
- Model database, migration, permission, dan konfigurasi server-side tidak diubah pada audit penamaan karena tidak diperlukan.

Perubahan berikutnya wajib menjaga baseline ini. Jangan membuat alias lama tanpa kebutuhan jelas, dan jangan menyisakan referensi ke nama lama setelah rename.

## Struktur Aplikasi

Modul Django utama:

- `apps.core`: helper umum, permission, context processor, import/export, pagination, upload validation, cleanup file.
- `apps.pengguna`: user, role, profil, pelatihan, dashboard SDM.
- `apps.master_data`: data aset, QR code, import/export master data, detail publik aset.
- `apps.operasional`: tim, layanan, survei, instansi, kop dokumen.
- `apps.peminjaman`: pengajuan, laporan, item pinjaman, pengembalian, PDF, import riwayat.
- `apps.verifikasi`: alur approval/verifikasi pengajuan dan pengembalian.
- `apps.notifikasi`: notifikasi transaksi dan pengumuman.
- `apps.dashboard`: dashboard internal dan display TV.
- `apps.landing`: landing publik dan pengelolaan kartu peralatan.
- `apps.chatbot`: endpoint balasan chatbot sederhana.

Template global berada di `templates/`. Template app berada di `apps/<app>/templates/`. Asset frontend sumber berada di `static/css/`, `static/js/`, dan `static/assets/`.

## Static dan Media

Pahami perbedaan folder static agar tidak salah edit:

- `static/` adalah sumber asli CSS, JS, gambar, font, dan aset frontend project. Semua perubahan frontend dilakukan di folder ini.
- `staticfiles/` adalah output `python manage.py collectstatic` untuk production/Docker/Nginx. Jangan edit manual file di folder ini.
- `media/` adalah file upload runtime dari user atau data aplikasi. Jangan hapus file media yang masih direferensikan record database.

Workflow benar:

```bash
# ubah file sumber di static/
python manage.py collectstatic --noinput
```

Jika perlu membersihkan output static lama:

```bash
python manage.py collectstatic --clear --noinput
```

Dalam Docker production, Nginx melayani URL `/static/` dari `staticfiles/`. Karena itu perubahan di `static/` harus diikuti `collectstatic` sebelum deploy/rebuild production.

## Aturan Wajib Saat Mengubah Kode

1. Baca pola existing sebelum mengubah file.
2. Jaga perubahan tetap sempit sesuai fitur yang diminta.
3. Jangan hanya menambah logic baru. Setelah perubahan diterapkan, lakukan audit lanjutan untuk membersihkan kode lama yang tidak efektif, tidak terpakai, duplikatif, atau bertumpuk dengan logic baru.
4. Pastikan semua query, views, models, forms, templates, CSS, dan JS yang terdampak ikut disesuaikan secara teliti.
5. Jangan hapus kode yang masih dibutuhkan fitur lain.
6. Hindari identifier yang terlalu panjang. Gunakan nama class, model, id, variabel, function, selector CSS, dan identifier JS/backend yang singkat, jelas, konsisten, dan mudah dipahami.
7. Utamakan istilah teknis yang sudah lazim untuk UI/frontend/backend seperti `sidebar`, `navbar`, `pagination`, `modal`, `landing`, `dashboard`, dan `refresh`. Jika konteksnya domain SILEBAT dan tidak ada istilah teknis yang lebih tepat, gunakan bahasa Indonesia.
8. Jangan mengandalkan frontend untuk validasi, pembatasan akses, role permission, approval, upload file, perubahan status, atau logic penting. Semua aturan wajib diamankan di server-side.
9. Jangan menyimpan secret baru di repo. Gunakan `.env` atau environment variable.
10. Jangan menyentuh file backup, media arsip, atau file untracked kecuali diminta eksplisit.
11. Jika file yang akan diubah sudah memiliki perubahan user, pahami dulu lalu lanjutkan tanpa merevert perubahan tersebut.

## Aturan Penamaan

Gunakan penamaan singkat, jelas, konsisten, dan selaras dengan baseline audit terakhir. Prioritas penamaan: istilah teknis umum lebih dulu, lalu bahasa Indonesia untuk domain aplikasi.

### File Template

- Gunakan `snake_case`.
- Maksimal dua kata inti sebelum ekstensi.
- Gunakan pola konteks + jenis halaman bila perlu: `pengajuan_list.html`, `pengajuan_detail.html`, `pengembalian_form.html`, `instansi_list.html`.
- Gunakan istilah teknis untuk konteks UI/framework seperti `active_rows.html` bila lebih tepat. Gunakan bahasa Indonesia untuk konteks domain seperti `pengajuan`, `pengembalian`, `instansi`, `bahan`, dan `peralatan`.
- Jika rename template, update semua referensi di `render(...)`, include, extends, tests, dan dokumentasi terkait.

### CSS, JS, Asset, Template Tag, dan Command

- Gunakan istilah teknis untuk file internal project bila tersedia: `sidebar.css`, `navbar.js`, `landing_page.css`, `dashboard_display.js`, `import_modal.html`, `pagination.html`, dan `refresh_qr`.
- Gunakan `snake_case` untuk nama file Python, command, template tag, dan asset internal.
- Gunakan `kebab-case` untuk file CSS/JS jika pola existing pada area tersebut sudah memakai kebab-case. Jangan mencampur gaya dalam folder yang sama tanpa alasan.
- Jangan rename file vendor atau library pihak ketiga di `static/vendor/`.
- Setelah rename static asset, update `{% static %}`, import JS, link CSS, test, dan referensi Docker/collectstatic bila terdampak.

### Backend Python

- Gunakan `snake_case` untuk function, method, variable, dan konstanta module.
- Gunakan `PascalCase` untuk class/model/form sesuai standar Python/Django.
- Nama model boleh tetap istilah domain yang sudah mapan. Jangan rename model/database hanya demi kosmetik karena akan memicu migration dan risiko data.
- Konstanta gunakan huruf besar dan ringkas, misalnya `HEADER_IMPOR_PERALATAN`.
- Helper umum harus ditempatkan di module existing yang relevan. Hindari helper baru yang menggandakan fungsi lama.

### CSS dan JS Selector

- Class CSS wajib mengikuti pola BEM yang ringkas:
  - Block: `dashboard-chart`
  - Element: `dashboard-chart__area`
  - Modifier: `dashboard-chart--kosong`
- Gunakan `kebab-case` untuk class dan id frontend.
- Id hanya dipakai jika memang perlu target unik untuk JS atau anchor.
- Jika mengubah class/id yang dipakai JS, update semua selector JS terkait.
- Jangan membuat selector terlalu spesifik atau terlalu panjang.
- Jangan menyisakan selector lama yang sudah tidak dipakai setelah markup diganti.

### Prinsip Rename Aman

Sebelum rename:

- Cari semua referensi dengan `rg "nama_lama"`.
- Pastikan nama baru tidak konflik dengan file, class, id, route, command, atau template lain.
- Periksa dampak ke view, form, template, CSS, JS, tests, import/export, PDF, dan dokumentasi.

Setelah rename:

- Jalankan ulang pencarian nama lama.
- Hapus alias, wrapper, selector, include, atau helper lama jika sudah tidak dipakai.
- Jangan hapus kode yang masih dipakai fitur lain.

## Permission dan Role

Role utama project:

- `Super Admin`
- `User`
- `Admin Lab`
- `Teknisi Lab`
- `Kepala Lab`
- `Pimpinan`

Helper akses terpusat berada di `apps/core/permissions.py`. Gunakan helper ini sebelum membuat aturan akses baru.

Pola akses yang harus dijaga:

- Master Data baca: `Super Admin`, `Admin Lab`, `Teknisi Lab`, `Kepala Lab`, `Pimpinan`
- Master Data kelola: `Super Admin`, `Admin Lab`, `Teknisi Lab`
- Import Master Data: `Super Admin`
- Export Master Data: `Super Admin`, `Admin Lab`, `Teknisi Lab`, `Pimpinan`
- Operasional: `Super Admin`
- Pengguna/Data User: `Super Admin`
- Peminjaman/Permintaan: role verifikasi yang terdaftar
- Verifikasi/Laporan: role verifikasi yang terdaftar
- Detail/edit profil: admin terkait atau pemilik data sendiri

Jika menambah halaman, endpoint, import, export, atau action POST:

- Tambahkan `login_required` jika butuh autentikasi.
- Tambahkan `app_access_required(...)` atau pengecekan permission setara di view.
- Validasi object ownership dan role di server-side.
- Untuk action status/approval, cek actor, status saat ini, step saat ini, dan transisi yang valid sebelum menyimpan.

## Validasi Server-Side

Validasi wajib berada di form, model, service, atau view backend sesuai konteks.

Gunakan helper existing:

- Upload file: `apps/core/upload_validation.py`
- Cleanup file tidak terpakai: `apps/core/file_cleanup.py`
- Import workbook dan header: `apps/core/import_utils.py`
- Export Excel: `apps/core/excel_utils.py`
- Pagination list: `apps/core/list_pagination.py`

Untuk upload:

- Batas default file adalah 7 MB.
- Validasi ekstensi dan ukuran di backend.
- Attribute frontend hanya pendukung UX, bukan sumber keamanan.
- Jika file diganti atau data dihapus, pastikan file lama dibersihkan memakai helper cleanup yang sudah ada.

Untuk import Excel:

- Validasi header wajib, tipe data, pilihan enum/choices, duplikasi, dan relasi data sebelum menyimpan.
- Jangan simpan sebagian data jika validasi import gagal.
- Berikan error per baris yang jelas.
- Batasi akses import ke role yang memang berwenang.

## Data, Query, dan Model

Saat mengubah model:

- Buat migration yang jelas dan minimal.
- Tambahkan constraint/index hanya jika benar-benar dibutuhkan.
- Pertimbangkan data existing dan buat data migration jika perlu.
- Jaga snapshot laporan/peminjaman agar tidak rusak oleh perubahan master data.
- Pastikan relasi `on_delete`, `related_name`, dan ordering konsisten dengan pola existing.
- Jangan rename model, field database, atau migration hanya demi penyeragaman nama kosmetik.

Saat mengubah query:

- Hindari N+1 query dengan `select_related`/`prefetch_related` bila list/detail menampilkan relasi.
- Jangan mengubah queryset laporan, dashboard, landing, atau notifikasi tanpa mengecek efek ke template dan export.
- Pertahankan filter role/ownership di backend.

## Alur Peminjaman, Verifikasi, dan Pengembalian

Area ini sensitif. Saat mengubah logic:

- Periksa `apps/peminjaman/models.py`, `apps/peminjaman/views.py`, `apps/peminjaman/pengembalian_views.py`, dan `apps/verifikasi/views.py`.
- Jaga konsistensi status pengajuan, step verifikasi, timeline, notifikasi, laporan, PDF, dan snapshot item.
- Validasi stok/volume di backend.
- Gunakan helper `get_step_pengembalian` untuk alur pengembalian. Jangan membuat helper paralel dengan logic sama.
- Jangan membuat transisi status ganda atau jalur approval paralel tanpa kebutuhan jelas.
- Jika menambah status baru, update model choices, views, templates, notifikasi, laporan, export, dan CSS/JS indikator status.

## Master Data dan QR

Master data memakai QR code dan detail publik berbasis token.

Saat mengubah master data:

- Periksa `apps/master_data/models.py`, `apps/master_data/views.py`, `apps/master_data/forms.py`, `apps/master_data/qr_utils.py`, dan `apps/master_data/signals.py`.
- Pastikan token QR tetap unik.
- Gunakan helper generate QR existing.
- Gunakan command QR teknis yang sudah ada, misalnya `refresh_qr`.
- Jika field aset berubah, update form, list template, detail template, public detail, import/export, PDF/laporan terkait, dan snapshot peminjaman bila terdampak.
- Jangan menghapus file foto/dokumen yang masih direferensikan record lain.

## Notifikasi

Notifikasi transaksi dan pengumuman berada di `apps/notifikasi/`.

Saat mengubah approval, pengajuan, pengembalian, atau role:

- Periksa `apps/notifikasi/services.py`.
- Pastikan penerima notifikasi benar.
- Hindari duplikasi notifikasi untuk step yang sama.
- Tutup notifikasi lama jika status sudah berubah dan tidak lagi relevan.

## Frontend

Asset frontend project dipisah per area:

- CSS global/layout: `static/css/base.css`, `sidebar.css`, `navbar.css`
- JS global/layout: `static/js/apps.js`, `sidebar.js`, `navbar.js`
- Halaman/domain tertentu memakai file CSS/JS masing-masing.

Saat mengubah template:

- Cek file CSS dan JS yang terkait.
- Terapkan BEM untuk class baru atau class yang disentuh.
- Jangan membuat selector terlalu panjang.
- Jangan menambah logic JS yang menggandakan validasi penting backend.
- Pastikan tampilan desktop dan mobile tetap rapi.
- Jika mengubah id/class yang dipakai JS, update semua selector terkait.
- Jangan menyisakan markup tersembunyi lama yang sudah diganti logic baru.

### Button Tidak Aktif dan Terkunci

Gunakan pola seragam untuk semua tombol yang tidak bisa diklik, baik hapus, edit, download, export, import, tambah, maupun tombol aksi lain.

- Untuk tombol HTML, gunakan attribute `disabled` dan tetap pakai class dasar `.btn` beserta varian warnanya, misalnya `btn btn-danger btn-sm`.
- Untuk link yang harus tampil seperti tombol tidak aktif, jangan beri `href`; gunakan elemen `<button type="button" disabled>` bila memang tidak boleh diklik.
- Tambahkan class modifier lock yang singkat dan spesifik konteks bila tombol terkunci karena aturan data, misalnya `master-delete-lock`, `operasional-delete-lock`, atau `komponen-rutin__remove--locked`.
- Style tombol tidak aktif wajib samar, memakai `cursor: not-allowed`, dan tidak boleh memiliki efek hover visual. Hover hanya boleh mengubah cursor menjadi icon dilarang, bukan warna, border, ikon, shadow, transform, atau opacity.
- Jangan mengganti ikon tombol terkunci saat hover. Ikon tetap sama dengan aksi aslinya agar UI konsisten.
- Untuk selector CSS, batasi hover tombol aktif dengan pola seperti `.nama-button:not(.nama-button--locked):not(:disabled):hover`.
- Style global tombol disabled berada di `static/css/base.css`. Jangan membuat aturan disabled baru yang bertumpuk bila bisa memakai `.btn:disabled`, `.btn-disabled`, atau modifier lock existing.
- Jika status lock berubah lewat JS, sinkronkan class modifier, attribute `disabled`, `title`, dan `aria-label` sejak render awal dan setiap update state.
- Tombol terkunci hanya UX. Aturan hapus/edit/download yang penting wajib tetap divalidasi di server-side view/form/model agar request manual tidak bisa melewati lock.

Saat mengubah asset:

- Edit sumber di `static/`, bukan `staticfiles/`.
- Jalankan `collectstatic` bila perubahan perlu diuji di Docker/production.
- Jangan commit output `staticfiles/` jika memang diabaikan `.gitignore`.

## Deployment dan Environment

Docker:

- `Dockerfile` memakai Python 3.12 slim.
- `docker-compose.yml` menjalankan web, PostgreSQL, dan Nginx.
- `entrypoint.sh` menunggu PostgreSQL, menjalankan `migrate`, lalu `collectstatic`.
- Nginx production melayani `/static/` dari `staticfiles/`.

Environment penting:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `PUBLIC_BASE_URL`
- `DATABASE_URL` atau `DB_*`
- `DASHBOARD_TV_SLUG`

Jangan commit nilai secret asli. Jika menambah env baru, update `.env.example` yang relevan.

## Perintah Pengecekan

Gunakan perintah ini sesuai jenis perubahan:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py migrate
python manage.py collectstatic --noinput
```

Untuk Docker:

```bash
docker compose up --build
```

Untuk audit rename dan referensi lama:

```bash
rg "nama_lama"
rg "nama_baru"
python manage.py collectstatic --clear --noinput
```

Jika perubahan hanya dokumentasi, minimal cek file yang dibuat, struktur Markdown, dan jelaskan bahwa pengecekan Django tidak wajib karena tidak ada kode runtime yang berubah.

## Audit Lanjutan Setelah Perubahan

Setelah implementasi, lakukan audit ini sebelum final:

- Cari logic lama yang sudah tidak dipakai.
- Cari fungsi, branch, template block, selector CSS, atau handler JS yang menjadi duplikatif.
- Cek query/list/detail/export yang terdampak.
- Cek model, form, view, template, CSS, dan JS terkait.
- Cek permission dan validasi server-side.
- Cek import/export, upload, status, approval, notifikasi, dan file cleanup bila relevan.
- Untuk rename, pastikan tidak ada referensi nama lama yang tertinggal.
- Untuk static, pastikan perubahan dilakukan di `static/`, lalu regenerate `staticfiles/` jika diperlukan.
- Jalankan pengecekan syntax/error yang sesuai.
- Jangan hapus kode yang masih dipakai fitur lain.

## Format Laporan Akhir

Setelah selesai, jelaskan secara ringkas:

- File yang diubah.
- Logic lama yang dibersihkan.
- Logic baru yang diterapkan.
- Konfigurasi server-side yang ditambahkan atau disesuaikan.
- Hasil pengecekan syntax/error.
- Catatan jika ada pengecekan yang tidak dijalankan beserta alasannya.
