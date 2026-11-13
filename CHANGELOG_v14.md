# v14 - Assignment Auto-Checklist on Photo Save

- Assignment otomatis menjadi Selesai (tercentang) setelah foto berhasil diunggah dan respons Supabase mengonfirmasi penyimpanan status + foto secara bersamaan.
- Tidak auto-complete hanya karena membuka galeri, melepas foto, sebagian upload gagal, atau server menolak penyimpanan.
- Status Selesai tidak ditampilkan sebelum transaksi penyimpanan berhasil.
- Upload yang sedang berjalan mencegah aksi centang manual bertabrakan.
- Kontrol upload tersembunyi untuk Store jika checklist divalidasi SPV.
- Tidak ada perubahan SQL khusus v14 dan tidak ada perubahan destruktif pada data.
- Fitur v13: validasi DSO multi-foto, watermark WITA, foto receipt, tetap tersedia.
