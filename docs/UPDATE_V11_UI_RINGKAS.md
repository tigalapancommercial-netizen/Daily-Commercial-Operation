# Update v11 — Header ABCDE + Bukti Foto Ringkas

## Yang berubah

- **Visiting Check Point → Riwayat & Validasi**: header kategori visit kini menampilkan nama singkat **A Finance**, **B Aset/GA**, **C Merchandise**, **D SDM**, **E Gudang**. Nama lengkap tetap terlihat pada judul seksi/form (dan tooltip header).
- **Assignment Checklist, DSO, per-point Visit, form Issue**: tombol foto disederhanakan menjadi **satu tombol `📷 Foto [jumlah]`** per item. Tidak lagi ada tiga tombol pengambilan foto yang selalu memenuhi layar.
- Ketika tombol Foto diklik muncul satu **galeri HTML** dengan thumbnail dan pilihan **Foto langsung**, **Kamera HP**, **Dari galeri**. Masing-masing foto tetap tersimpan sebagai file gambar di Supabase Storage, bukan sebagai file HTML; gambar baru dikompresi ke WebP seperti versi v10.
- Foto lama dan foto banyak dari v10 tetap dapat dilihat/dihapus secara individual. Tanggal, jawaban checklist, hasil visit, status validasi, dan relasi database tidak diubah.
- Layout Assignment dan 35-point Visit dibuat lebih ringkas dan responsif.

## Pemasangan ke GitHub Pages

1. **Backup repository** saat ini (unduh ZIP atau buat branch GitHub).
2. Bila sudah menggunakan v10, ekstrak `Daily_Commercial_Operation_v11_Patch_Ringkas.zip` dan **upload file** `index.html`, `scripts/build_index.py`, `scripts/patch_v11_compact.py`, dan dokumentasi ke path yang sama di repository GitHub.
3. Commit ke branch `main`. GitHub Actions otomatis build dan deploy ke GitHub Pages sesuai workflow yang sudah ada.
4. Tunggu status build di tab **Actions** menjadi hijau, lalu buka website dan hard-refresh `Ctrl+Shift+R`.
5. Masuk ke Visiting Check Point → Riwayat & Validasi: pastikan header A–E menampilkan nama. Cek Assignment: satu tombol Foto membuka galeri untuk kamera atau file.

## Pemasangan dari ZIP lengkap

Jika repository tidak lagi berisi kode aplikasi v10 yang utuh, gunakan `Daily_Commercial_Operation_v11_Full_GitHub.zip`. Unggah isinya (bukan file ZIP-nya) ke repository. Pertahankan file konfigurasi hosting dan nilai Secrets Anda (jangan simpan secret di repository).

## Database

**Tidak ada SQL tambahan untuk v11.** Fitur multi-foto tetap membutuhkan migrasi v10 `supabase/migrations/20261112_008_multiphoto.sql`, yang sudah tersedia dalam paket lengkap. Jalankan migrasi itu hanya jika belum terpasang. **Jangan hapus tabel atau reset Supabase untuk update UI ini.**

## Pengujian

- `npm run check`: pemeriksaan JS, kesesuaian hasil generate `index.html`, pemetaan RPC/UI lulus.
- `python tests/v11_compact_smoke.py`: 54 pemeriksaan berurutan pada lebar 390/768/1280, termasuk kamera live simulasi, unggah 2 WebP, hapus 1 foto, 9 navigasi utama, dan 5 nama seksi. Tidak ada JavaScript pageerror.
- **Belum diuji pada akun Supabase produksi maupun kamera HP fisik.** Fitur memerlukan HTTPS dan izin kamera browser. Pastikan pengujian setelah deploy.

### Re-generasi index.html

`python3 scripts/build_index.py` sekarang menjalankan patch v10 dan v11 secara otomatis. Jangan mengunggah ulang `index.html` versi lama setelah perubahan.
