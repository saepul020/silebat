# Live TV: mode signage

Aktifkan melalui tautan **Aktifkan Mode TV** pada halaman Live TV normal, atau tambahkan
`?tv=1` pada URL Live TV yang sudah dipakai (`&tv=1` jika ada parameter lain).
Simpan URL tersebut sebagai bookmark pada BrowseHere. Hapus parameter untuk kembali ke mode normal.
Mode tidak ditentukan dari user agent atau resolusi fisik TV.

## Layout dan refresh

- `dashboard_display.css` menjadi sumber bersama ukuran teks, padding, jarak, dan
  style card untuk kedua mode. `tv_screen.css` hanya mengatur kebutuhan signage dan
  `tv_layout.js` menangani viewport/paginasi; keduanya hanya dimuat pada mode TV.
  Breakpoint tablet/ponsel tidak mengubah jumlah kolom mode TV.
- `--tv-columns` pada `.tv-equipment` menjadi sumber ukuran halaman card (enam).
  Card tambahan dibagi ke halaman berikutnya. Slot yang belum dipilih tidak diduplikasi
  menjadi alat; halaman tanpa pilihan menampilkan pesan kosong.
- Halaman menggunakan ukuran dan offset `visualViewport`, dengan fallback `innerWidth`
  dan `innerHeight`. Ukuran dihitung ulang pada resize, perubahan visual viewport,
  perubahan ukuran halaman, pemuatan font/gambar, dan pembaruan data.
  Font root dimulai dari 16 px seperti mode normal, tanpa mengecilkannya berdasarkan
  tinggi/lebar viewport. Ukuran elemen mengikuti aturan responsif bersama. Jika konten
  benar-benar tidak muat, kurangi baris tabel per halaman dahulu, kemudian font root
  secara bertahap hingga 12 px. Tidak ada viewport/canvas dengan resolusi paksa.
- Layout mengisi viewport aktual dengan ukuran CSS biasa, tanpa CSS `zoom` atau
  `transform: scale()` pada dashboard. Frame foto selalu selebar card dan berasio 4:3,
  dengan gambar mengisi frame. Jika konten padat, tinggi halaman tabel dan ukuran teks
  disesuaikan bersama; frame tidak diperkecil sendiri-sendiri berdasarkan isi card.
- Tabel memakai maksimal sekitar 30% tinggi viewport. Jika tidak muat, seluruh baris
  tetap tersedia dalam halaman otomatis dengan indikator `Realtime · 1/2` dan seterusnya.
  Pergantian tabel mengikuti timer slideshow 8,5 detik yang sama.
- Polling 10 detik memperbarui tabel, pilihan alat, dan rekap kondisi. HTML sumber disimpan
  terpisah dari halaman hasil pembagian agar refresh tidak menggandakan card atau timer.
- Layout normal tetap enam kolom pada desktop, tiga pada tablet, dan satu pada ponsel,
  dengan perilaku scroll normal sebelumnya.
- Badge status pada mode TV mewarisi jenis font cell tabel dan memakai ketebalan
  700 seperti teks Peminjam. Khusus primary dan secondary, ukuran font memakai
  aturan bersama `0.86em` dengan teks tanggal `s/d ...` pada kolom Periode.
  Cell status dan `cell-wrap` memakai tinggi baris yang sama.
- Di kedua mode Live TV, label sumbu bawah yang panjang menggunakan font 6–8 px
  dan rotasi tetap 22,5°. Label pendek tetap horizontal jika ruang mencukupi.
  Satu plugin menghitung ulang pengaturan sebelum layout grafik, termasuk setelah resize.
  Pembungkusan label mempertahankan seluruh teks, termasuk kata panjang tanpa spasi.

Referensi perilaku viewport: [MDN VisualViewport](https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport).
Pengaturan rotasi mengikuti opsi tick [Chart.js](https://www.chartjs.org/docs/latest/axes/cartesian/#tick-configuration).

## Validasi implementasi

Pengujian browser menggunakan Chrome headless, template Django sebenarnya, data uji
delapan kegiatan aktif, dua kelompok alat berisi enam card, dan enam card rekap.
Data aplikasi asli tidak diubah.

| Viewport dasar | Zoom halaman Chrome | Hasil |
| --- | --- | --- |
| 960×540 | 75%, 80%, 90%, 100%, 110% | Enam card sejajar, viewport terisi, tanpa scroll |
| 1280×720 | 75%, 80%, 90%, 100%, 110% | Enam card sejajar, viewport terisi, tanpa scroll |
| 1920×1080 | 75%, 80%, 90%, 100%, 110% | Enam card sejajar, viewport terisi, tanpa scroll |
| 3840×2160 | 75%, 80%, 90%, 100%, 110% | Enam card sejajar, viewport terisi, tanpa scroll |

Zoom di atas adalah perubahan zoom halaman Chrome, diverifikasi melalui `devicePixelRatio`
dan dimensi CSS viewport, bukan sekadar emulasi DPR. Pergantian zoom pada halaman yang
tetap terbuka juga diuji. Uji visual viewport/pinch 110% dilakukan terpisah; Chrome
membatasi page scale di bawah 100% pada konfigurasi emulasi tersebut.

Pemeriksaan DOM mencakup posisi horizontal card, batas halaman, rasio foto, overflow
body card/tabel, `scrollWidth/clientWidth`, dan `scrollHeight/clientHeight`.
Frame foto juga diperiksa selebar card, sama tinggi antar-card dalam satu grid,
serta gambar/placeholder memenuhi seluruh frame dengan rasio 4:3. Badge primary
dan secondary diverifikasi memiliki ukuran font yang sama dengan tanggal `s/d ...`
pada mode TV, dengan ketebalan 700 seperti teks Peminjam.
Label grafik panjang diperiksa pada kedua mode, termasuk perubahan ukuran layar:
rotasi 22,5°, font lebih kecil, dan tidak ada teks label yang terbuang.
Pada viewport 1918×912 dengan dua kegiatan aktif, ukuran judul, nama alat, merek,
metadata, padding card, serta teks tabel sama dengan mode normal; font root tetap 16 px.
Header normal lebih tinggi karena memuat tombol aktivasi Mode TV, sehingga tinggi
area slideshow kedua mode dapat berbeda meskipun ukuran isi card sudah sama.
Kasus lain: viewport 1024×768 dan 1920×720, field master panjang, 13 card menjadi
6–6–1 pada kedua jenis card, pengurangan menjadi dua card tanpa duplikasi, seluruh
delapan baris tabel bergantian terlihat, satu timer slideshow, polling nyata, jam,
serta mode normal desktop/tablet/ponsel.

Tes yang dapat dijalankan kembali:

```powershell
node --test apps/dashboard/test_layout.js apps/dashboard/test_chart.js
..\env\Scripts\python.exe manage.py check
..\env\Scripts\python.exe manage.py test apps.dashboard.tests apps.dashboard.test_display apps.dashboard.test_inventory apps.landing.tests apps.landing.test_konten_tv --noinput
..\env\Scripts\python.exe manage.py collectstatic --noinput
```

## Verifikasi di TCL BrowseHere

1. Deploy sumber dan hasil `collectstatic`, lalu muat ulang URL dengan `?tv=1`.
2. Periksa kedua slide alat: enam card sejajar, seluruh label/angka terbaca, dan tidak ada scroll.
3. Coba zoom 75%, 80%, 90%, 100%, dan 110% tanpa menutup halaman; periksa keempat tepi layar.
4. Tunggu lebih dari 20 detik: slide berpindah, jam berjalan, tabel berganti halaman
   bila diperlukan, serta data alat/kondisi mengikuti polling.
5. Jika tersedia, gunakan mode fullscreen dari menu browser untuk menyembunyikan bilah
   browser. Halaman web mengisi viewport konten; bilah browser dikendalikan BrowseHere.

Belum ada pengujian langsung pada TCL V8-R51AT01/BrowseHere. Platform TV tidak cukup
untuk memastikan versi engine browser. Halaman hanya bisa menanggapi perubahan metrik
yang dilaporkan browser; pembesaran yang dilakukan browser tanpa perubahan metrik/event
viewport tidak dapat dikendalikan sepenuhnya dari JavaScript.
