from pathlib import Path
p=Path(__file__).resolve().parents[1]/'supabase'/'migrations'/'20261112_006_dco_parity.sql'
s=p.read_text()
a=s.index('create or replace function public.dco_dso_submit(')
b=s.index('\n-- DSO validasi SPV',a)
fn=s[a:b]
old="      if dco.valid_photo(dco.jtext(e.value)) then jaw := jaw || jsonb_build_object(e.key, dco.jtext(e.value)); end if;"
new="""      if dco.valid_photo(dco.jtext(e.value)) then
        jaw := jaw || jsonb_build_object(e.key, dco.jtext(e.value));
      elsif exists (select 1 from dco.form_def d where d.form = p->>'form' and d.id = e.key and d.aktif <> 'N') then
        raise exception 'Foto item % tidak valid. Daftar foto harus berupa path Storage atau ID foto lama (maksimal 30). Jalankan migrasi SQL 010.', e.key;
      end if;"""
assert fn.count(old)==1
fn=fn.replace(old,new)
pre=r'''-- v13: Fix DSO multi-photo validation and create server-side upload receipts.
-- NON-DESTRUCTIVE: no existing data, photo or form definition is deleted.
-- Run this AFTER 20261112_008_multiphoto.sql and 20261112_009_visit_before_after.sql.
BEGIN;

-- Some production projects still have the old single-photo validator from 006.
-- Re-install a strict validator supporting both one legacy ID and a JSON list.
CREATE OR REPLACE FUNCTION dco.valid_photo(t text)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE
SET search_path = pg_catalog, pg_temp AS $dco$
DECLARE a jsonb; el jsonb; item text; clean text;
BEGIN
  clean := btrim(coalesce(t,''));
  IF clean = '' OR length(clean) > 5500 THEN RETURN false; END IF;
  IF clean ~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
     OR clean ~ '^[A-Za-z0-9_-]{10,}$' THEN RETURN true; END IF;
  IF left(clean,1) <> '[' THEN RETURN false; END IF;
  BEGIN a := clean::jsonb; EXCEPTION WHEN others THEN RETURN false; END;
  IF jsonb_typeof(a) <> 'array' OR jsonb_array_length(a) NOT BETWEEN 1 AND 30 THEN RETURN false; END IF;
  FOR el IN SELECT value FROM jsonb_array_elements(a) LOOP
    IF jsonb_typeof(el) <> 'string' THEN RETURN false; END IF;
    item := el #>> '{}';
    IF NOT (item ~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
            OR item ~ '^[A-Za-z0-9_-]{10,}$') THEN RETURN false; END IF;
  END LOOP;
  RETURN true;
END;
$dco$;

'''
post=r'''
-- Server receipt for each uploaded file. User-supplied hash/source are claims;
-- timestamps come from Postgres and Storage, not from the user's device.
CREATE TABLE IF NOT EXISTS dco.photo_receipts (
  path text PRIMARY KEY,
  username text NOT NULL,
  capture_source text NOT NULL CHECK (capture_source IN ('kamera_live','kamera_hp','galeri','legacy')),
  item_context text NOT NULL DEFAULT '',
  client_sha256 text NOT NULL CHECK (client_sha256 ~ '^[0-9a-f]{64}$'),
  storage_created_at timestamptz NOT NULL,
  registered_at timestamptz NOT NULL DEFAULT now()
);
REVOKE ALL ON dco.photo_receipts FROM PUBLIC, anon, authenticated;
CREATE INDEX IF NOT EXISTS photo_receipts_username_time ON dco.photo_receipts (username, registered_at DESC);

CREATE OR REPLACE FUNCTION public.dco_photo_register(
  p_token text, p_path text, p_source text DEFAULT 'galeri',
  p_client_sha256 text DEFAULT '', p_context text DEFAULT ''
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $dco$
DECLARE
  me jsonb := dco.auth(p_token);
  ticket text;
  created_at_storage timestamptz;
  r dco.photo_receipts%ROWTYPE;
BEGIN
  IF p_path IS NULL OR p_path !~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
     THEN RAISE EXCEPTION 'Path foto tidak valid'; END IF;
  IF p_source NOT IN ('kamera_live','kamera_hp','galeri','legacy')
     THEN RAISE EXCEPTION 'Sumber foto tidak dikenal'; END IF;
  IF p_client_sha256 IS NULL OR p_client_sha256 !~ '^[0-9a-f]{64}$'
     THEN RAISE EXCEPTION 'Checksum upload tidak valid'; END IF;
  ticket := substr(p_path,9,32);
  IF NOT EXISTS (
    SELECT 1 FROM dco.upload_tickets t
    WHERE t.ticket = ticket AND t.username = me->>'username'
      AND t.expires_at > now() - interval '2 minutes'
  ) THEN RAISE EXCEPTION 'Tiket foto tidak cocok dengan pengguna atau telah kedaluwarsa'; END IF;
  SELECT o.created_at INTO created_at_storage
    FROM storage.objects o WHERE o.bucket_id='dco-foto' AND o.name = p_path;
  IF created_at_storage IS NULL THEN RAISE EXCEPTION 'File belum ada di Supabase Storage'; END IF;
  IF created_at_storage < now() - interval '25 minutes'
     THEN RAISE EXCEPTION 'Foto diunggah terlalu lama; gunakan sesi upload baru'; END IF;
  INSERT INTO dco.photo_receipts(path,username,capture_source,item_context,client_sha256,storage_created_at)
  VALUES (p_path, me->>'username', p_source, left(coalesce(p_context,''),240), p_client_sha256,created_at_storage)
  ON CONFLICT(path) DO NOTHING;
  SELECT * INTO r FROM dco.photo_receipts WHERE path = p_path;
  IF r.username IS DISTINCT FROM me->>'username' THEN RAISE EXCEPTION 'Foto tidak dimiliki oleh sesi ini'; END IF;
  RETURN jsonb_build_object('path',r.path,'source',r.capture_source,'uploadedAt',r.storage_created_at,
    'receiptAt',r.registered_at,'checksum',r.client_sha256,'context',r.item_context);
END;
$dco$;

CREATE OR REPLACE FUNCTION public.dco_photo_receipt(p_token text,p_path text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $dco$
DECLARE me jsonb := dco.auth(p_token); r dco.photo_receipts%ROWTYPE;
BEGIN
  SELECT * INTO r FROM dco.photo_receipts WHERE path=p_path;
  IF NOT FOUND THEN RETURN jsonb_build_object('verified',false,'reason','Belum memiliki catatan waktu server (foto lama atau migrasi belum dilakukan)'); END IF;
  RETURN jsonb_build_object('verified',true,'source',r.capture_source,'uploadedAt',r.storage_created_at,
    'receiptAt',r.registered_at,'checksum',r.client_sha256,'context',r.item_context);
END;
$dco$;

REVOKE ALL ON FUNCTION public.dco_photo_register(text,text,text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_photo_receipt(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dco_photo_register(text,text,text,text,text) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_photo_receipt(text,text) TO anon,authenticated,service_role;
NOTIFY pgrst, 'reload schema';
COMMIT;
'''
Path(__file__).resolve().parents[1].joinpath('supabase/migrations/20261113_010_dso_photo_audit.sql').write_text(pre+fn+post)
