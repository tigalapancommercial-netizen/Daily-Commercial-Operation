# Pemetaan data v7 → Supabase

| CSV Google Sheets lama | PostgreSQL baru | Kunci idempotent |
|---|---|---|
| `MASALAH.csv` | `issues` + `briefings` | `legacy_source_id`, UUID dari ID lama |
| `RUTIN.csv` | `checklist_templates` | `source_id` |
| `CEKLIS.csv` | `checklist_entries` | `source_id` |
| `DSO.csv` | `dso_reports` | `source_id` |
| `JADWAL.csv` | `visit_schedules` | `source_id` |
| `VISIT.csv` | `visits` + `visit_points` | `source_id` dan visit UUID |
| `VISIT_ISSUE.csv` | `issues` (origin=visit) | `legacy_source_id = VISIT-...` |
| `USERS.csv` | **TIDAK DIIMPOR** | Akun Supabase Auth dibuat ulang |

Nama toko disesuaikan pada 12 kode `t01...t12/m02...m11`; alias `TIGALAPANKAOS MAKASSAR` dianggap `TIGALAPANKAOS BTP` dan harus diverifikasi manual sebelum apply.

**Foto:** Drive ID tidak dapat dijadikan path Supabase Storage otomatis. Gunakan `migrate_photos.py` untuk membuat mapping berdasarkan manifest foto yang telah diekspor lalu rekonsiliasi referensi di tabel.

**Catatan:** pada tahap pemindahan data, jangan menulis dua arah sekaligus. Setelah cutover Supabase adalah satu-satunya sumber data operasional.
