# Arsitektur Supabase Native

## Runtime produksi (tanpa Google Apps Script)
- Browser → frontend Vite (Vercel) → Supabase JS client → Supabase Auth/PostgREST/PostgreSQL/Storage.
- SQL functions `submit_briefing_bundle` dan `submit_visit_bundle` menyimpan data terkait secara atomik.
- PostgreSQL RLS membatasi akses Master/SPV/Store. Foto disimpan dalam bucket private, dibaca via signed URL.
- Data contoh hanya aktif jika `VITE_DEMO_MODE=true`. Pada production `false`; jika belum terkoneksi, aplikasi meminta konfigurasi/login.

## Entitas
`stores`, `profiles`, `spv_store_assignments`, `briefings`, `issues`, `visit_schedules`, `visits`, `visit_points`, `visit_templates`, `checklist_templates`, `checklist_entries`, `dso_form_points`, `dso_reports`, `assignments`, `app_settings`, `audit_events`.

## Role
- **Master:** semua toko, master template dan laporan.
- **SPV:** semua toko jika tanpa assignment khusus; jika ada assignment hanya toko terkait; dapat validasi dan submit visit.
- **Store:** hanya store_id yang tercantum dalam profile; input briefing, checklist, issue dan DSO tokonya; tidak memvalidasi.

## Masih harus diterima sebelum cutover produksi
- Test nyata migrasi skema SQL dan RLS dengan 3 akun terpisah di Supabase staging.
- Migration semua histori dan foto: CSV + storage manifest + rekonsiliasi.
- Uji backup/restore dari snapshot; **tidak ada tombol hapus permanen otomatis**.
- Uji end-to-end pada browser yang punya akses jaringan Supabase dan test beban sesuai kebutuhan perusahaan.
- Setelah lulus, atur sistem lama read-only lalu putus alur Apps Script.

Google Sheets/Apps Script bukan dependensi runtime baru; hanya bahan migrasi sekali dan opsi rollback historis.
