# Total grafik SILEBAT

`static/js/chart_summary.js` menghitung total dari dataset yang sedang ditampilkan,
setelah filter tahun, bulan, atau barang diterapkan. Seri dan irisan pie yang
disembunyikan melalui legenda tidak ikut dijumlahkan. Nilai kosong/tidak valid
tidak menambah total; grafik kosong menampilkan `Total: 0`. Angka memakai format
Indonesia. Total merupakan jumlah nilai pada grafik, bukan hitungan record unik.

Plugin `chartSummary` dipakai Dashboard utama, Dashboard SDM, Live TV, detail alat
internal/publik, dan grafik landing page. Label berada di kanan baris filter atau
header jika tidak ada filter, dengan latar gradasi biru/teal dan sudut proporsional
terhadap font. CSS bersama ada di `static/css/charts.css`. Di Live TV, total ada
di kiri atas, judul tetap di tengah, dan indikator slide di kanan. Label mengikuti
slide grafik aktif dan disembunyikan pada slide card.

Khusus grafik Internal SDA, bawah chart memuat `BWS Nihil : … Instansi` dan
`BBWS Nihil : … Instansi` dalam dua kotak berlatar terpisah, rata tengah.
Footer berada di luar canvas dan area scroll, sehingga tidak menutupi label sumbu
atau ikut bergulir horizontal. Nihil menghitung kategori balai tanpa transaksi pada
tahun terpilih; pilihan Semua Tahun memakai seluruh tahun yang tersedia. Nama
singkat BWS/BBWS maupun nama lengkap Balai (Besar) Wilayah Sungai dikenali tanpa
membedakan kapitalisasi. Instansi lain tidak dihitung. Menyembunyikan seri lewat
legenda tidak mengubah status nihil. Angka nol tetap ditampilkan jika semua balai
sudah memiliki transaksi. Ringkasan ini juga ikut dalam JPG Dashboard utama dan
berganti mengikuti slide aktif Live TV.

Download JPG Dashboard utama/SDM memakai perhitungan total yang sama dan menggambar
total berlatar di kanan baris informasi filter, termasuk ketika sebagian
seri/irisan tidak ditampilkan. Dua kotak nihil berada di bawah plot, rata tengah,
dengan ruang tersendiri dalam JPG. Export Excel tidak diubah.

Dataset bar memakai `borderSkipped: 'start'`: pangkal pada sumbu nol siku, ujung
batang tetap rounded. Hal ini juga berlaku pada stack kondisi barang dan bar
horizontal landing page (pangkal di kiri).

Validasi 11 November 2026: tes JS meliputi stack, pie tersembunyi, angka desimal,
data objek, data kosong, rounding, dan penulisan total ke canvas JPG. Chrome
memeriksa filter, pilihan inventaris, grafik detail yang berganti, TV 360p,
landing page, serta render JPG dari kedua Dashboard. Pemeriksaan memakai data
sintetis tanpa mengubah record aplikasi.

Tambahan nihil diuji untuk tahun 2026/2025, semua tahun, tahun kosong, nama lengkap,
instansi di luar balai, dan seri tersembunyi. Browser memeriksa label pada Dashboard
390/768/1440 px, TV/normal 640×360 hingga 1920×1080, pergantian slide dan JPG.

Layout badge diperiksa kembali pada Dashboard 360/390/768/1440 px dan Live TV
mode TV/normal 640×360, 1280×720, 1920×1080, serta portrait 390×844. Pemeriksaan
memastikan total di kiri atas Live TV, dua kotak terpusat di bawah canvas, latar
terpisah, filter memperbarui angka, dan footer hilang pada slide lain. Tes JPG
memastikan latar total dan kotak nihil tidak memotong plot. Chrome juga memeriksa
Dashboard SDM, detail alat, dan landing tanpa error JavaScript.

```powershell
node --test apps/dashboard/test_summary.js apps/dashboard/test_export.js apps/dashboard/test_chart.js apps/dashboard/test_layout.js apps/dashboard/test_inventory.js
..\env\Scripts\python.exe manage.py check
..\env\Scripts\python.exe manage.py test apps.dashboard.tests apps.dashboard.test_display apps.dashboard.test_inventory apps.pengguna.test_pelatihan apps.master_data.test_detail_chart apps.landing.tests apps.landing.test_konten_tv --noinput
..\env\Scripts\python.exe manage.py collectstatic --noinput
```
