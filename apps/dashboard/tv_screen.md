# Live TV: mode signage

Aktifkan melalui tautan **Aktifkan Mode TV** pada halaman Live TV normal, atau tambahkan
`?tv=1` pada URL Live TV yang sudah dipakai (`&tv=1` jika ada parameter lain).
Simpan URL tersebut sebagai bookmark pada BrowseHere. Hapus parameter untuk kembali ke mode normal.
Mode tidak ditentukan dari user agent atau resolusi fisik TV.

## Layout dan refresh

- `dashboard_display.css` menyimpan layout normal. `tv_screen.css` dan `tv_layout.js`
  hanya dimuat pada mode TV; breakpoint tablet/ponsel tidak mengubah jumlah kolom mode TV.
- `--tv-columns` pada `.tv-equipment` menjadi sumber ukuran halaman card (enam).
  Card tambahan dibagi ke halaman berikutnya. Slot yang belum dipilih tidak diduplikasi
  menjadi alat; halaman tanpa pilihan menampilkan pesan kosong.
- Halaman menggunakan ukuran dan offset `visualViewport`, dengan fallback `innerWidth`
  dan `innerHeight`. Ukuran dihitung ulang pada resize, perubahan visual viewport,
  perubahan ukuran halaman, pemuatan font/gambar, dan pembaruan data.
  Ukuran 1920×1080 di JS hanya acuan proporsi font, bukan ukuran viewport atau canvas paksa.
- Layout mengisi viewport aktual dengan ukuran CSS biasa, tanpa CSS `zoom` atau
  `transform: scale()` pada dashboard. Foto tetap berasio 4:3; pada rasio layar yang
  sangat lebar, frame foto dapat mengecil secara proporsional untuk memberi ruang informasi.
- Tabel memakai maksimal sekitar 30% tinggi viewport. Jika tidak muat, seluruh baris
  tetap tersedia dalam halaman otomatis dengan indikator `Realtime · 1/2` dan seterusnya.
  Pergantian tabel mengikuti timer slideshow 8,5 detik yang sama.
- Polling 10 detik memperbarui tabel, pilihan alat, dan rekap kondisi. HTML sumber disimpan
  terpisah dari halaman hasil pembagian agar refresh tidak menggandakan card atau timer.
- Layout normal tetap enam kolom pada desktop, tiga pada tablet, dan satu pada ponsel,
  dengan perilaku scroll normal sebelumnya.

Referensi perilaku viewport: [MDN VisualViewport](https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport).

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
