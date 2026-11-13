# v17 — General Task Management + Periodic Report Integration

- `src/server/core.js`: add validated general-task fields and Once / Date-range schedules, historical checklist preservation.
- `supabase/migrations/20261113_013_global_tasks.sql`: additive columns on `dco.rutin` (type, project, location, expected output, end date, deadline), no deletion.
- `index.html`: universal task creation UI, compact task table/filters, Assignment task metadata, executive task portfolio; Weekly/Monthly form navigation and tracking.
- `src/server/period.js`, `src/server/index.js` and SQL 012: four new weekly/monthly reports, validation, store-scope visibility and tracking.
- UI fix: choosing 'Ada Genset' now displays 8 inspection items immediately (previously required manual reload).
- No photo CSV historical import, no database mutations executed in user Supabase.
