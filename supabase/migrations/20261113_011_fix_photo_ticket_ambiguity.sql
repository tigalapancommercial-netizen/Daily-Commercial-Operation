-- Hotfix v15, 2026-11-13.
-- Fix PL/pgSQL error: column reference "ticket" is ambiguous.
-- Safe to run repeatedly. No DROP TABLE, DELETE, or changes to photo rows.
-- Requires migration 010 and dco.photo_receipts to exist.
BEGIN;

CREATE OR REPLACE FUNCTION public.dco_photo_register(
  p_token text, p_path text, p_source text DEFAULT 'galeri',
  p_client_sha256 text DEFAULT '', p_context text DEFAULT ''
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp AS $dco$
DECLARE
  me jsonb := dco.auth(p_token);
  v_ticket text;
  created_at_storage timestamptz;
  r dco.photo_receipts%ROWTYPE;
BEGIN
  IF p_path IS NULL OR p_path !~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
     THEN RAISE EXCEPTION 'Path foto tidak valid'; END IF;
  IF p_source NOT IN ('kamera_live','kamera_hp','galeri','legacy')
     THEN RAISE EXCEPTION 'Sumber foto tidak dikenal'; END IF;
  IF p_client_sha256 IS NULL OR p_client_sha256 !~ '^[0-9a-f]{64}$'
     THEN RAISE EXCEPTION 'Checksum upload tidak valid'; END IF;
  v_ticket := substr(p_path,9,32);
  IF NOT EXISTS (
    SELECT 1 FROM dco.upload_tickets t
    WHERE t.ticket = v_ticket AND t.username = me->>'username'
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

-- Keep the execute permissions from migration 010 explicitly.
REVOKE ALL ON FUNCTION public.dco_photo_register(text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dco_photo_register(text,text,text,text,text)
TO anon, authenticated, service_role;
NOTIFY pgrst, 'reload schema';
COMMIT;

-- The result must show "OK - ticket ambiguity fixed".
SELECT CASE
  WHEN POSITION('WHERE t.ticket = v_ticket' IN pg_get_functiondef(
       'public.dco_photo_register(text,text,text,text,text)'::regprocedure)) > 0
    THEN 'OK - ticket ambiguity fixed'
  ELSE 'PERIKSA - fungsi belum diperbaiki'
END AS hasil_verifikasi;
