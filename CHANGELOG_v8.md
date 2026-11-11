# v8 — Data Management & Storage Control

- Export CSV lengkap per menu dengan pagination Supabase dan RLS.
- Full JSONL (gzip when supported) backup untuk semua tabel operasional, konfigurasi, master, profil/role dan audit (tanpa PIN/password/token/foto binary).
- Menu Export & Penyimpanan khusus Master, statistik baris dan ukuran foto.
- Arsip terkontrol: preview data >90 hari selesai/tervalidasi, copy snapshot ke private, verify count dan SHA256, delete active transactionally.
- Unduh arsip + verifikasi checksum; purge arsip setelah minimal 24 jam dan konfirmasi manual.
- Foto baru dikonversi WebP di browser, max edge 1600px; ditampilkan lightbox dalam halaman menggunakan signed URL.
- Tidak ada photo-orphan automatic deletion; bukti historis tetap terlindungi.

**Belum** di-deploy ke Supabase/GitHub; migrasi data lama 1:1 tidak diselesaikan oleh patch ini.
