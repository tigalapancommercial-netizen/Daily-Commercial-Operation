# Tigalapan — Export CSV, Kompres Foto, Arsip & Bersihkan Database (v8)

## Status: **paket kode / migrasi, belum terpasang di Supabase produksi**

Paket ini dibuat dari versi `Daily_Commercial_Operation_Login_Fix_Full`, lalu ditambahkan fitur pemeliharaan. Perbaikan ini **bukan bukti** bahwa migrasi semua form 1:1 dari aplikasi Google Apps Script lama sudah selesai. Seluruh data aktif pada project lama harus tetap dipertahankan hingga uji rekonsiliasi dan restore selesai.

## Apa yang tersedia

1. **Export CSV di tiap menu**. CSV untuk Issue, Pending Matter, Kepatuhan, Checklist, DSO, Jadwal, Visit, Assignment, dan Template diambil **langsung dari Supabase per halaman (500 baris)**, bukan dari hanya data yang sedang ada di memori/dashboard. Data JSON seperti jawaban foto DSO ikut diekspor sebagai JSON teks. Kolom rahasia seperti password/token tidak diekspor.
2. Menu khusus **Master: Export & Penyimpanan**. Dapat mengekspor satu dataset dengan filter toko/tanggal atau backup seluruh dataset sebagai **JSONL** (gzip jika browser mendukung), termasuk konfigurasi, akun role/profil dan audit log (bukan password, PIN dan bukan file foto biner).
3. **Foto baru dikompresi di browser** menjadi WebP (sisi terpanjang maksimal 1600px; sasaran 450KB tetapi ukuran akhir bergantung foto). Diupload ke private Supabase Storage. Di aplikasi foto tampil pada lightbox HTML dengan URL signed. Foto lama **tidak otomatis dikonversi**.
4. **Preview arsip**, hanya Master. Maksimal 2000 baris per batch, dan hanya baris yang berumur minimal **90 hari** serta memiliki status final + validasi sesuai tabel. Tidak bisa mengarsip data open/pending. Tabel briefing, visit, visit point, master, profil, dan audit tidak dihapus karena relasi/histori.
5. **Arsip transaksional di database**: salin snapshot lengkap baris ke `private.maintenance_rows`, cek jumlah, hitung SHA256, hapus dari tabel aktif dalam satu transaksi; jika satu langkah gagal, transaksi rollback.
6. **Unduh arsip JSONL** disertai verifikasi SHA256 di browser. **Hapus arsip permanen** baru diizinkan setelah 24 jam, telah diverifikasi/diunduh pada browser saat ini, dan Master mengetik konfirmasi dua tahap. SQL mengulang verifikasi checksum tepat sebelum menghapus.
7. **Statistik penyimpanan**: total baris aktif, arsip, estimasi ukuran tabel, dan ukuran foto pada bucket.

## Cara memasang lewat GitHub Pages + Supabase

1. **Backup dulu** database dan foto. Simpan backup terpisah dari Supabase yang sama (mis. drive organisasi terenkripsi). Jangan gunakan alat Hapus sebelum memulihkan backup di staging.
2. Upload **isi proyek** ini ke repository GitHub `tigalapancommercial-netizen/Daily-Commercial-Operation`. Pastikan branch `main` dan folder `.github/workflows/deploy.yml` ada. Jangan upload `.env.local`, password atau file foto sumber.
3. Supabase Dashboard > **SQL Editor**: jalankan file `supabase/migrations/20261111_005_storage_maintenance.sql` **setelah migrasi 001–004**. (Jika migrasi 001–004 belum dipasang, jalankan berurutan dahulu di staging.) File ini hanya membuat fungsi dan tabel; **tidak menghapus baris dengan sendirinya**.
4. GitHub > `Settings > Secrets and variables > Actions`: konfigurasi `VITE_SUPABASE_URL` dan `VITE_SUPABASE_PUBLISHABLE_KEY`. `Settings > Pages` → **GitHub Actions**. Setelah push, lihat tab Actions sampai build sukses.
5. Login sebagai **Master**. Lihat menu **Export & Penyimpanan**. Mulai dari CSV dan tombol Preview (jangan jalankan arsip terlebih dulu). Login SPV/Store untuk memastikan **menu hapus tidak tersedia** dan export hanya menampilkan data sesuai RLS.
6. Uji lengkap di staging: export semua, checksum file arsip, restore sampel dari JSONL, baru pertimbangkan arsip produksi. Setelah penghapusan permanen, ukuran PostgreSQL yang dialokasikan belum tentu langsung mengecil; vacuum/autovacuum dan kebijakan penyimpanan Supabase menentukan pemakaian disk sebenarnya.

## Ketentuan keamanan & cakupan

- Tidak ada perintah Hapus Otomatis. Semua penghapusan memerlukan Master dan konfirmasi eksplisit.
- Backup JSONL/CSV berisi **path** foto, tetapi bukan **byte** foto. Backup foto dari bucket `store-evidence` **secara terpisah**, lalu uji pemulihan beberapa foto. Penghapusan foto yang dianggap orphan **belum diaktifkan**; penghapusan otomatis berisiko memutus bukti visit/issue/DSO.
- Arsip dalam database masih memakai kapasitas DB sampai dipurge. Backup file sebaiknya disimpan **di luar** Supabase untuk mitigasi insiden pada satu provider.
- Relasi visit, briefing, dan referensi item yang masih aktif dilindungi: tidak disertakan dalam pilihan pembersihan.
- Error akses/SQL akan muncul bila migration 005 belum dijalankan atau akun bukan Master.
- Pengujian lokal **tidak menggantikan** uji pada Auth, RLS, Storage, PostgreSQL, dan GitHub Pages produksi.

## Alur singkat

**Export penuh → Backup eksternal → Preview → Arsip → Download arsip & verifikasi SHA256 → Uji restore → (setelah 24 jam) Hapus arsip permanen**

### Dataset yang boleh diarsip

| Dataset | Syarat | Tanggal cutoff |
|---|---|---|
| `issues` | Selesai dan sudah diverifikasi SPV | closed_at/updated_at |
| `checklist_entries` | Selesai dan sudah divalidasi | check_date |
| `dso_reports` | Approved dan sudah divalidasi | report_date |
| `visit_schedules` | Selesai atau Batal | visit_date |
| `assignments` | Selesai, progress = 100 | due_date |

**Penting:** Seluruh database masih harus direkonsiliasi terhadap snapshot Google Sheets lama dan file foto. Paket ini menambahkan pengendalian data; tidak memindahkan data live ke Supabase tanpa koneksi proyek yang sah.
