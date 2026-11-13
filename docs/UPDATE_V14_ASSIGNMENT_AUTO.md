# v14 - Assignment Checklist otomatis Selesai setelah foto berhasil diunggah

## Yang berubah

- Satu tombol **Foto** per Assignment tetap digunakan. Kamera live, Kamera HP dan galeri beberapa foto tetap didukung.
- Saat pengguna menambahkan foto, frontend menunggu **seluruh file** selesai diunggah ke Supabase Storage.
- Jika semua foto berhasil, frontend mengirim **satu transaksi penyimpanan checklist** melalui aksi `ceklisSet`: daftar foto (`fotoId`) dan `status: true` dikirim bersamaan.
- Item baru tampil **Selesai / tercentang** setelah respons Supabase mengonfirmasi daftar foto dan status. Item yang belum pernah disimpan mendapatkan ID checklist dari server.
- Saat sebagian foto gagal, foto yang berhasil boleh tersimpan, tetapi **status belum otomatis berubah**. Pengguna perlu mengulangi foto yang gagal.
- Saat penyimpanan checklist ditolak server, tampilan tidak berpura-pura berhasil. Status lama tetap terjaga dan pesan error ditampilkan.
- Hanya membuka galeri, membatalkan pemilihan foto, atau menghapus foto tidak otomatis mengubah checklist.
- Ketika upload berlangsung, pengguna tidak bisa menekan centang manual bersamaan untuk menghindari benturan update.
- Kontrol upload pada galeri yang sudah terkunci karena validasi SPV tetap disembunyikan.
- Modul lain (DSO, Rekap Masalah, Visit, Pending Matter, Before/After, Export, Arsip) tidak berubah perilakunya.

## Cara memasang melalui GitHub Pages

1. Backup repository, database, dan Supabase Storage terlebih dahulu.
2. Ekstrak `Daily_Commercial_Operation_v14_Auto_Checklist_Patch.zip`.
3. Upload **isi ZIP** ke root repository `Daily-Commercial-Operation`, menggantikan file pada lokasi yang sama. Jangan membuat folder ZIP baru di dalam repository.
4. Jika migrasi SQL v13 belum dijalankan, di Supabase SQL Editor jalankan `supabase/migrations/20261113_010_dso_photo_audit.sql` setelah 008 & 009. Tidak ada SQL baru untuk fitur checklist otomatis v14.
5. Cek GitHub Actions dan pastikan build+deploy berhasil. Refresh website dengan Ctrl+Shift+R.
6. Uji pada satu Assignment belum selesai: pilih foto, tunggu sampai upload & simpan berhasil, cek status berubah menjadi **Selesai (centang)** pada aplikasi dan baris tabel CEKLIS/Supabase.
7. Uji unggah ditolak (di staging), tanggal/toko berbeda, dan item yang telah divalidasi SPV sebelum digunakan serentak oleh 12 toko.

## Pengujian lokal

- `node scripts/check.mjs`: pemeriksaan JS, action routing dan SQL deklarasi.
- `python3 tests/v14_assignment_auto_smoke.py`: 27 pemeriksaan, 390/768/1280 px. Termasuk auto-centang, foto ganda, retry, unggah sebagian gagal, backend gagal, hapus satu foto, dan status divalidasi.
- `python3 tests/v13_regression.py`: DSO multi-foto, watermark WITA, navigasi, detail receipt foto.
- `python3 tests/v12_before_after_smoke.py`: Before/After, Pending Matter.
- `python3 tests/v11_compact_smoke.py`: 1 tombol foto per item, nama seksi A-E.

**Batasan:** Pengujian dilakukan dengan Supabase mock. Deployment live, kamera fisik, data serta RLS produksi tidak dapat diverifikasi dalam paket ini. Watermark WITA dan metadata upload membantu audit, tetapi tidak membuktikan foto mustahil dimanipulasi.
