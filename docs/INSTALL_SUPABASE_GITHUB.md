# Panduan Pemasangan v9 (Supabase + GitHub Pages)

Target: `https://tigalapancommercial-netizen.github.io/Daily-Commercial-Operation/`

## A. Supabase (± 5 menit)
1. Buka project Supabase → **SQL Editor** → **New query**.
2. Salin seluruh isi `supabase/migrations/20261112_006_dco_parity.sql` → **Run**. Harus selesai tanpa error
   (pesan NOTICE "already exists, skipping" normal bila dijalankan ulang — file ini aman dijalankan berkali-kali).
3. Cek pemasangan: jalankan `select public.dco_ping();` → harus muncul `"version": "v9"`, `"stores": 12`, `"users": 14`.
4. **Impor data lama** (Rekap Masalah 33 baris, Daily Routine, Checklist): buka file
   `JANGAN_UPLOAD_KE_GITHUB/20261112_007_import_data.sql` dari paket ZIP → salin → **Run**.
   Hasil akhir menampilkan jumlah baris per tabel (masalah 33, rutin 1, ceklis 1). Aman dijalankan ulang (tidak menggandakan).
5. Tidak perlu mengatur Supabase Auth / Site URL / Redirect URL — v9 memakai login username + PIN seperti Apps Script.
6. Pastikan **Project Settings → Data API → Exposed schemas** memuat `public` (bawaan Supabase).

> Migrasi v8 (`supabase/legacy_v8/`) tidak diperlukan. Bila sudah pernah dijalankan, biarkan saja — v9 memakai schema
> terpisah (`dco`), bucket terpisah (`dco-foto`) dan fungsi berawalan `dco_`, jadi tidak bentrok.

## B. GitHub Pages
1. Unggah isi folder `Daily-Commercial-Operation/` dari ZIP ke **root** repository (timpa file lama; hapus folder `src/` lama
   dulu agar file v8 `src/data.js`, `src/constants.js`, `src/styles.css` tidak tertinggal — tidak berbahaya, hanya tidak terpakai).
2. **Settings → Secrets and variables → Actions → New repository secret**:
   - `VITE_SUPABASE_URL` = Project URL (contoh `https://xxxx.supabase.co`)
   - `VITE_SUPABASE_PUBLISHABLE_KEY` = Publishable key (`sb_publishable_…`) atau anon key
   - (opsional) `VITE_GOOGLE_API_KEY` — hanya bila tombol "Sinkron Google Sheet Rekap Masalah" dipakai dan sheet sumber tidak dibagikan publik via link.
3. **Settings → Pages → Source: GitHub Actions**.
4. **Actions → Deploy … → Run workflow** (atau push ke `main`). Tunggu hijau, buka URL target.

## C. Login pertama & keamanan akun
1. Login `master` PIN `1234` → klik **Ganti PIN** (kiri bawah).
2. Pengaturan → **User**: ganti PIN `spv` dan ke-12 akun toko (`tk-btp`, `mamu-btp`, `mamu-palopo`, `tk-palu`, `mamu-tamalate`,
   `tk-manado`, `tk-samarinda`, `mamu-kendari`, `tk-polman`, `tk-bone`, `mamu-gowa`, `tk-toraja`). Saat PIN direset, sesi lama user tsb otomatis keluar.
3. Akun terkunci 10 menit setelah 5x PIN salah.

## D. Peralihan dari Apps Script (cutover)
Data di spreadsheet terus bertambah selama Apps Script masih dipakai. Saat hari peralihan:
1. Minta semua toko berhenti input di Apps Script.
2. Di spreadsheet DASHBOARD ASSIGNMENT: **File → Download → CSV** untuk tab MASALAH, TUGAS, RUTIN, CEKLIS, DSO, VISIT,
   VISIT_ISSUE, JADWAL, CONFIG (dan TOKO / FORM_DEF / VISIT_DEF bila diubah). Simpan semuanya di satu folder.
3. `python3 scripts/import_sheets.py folder_csv/ --overwrite` → hasilnya `supabase/data_import/20261112_007_import_data.sql` → jalankan di SQL Editor.
   (`--overwrite` = nilai spreadsheet menimpa baris dengan ID sama.)
4. Foto lama tersimpan di Google Drive dan tetap tampil (ID Drive dikenali aplikasi) selama file Drive dibagikan "siapa saja yang punya link".
5. Setelah toko memakai v9, Apps Script boleh dinonaktifkan (Deploy → Manage deployments → Archive).
6. Setelah peralihan selesai, matikan berbagi "siapa saja yang memiliki link" pada spreadsheet lama (DASHBOARD ASSIGNMENT & REKAP GLOBAL)
   karena repository GitHub Pages bersifat publik. Konsekuensinya tombol "Sinkron Google Sheet Rekap Masalah" tidak lagi dipakai (data sudah dipindah).

## E. Jika ada masalah
| Gejala | Penyebab / solusi |
|---|---|
| "Konfigurasi Supabase belum diisi" di halaman login | Secrets GitHub belum diisi / nama salah → isi lalu jalankan ulang workflow |
| "Database belum terpasang: jalankan file …006…" | SQL 006 belum dijalankan di project yang sama dengan URL di Secrets |
| "Gagal mengunggah foto" | Pastikan bagian STORAGE di SQL 006 berjalan (bucket `dco-foto` + 3 policy) |
| Halaman putih / 404 asset | Base path `vite.config.js` harus `/Daily-Commercial-Operation/` (sudah diatur di workflow) |
| Tombol Sinkron Rekap Masalah gagal | Sheet sumber harus "Siapa saja yang memiliki link: Viewer", atau isi `VITE_GOOGLE_API_KEY` |
| Backup sangat besar gagal | Pilih rentang tanggal lebih pendek (batas file 25 MB) |
