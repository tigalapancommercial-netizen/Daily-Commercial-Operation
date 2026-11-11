# Assignment Control Center — Supabase Native

**Tidak menggunakan Google Apps Script sebagai backend maupun runtime.**

Aplikasi web modern PT Tigalapan Sukses Indonesia untuk 12 toko: Executive Dashboard, Kepatuhan Briefing, Rekap Masalah, Assignment Checklist, DSO, Jadwal Visit, Visit Check Point 15 poin, Pending Matter, Scorecard dan Pengaturan.

## Stack
- Frontend: Vite + ES Modules + responsive CSS, cocok untuk Vercel.
- Backend: Supabase Auth, PostgreSQL + RLS, private Supabase Storage, SQL RPC untuk bundel input briefing dan visit atomik.
- GitHub: version control; bukan database.
- Tanggal bisnis WITA / Asia-Makassar. Timestamp database tersimpan dalam UTC.

## Mulai

```bash
npm install
cp .env.example .env.local
# Isi URL + Supabase publishable key di .env.local (jangan commit file ini)
npm run dev
```

`npm run build` menghasilkan `dist` untuk Vercel. `npm run check` menjalankan pemeriksaan kode dan uji importer.

## Database
Urutan migrasi `20261111_001_initial.sql`, `20261111_002_full_operations.sql`, `20261111_003_security_and_briefing.sql`, `20261111_004_integrity.sql`. Jalankan di Supabase **staging** dan uji RLS sebelum production.

## Migrasi data dari v7
- `scripts/migrate_legacy.py` mengimpor CSV tab spreadsheet lama; **dry run adalah default**.
- `scripts/migrate_photos.py` mengunggah foto yang telah diekspor ke private Supabase Storage serta menghasilkan daftar pemetaan; tautan foto lama perlu diverifikasi.
- `scripts/backup_supabase.py` membuat snapshot data JSON beserta checksum, **tanpa menghapus data**.
- `USERS`/PIN lama tidak diekspor; akun diprovisikan ulang menggunakan Supabase Auth.

## Keamanan
Tidak menyimpan `service_role`/secret di web atau GitHub. Pengguna store hanya boleh melihat/mengubah toko yang diizinkan; validasi SPV/Master dijaga di server. Backup dan kunci rahasia hanya dijalankan pada komputer/admin server yang aman.

## Status
**Paket sumber aplikasi siap dipasang di staging; belum terkoneksi/deploy ke akun Supabase atau GitHub pengguna.** Pengujian sintaks dan importer lokal tidak menggantikan pengujian database RLS, akses foto, serta cutover produksi. Jangan matikan Apps Script lama sebelum checklist penerimaan selesai.

**Tutorial pemasangan terperinci:** [docs/INSTALL_GITHUB_SUPABASE.md](docs/INSTALL_GITHUB_SUPABASE.md).
