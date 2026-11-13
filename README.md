# v14: Auto-check Assignment setelah upload foto

Fitur baru: unggah bukti foto pada Assignment Checklist otomatis menyimpan status **Selesai** setelah server mengonfirmasi foto dan status. Jika gagal, tidak ada centang palsu. Panduan: `docs/UPDATE_V14_ASSIGNMENT_AUTO.md`.

# **Update v13**

Perbaikan DSO submit multi-foto, live watermark WITA, dan receipt server. Lihat `docs/UPDATE_V13_DSO_TIMESTAMP.md`. **Jalankan SQL 010 sebelum deploy frontend.**

---

# Daily Operation Commercial — Assignment Checklist Store (v12, Supabase)

Aplikasi ini menggunakan **struktur/paritas UI v7 sebagai baseline** dari Apps Script v6/v7 (`Code.gs` + `Index.html`) ke **Supabase + GitHub Pages**.
Fungsi asal diadaptasi ke Supabase (tidak membutuhkan Apps Script). Kesesuaian setiap alur produksi perlu diuji dengan pengguna nyata.
Update v12 mempertahankan perapian v11 (satu tombol foto per item; nama seksi A–E), sekaligus menambahkan galeri **Before/After**, foto hasil update visit dan catatan perbaikan di Issue Visit. Kamera langsung/HP dan kompresi multi-foto WebP tetap tersedia.

| Bagian | Apps Script v6/v7 | v9 (repo ini) |
|---|---|---|
| Tampilan | `Index.html` | `index.html` = `legacy/Index.reference.html` + patch (lihat `scripts/build_index.py`); v9.1: menu per role, login baru, lihat `docs/PARITAS_APPS_SCRIPT.md` |
| Server | `Code.gs` (`api(action,p,token)`) | `src/server/*.js` (port fungsi-per-fungsi) + RPC `dco_*` di Postgres |
| Database | Tab spreadsheet | Schema `dco` (tabel = tab, kolom = kolom) |
| Foto | Folder Drive | Supabase Storage bucket `dco-foto` (foto dikompres di HP seperti sebelumnya) |
| Backup | Google Sheet di Drive | File Excel `.xlsx` disimpan di Supabase + langsung terunduh |
| Login | username + PIN (PIN teks biasa di sheet) | username + PIN (**hash bcrypt**), sesi token 30 hari, kunci 10 menit setelah 5x salah |

## Isi folder
- `index.html` — UI referensi + jembatan `google.script.run` → Supabase.
- `src/` — `main.js` (pemasang), `db.js` (Supabase RPC & Storage), `xlsx.js` (file backup), `server/` (port Code.gs).
- `supabase/migrations/20261112_006_dco_parity.sql` — **SQL dasar v9** (tabel, fungsi aman, storage, data awal).
- `supabase/legacy_v8/` — migrasi v8 lama (arsip; tidak dipakai aplikasi v9).
- `scripts/import_sheets.py` — membuat SQL impor data dari spreadsheet lama (CSV/JSON).
- `tests/` — uji database & uji end-to-end (138 skenario) dengan PostgreSQL lokal.
- `docs/` — panduan pemasangan, peta paritas, catatan reminder email.

## Mulai cepat
1. Supabase → SQL Editor → jalankan `supabase/migrations/20261112_006_dco_parity.sql`, kemudian `supabase/migrations/20261112_008_multiphoto.sql` untuk mendukung banyak foto, kemudian `supabase/migrations/20261112_009_visit_before_after.sql` untuk dokumentasi foto update.
2. (Data lama) jalankan file `20261112_007_import_data.sql` yang dikirim terpisah (**jangan diunggah ke GitHub**).
3. GitHub → Settings → Secrets → Actions: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`.
4. Push ke `main` → workflow GitHub Pages membangun & menerbitkan.
5. Login `master` / `1234` → **segera Ganti PIN**, lalu ganti PIN semua user di Pengaturan → User.

Langkah lengkap: [docs/INSTALL_SUPABASE_GITHUB.md](docs/INSTALL_SUPABASE_GITHUB.md). Untuk perubahan terbaru, baca [docs/UPDATE_V12_BEFORE_AFTER.md](docs/UPDATE_V12_BEFORE_AFTER.md), [docs/UPDATE_V11_UI_RINGKAS.md](docs/UPDATE_V11_UI_RINGKAS.md) dan [docs/UPDATE_V10_KAMERA_NAVIGASI.md](docs/UPDATE_V10_KAMERA_NAVIGASI.md).

## Pengembangan lokal
```bash
npm install
cp .env.example .env.local   # isi URL + publishable key
npm run dev
npm run check                # pemeriksaan statis
npm run test:db              # uji migrasi SQL (butuh PostgreSQL lokal)
npm run test:e2e             # uji end-to-end (butuh PostgreSQL + Chrome + Playwright)
```

## Keamanan
- Hanya **publishable/anon key** di frontend. Jangan pernah memasukkan `service_role`, secret key, atau password database ke variabel `VITE_*` atau GitHub.
- Tabel schema `dco` tidak bisa diakses langsung dari API; semua akses lewat fungsi `dco_*` yang memeriksa sesi dan role di server
  (STORE hanya tokonya & kolom yang diizinkan, data tervalidasi terkunci, SLA dihitung jam server WITA).
- PIN disimpan sebagai hash bcrypt; PIN tidak pernah dikirim balik ke aplikasi / export.
