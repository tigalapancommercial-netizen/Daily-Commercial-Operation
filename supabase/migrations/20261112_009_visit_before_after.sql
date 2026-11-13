-- v12: before/after documentation for each Visit Issue. Run after 008_multiphoto.sql.
-- Non-destructive: existing data and photo references are preserved as-is.
ALTER TABLE dco.visit_issue
  ADD COLUMN IF NOT EXISTS foto_after text NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS update_note text NOT NULL DEFAULT '';

-- New after-photo submissions must contain recognized Storage paths or legacy IDs.
-- NOT VALID preserves historical records; PostgreSQL still validates new/updated rows.
DO $dco$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM pg_constraint
   WHERE conname = 'visit_issue_foto_after_valid'
     AND conrelid = 'dco.visit_issue'::regclass
 ) THEN
   ALTER TABLE dco.visit_issue ADD CONSTRAINT visit_issue_foto_after_valid
     CHECK (foto_after = '' OR dco.valid_photo(foto_after)) NOT VALID;
 END IF;
END
$dco$;

-- Extend deletion-protection logic to BOTH photo sets, including JSON arrays.
CREATE OR REPLACE FUNCTION dco.photo_referenced(p text)
RETURNS boolean LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $$
 SELECT exists(SELECT 1 FROM dco.masalah WHERE strpos(foto_id,p)>0)
    OR exists(SELECT 1 FROM dco.tugas WHERE strpos(foto_id,p)>0)
    OR exists(SELECT 1 FROM dco.ceklis WHERE strpos(foto_id,p)>0)
    OR exists(SELECT 1 FROM dco.visit_issue WHERE strpos(foto_id,p)>0 OR strpos(foto_after,p)>0)
    OR exists(SELECT 1 FROM dco.dso WHERE strpos(jawaban,p)>0)
    OR exists(SELECT 1 FROM dco.visit WHERE strpos(foto,p)>0)
$$;

CREATE OR REPLACE FUNCTION dco.photo_paths(r jsonb)
RETURNS text[] LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $$
 SELECT coalesce(array_agg(DISTINCT m[1]),'{}')
 FROM regexp_matches(
   coalesce(r->>'foto_id','') || ' ' || coalesce(r->>'foto_after','') || ' ' ||
   coalesce(r->>'foto','') || ' ' || coalesce(r->>'jawaban',''),
   '(\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(?:jpg|jpeg|png|webp))','g') m
$$;

COMMENT ON COLUMN dco.visit_issue.foto_after IS 'Foto sesudah perbaikan, 1 path lama atau JSON-array sampai 30 foto WebP terpisah.';
COMMENT ON COLUMN dco.visit_issue.update_note IS 'Catatan tindak lanjut tindakan perbaikan untuk perbandingan before/after.';
