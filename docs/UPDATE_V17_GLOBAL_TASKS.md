# Pembaruan v17 — Weekly/Monthly Reports + Tugas Global & Routine

**Target:** Daily-Commercial-Operation (GitHub Pages + Supabase), tanpa Google Apps Script.

## Apa yang ditambahkan

1. **Weekly & Monthly Reports:** Weekly Sales, Weekly Genset, Monthly Sales, Monthly APAR. Input untuk semua 12 toko; setiap akun Store hanya melaporkan data tokonya. Master/SPV dapat memfilter dan memvalidasi. Riwayat serta matriks kepatuhan per toko tersedia di Dashboard.
2. **Tugas Global & Routine:** membuat tugas operasional, periodik, campaign, kunjungan sekolah, project, administrasi atau jenis tugas bebas.
3. Pengaturan tugas: judul, instruksi, jenis pekerjaan, kategori/divisi, nama campaign/project, lokasi, output, PIC, prioritas, semua toko / toko terpilih, tanggal mulai, tanggal akhir, dan tenggat.
4. Jadwal: **Sekali** (hanya pada tanggal yang dipilih), **Rentang** (muncul setiap hari dalam rentang, dicentang per hari), **Harian**, **Mingguan**, **Periodik** (setiap N hari), **Bulanan**, **Tahunan**.
5. Tugas aktif otomatis tampil dalam **Assignment Checklist Store** sesuai tanggal dan toko. Foto Assignment tetap memakai tombol galeri ringkas dan otomatis mencentang item setelah unggahan benar-benar berhasil.
6. Tugas historis yang telah dicentang tidak hilang dari riwayat hari tersebut saat template diubah/dinonaktifkan/dihapus.

## Langkah instalasi ringkas

1. **Backup** database Supabase (termasuk `dco.rutin`, `dco.ceklis`) dan salin repository GitHub lama.
2. Buka **Supabase → SQL Editor**. Jika belum ada, jalankan `supabase/migrations/20261113_012_periodic_reports.sql` **lebih dulu**. Setelah itu jalankan `supabase/migrations/20261113_013_global_tasks.sql`.
3. Ekstrak ZIP patch. Unggah file ke repository `tigalapancommercial-netizen/Daily-Commercial-Operation` **sesuai struktur folder**, bukan file ZIP mentah. Commit ke branch yang dideploy.
4. **GitHub → Actions:** periksa workflow deploy Pages sukses. Hard refresh aplikasi / tutup-buka tab.
5. Login Master atau SPV, buka **Tugas Global & Routine → + Tugas baru**. Pilih jenis tugas, jadwal, PIC, target toko dan simpan.
6. Buka akun toko target → **Assignment Checklist** pada tanggal berlaku, lalu uji centang + foto + riwayat. Di dashboard Master, periksa portofolio Tugas Global serta Weekly/Monthly compliance.

## Contoh pengisian

| Kegiatan | Jenis | Jadwal | Penugasan |
| --- | --- | --- | --- |
| Story WA Focus Selling | Operasional | Harian | Seluruh toko |
| Follow-up vendor setiap 7 hari | Periodik | Periodik = 7 hari | Toko terpilih |
| Program Payday Sale | Campaign | Rentang 25–30 November | Seluruh toko |
| Visit SMK untuk penawaran PKS | Kunjungan Sekolah | Sekali = 20 November | PIC Sales, toko terpilih |
| Persiapan booth bazar | Project | Rentang / Sekali | PIC Project |

## Data & keamanan

- Tidak ada migrasi atau penghapusan file foto lama dalam paket ini. Form Weekly/Monthly tersedia untuk penginputan baru; 352 baris CSV historis sebelumnya **tidak diimpor ke Supabase oleh patch ini**.
- `013_global_tasks.sql` hanya menambahkan kolom dan indeks pada tabel lama, tidak berisi `DELETE`, `DROP TABLE`, atau perubahan hak akses berbahaya.
- Master / SPV dapat membuat template tugas. Store hanya mengakses item Assignment untuk tokonya melalui aturan yang sudah ada.
- WebP, timestamp, backup, arsip, serta before–after dari versi terdahulu dipertahankan; pemrosesan asli di Supabase tetap perlu diuji dengan kredensial produksi.
- Bila setelah klik Simpan muncul pesan **Migrasi database 013 belum diterapkan**, jalankan SQL 013 dan muat ulang aplikasi. Jangan ulangi unggah atau hapus data tanpa memeriksa hasilnya.

## Batas pengujian

Pengujian kode, jadwal, simulasi alur browser, upload otomatis Assignment, dan empat form periodik dilakukan **dengan data mock**, bukan dengan Supabase produksi. Build Vite penuh tidak berhasil diverifikasi karena instalasi dependency terhambat di lingkungan pengujian. GitHub Actions dan data production perlu diuji setelah deploy.
