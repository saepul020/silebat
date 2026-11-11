# Live TV: mode signage

Aktifkan melalui **Aktifkan Mode TV**, atau tambahkan `?tv=1` pada URL Live TV
(`&tv=1` jika sudah ada parameter lain). Mode tidak ditentukan dari user agent.

Acuan viewport terkecil mode TV adalah **640 x 360 px (360p, 16:9)**.
Ini ukuran viewport CSS, bukan resolusi foto atau panel fisik TV.

## Layout dan refresh

- Setiap slide grafik menampilkan total nilai yang terlihat di kanan atas. Total
  mengikuti grafik aktif dan disembunyikan pada slide peralatan/rekap card. Label
  memakai skala font TV. Pangkal batang pada sumbu nol siku; rounded hanya di ujung.
- Nama pada `tv-equipment__name` diisi manual melalui **Judul Barang** pada setiap
  slot halaman **Konten Alat TV**. Judul berupa teks konfigurasi maksimal 200
  karakter, wajib ketika alat dipilih, dan tidak mengikuti perubahan nama master
  atau pergantian pilihan alat. Foto dan metadata tetap memakai alat yang dipilih.
  Migrasi `landing.0008_tv_judul` menyalin judul lama sekali untuk menjaga tampilan
  existing; setelah itu hanya input manual yang mengubah judul. Judul kosong tidak
  mengambil nama master sebagai fallback. Refresh berkala membawa judul terbaru.
- Outline panel dan card memakai satu skala ketebalan dari sisi viewport terpendek,
  sekitar 0,5 px pada 640 x 360 px hingga maksimum 1 px di layar besar. Garis memakai
  overlay inset agar ketebalan subpixel tetap terlihat lebih halus pada DPR 1 dan
  tidak tertutup foto. Bayangan panel/card dan bingkai ikon mengikuti skala yang
  sama pada mode normal dan TV. Overlay tidak menerima klik.
- Radius sudut di kedua mode memakai satu skala berdasarkan sisi viewport terpendek
  (`vmin`), dengan batas minimum/maksimum melalui `clamp()`. Panel ringkasan, tabel,
  dan carousel memakai radius 4–18 px; card alat 3–14 px; ikon, tombol, dan kotak
  kondisi 2–9 px. Radius badge juga dibatasi ukuran font. Aturan radius khusus TV
  dihapus agar ukuran dan transisi konsisten pada semua breakpoint.
- `dashboard_display.css` dan `tv_layout.js` dipakai mode normal dan TV. Ukuran font
  tabel mengikuti field yang paling membutuhkan ruang, termasuk header, periode,
  nama, instansi, dan badge. Semua cell memakai satu baris dengan font seragam.
- Tabel display memakai wrapper sendiri, tanpa class list transaksi umum yang
  membawa minimum lebar, tinggi baris, dan breakpoint berbeda. Padding toolbar,
  cell, badge, serta kondisi kosong mengikuti `--tv-type` di kedua mode. Pemisah
  baris, toolbar, dan bingkai badge memakai garis inset `--tv-stroke`, sekitar
  0,5 px pada 360p. Warna status tetap mengikuti jenis prosesnya. Seluruh kegiatan
  tetap ditampilkan berurutan, termasuk hasil polling, tanpa paginasi tabel.
- Seluruh tipografi halaman memakai skala bersama dari lebar dan tinggi viewport
  (`--tv-type`, acuan 1280 x 720 px), termasuk judul, jam, ringkasan, tabel, badge,
  card, rekap, dan placeholder foto. Ada batas minimum terpisah untuk mode normal
  dan TV serta batas maksimum pada layar besar. Override font per breakpoint
  dihapus; penyesuaian teks terpanjang tetap diterapkan di atas skala ini.
- Khusus `tv-equipment__body`, font awal dimaksimalkan terhadap lebar dalam card.
  Nama, merek, dan metadata memakai satu pengali bersama per slide agar hierarki
  serta ukuran antar-card seragam. Pengali bisa lebih besar atau lebih kecil dari
  satu, dibatasi judul/merek atau gabungan label dan nilai metadata terpanjang.
  Slide lain tidak membatasi ukuran font slide yang sedang ditampilkan. Jarak
  metadata mengikuti font dalam satuan `em`; label dan nilai tetap satu baris
  tanpa elipsis. Card kosong dan rekap memakai penyesuaian ukurannya sendiri.
- Pengukuran memakai lebar teks hasil render. Ukuran dihitung ulang setelah resize,
  font/gambar selesai dimuat, pergantian slide, dan pembaruan data. Font kembali ke
  ukuran CSS dasarnya sebelum dihitung agar tidak terus membesar/mengecil setelah resize.
- `tv_screen.css` mengatur frame signage dan layout TV ringkas hingga lebar 1024 px.
  Padding, jarak, header, ringkasan, tabel, dan card mengikuti unit proporsional
  dengan acuan 640 px; enam card tetap sejajar. Mode normal mempertahankan jumlah
  kolom responsifnya dan memakai skala font bersama.
  Mode TV mengikuti ukuran dan offset
  `visualViewport`, dengan fallback `innerWidth`/`innerHeight`. Tidak ada pengecilan
  font root, CSS zoom, atau transform scale pada dashboard.
- Tinggi minimum area slide mengikuti konfigurasi CSS dan tinggi isi card. Pada
  360p, batas dasar 180 px diganti 120 px agar header, tabel, dan carousel mendapat
  ruang yang cukup. Judul/subjudul TV diukur agar tetap satu baris.
- Seluruh kegiatan aktif tampil berurutan dalam satu tabel, termasuk pada polling;
  batas delapan record dan paginasi otomatis tabel sudah dihapus. Badge tetap
  **Realtime** dan timer carousel hanya mengganti slide alat/grafik.
- Track tabel mengikuti tinggi seluruh isinya. Carousel ditempatkan setelah tabel
  dengan tinggi minimum yang cukup untuk foto 4:3 dan isi card. Jika seluruh konten
  melebihi layar, halaman bisa digulir ke bawah tanpa menumpuk atau menyembunyikan baris.
- Mode TV menampilkan enam card per slide. Card tambahan dibagi ke slide berikutnya;
  slot kosong tidak menjadi alat duplikat. Mode normal tetap enam kolom di desktop,
  tiga di tablet, dan satu di ponsel.
- Polling 10 detik memperbarui tabel, alat, dan rekap kondisi. HTML sumber card
  disimpan terpisah dari slide hasil pembagian agar polling tidak menggandakan card.
  Carousel memakai satu timer 8,5 detik.
- Khusus label sumbu X chart Live TV, teks membungkus maksimal dua baris berdasarkan
  lebar teks canvas. Pemisahan mengikuti kata; kata tanpa spasi dipotong sesuai lebar.
  Jika sisa teks melebihi baris kedua, ujungnya diberi elipsis `…`. Label sumber dan
  hubungan kategori/nilai tetap utuh. Semua label memakai font seragam yang mengikuti
  skala layar dan ruang untuk dua baris. Pada 360p, font dan lebar area label
  diperkecil sekitar 29% dari ukuran sebelumnya. Sumbu Y, legend, dan tanda nilai nol
  juga mengikuti skala halaman. Label pendek tetap horizontal; label padat
  dimiringkan 45–90 derajat berdasarkan jarak antarkategori. Pengaturan dihitung
  ulang sebelum layout, termasuk resize, pada mode normal maupun TV.

## Validasi 11 November 2026

Judul manual diperiksa pada kedua slide, mode normal/TV, serta polling. Validasi
server menolak judul kosong/spasi dan panjang di atas 200 karakter tanpa menyimpan
sebagian konfigurasi. Penggantian nama master/pilihan alat tidak mengubah judul,
teks di-escape saat render, dan akses tetap hanya Super Admin. Migrasi tambahan
sudah diuji dan diterapkan di database lokal. Pada server lain, jalankan `migrate`
sebelum memakai kode baru. Form 12 input judul diperiksa pada lebar 390–1920 px;
heading manual dan fitting font Live TV diperiksa pada 360p, HD, dan 4K.

Maksimalisasi font equipment diperiksa pada mode normal dan TV dari 640 x 360 px
hingga 3840 x 2160 px, serta 390 x 844 px pada mode normal. Pada contoh data seperti
referensi, metadata di 1600 x 900 px menjadi sekitar 13,1 px dari font awal 10 px,
dan nama alat 18 px. Teks terpanjang memanfaatkan lebih dari 98% lebar yang tersedia
tanpa overflow. Hierarki dan ukuran antar-card seragam dalam setiap slide.
Nama/kode panjang di slide lain tidak mengecilkan slide pertama. Resize kembali
memulihkan ukuran awal; polling menjadi 13 card pada mode TV tetap membaginya
menjadi 6–6–1 tanpa duplikasi. Pengujian memakai data sintetis dan template asli.

## Validasi 10 November 2026

Tabel diperiksa dari lebar 390 px pada mode normal dan 640 x 360 px pada mode TV
hingga 4K, termasuk 1920 x 720 px, resize kembali, tabel kosong, dan polling menjadi
11 kegiatan. Font header/cell/badge seragam; padding mengikuti skala layar; tidak
ada border native 1 px yang tertinggal pada cell dan badge. Tabel tiga kegiatan
di TV 360p sekitar 51 px, dengan tinggi baris sekitar 9,7 px. Seluruh data tetap
terlihat tanpa wrap, overflow horizontal, atau tumpang tindih dengan carousel.

Outline dan shadow diperiksa pada DPR 1 dan 2, kedua mode, dari 640 x 360 px
hingga 3840 x 2160 px, termasuk resize kembali ke 360p. Ring kontainer berisi data
memakai ketebalan 0,5 px pada 360p dan maksimum 1 px pada layar besar; radius
mengikuti kontainer dan overlay tidak menangkap klik. Layout tiga kegiatan,
kondisi tabel kosong, dan sebelas kegiatan juga diperiksa tanpa tumpang tindih.

Chrome headless memakai template Django sebenarnya dan data sintetis, tanpa mengubah
record aplikasi. Mode normal dan TV diuji pada 960×540, 1280×720, 1920×900, serta
3840×2160. Mode normal juga diuji pada 390×844.

Baseline 360p diuji khusus pada 640 x 360 px: tiga kegiatan dan enam card muat
dalam satu viewport tanpa overflow; nol kegiatan tetap rapi. Sebelas kegiatan
tetap tersedia berurutan dengan scroll vertikal, tanpa paginasi atau tumpang tindih.
Resize dari 360p ke layar lebih besar lalu kembali, polling menjadi 11 kegiatan dan
13 card, serta jarak 55 label chart juga lolos pada viewport 640 x 360 px.

Radius responsif diperiksa pada 18 kombinasi mode/viewport dari lebar 320 px
(mode normal) dan 640 x 360 px (TV) hingga 3840 x 2160 px. Panel kedua mode
memakai radius yang sama pada viewport yang sama, mengikuti resize tanpa reload,
dan tetap dalam batas minimum/maksimum. Tidak ada overflow horizontal atau panel
yang saling menumpuk pada skenario tersebut.

Pemeriksaan mencakup 11 kegiatan terlihat tanpa baris tersembunyi, teks dan metadata
tidak meluber horizontal, body card tidak terpotong, tabel tidak menumpuk dengan
carousel, dan halaman tidak meluber horizontal. Resize tanpa reload memulihkan ukuran
font semula. Polling menjadi 11 kegiatan dan 13 card, pergantian carousel, serta
polling berulang diperiksa agar tidak menggandakan slide atau menghilangkan baris.
Chart berisi 55 instansi diperiksa dari geometri label Chart.js: label maksimal
dua baris, memakai elipsis bila perlu, dan jarak tegak lurus antarteks mencukupi
tinggi kedua baris. Validasi wrap dilakukan pada kedua mode dari 640 x 360 px hingga
3840 x 2160 px, ditambah 390 x 844 px pada mode normal. Resize kembali ke 360p
memulihkan hasil wrap semula dan tidak mengubah data label sumber.

Sesudah penyatuan skala font, chart 55 instansi di TV 640 x 360 px memakai label
sekitar 2,44 px (sebelumnya 3,45 px); lebar maksimum teks sekitar 21 px
(sebelumnya 30 px). Wrap dua baris, elipsis, dan jarak antarteks tetap diperiksa.
Ukuran font header, tanggal/jam, statistik, judul, badge, rekap, dan placeholder
juga diverifikasi mengikuti skala yang sama, termasuk kasus 1920 x 720 px untuk
memastikan tinggi layar ikut diperhitungkan. Font sumbu Y dan legend di TV 360p
menjadi sekitar 4,95 px; resize kembali memulihkan ukuran awal.

Tes otomatis yang dapat dijalankan kembali:

```powershell
node --test apps/dashboard/test_layout.js apps/dashboard/test_chart.js apps/dashboard/test_inventory.js apps/dashboard/test_export.js
..\env\Scripts\python.exe manage.py check
..\env\Scripts\python.exe manage.py test apps.dashboard.tests apps.dashboard.test_display apps.dashboard.test_inventory apps.landing.tests apps.landing.test_konten_tv --noinput
..\env\Scripts\python.exe manage.py collectstatic --noinput
```

## Dokumentasi kegiatan TV

Menu Landing Page > Dokumentasi Kegiatan TV menampilkan seluruh slide berurutan
ke bawah dalam satu halaman, dikelola oleh Super Admin. Tombol Tambah Slide
mengarahkan halaman ke panel slide baru. Tiap slide mempunyai enam kartu upload
ringkas dengan preview, Simpan Slide, dan Hapus Slide. Layout upload memakai enam
kolom di desktop, tiga/dua kolom pada layar lebih kecil, dan satu kolom di bawah
360 px. Preview dibatasi tingginya agar tidak menghabiskan ruang.
Setiap slide disimpan terpisah; field memakai prefix ID slide agar input/label
tidak bertabrakan. Seluruh foto diprefetch sekali untuk menghindari query per slide.
Dropdown dan query pemilihan slide lama sudah dihapus.

Hapus Slide memakai modal hapus master yang sudah ada dan endpoint POST khusus,
dengan autentikasi, role Super Admin, dan CSRF. Penghapusan mencakup gambar dalam
slide tersebut; file yang masih dipakai slide lain tetap dipertahankan. Slide
terakhir juga boleh dihapus, menampilkan kondisi kosong tanpa membuat slide baru
otomatis. Polling Live TV menghapus slide terkait dari slideshow berikutnya.
Upload memakai JPG/JPEG/PNG asli, maksimal
7 MB per gambar; validasi format, isi gambar, dan ukuran dilakukan di backend.
Gambar dapat diganti atau dihapus per slot. File lama dibersihkan setelah commit
dan hanya jika tidak lagi dipakai slot lain. Migration `landing.0010_dokumentasi_slide`
menambahkan induk slide dan memindahkan enam gambar lama ke Slide 1 tanpa mengubah
lokasi file. ID gambar memakai urutan otomatis, sedangkan nomor 1-6 unik per slide.

Slide dokumentasi menampilkan enam posisi dalam grid 3 kolom x 2 baris. Gambar
ditampilkan utuh dengan `object-fit: contain`; slot kosong memakai placeholder.
Jika semua slot suatu slide kosong, slide beserta indikatornya dilewati. Polling
10 detik menerima `documentationSlides` dengan ID dan HTML setiap slide terisi,
memperbarui gambar dan menambah/menghilangkan slide tanpa reload halaman, termasuk
ketika sebelumnya belum ada gambar. Slide aktif dipertahankan selama masih ada;
DOM gambar tidak dibuat ulang saat kontennya sama. Indikator menyesuaikan jumlah
slide dan menjaga indikator aktif terlihat meski jumlah slide banyak.
Durasi slideshow tetap 8,5 detik. Total chart
dan informasi nihil disembunyikan saat slide dokumentasi aktif. Logika pembaruan
konten dan indikator memakai controller slideshow yang sama dengan peralatan.

Validasi mencakup akses GET/POST, penambahan/penyimpanan slide, 12 upload pada dua slide,
isolasi penyimpanan dan kegagalan validasi antar-slide, format/ukuran tidak valid, penyimpanan
tanpa perubahan, replace/hapus, cleanup setelah commit, rollback, file bersama,
batas nomor slot, keunikan slot per slide, render serta payload polling. Tes migration
memakai schema lama berisi enam gambar, lalu memeriksa lokasi file dan kelanjutan
urutan ID gambar setelah upgrade. Browser memakai gambar sintetis
untuk mode TV/normal 640x360, 1280x720, 1920x1080 dan portrait 390x844; menguji
polling saat kosong/terisi/dihapus dan penambahan slide ketiga tanpa reload.
Sebanyak 30 indikator diuji pada 360p. Listing pengaturan diverifikasi dengan tiga
slide dan 18 ID upload unik pada lebar 320/390/768/1024/1280/1440 px, pratinjau
terpisah, simpan per slide, dan batal/konfirmasi hapus. Tes backend memastikan
hapus slide kosong/terisi/terakhir, cleanup setelah commit, file bersama, akses
role, larangan GET, CSRF, serta satu query foto untuk listing banyak slide.

```powershell
..\env\Scripts\python.exe manage.py migrate landing --noinput
..\env\Scripts\python.exe manage.py test apps.landing.test_dokumentasi apps.landing.test_konten_tv apps.dashboard.test_display apps.dashboard.test_inventory --noinput
..\env\Scripts\python.exe manage.py collectstatic --noinput
```

## Verifikasi perangkat TV

Total grafik ditampilkan sebagai badge di kiri atas header; judul tetap di tengah
dan indikator slide di kanan. Pada Internal SDA, BWS/BBWS Nihil berada dalam dua
kotak terpisah di bawah canvas dengan rata tengah. Footer memakai skala font layar,
disembunyikan pada slide lain, dan tingginya ikut dihitung dalam ruang minimum chart.

Belum diuji langsung pada TCL/BrowseHere. Setelah deploy dan `collectstatic`, buka
ulang URL `?tv=1`, periksa kode barang dan asal perolehan tetap satu baris, tabel
menampilkan semua kegiatan, serta chart Internal SDA tidak menumpuk labelnya.
Periksa juga resize/zoom browser dan tunggu polling. Jika konten lebih tinggi dari
viewport, seluruh baris tetap tersedia dengan menggulir halaman. Fullscreen browser
mengikuti kontrol BrowseHere.
