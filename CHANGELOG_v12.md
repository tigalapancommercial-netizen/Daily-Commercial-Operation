# v12 — Before/After Visit Issue & Foto Update

- Satu tombol **Before / After** per issue, galeri terpisah kondisi awal vs foto update.
- Update Notes dan foto terbaru per seksi A–E.
- Dua kolom baru `dco.visit_issue.foto_after` dan `update_note`, SQL 009 non-destructive.
- Kontrol kamera/galeri/kompres WebP tetap dipertahankan dari v10; layout ringkas dari v11.
- Proteksi path foto update dari pembersihan database otomatis.
- Pengujian browser simulasi 39 pemeriksaan pada lebar 390/768/1280 piksel.
