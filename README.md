# Tigalapan Daily Commercial Operation (DCO) v26 — Paket integrasi UI

## Apa yang diperbaiki
- Kartu profil sidebar (nama pengguna dan role) dibuat proporsional/responsif.
- Bilah mengambang `0 draft · 0 foto` / `Draft` / `Foto` disembunyikan, sehingga tidak menutupi form atau tabel.
- **Tidak mematikan** autosave IndexedDB versi v25, tetapi **belum mengubah** kode auto-restore draft maupun unggahan foto ke Supabase.

## Mengapa tidak ada `index.html` produksi dalam ZIP ini?
Source `index.html` aplikasi asli tidak berhasil diakses di sesi pembuatan. Mengganti dengan HTML buatan ulang akan **menghilangkan menu dan fungsi yang ada**. Karena itu, paket ini berisi *pembuat* `index.html` lengkap dari **file asli** Anda, bukan file placeholder yang tidak bisa dipakai.

### Cara termudah — tanpa coding
1. Ekstrak ZIP dan buka `installer.html` dengan Chrome/Edge.
2. Pilih file **`index.html` asli** dari repository `tigalapancommercial-netizen/Daily-Commercial-Operation` di komputer.
3. Klik **Unduh index.html lengkap (v26)**.
4. Di GitHub, backup file root `index.html` dan ganti dengan file yang baru diunduh.
5. Tambahkan `public/dco-v26-ui-hotfix.js` di folder `public/`.
6. Commit; uji build dan aplikasi setelah deploy. **Jangan mengganti file lain.**

### Cara membuat ZIP gabungan dari source lengkap
Jika Anda punya ZIP source aplikasi, gunakan Python 3:

```bash
python tools/bangun_zip_v26.py "Daily-Commercial-Operation.zip" "Tigalapan_DCO_v26_GABUNGAN.zip"
```

Output memiliki `index.html` dan semua file asli di source input, serta JS UI hotfix. Skrip menolak ZIP tidak berisi `index.html`; jika source hanya patch, output tetap patch (tidak boleh diklaim repo lengkap).

### Mengapa `./dco-v26-ui-hotfix.js` (bukan `/dco-v26-ui-hotfix.js`)?
Untuk GitHub Pages pada subpath `/Daily-Commercial-Operation/`, URL absolut `/...` mengarah ke root domain dan bisa salah. Prefix relatif `./` mengikuti path aplikasi dan tetap cocok dengan folder `public/` pada Vite.

## Batasan untuk keselamatan data
Menurut panduan v25, penyimpanan draft lokal berjalan otomatis, **tetapi pemulihan draft dilakukan manual** lewat Draft/Pulihkan. Menyembunyikan panel **tidak sama** dengan menerapkan auto-restore. Sampai auto-restore diverifikasi, gunakan **Ctrl+Alt+D** sebagai akses darurat untuk membuka panel dan memulihkan draft. Jangan hapus data situs/browser saat draft belum tersinkron.

**Untuk versi produksi yang benar-benar memenuhi permintaan auto-restore tanpa tombol**, diperlukan file `index.html`, `src/main.js`, `src/drafts.js`, dan `public/dco-sw.js` asli untuk diintegrasikan dan diuji terhadap Supabase/IndexedDB. Tanpa source tersebut, klaim seluruh formulir sudah otomatis pulih atau bebas error tidak dapat dibenarkan.

## Cek instalasi
- Tampilan desktop dan HP: profil proporsional; panel Draft/Foto tidak menutupi layar.
- Refresh, logout/login, pindah menu, koneksi offline, pilih foto lalu tutup tab: periksa draft tetap ada.
- Uji `Ctrl+Alt+D` agar akses draft darurat tersedia sebelum auto-restore dibangun.
- Periksa browser Console, Vite build, dan Network (jangan ada 404 untuk `dco-v26-ui-hotfix.js`).
- Uji batas penyimpanan, gagal unggah foto, dan data pengguna berbeda; jangan klaim draft tersimpan server bila hanya lokal.

## Rollback
Kembalikan backup `index.html` atau hapus tag `./dco-v26-ui-hotfix.js`, lalu deploy. Data IndexedDB tidak dihapus oleh hotfix.
