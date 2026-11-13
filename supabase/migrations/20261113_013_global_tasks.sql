-- v17: Daily Routine sebagai tugas serbaguna untuk 12 toko.
-- Additive/idempotent. Data RUTIN dan CEKLIS lama tetap disimpan.
BEGIN;
ALTER TABLE dco.rutin ADD COLUMN IF NOT EXISTS jenis_tugas text NOT NULL DEFAULT 'Operasional';
ALTER TABLE dco.rutin ADD COLUMN IF NOT EXISTS nama_project text NOT NULL DEFAULT '';
ALTER TABLE dco.rutin ADD COLUMN IF NOT EXISTS lokasi text NOT NULL DEFAULT '';
ALTER TABLE dco.rutin ADD COLUMN IF NOT EXISTS hasil_diharapkan text NOT NULL DEFAULT '';
ALTER TABLE dco.rutin ADD COLUMN IF NOT EXISTS akhir text NOT NULL DEFAULT '';
ALTER TABLE dco.rutin ADD COLUMN IF NOT EXISTS tenggat text NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS rutin_aktif_jenis_idx ON dco.rutin (aktif, jenis_tugas);
-- Simpan metadata lengkap tetap di dco.rutin; CEKLIS merujuk ke rutin_id dan tidak digandakan.
COMMIT;
