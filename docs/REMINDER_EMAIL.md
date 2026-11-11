# Reminder Email Otomatis

Di Apps Script, fungsi `kirimReminder` dikirim lewat `MailApp` jam 09:00 & 16:00 (dipasang dengan `pasangTriggerReminder`).
Supabase tidak punya layanan kirim email bawaan untuk aplikasi, sehingga fitur ini **belum disertakan di v9**.

Yang tetap berjalan sama persis: ikon 🔔 di aplikasi (Store, SPV, Master) dengan isi dan aturan yang sama seperti email
(DSO belum dikirim lewat batas, DSO ditolak, checklist belum dicentang, belum lapor briefing, masalah lewat due date, jadwal visit).

Bila email tetap dibutuhkan, cara yang disarankan:
1. Buat akun penyedia email (mis. Resend) dan simpan API key-nya sebagai **Supabase Edge Function secret** (bukan di GitHub / `VITE_*`).
2. Buat Edge Function yang menghitung daftar tertunda per toko (logika `pendingToko_` di `src/server/report.js`) dan mengirim email ke kolom Email user.
3. Jadwalkan dengan `pg_cron` + `pg_net` di Supabase jam 01:00 & 08:00 UTC (= 09:00 & 16:00 WITA).
