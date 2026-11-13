# Update v12 — Foto Before / After Visit & Issue

## Ringkasan perubahan
- **Visiting Check Point (A–E):** setiap item tetap memakai satu tombol foto yang membuka galeri (kamera live, kamera HP, atau galeri). Tabel riwayat menampilkan nama singkat A–E: **A Finance · B Aset/GA · C Merchandise · D SDM · E Gudang**.
- **Issue pada form Visit:** satu tombol **Before / After**. Galeri terbagi menjadi **SEBELUM (kondisi awal)** dan **SESUDAH (hasil perbaikan)**. Masing-masing dapat menyimpan hingga 30 foto, terpisah dan dikompres WebP sebelum upload. Pilih bagian foto sebelum mengambil/memilih foto baru.
- **Tab Issue Visit/Pending Matter:** tombol **Update** berisi galeri Before/After dan **Catatan hasil perbaikan**. Perbandingan thumbnail juga terlihat dalam tabel issue.
- **Update temuan per seksi A–E:** kini tersedia tombol **Foto hasil update** di bawah catatan update seksi untuk visit yang sudah tersimpan.
- **Data lama:** foto awal (`foto_id`) dipertahankan; foto hasil tindakan ditaruh di kolom baru (`foto_after`). Kolom catatan hasil perbaikan baru bernama (`update_note`). Tidak ada baris/kolom historis yang dihapus.

## Instalasi GitHub Pages + Supabase (tanpa Apps Script)
1. **Backup** repository serta database Supabase sebelum perubahan. Gunakan branch uji/staging jika memungkinkan.
2. Buka **Supabase → SQL Editor** pada proyek yang benar. Pastikan `supabase/migrations/20261112_006_dco_parity.sql` dan `supabase/migrations/20261112_008_multiphoto.sql` telah dijalankan. Selanjutnya jalankan **`supabase/migrations/20261112_009_visit_before_after.sql`** satu kali. SQL ini menambahkan dua kolom dan memperluas proteksi foto yang masih direferensikan.
3. Di GitHub repository **`tigalapancommercial-netizen/Daily-Commercial-Operation`**, unggah isi ZIP patch ke root repository **dengan folder yang sama**, termasuk `src/server/core.js`, `src/server/util.js`, `index.html`, dan `scripts`. Jangan mengunggah foto customer, data export, `.env` atau kunci rahasia.
4. Commit, buka **GitHub → Actions**, pastikan workflow Pages sukses (Build + Deploy) lalu refresh aplikasi (`Ctrl+Shift+R`).
5. Coba login dengan akun Master/SPV. Pilih **Visiting Check Point → Edit Visit**, pilih **Issue**, buka **Before / After**, unggah foto terbaru di tab **Sesudah**, isi catatan perbaikan dan **Simpan Visit**. Bisa juga lewat **Issue Visit → Update → Before / After → Simpan**.
6. Buka ulang issue, pastikan foto awal dan hasil update masih terlihat dan dapat diperbesar. Uji juga dengan telepon (HTTPS + izin kamera), lalu verifikasi kontrol akses SPV dan Master serta backup/export.

## Aturan foto
- Maksimal **30 foto di setiap kelompok**; jumlah sebelum/sesudah independen.
- Foto menjadi WebP adaptif (JPEG jika WebP tidak tersedia), sisi terpanjang 1.600 px, target kompresi ~500 KB per foto, sesuai kompleksitas gambar.
- Foto tersimpan sebagai file gambar di Supabase Storage, bukan HTML. Aplikasi menampilkan galeri HTML agar cepat diakses.
- Sebelum disimpan form, unggahan di modal merupakan *draft yang sudah ada di Storage*, belum terhubung secara permanen ke laporan. Tekan **Simpan** agar relasinya tercatat.
- Pemisahan `foto_id` (awal) dan `foto_after` (sesudah) memungkinkan foto lama tidak tertimpa. Jika issue baru terhubung ke suatu point Visit, sistem mencoba menggunakan foto point itu sebagai kondisi awal.
- Jika point/issue tervalidasi, akses ubah mengikuti kebijakan role lama (SPV tidak boleh mengubah issue tervalidasi; Master dapat mengoreksi).

## Peringatan pengujian
- `npm run check`: pemeriksaan sintaks, RPC dan fungsi UI lokal.
- `python3 tests/v11_compact_smoke.py`: interaksi menu, header A–E, satu kontrol foto per item.
- `python3 tests/v12_before_after_smoke.py`: **39 pemeriksaan** (3 viewport x 13) termasuk foto sebelum/sesudah, foto seksi update, WebP, form submission simulasi, dan status modal.
- Foto dan server pada tes browser adalah simulasi; belum berarti SQL migration atau Supabase Storage produksi sudah diuji. Uji staging terlebih dahulu.
- Jika migrasi `009` belum terpasang, penyimpanan `foto_after` akan ditolak. Jangan gunakan aplikasi versi ini untuk menulis data sebelum SQL siap.

## Rollback
- Kembalikan commit GitHub sebelumnya bila terjadi masalah. Kolom `foto_after` dan `update_note` dibiarkan ada (aman dan tidak merusak data lama). Jangan melakukan penghapusan kolom/restore tanpa backup yang telah diverifikasi.
