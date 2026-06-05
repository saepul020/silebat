# AGENT.MD

Panduan kerja untuk agent/developer yang mengubah project Django SILEBAT.

## Ringkasan Project

SILEBAT adalah aplikasi Django untuk layanan laboratorium, inventaris, permintaan peminjaman, verifikasi, pengembalian, notifikasi, dashboard, landing page, dan manajemen SDM.

Stack utama:

- Python 3.12
- Django 6.0.x
- PostgreSQL
- Gunicorn, Nginx, Docker Compose
- Vercel/serverless support melalui environment variable
- Static/media lokal melalui `static/`, `staticfiles/`, dan `media/`

Konfigurasi penting:

- Settings utama: `config/settings.py`
- URL utama: `config/urls.py`
- Custom user model: `apps.pengguna.User`
- Time zone: `Asia/Jakarta`
- Bahasa: `id-id`
- Login URL: `/login/`
- Redirect login: `/dashboard/`

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

Template global berada di `templates/`. Template app berada di `apps/<app>/templates/`. Asset frontend berada di `static/css/`, `static/js/`, dan `static/assets/`.

## Aturan Wajib Saat Mengubah Kode

1. Baca pola existing sebelum mengubah file.
2. Jaga perubahan tetap sempit sesuai fitur yang diminta.
3. Jangan hanya menambah logic baru. Setelah perubahan diterapkan, lakukan audit lanjutan untuk membersihkan kode lama yang tidak efektif, tidak terpakai, duplikatif, atau bertumpuk dengan logic baru.
4. Pastikan semua query, views, models, forms, templates, CSS, dan JS yang terdampak ikut disesuaikan secara teliti.
5. Jangan hapus kode yang masih dibutuhkan fitur lain.
6. Hindari identifier yang terlalu panjang. Gunakan nama class, model, id, variabel, function, selector CSS, dan identifier JS/backend yang singkat, jelas, konsisten, dan mudah dipahami.
7. Jangan mengandalkan frontend untuk validasi, pembatasan akses, role permission, approval, upload file, perubahan status, atau logic penting. Semua aturan wajib diamankan di server-side.
8. Jangan menyimpan secret baru di repo. Gunakan `.env` atau environment variable.
9. Jangan menyentuh file backup, media arsip, atau file untracked kecuali diminta eksplisit.
10. Jika file yang akan diubah sudah memiliki perubahan user, pahami dulu lalu lanjutkan tanpa merevert perubahan tersebut.

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

- Master Data: `Super Admin`, `Admin Lab`, `Teknisi Lab`
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

Saat mengubah query:

- Hindari N+1 query dengan `select_related`/`prefetch_related` bila list/detail menampilkan relasi.
- Jangan mengubah queryset laporan, dashboard, landing, atau notifikasi tanpa mengecek efek ke template dan export.
- Pertahankan filter role/ownership di backend.

## Alur Peminjaman, Verifikasi, dan Pengembalian

Area ini sensitif. Saat mengubah logic:

- Periksa `apps/peminjaman/models.py`, `apps/peminjaman/views.py`, `apps/peminjaman/pengembalian_views.py`, dan `apps/verifikasi/views.py`.
- Jaga konsistensi status pengajuan, step verifikasi, timeline, notifikasi, laporan, PDF, dan snapshot item.
- Validasi stok/volume di backend.
- Jangan membuat transisi status ganda atau jalur approval paralel tanpa kebutuhan jelas.
- Jika menambah status baru, update model choices, views, templates, notifikasi, laporan, export, dan CSS/JS indikator status.

## Master Data dan QR

Master data memakai QR code dan detail publik berbasis token.

Saat mengubah master data:

- Periksa `apps/master_data/models.py`, `apps/master_data/views.py`, `apps/master_data/forms.py`, `apps/master_data/qr_utils.py`, dan `apps/master_data/signals.py`.
- Pastikan token QR tetap unik.
- Gunakan helper generate QR existing.
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

- CSS global/layout: `static/css/style.css`, `style_sidebar.css`, `style_navbar.css`
- JS global/layout: `static/js/apps.js`, `sidebar.js`, `navbar.js`
- Halaman/domain tertentu memakai file CSS/JS masing-masing.

Saat mengubah template:

- Cek file CSS dan JS yang terkait.
- Jangan membuat selector terlalu panjang.
- Jangan menambah logic JS yang menggandakan validasi penting backend.
- Pastikan tampilan desktop dan mobile tetap rapi.
- Jika mengubah id/class yang dipakai JS, update semua selector terkait.
- Jangan menyisakan markup tersembunyi lama yang sudah diganti logic baru.

## Deployment dan Environment

Docker:

- `Dockerfile` memakai Python 3.12 slim.
- `docker-compose.yml` menjalankan web, PostgreSQL, dan Nginx.
- `entrypoint.sh` menunggu PostgreSQL, menjalankan `migrate`, lalu `collectstatic`.

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

Jika perubahan hanya dokumentasi, minimal cek file yang dibuat dan jelaskan bahwa pengecekan Django tidak wajib karena tidak ada kode runtime yang berubah.

## Audit Lanjutan Setelah Perubahan

Setelah implementasi, lakukan audit ini sebelum final:

- Cari logic lama yang sudah tidak dipakai.
- Cari fungsi, branch, template block, selector CSS, atau handler JS yang menjadi duplikatif.
- Cek query/list/detail/export yang terdampak.
- Cek model, form, view, template, CSS, dan JS terkait.
- Cek permission dan validasi server-side.
- Cek import/export, upload, status, approval, notifikasi, dan file cleanup bila relevan.
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
