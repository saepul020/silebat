# Live TV: mode signage

Aktifkan melalui **Aktifkan Mode TV**, atau tambahkan `?tv=1` pada URL Live TV
(`&tv=1` jika sudah ada parameter lain). Mode tidak ditentukan dari user agent.

Acuan viewport terkecil mode TV adalah **640 x 360 px (360p, 16:9)**.
Ini ukuran viewport CSS, bukan resolusi foto atau panel fisik TV.
Perangkat TV yang digunakan memiliki viewport **960 x 540 px dengan DPR 2**.
Ukuran ini menjadi acuan tipografi mode TV; DPR menentukan kepadatan render,
tanpa mengalikan ukuran layout CSS menjadi 1920 x 1080 px.

## Layout dan refresh

- Setiap slide grafik menampilkan total nilai yang terlihat di kiri atas. Total
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
- `dashboard_display.css` dan `tv_layout.js` dipakai mode normal dan TV. Pada mode
  normal, font tabel mengikuti field terpanjang; cell biasa satu baris dan status
  membungkus maksimal 22 karakter per baris. Pada mode TV, font mengikuti skala
  layar/header, tanpa mengecilkan seluruh tabel karena satu field panjang.
  Seluruh isi field, termasuk status, membungkus sesuai lebar kolom maksimal dua
  baris; teks berlebih diberi elipsis di baris kedua. Kata tanpa spasi juga dapat
  dipotong. Status memakai satu unit skala lebih kecil; khusus badge peringatan
  mode TV, font dua unit skala lebih kecil dari font isi tabel. Teks lengkap tetap ada dalam
  DOM dan tooltip nomor/nama/layanan/instansi/status, tanpa mengubah data tersimpan.
  Partial render awal dan polling sama; clamp CSS hanya aktif pada mode TV.
  Teks status memakai line-height 1,5 dan hanya clamp dua baris, tanpa batas
  max-height tambahan yang dapat memotong huruf pada font kecil/subpixel.
- Tabel display memakai wrapper sendiri, tanpa class list transaksi umum yang
  membawa minimum lebar, tinggi baris, dan breakpoint berbeda. Padding toolbar,
  cell, badge, serta kondisi kosong mengikuti `--tv-type` di kedua mode. Pemisah
  baris, toolbar, dan bingkai badge memakai garis inset `--tv-stroke`, sekitar
  0,5 px pada 360p. Warna status tetap mengikuti jenis prosesnya. Seluruh kegiatan
  tetap ditampilkan berurutan, termasuk hasil polling, tanpa paginasi tabel.
- Seluruh tipografi halaman memakai skala bersama dari lebar dan tinggi viewport
  (`--tv-type`, acuan 1280 x 720 px normal dan 960 x 540 px TV), termasuk judul, jam, ringkasan, tabel, badge,
  card, rekap, dan placeholder foto. Ada batas minimum terpisah untuk mode normal
  dan TV serta batas maksimum pada layar besar. Override font per breakpoint
  dihapus; penyesuaian teks terpanjang tetap diterapkan di atas skala ini.
- Khusus `tv-equipment__body`, font awal dimaksimalkan terhadap lebar dalam card.
  Nama/merek memakai pengali bersama per slide dan tetap proporsional terhadap
  metadata ketika judulnya pendek.
  Metadata dihitung terpisah terhadap gabungan label/nilai terpanjang dan dibatasi
  sekitar 65% ukuran judul serta 90% ukuran merek agar hierarkinya tetap jelas.
  Pada mode TV, font metadata berawal dari 5,5 unit `--tv-type` dan hanya boleh
  mengecil saat fitting. Data pendek tidak memperbesar metadata untuk mengisi
  lebar; kolom label/nilai membagi ruang sekitar 45/55 agar tetap memenuhi body
  dan sejajar antar-card. Ukuran font seragam per slide.
  Jarak baris/kolom mengikuti font dalam satuan `em`. Asal Perolehan membungkus
  maksimal 18 karakter per baris, termasuk spasi; metadata lain tetap satu baris.
  Pada mode TV, baris Asal Perolehan dapat membungkus lagi mengikuti lebar kolom
  nilai jika ruangnya menyempit, termasuk kata tanpa spasi. Aturan `nowrap` tidak
  memaksa nilai meluber; tidak ada elipsis atau batas jumlah baris untuk field ini.
  Ukuran diukur dari baris terpanjang setelah wrap, bukan gabungan teks seluruh
  baris. Semua card dalam satu slide memakai ukuran seragam; slide lain tidak
  membatasi ukuran slide aktif. Card kosong dan rekap memakai penyesuaian sendiri.
  Pada mode TV, nama/merek/metadata juga dikecilkan bersama jika tinggi teks,
  margin, dan jaraknya melebihi ruang body setelah foto; hierarki tetap dijaga.
- Pengukuran memakai lebar teks hasil render. Ukuran dihitung ulang setelah resize,
  font/gambar selesai dimuat, pergantian slide, dan pembaruan data. Font kembali ke
  ukuran CSS dasarnya sebelum dihitung agar tidak terus membesar/mengecil setelah resize.
- `tv_screen.css` mengatur frame signage dan layout TV ringkas hingga lebar 1024 px.
  Padding, jarak, header, ringkasan, tabel, dan card mengikuti unit proporsional
  dari lebar maupun tinggi viewport; enam card tetap sejajar. Mode normal mempertahankan jumlah
  kolom responsifnya dan memakai skala font bersama.
  Mode TV mengikuti ukuran dan offset
  `visualViewport`, dengan fallback `innerWidth`/`innerHeight`. Tidak ada pengecilan
  font root, CSS zoom, atau transform scale pada dashboard.
- Pada mode normal, tinggi minimum area slide mengikuti tinggi isi card.
  Pada mode TV, carousel memakai sisa tinggi viewport setelah header, ringkasan,
  dan tabel. Stage memakai basis flex nol agar header dan footer BWS/BBWS Nihil
  ikut mendapat ruang, tanpa memaksa tinggi canvas sebesar seluruh card.
  Tinggi alat di slide tidak aktif tidak memperbesar carousel TV.
  Judul/subjudul TV diukur agar tetap satu baris.
- Seluruh kegiatan aktif tampil berurutan dalam satu tabel, termasuk pada polling;
  batas delapan record dan paginasi otomatis tabel sudah dihapus. Badge tetap
  **Realtime** dan timer carousel hanya mengganti slide alat/grafik.
- Pada mode normal, track tabel mengikuti tinggi seluruh isinya dan halaman dapat
  digulir. Pada mode TV, tinggi tabel dibatasi 28% viewport; daftar padat digulir
  di wrapper tabel tanpa paginasi atau penghapusan record. Carousel tetap dalam
  viewport, termasuk label sumbu dan footer nihil. Foto alat tetap 4:3.
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

Pengurangan metadata dan perbaikan clipping badge diperiksa pada 640x360,
960x540, 1280x720, dan 1920x1080 dengan DPR 1/2. Di 960x540, metadata fixture
menjadi sekitar 5,4 px dan seragam pada enam card; polling data pendek tetap
mempertahankan batas font. Asal Perolehan lengkap, field/body tidak meluber,
dan resize kembali memulihkan ukuran. Badge dipersempit agar status asli memakai
dua baris: seluruh glyph berada di dalam area teks, termasuk pada DPR 2. Status
yang melebihi dua baris tetap memakai elipsis. Mode normal tidak berubah.

Asal Perolehan `TKTM - Direktorat BINTEK SDA` diperiksa di 640x360, 960x540,
1280x720, dan 1920x1080, dengan DPR 1/2. Kolom nilai juga dipersempit untuk
memeriksa seluruh baris teks tetap berada dalam field/body. Resize dan polling
mempertahankan teks lengkap. Badge peringatan di 960x540 memakai 5,5 px dari font
isi tabel 7,5 px; selisih dua unit mengikuti skala layar. Mode normal tetap memakai
wrap dan ukuran status sebelumnya. Tidak ada perubahan nilai database.

Wrap tabel dua baris diperiksa pada 640x360, 960x540, 1280x720, dan 1920x1080
dengan DPR 1/2. Fixture memakai kalimat panjang dan kode 240 karakter tanpa spasi:
semua field maksimal dua baris, elipsis terlihat di baris kedua, tidak meluber
ke kolom sebelah, dan font tidak mengecil akibat panjang data. Status tetap lebih
kecil; teks lengkap dan escaping HTML terjaga. Polling mengembalikan field pendek,
resize memulihkan skala, dan mode normal mempertahankan pola sebelumnya.

Perbaikan teks terpotong dan footer chart diuji pada TV 640x360, 960x540,
dan 1280x720 dengan DPR 1/2. Fixture memakai 0, 3, 11, dan 30 kegiatan serta
Asal Perolehan 22 baris di slide kedua. Body tidak overflow horizontal/vertikal,
font tetap seragam per slide, dan slide tidak aktif tidak mendorong chart keluar
viewport. Semua baris tetap ada; tabel padat menggulir secara internal.
Seluruh slide termasuk rekap diperiksa pada DPR 2, termasuk resize dan polling.

Kalibrasi 960 x 540 px diperiksa di Chrome dengan DPR 1 dan 2. Pada mode TV,
judul utama menjadi 16 px dan font awal cell tabel 7,5 px (sebelumnya 12 px dan
5,625 px); pengukuran teks terpanjang tetap mengecilkan font jika diperlukan.
Metadata alat tetap dihitung dari lebar card dan lebih kecil dari judul.
Jarak dan indikator compact yang sebelumnya memakai ukuran tetap kini mengikuti
skala teks. Unit ruang compact juga memperhitungkan tinggi layar.
Judul card rekap mengisi lebar body agar fitting teks memakai ruang card yang
sebenarnya, termasuk nama alat panjang pada slide keberfungsian.

Browser memeriksa 640x360, 960x540, 1280x720, dan 1920x1080 pada kedua DPR:
tiga kegiatan/enam alat muat tanpa scroll horizontal atau vertikal, status
maksimal 22 karakter, Asal Perolehan maksimal 18 karakter, empat foto berpusat,
serta 55 label chart maksimal dua baris tanpa tabrakan. Total/nihil tetap tertata.
Resize kembali ke 960x540 dan polling mempertahankan skala; sebelas kegiatan
tetap tampil lengkap dengan scroll vertikal. Mode normal 960x540 dan 390x844
ikut diperiksa. Pengujian memakai template asli dan data sintetis, tanpa mengubah
record aplikasi. Tampilan pada perangkat TV langsung belum diverifikasi.

Wrap status/Asal Perolehan memakai filter `tv_lines` pada partial yang sama untuk
render awal dan polling. HTML sumber di-escape; pemisahan kata, kata tanpa spasi,
Unicode, teks kosong dan batas 18/22 karakter diuji. Browser memeriksa badge lebih
kecil dari cell biasa, semua field berada dalam card/cell, dan metadata lebih kecil
dari judul pada mode TV/normal 640x360, 1280x720, 1600x900, 1920x1080, 390x844.
Resize bolak-balik serta pembaruan melalui polling juga diperiksa.

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

Menu Manage Konten > Konten Kegiatan TV menampilkan seluruh slide berurutan
ke bawah dalam satu halaman, dikelola oleh Super Admin. Tombol Tambah Slide
mengarahkan halaman ke panel slide baru. Tiap slide mempunyai enam kartu upload
ringkas dengan preview, Simpan Slide, dan Hapus Slide. Layout upload memakai enam
kolom di desktop, tiga/dua kolom pada layar lebih kecil, dan satu kolom di bawah
360 px. Preview dibatasi tingginya agar tidak menghabiskan ruang.
Setiap slide disimpan terpisah; field memakai prefix ID slide agar input/label
tidak bertabrakan. Seluruh foto diprefetch sekali untuk menghindari query per slide.
Dropdown dan query pemilihan slide lama sudah dihapus.

Nomor tampilan dihitung ulang dari urutan slide yang tersedia: judul panel, tombol
simpan/hapus, modal dan pesan penghapusan memakai Slide 1, Slide 2, dan seterusnya.
Setelah penghapusan tidak ada nomor yang terlewat; penambahan slide ditempatkan
setelah slide terakhir. ID penyimpanan, relasi foto, prefix form dan URL aksi tetap
stabil sehingga penomoran tampilan tidak memindahkan gambar antar-slide.

Kontrol upload memakai `landing-gallery-input` dan `landing-gallery-trigger` yang
sama dengan galeri peralatan, dengan ukuran ringkas untuk enam kolom. Tombol
menampilkan Pilih/Ganti gambar atau nama file yang dipilih, dilengkapi pratinjau
dan tombol X di kanan atas preview untuk mengosongkan slot. Nama file dipasang melalui `textContent`; file picker dapat dibuka
dengan klik label maupun keyboard. Style input native lama di kartu dihapus.
Validasi meliputi hapus di tengah lalu tambah, hapus seluruh slide lalu tambah,
label modal/target data, pratinjau, nama file dan layout pada lebar 320-1440 px.

Tombol X menggantikan checkbox dengan flag hidden yang tetap divalidasi di server.
File baru yang belum disimpan dibatalkan langsung; gambar tersimpan ditandai untuk
dihapus saat Simpan Slide. Memilih file pengganti membatalkan flag hapus. Backend
mengganti referensi file pada record slot, menghapus record gambar yang dikosongkan,
dan membersihkan file lama setelah commit melalui signal yang sudah ada. Hapus Slide
mencakup seluruh record/file miliknya; file yang masih dipakai slot lain tetap ada.
Tes HTTP memeriksa replace lalu hapus dan penghapusan slide berisi enam file.

Tambah Slide membuka popup pengingat untuk menyimpan perubahan slide sebelumnya.
Jika masih ada file baru/pengganti atau flag hapus, tombol konfirmasi tambah menjadi
disabled dan popup mengarahkan pengguna kembali ke slide yang perlu disimpan.
Penambahan tidak mengirim POST sampai tidak ada perubahan tertunda. Pembatalan
popup mempertahankan file pilihan dan preview. Saat pilihan file baru dibatalkan
hingga form kembali bersih, guard navigasi global direset sebelum POST tambah.
Browser menguji gambar baru/tersimpan/pengganti, X, flag hapus yang dikirim, popup
bersih/kotor, batal/kembali, dan penambahan setelah membatalkan pilihan file.

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

Slide Dokumentasi Kegiatan Laboratorium menampilkan hanya slot yang berisi foto,
maksimal enam gambar. Susunan flex membungkus maksimal tiga foto per baris dan
memusatkan seluruh kelompok secara horizontal/vertikal. Baris terakhir juga
dipusatkan: empat foto menjadi 3+1, lima foto menjadi 3+2. Untuk satu sampai tiga
foto, satu baris berada di tengah tinggi container. Ukuran kotak tetap konsisten
dan foto ditampilkan utuh dengan `object-fit: contain`; placeholder kosong dihapus.
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
disembunyikan pada slide lain, dan mendapat ruang sendiri dalam tinggi card TV.

Belum diuji langsung pada TCL/BrowseHere. Setelah deploy dan `collectstatic`, buka
ulang URL `?tv=1` pada viewport 960x540/DPR 2, periksa kode barang tetap satu baris,
Asal Perolehan membungkus maksimal 18 karakter per baris, tabel
menampilkan semua kegiatan, serta chart Internal SDA tidak menumpuk labelnya.
Periksa juga resize/zoom browser dan tunggu polling. Jika tabel kegiatan padat,
seluruh baris tetap tersedia dengan menggulir area tabel. Fullscreen browser
mengikuti kontrol BrowseHere.
