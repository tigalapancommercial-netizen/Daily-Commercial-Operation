# Update v10 — Kamera, Foto Bukti Multi-file, dan Navigasi

## Apa yang berubah
- Menu: pengujian klik 9 menu utama untuk 3 lebar layar; click-through dari matriks kepatuhan toko menuju Assignment.
- Bukti Assignment: tombol **Foto langsung**, **Kamera HP**, dan **Dari galeri** selalu tampil pada setiap item; tidak lagi hanya di menu tiga titik.
- DSO, Visit Point, Issue Visit, Rekap Masalah, dan tindak lanjut issue: unggah beberapa foto terpisah per item, pratinjau thumbnail, tampilan penuh ketika diketuk, dan lepas satu foto tanpa menghapus foto lain.
- Kamera web: live preview, ganti kamera, ambil berulang kali dan simpan semua sekaligus; `getUserMedia` membutuhkan HTTPS, izin kamera, dan browser yang mendukung. Tersedia input **Kamera HP** (`capture=environment`) sebagai fallback native di perangkat seluler.
- Foto diperkecil menjadi sisi panjang maksimum 1600 px dan dikompres WebP adaptif (target sekitar 500 KB/foto, dapat lebih besar untuk gambar kompleks). Jika browser tidak mendukung WebP, dipakai JPEG. File yang disimpan di Supabase Storage tetap gambar, **bukan dokumen .html**; HTML aplikasi hanya menampilkan thumbnail/galeri.
- Foto lama dengan satu ID tetap didukung, foto baru yang berjumlah dua atau lebih dicatat sebagai array JSON berbentuk string di field foto terkait. Maksimum 30 foto/bukti.
- Foto pada formulir yang belum dikirim hanya menjadi **draft**. Tekan **Simpan/Kirim laporan** untuk mengaitkan bukti ke data form.

## Instalasi (tanpa Apps Script, langsung GitHub Pages + Supabase)
1. **Backup dulu**: unduh kode repository saat ini dan buat backup database Supabase. Jangan menghapus data lama.
2. Supabase > SQL Editor: jalankan `supabase/migrations/20261112_008_multiphoto.sql` **setelah** migrasi v9 `20261112_006_dco_parity.sql` berhasil. SQL 008 memperluas pemeriksaan ID foto dan perlindungan foto yang masih direferensikan. SQL ini tidak mengubah/menghapus baris historis.
3. Ekstrak **ZIP full** dan unggah isinya ke root repository `tigalapancommercial-netizen/Daily-Commercial-Operation` (pertahankan folder `.github/` tersembunyi). Atau gunakan **ZIP patch** untuk mengganti file yang tercantum di dalamnya.
4. Pada GitHub > Settings > Secrets and variables > Actions, pastikan `VITE_SUPABASE_URL` dan `VITE_SUPABASE_PUBLISHABLE_KEY` sudah ada. Jangan pernah menaruh service-role key atau password database di Vite.
5. GitHub > Actions > **Deploy Daily Operation Commercial (GitHub Pages)**. Pastikan langkah `Install dependencies`, `Build Vite application`, dan `Publish website` selesai sukses, lalu refresh website secara paksa (Ctrl+Shift+R).
6. Supabase > Authentication > URL Configuration: tambahkan alamat GitHub Pages sebagai URL yang diizinkan bila autentikasi memerlukan redirect. Camera live di GitHub Pages berjalan dalam HTTPS, tetapi tetap membutuhkan izin user.

## Pemeriksaan wajib setelah deploy
- Master / SPV / Store hanya melihat menu dan data sesuai role.
- Dashboard: pindah 5 tab (Overview, Kepatuhan, Action Plan, Visit & Issue, Scorecard); klik data toko di matriks membuka modul yang tepat.
- Assignment: tombol bukti foto terlihat tanpa membuka menu titik tiga; coba kamera langsung, Kamera HP, dan galeri dengan 2 foto, lalu refresh dan cek bukti masih ada.
- DSO/Visit: ambil 2 foto untuk satu point, kirim form, kemudian buka kembali riwayat dan perbesar setiap foto secara terpisah.
- Issue: foto, PIC, due date, dan status tetap tersimpan; uji validasi dan akses per role.
- Verifikasi backup/export sebelum membersihkan data. Jangan menghapus database/foto untuk pengujian.

## Laporan pengujian lokal
- `node scripts/check.mjs`: lolos pemeriksaan syntax dan relasi API.
- `python3 tests/v10_ui_smoke.py`: lulus 27 perpindahan menu pada lebar 390/768/1280 px, kelima tab dashboard, ketiga tampilan jadwal, Assignment visible evidence, galeri dua foto, simulasi kamera dua tangkapan, point visit, issue, dan tidak ada exception JavaScript yang tertangkap. Pengujian DSO juga memverifikasi bahwa dua foto terkirim sebagai daftar dalam payload submit.
- Foto tes adalah **data sintetis**, tidak ada perubahan data Supabase produksi.
- Pengujian build `npm run build` lokal tidak selesai karena dependensi Vite tidak dapat diunduh ke lingkungan pemeriksaan. GitHub Actions harus menunjukkan build sukses sebelum versi ini dianggap siap digunakan. Kamera fisik di ponsel, SQL migrasi, permission Storage, dan persistensi DB harus diuji pada staging.

## Rollback
Jika hasil deploy bermasalah, kembalikan commit GitHub sebelumnya dan jalankan workflow lagi. SQL 008 hanya menambah dukungan format foto; tidak perlu rollback database untuk mengembalikan antarmuka lama. Jangan melakukan restore database tanpa backup terverifikasi.
