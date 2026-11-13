# Daily Commercial Operation — v17 (Supabase native)

Web app for PT Tigalapan Sukses Indonesia, 12 stores. GitHub Pages hosts frontend; Supabase PostgreSQL and Storage handle data/photos. No Google Apps Script runtime.

## Instalasi

Lihat **[docs/UPDATE_V17_GLOBAL_TASKS.md](docs/UPDATE_V17_GLOBAL_TASKS.md)** untuk langkah sederhana. Jika memakai patch dari v15, jalankan migrasi SQL `012_periodic_reports.sql` lalu `013_global_tasks.sql` di Supabase, dan unggah source patch sesuai path ke GitHub.

## Modul

Executive Dashboard, Assignment Checklist Store, Daily Store Operation, Weekly/Monthly Reporting, Rekap Masalah, Jadwal Visit, Visiting Check Point, Pending Matter, Tugas Global & Routine, Pengaturan, Export/Backup/Arsip.

## Uji lokal

```bash
npm ci
npm run check
npm run build
node tests/v17_routine_schedule.mjs
python3 tests/v17_global_tasks_smoke.py
python3 tests/v17_period_smoke.py
```

Jangan unggah environment secrets, foto atau CSV historis ke repository publik. Tidak ada klaim build produksi atau penyalinan data produksi yang telah dilaksanakan.
