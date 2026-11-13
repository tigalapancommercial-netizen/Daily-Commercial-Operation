# DCO v19 — Edit, Sampah, Pulihkan, Hapus Permanen Campaign

## Instalasi pada aplikasi v18
1. Backup database Supabase dan repository GitHub sebelum pembaruan.
2. Buka Supabase > SQL Editor, jalankan `supabase/migrations/20261113_015_campaign_trash_and_permanent_delete.sql` **setelah migrasi 014**. File ini hanya memasang fitur; **tidak menghapus campaign saat dieksekusi**.
3. Upload `index.html`, `src/v18_frontend.js`, `src/server/index.js`, `src/server/campaign.js` ke lokasi sesuai struktur repository. Pertahankan semua file lain yang sudah ada. Jangan unggah `node_modules`.
4. Pastikan GitHub Actions berhasil deploy, buka halaman GitHub Pages lalu hard-refresh.
5. Login sebagai Master untuk menguji menu Campaign. Tombol Edit Campaign masih dapat dipakai Master dan SPV; Hapus Campaign/Sampah hanya Master.

## Alur penggunaan
- **Edit Campaign**: ubah nama, tanggal, PIC, target per toko; rekam aktivitas/closing tetap terhubung.
- **Hapus Campaign**: pindahkan campaign ke Sampah. Tidak tampil di dashboard/toko, tetapi data tetap ada dan bisa dipulihkan.
- **Sampah / Pulihkan**: lihat jumlah data, target, audit; pulihkan campaign jika salah hapus.
- **Backup JSON**: unduh campaign, semua toko, record aktif+arsip, dan audit. Pastikan file JSON benar-benar tersimpan dan bisa dibuka.
- **Hapus Permanen**: centang pengakuan backup, ketik nama campaign persis, dan setujui konfirmasi kedua. SQL mensyaratkan role MASTER dan campaign sudah di Sampah; penghapusan baris dilakukan atomik dalam satu transaksi.
- **Bersihkan Foto Tersisa**: menghapus kandidat foto yang telah kehilangan seluruh referensi dari Campaign serta modul operasi lainnya. Izin hapus disiapkan sementara di server dan penghapusan fisik menggunakan Supabase Storage API. Jika gagal, antrean tetap bisa dicoba ulang.

## Data yang dibersihkan permanen
- dco.campaign_audit
- dco.campaign_records (prospek, aktivitas, action plan, order, monitoring termasuk yang diarsipkan)
- dco.campaign_stores (PIC/target toko)
- dco.campaigns (campaign utama)
- Menghasilkan satu baris jejak minimal di dco.campaign_purge_log (siapa, kapan, jumlah record), tanpa isi data operasional.

**PENTING:** Hapus Permanen tidak bisa dibatalkan setelah berhasil. Backup JSON tidak berisi **file gambar binary**; foto lama tetap perlu backup Storage terpisah apabila hendak disimpan. Foto yang masih dipakai laporan/modul lain tidak akan dibersihkan. Jangan klik Bersihkan Foto jika Anda belum mengamankan bukti yang diperlukan secara hukum/operasional.

## Klaim kapasitas database
Menghapus baris mengurangi isi tabel aktif dan query yang harus dibaca. PostgreSQL dapat menahan ruang disk fisik sampai VACUUM/maintenance dan reclaim. Jangan berasumsi angka kapasitas project Supabase langsung turun setelah DELETE. File foto Storage tidak berkurang sampai proses Bersihkan Foto berhasil.

## Status validasi
- Node syntax check: `src/server/index.js`, `src/server/campaign.js`, `src/v18_frontend.js` berhasil.
- Browser Chromium mock: 17 pemeriksaan desktop/HP/Store, termasuk backup, restore dan purge, lulus.
- Validasi live Supabase (RLS, SQL, Storage) **belum dilakukan** karena akses proyek produksi tidak tersedia di sesi ini. Uji pada staging terlebih dahulu, terutama SQL 015 dan backup/restore.
- Tidak ada proses penghapusan produksi yang dijalankan dalam pembuatan paket.

## Jika ada error
- `Could not find the function public.dco_campaign_*`: SQL 015 belum dijalankan pada project Supabase yang sedang dipakai.
- `Hanya Master`: login ulang sebagai akun dengan role MASTER.
- `Pindahkan ke Sampah terlebih dahulu`: langkah Sampah belum selesai.
- `Konfirmasi nama campaign tidak cocok`: ketik nama case-sensitive dengan spasi yang sama.
- `Foto belum terhapus`: ulangi tombol Bersihkan Foto, cek policy bucket `dco-foto` dan migrasi 006/008.
