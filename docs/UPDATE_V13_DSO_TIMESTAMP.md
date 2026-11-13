# Update v13 — Perbaikan Submit DSO + Audit Foto Kamera

**Basis:** Daily Commercial Operation v12 (Supabase Native, GitHub Pages).

## Masalah yang diperbaiki

1. **DSO menolak submit walaupun ada 6 foto / multi-foto.** Fungsi `dco.valid_photo` versi awal hanya mengenali satu path, bukan daftar JSON. Saat submit, item gagal validasi dahulu lalu dianggap kosong. SQL 010 mengenali satu foto, foto lama Google Drive, atau daftar maksimal 30 foto, dan menolak nilai tidak valid secara eksplisit.
2. **Progres foto tidak ikut berubah** saat upload selesai: kini progress dan badge DSO diperbarui tanpa me-reset form.
3. **Error submit tidak jelas**: kini pesan tetap tampil di form, menandai item yang belum diisi, memblokir submit saat proses upload masih berlangsung, mencegah klik ganda, dan menjaga foto di state lokal jika server menolak.
4. **Timestamp kamera live**: waktu WITA ditanam pada piksel foto saat kamera live mengambil gambar. Setiap foto baru mendapat receipt berisi waktu pembuatan file di Supabase Storage, waktu pencatatan, sumber upload, checksum SHA-256 yang dihitung pada browser. Klik foto untuk melihat keterangan receipt.

## Pemasangan (WAJIB urut)

1. **Backup lebih dahulu:** salin repository GitHub, backup database Supabase dan foto Storage. Jangan hapus tabel/foto lama.
2. **Supabase SQL Editor:** jalankan `supabase/migrations/20261113_010_dso_photo_audit.sql` sebagai **satu** query. Pastikan migrasi dasar v12 dan SQL `008_multiphoto.sql` serta `009_visit_before_after.sql` sudah ada. SQL 010 tidak menghapus atau mengubah baris data lama.
3. **GitHub:** ekstrak `Daily_Commercial_Operation_v13_Patch.zip`; unggah seluruh isi ZIP (bukan ZIP-nya) ke root repository `tigalapancommercial-netizen/Daily-Commercial-Operation`, pertahankan semua subfolder. Pilih *Commit changes*.
4. **GitHub Actions → workflow deployment:** pastikan status hijau. Gunakan `Ctrl+Shift+R` atau mode incognito agar cache lama tidak terbuka.
5. **Uji DSO pada satu toko:** upload 2–6 foto pada satu item wajib dan 1 foto di item wajib lain, lalu tekan Kirim. Periksa progres, notifikasi sukses, dan riwayat.
6. **Uji Foto langsung:** berikan izin kamera, tekan Ambil Foto, perbesar hasilnya; teks `KAMERA LIVE`, tanggal dan jam WITA harus tercetak langsung pada gambar. Klik foto terunggah untuk melihat *Diterima server*.
7. **Uji izin Store, SPV, Master**, validasi, Assignment, Visit, Before/After, export dan backup menggunakan akun non-produksi dahulu.

## Diagnostik singkat

Jalankan query ini di SQL Editor bila masih muncul `Foto wajib belum lengkap` padahal galeri sudah terisi:

```sql
SELECT dco.valid_photo('["2026-11/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa_ABCDE12345.webp","2026-11/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb_FGHIJ67890.webp"]') AS foto_multi_valid;
-- harus true setelah migrasi 010

SELECT proname FROM pg_proc
JOIN pg_namespace n ON n.oid=pronamespace
WHERE n.nspname='public' AND proname IN ('dco_dso_submit','dco_photo_register','dco_photo_receipt');
-- harus muncul ketiganya
```

Jika upload baru gagal dengan pesan `bukti waktu server belum tercatat`, periksa apakah SQL 010 sudah dijalankan dan bucket `dco-foto` ada.

## Batas keamanan yang perlu dipahami

- Timestamp pada gambar dan waktu `storage.objects.created_at` di Supabase dibuat untuk **membantu audit**, bukan bukti kamera anti-manipulasi mutlak. Pengguna dengan akses perangkat dapat memotret ulang gambar, mengubah konten sebelum mengambil foto, atau memanipulasi aplikasi browser.
- `client_sha256` merupakan checksum dari **file yang dikirim oleh browser**, bukan bukti bahwa file berasal dari objek fisik tertentu. Receipt server adalah sumber waktu upload yang lebih dapat dipercaya daripada jam perangkat.
- Upload melalui Kamera HP/Galeri memperoleh **waktu diterima server**, tetapi tidak diberi label `KAMERA LIVE` dan tidak mengklaim waktu pengambilan asli.
- Perlindungan yang lebih kuat memerlukan verifikasi server atas bytes, private storage, kebijakan autentikasi/otorisasi, serta proses inspeksi SPV.

## Status QA

- `node scripts/check.mjs`: lulus pemeriksaan sintaks, action routing, dan deklarasi RPC.
- `python tests/v13_regression.py`: 51 pemeriksaan mock-browser pada 390/768/1280 px, termasuk submit DSO multi-foto, penyimpanan foto saat submit ditolak, watermark piksel kamera, dan pembukaan receipt.
- `python tests/v12_before_after_smoke.py`: 39 pemeriksaan lulus.
- `python tests/v11_compact_smoke.py`: 54 pemeriksaan lulus.
- **Belum diuji pada Supabase produksi.** Pengujian build Vite tidak selesai karena dependency npm tidak tersedia di lingkungan ini. Verifikasi build dan koneksi server harus dilakukan lewat GitHub Actions + akun staging.
