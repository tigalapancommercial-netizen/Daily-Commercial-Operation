# Daily Operation Commercial — Assignment Checklist Store (v9, Supabase)

Aplikasi ini adalah **pindahan 1:1** dari Apps Script v6/v7 (`Code.gs` + `Index.html`) ke **Supabase + GitHub Pages**.
Tampilan, menu, alur, rumus scorecard, SLA, notifikasi, role, dan pesan error **sama persis** dengan versi Apps Script,
karena UI referensi dipakai apa adanya (CSS/markup/script tidak diubah) dan seluruh fungsi server `Code.gs` dipindahkan
fungsi-per-fungsi ke JavaScript + fungsi database Supabase.

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
- `supabase/migrations/20261112_006_dco_parity.sql` — **satu-satunya SQL yang wajib dijalankan** (tabel, fungsi aman, storage, data awal).
- `supabase/legacy_v8/` — migrasi v8 lama (arsip; tidak dipakai aplikasi v9).
- `scripts/import_sheets.py` — membuat SQL impor data dari spreadsheet lama (CSV/JSON).
- `tests/` — uji database & uji end-to-end (138 skenario) dengan PostgreSQL lokal.
- `docs/` — panduan pemasangan, peta paritas, catatan reminder email.

## Mulai cepat
1. Supabase → SQL Editor → jalankan `supabase/migrations/20261112_006_dco_parity.sql`.
2. (Data lama) jalankan file `20261112_007_import_data.sql` yang dikirim terpisah (**jangan diunggah ke GitHub**).
3. GitHub → Settings → Secrets → Actions: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`.
4. Push ke `main` → workflow GitHub Pages membangun & menerbitkan.
5. Login `master` / `1234` → **segera Ganti PIN**, lalu ganti PIN semua user di Pengaturan → User.

Langkah lengkap: [docs/INSTALL_SUPABASE_GITHUB.md](docs/INSTALL_SUPABASE_GITHUB.md).

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
