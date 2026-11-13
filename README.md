# Patch DCO v19 — Hapus Permanen Campaign

Patch aplikasi **v18**. Menambahkan tombol Edit Campaign yang jelas, Hapus ke Sampah, Pulihkan, Backup JSON lengkap, Hapus Permanen khusus Master, dan pembersihan foto yatim melalui Storage API dengan pengamanan referensi.

Baca `docs/PANDUAN_V19_CAMPAIGN_HAPUS_PERMANEN.md` sebelum memasang. Untuk keamanan, backup terlebih dahulu dan lakukan uji staging.

File runtime yang berubah: `index.html`, `src/v18_frontend.js`, `src/server/index.js`, `src/server/campaign.js`. Database tambahan: `supabase/migrations/20261113_015_campaign_trash_and_permanent_delete.sql`.

Migrasi SQL ini **tidak menghapus data apa pun ketika dijalankan**; fungsi Hapus Permanen hanya bekerja setelah aksi eksplisit Master pada UI dan konfirmasi ketat.
