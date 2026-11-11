# Acceptance / Cutover Checklist

- [ ] Supabase staging project tersedia; 4 migrasi berhasil dan 12 toko terbaca.
- [ ] Supabase Auth dibuat untuk 1 Master, 1 SPV, minimal 2 Store yang berbeda.
- [ ] RLS: store A tidak bisa membaca/menulis store B via API langsung.
- [ ] Master/SPV melihat seluruh toko sesuai assignment; Store hanya tokonya.
- [ ] Briefing NIHIL dan issue multi-baris; submit ganda tidak menduplikasi issue.
- [ ] Checklist toggle, foto, validasi SPV, dan audit history.
- [ ] DSO foto wajib, submit, Approved/Rejected, dan revisi.
- [ ] Visit 15+ checkpoint, foto per checkpoint, issue dengan PIC/due date.
- [ ] Issue yang tidak sesuai muncul Pending Matter; selesai perlu validasi.
- [ ] Jadwal visit waktu WITA, export CSV per menu, filter, dashboard KPI.
- [ ] Rekonsiliasi CSV MASALAH/CEKLIS/DSO/VISIT/JADWAL/VISIT_ISSUE terhadap source.
- [ ] Semua foto lama yang dimigrasi tersedia lewat signed URL; peta ID telah diaplikasikan.
- [ ] Backup data & file diuji RESTORE pada project staging (bukan sekadar terunduh).
- [ ] Pengujian minimal 12 toko dan concurrent users; tidak ada error blocker.
- [ ] Bekukan sistem lama; jalankan impor akhir; verifikasi hitungan dan bukti.
- [ ] Deploy Vercel production setelah RLS dan test berhasil; simpan rollback plan.

Jika ada butir kritikal belum lulus, sistem lama tetap sumber utama dan aplikasi Supabase belum boleh dianggap go-live.
