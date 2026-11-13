# v13 — 13 November 2026

- DSO: dukung foto multi dalam validasi SQL, error item invalid dijelaskan, state foto tidak dibuang saat submit gagal.
- DSO: indikator progress dan highlight wajib diperbarui saat galeri berubah, upload pending dan submit ganda diblokir.
- Kamera Live: watermark WITA di piksel asli, catatan waktu dan hash baru via Supabase Storage receipt, label sumber foto.
- Bukti Foto: buka gambar untuk melihat informasi waktu penerimaan server; foto lama tetap ada.
- Seluruh modul lama (Assignment, DSO, Issue, Visit, Before/After, Dashboard, Export/Backup) tetap ada.
- SQL 010 merupakan migrasi non-destruktif, harus dijalankan sebelum memperbarui frontend karena upload foto kini mencatat receipt server.
