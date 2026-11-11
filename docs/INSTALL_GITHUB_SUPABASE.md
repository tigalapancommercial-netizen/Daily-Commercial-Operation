# Instalasi penuh — Supabase + GitHub + Vercel (tanpa Apps Script)

## 0. Persyaratan
- Akun Supabase, GitHub, dan Vercel yang Anda kontrol.
- Node.js 20+ di komputer pengembang.
- Proyek Google Apps Script lama dan Google Sheets dibiarkan **read-only/backup** saat cutover.
- Dua proyek Supabase: **STAGING** terlebih dahulu, lalu **PRODUCTION** setelah semua uji diterima.

## 1. Buat Supabase
1. Buat project Supabase baru; catat **Project URL** dan **publishable key** (bukan secret/service-role key).
2. Di komputer: `npm install -g supabase` atau gunakan CLI sesuai panduan resmi (perhatikan kebutuhan versi Node); `supabase login`.
3. Di root repositori: `supabase link --project-ref ID_PROJECT_STAGING`.
4. **Untuk CLI v3**: `supabase db push --remote` (konfirmasi perubahan). Migrasi SQL dalam folder `supabase/migrations` dijalankan **urut berdasarkan nama**.
5. Pastikan 12 baris master toko, tabel `briefings`, `issues`, `visit_schedules`, `visits`, `visit_points`, `checklist_entries`, `dso_reports`, `assignments` dan bucket private `store-evidence` sudah terbentuk.
6. Supabase > Authentication > Users: buat akun operator secara individual menggunakan email. Setiap operator wajib punya password sendiri; jangan migrasikan PIN lama.
7. SQL Editor: kaitkan ID Auth ke `public.profiles` menggunakan SQL berikut (ganti UUID sesuai user yang telah dibuat):

```sql
insert into public.profiles(id,display_name,role,store_id,active)
values ('UUID_AUTH_USER','SPV Area','spv',null,true)
on conflict(id) do update set display_name=excluded.display_name,
 role=excluded.role, store_id=excluded.store_id, active=true;
```

Untuk petugas toko gunakan role `store` dan `store_id='m03'` (sesuaikan); Master menggunakan role `master`. Untuk SPV yang hanya boleh melihat toko tertentu, isi `public.spv_store_assignments(profile_id,store_id)`. **Secara default SPV tanpa assignment dapat melihat seluruh toko.**

## 2. GitHub
1. Buat repository **private** bernama misalnya `tigalapan-assignment-supabase`.
2. Upload seluruh isi paket ini **kecuali** `.env.local`, data CSV asli, backup produksi, foto sumber dan file kunci.
3. Jalankan `npm install`, `npm run build`, `npm run check` di komputer lokal jika internet tersedia.
4. Simpan migrasi di Git. Jangan commit URL bersama secret key, password DB atau password pengguna.

## 3. Deployment Vercel
1. Vercel > Add New Project > Import Git Repository.
2. Framework: **Vite**; build command `npm run build`; output directory `dist`.
3. Set environment variables untuk **Preview** dan **Production**:

```
VITE_SUPABASE_URL=https://PROJECT_REF.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
VITE_DEMO_MODE=false
```

4. Deploy. Anda akan melihat **login Supabase**, bukan PIN Google Apps Script.
5. Masuk dengan satu akun Master penguji dan akun Store penguji. Ketika data belum dimigrasi, angka dashboard harus 0 atau tidak ada data—bukan data simulasi.

## 4. Migrasi seluruh histori (sekali, tanpa Apps Script)
1. Di Spreadsheet lama `DASHBOARD ASSIGNMENT`, ekspor masing-masing tab: `MASALAH`, `RUTIN`, `CEKLIS`, `DSO`, `JADWAL`, `VISIT`, `VISIT_ISSUE` menjadi CSV UTF-8. Beri nama tepat `MASALAH.csv`, dst. ke folder lokal `legacy_exports/`.
2. **Jangan ekspor `USERS` berisi PIN**. Buat akun baru melalui Supabase Auth.
3. Periksa data dahulu:

```bash
python3 scripts/migrate_legacy.py --source legacy_exports
```

4. Untuk eksekusi, set `SUPABASE_URL` dan `SUPABASE_SECRET_KEY` pada **terminal pribadi**. Variabel tersebut tidak boleh berawalan `VITE_`, tidak boleh masuk Vercel frontend, dan tidak boleh tersimpan di Git.

```bash
python3 scripts/migrate_legacy.py --source legacy_exports --apply
```

5. Migrator memakai UUID deterministik agar **pengulangan impor tidak menggandakan record** (berdasar ID legacy). Tabel yang tidak ada CSV-nya dilewati. Periksa error dan jumlah per tabel sebelum lanjut.
6. Jika ada foto lama di Drive, unduh dengan akses sah ke folder lokal. Buat `photo_manifest.csv` dengan header `store_id,module,legacy_drive_id,local_file` dan jalankan:

```bash
python3 scripts/migrate_photos.py --manifest photo_manifest.csv --root legacy_photos
# Periksa output mapping, lalu:
python3 scripts/migrate_photos.py --manifest photo_manifest.csv --root legacy_photos --apply
```

**Perhatian:** alat upload foto menghasilkan peta ID Drive → path Supabase. Relasi foto lama pada `DSO`, `VISIT`, `CEKLIS` masih perlu dicocokkan dan diperbarui memakai peta ini. Jangan mematikan sistem lama sebelum seluruh foto bisa dibuka. Tidak ada impor otomatis folder Drive secara tersembunyi.

## 5. Verifikasi sebelum go-live
- Hitung rekonsiliasi data: total **33 MASALAH pada audit 11 Nov 2026** adalah baseline sementara, bukan jaminan data tetap 33. Hitung ulang pada jam cutover.
- Periksa tidak ada ID duplikat; bukti foto cocok; form DSO per tanggal lengkap; setiap point visit Tidak Sesuai punya Pending Matter.
- Uji akun `master`, `spv`, `store` pada dua browser: Store tidak dapat melihat data toko lain melalui REST langsung; Store tidak dapat memvalidasi dirinya; SPV dapat memvalidasi.
- Uji tanggal bisnis dan jam WITA terutama pergantian hari, 23:30, ekspor CSV, foto upload, checklist dan submit berulang.
- Lakukan load test di staging untuk jumlah data dan pengguna riil. Jangan membuat klaim "tanpa delay" tanpa metrik produksi.

## 6. Backup / rollback
1. Jalankan `python3 scripts/backup_supabase.py --out private_backups/snapshot-YYYYMMDD` dari komputer aman (butuh secret key hanya di terminal).
2. Set backup terjadwal melalui mekanisme resmi Supabase / layanan backup organisasi. **Jangan menghapus baris karena merasa backup pasti berhasil**; periksa checksum, jumlah record dan uji restore di staging.
3. Selama parallel run, sistem lama dibatasi read-only agar tidak muncul dua sumber data. Untuk rollback, aktifkan kembali sistem lama dari snapshot dan catat perubahan setelah cutover.
4. Tidak ada fitur hapus permanen otomatis pada paket ini. Ini disengaja sampai prosedur restore disetujui.

## 7. Menyelesaikan deployment
Perubahan kode di GitHub tidak otomatis membuat tabel di Supabase. Jalankan migrasi secara terpisah. Deploy ulang Vercel setiap kali environment variables berubah. Aktifkan email authentication Supabase sesuai kebijakan organisasi.

**Belum ada akses dalam percakapan ini untuk mendaftarkan user, memasang SQL ke project Supabase Anda, atau men-deploy repository GitHub Anda. Langkah-langkah tersebut harus dijalankan menggunakan akun Anda.**
