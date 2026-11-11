# Peta Paritas Code.gs v6 → v9

Setiap aksi `api(action, …)` di Code.gs punya padanan dengan nama, parameter, hasil, dan pesan error yang sama.

| Aksi | Code.gs | v9 (JS) | Penegakan di database |
|---|---|---|---|
| login | `login_` | `server/index.js login_` | `dco_login` (bcrypt, kunci 5x salah) |
| meta | `meta_` | `core.js meta_` | `dco_rows` TOKO/CONFIG/FORM_DEF/VISIT_DEF/USERS (tanpa PIN) |
| list | `list_` | `core.js list_` | `dco_rows` (STORE hanya tokonya; VISIT/VISIT_ISSUE khusus SPV/Master) |
| add / update / bulk | `add_` `update_` `bulk_` | `core.js` | `dco_save` / `dco_delete` (kolom STORE_EDIT, kunci data tervalidasi) |
| ceklisHari / ceklisSet | idem | `core.js` | `dco_save` CEKLIS (STORE: hari ini/kemarin, jam centang = jam server) |
| rutinSave / rutinHapus | idem | `core.js` | SPV/Master |
| dsoHari / dsoSubmit / dsoValidasi / dsoPatch / dsoHapus | idem | `core.js` | `dco_dso_submit` (SLA kirim jam server), `dco_dso_validate` (SLA validasi), `dco_dso_patch` |
| visitSave / visitValidasi / visitHapus | idem | `core.js` (skor, rating, isoWeek, issue wajib) | VISIT approved terkunci; approve khusus Master; hapus diblok bila issue open |
| issueList / issueUpdate | idem | `core.js` | VISIT_ISSUE khusus SPV/Master; tervalidasi → khusus Master |
| jadwalSave / jadwalHapus | idem | `core.js` | hanya PIC pembuat atau Master |
| tracking / notif / storeSummary / exportData | idem | `report.js` (rumus sama persis) | data dibaca sesuai role |
| uploadFoto / fotoB64 | Drive | Supabase Storage (tiket upload 20 menit) | policy storage `dco_foto_*` |
| cfgSave / defSave / defHapus / addToko / tokoSave | idem | `admin.js` | khusus Master |
| userSave / hapusUser / gantiPin | idem | `admin.js` | `dco_user_save`, `dco_user_delete`, `dco_change_pin` (+ cabut sesi) |
| archivePreview / backup / backupList / wipe | Drive Sheet | `admin.js` + file .xlsx | `dco_archive_*`, `dco_backup_*` (hapus atomik + verifikasi jumlah) |
| syncMasalah | SpreadsheetApp | `admin.js` (baca sheet sumber via link publik / API key) | `dco_save` (data hasil edit di aplikasi tidak ditimpa) |

## Perbedaan yang disengaja (tidak mengubah tampilan / alur)
1. **Backup**: dulu Google Sheet di folder Drive; sekarang file Excel `.xlsx` (tab INFO + 1 tab per jenis data, header sama) yang disimpan
   di Supabase, langsung terunduh, dan bisa diunduh ulang dari "Daftar backup". Verifikasi jumlah baris + ID awal/akhir + checksum dilakukan
   **sebelum** data aktif dihapus (mode arsip).
2. **Foto**: dulu file Drive; sekarang Supabase Storage. Foto lama (ID Drive) tetap tampil lewat thumbnail Drive.
3. **Keamanan**: token sesi acak (dulu base64 username|PIN di browser), PIN di-hash, kunci akun 5x salah, logout mencabut sesi di server.
4. **Bug v6 diperbaiki**: edit riwayat Checklist (aksi `update` tipe CEKLIS) sebelumnya ditolak "Tipe edit tidak diizinkan" — kini diizinkan
   dengan aturan kolom STORE yang sama.
5. **Reminder email terjadwal** (`pasangTriggerReminder`/`kirimReminder`) belum disertakan — lihat `REMINDER_EMAIL.md`.
   Notifikasi 🔔 dalam aplikasi (isi & logika sama) tetap berjalan.
6. Teks yang menyebut "Google Drive / Apps Script" pada kartu Backup & Reminder disesuaikan (9 patch di `scripts/build_index.py`).

## Perubahan v9.1 (permintaan 12 Nov 2026)
1. **Menu per role**: STORE hanya *Assignment Checklist Store*, *Daily Store Operation*, *Rekap Masalah* (langsung membuka Checklist;
   menu lain dialihkan). SPV: semua menu kecuali Pengaturan. Master: semua menu.
2. **Halaman login baru**: panel brand bergradien + kartu login (jam WITA & sapaan otomatis, ikon, tombol lihat PIN, indikator memuat,
   username terakhir diingat). Responsif untuk HP.
3. **Dashboard**: banner "Executive Control Center" dihapus. Tanggal pantau tetap tersedia di tab *02 · Kepatuhan*.
4. **Visiting Check Point**: foto per seksi ("Foto kolase maks 4") dihapus; kolom *Catatan [seksi]* dibuat selebar form (kotak teks).
   Foto bukti per poin (📷 di tiap baris) tetap ada.
