-- DCO v21: pembatalan validasi dengan audit, akses server, dan pembukaan kunci edit.
-- Jalankan SETELAH migrasi 006, 012, 014, 015; dapat diulang tanpa menghapus data.
BEGIN;

CREATE TABLE IF NOT EXISTS dco.validation_reversal_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  module text NOT NULL,
  record_id text NOT NULL,
  old_status text NOT NULL,
  old_validator text NOT NULL DEFAULT '',
  reversed_by text NOT NULL,
  reason text NOT NULL,
  reversed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dco_validation_reversal_lookup
  ON dco.validation_reversal_audit(module, record_id, reversed_at DESC);
ALTER TABLE dco.validation_reversal_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON dco.validation_reversal_audit FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE dco.validation_reversal_audit_id_seq FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.dco_validation_undo(
  p_token text, p_module text, p_id text, p_reason text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp
AS $fn$
DECLARE
  me jsonb := dco.auth(p_token);
  module_name text := upper(btrim(coalesce(p_module, '')));
  actor text := coalesce(me->>'nama', '');
  reason_text text := btrim(coalesce(p_reason, ''));
  source_row jsonb;
  updated_row jsonb;
  table_name text;
  old_status text;
  old_validator text;
  is_master boolean := (me->>'is_master')::boolean;
BEGIN
  PERFORM dco.must_mgr(me);
  IF nullif(btrim(coalesce(p_id, '')), '') IS NULL THEN
    RAISE EXCEPTION 'ID data wajib diisi';
  END IF;
  IF length(reason_text) < 5 OR length(reason_text) > 500 THEN
    RAISE EXCEPTION 'Alasan pembatalan wajib diisi (5-500 karakter)';
  END IF;

  IF module_name = 'PERIOD' THEN
    SELECT to_jsonb(r) INTO source_row FROM dco.period_reports AS r
      WHERE r.id = p_id::uuid FOR UPDATE;
    IF source_row IS NULL THEN RAISE EXCEPTION 'Laporan periodik tidak ditemukan'; END IF;
    old_status := coalesce(source_row->>'validation_status', '');
    old_validator := coalesce(source_row->>'validated_by', '');
    IF old_status = 'Pending' THEN RAISE EXCEPTION 'Laporan belum divalidasi'; END IF;
    IF NOT is_master AND old_validator IS DISTINCT FROM (me->>'username') THEN
      RAISE EXCEPTION 'Hanya Master atau SPV yang melakukan validasi dapat membatalkannya';
    END IF;
    UPDATE dco.period_reports AS r SET
      status = 'Submitted', validation_status = 'Pending', validation_note = '',
      validated_by = '', validated_at = NULL, updated_at = now()
      WHERE r.id = p_id::uuid RETURNING to_jsonb(r) INTO updated_row;
    INSERT INTO dco.period_report_audit(report_id, actor, event, previous_data, next_data)
      VALUES (p_id::uuid, me->>'username', 'VALIDATION_REVOKED: ' || reason_text, source_row, updated_row);
  ELSE
    -- Strict whitelist: user input NEVER becomes an arbitrary SQL identifier.
    table_name := CASE module_name
      WHEN 'MASALAH' THEN 'masalah'
      WHEN 'TUGAS' THEN 'tugas'
      WHEN 'CEKLIS' THEN 'ceklis'
      WHEN 'DSO' THEN 'dso'
      WHEN 'VISIT' THEN 'visit'
      WHEN 'VISIT_ISSUE' THEN 'visit_issue'
      ELSE NULL END;
    IF table_name IS NULL THEN RAISE EXCEPTION 'Modul pembatalan validasi tidak diizinkan'; END IF;
    IF module_name = 'VISIT' THEN PERFORM dco.must_master(me); END IF;

    EXECUTE format('SELECT to_jsonb(x) FROM dco.%I AS x WHERE x.id = $1 FOR UPDATE', table_name)
      INTO source_row USING p_id;
    IF source_row IS NULL THEN RAISE EXCEPTION 'Data yang akan dibatalkan tidak ditemukan'; END IF;
    old_status := coalesce(source_row->>'validasi', '');
    old_validator := coalesce(source_row->>'validasi_oleh', '');
    IF old_status = '' THEN RAISE EXCEPTION 'Data belum divalidasi'; END IF;
    IF NOT is_master AND old_validator IS DISTINCT FROM actor THEN
      RAISE EXCEPTION 'Hanya Master atau SPV yang melakukan validasi dapat membatalkannya';
    END IF;
    EXECUTE format(
      'UPDATE dco.%I AS x SET validasi = '''', validasi_oleh = '''', validasi_tgl = '''', '
      || 'update_tgl = $2, update_oleh = $3 %s WHERE x.id = $1 RETURNING to_jsonb(x)',
      table_name,
      CASE WHEN module_name = 'DSO' THEN ', sla_validasi = ''''' ELSE '' END
    ) INTO updated_row USING p_id, dco.now_s(), actor;
  END IF;

  INSERT INTO dco.validation_reversal_audit(
    module, record_id, old_status, old_validator, reversed_by, reason
  ) VALUES (module_name, p_id, old_status, old_validator, me->>'username', reason_text);

  RETURN jsonb_build_object(
    'ok', true, 'module', module_name, 'id', p_id,
    'status', 'Pending', 'unlocked', true, 'record', updated_row
  );
END $fn$;

REVOKE ALL ON FUNCTION public.dco_validation_undo(text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dco_validation_undo(text,text,text,text)
  TO anon, authenticated, service_role;
COMMIT;

-- Verifikasi setelah menjalankan:
-- SELECT to_regprocedure('public.dco_validation_undo(text,text,text,text)') AS function_ready;
-- SELECT count(*) AS pembatalan_tercatat FROM dco.validation_reversal_audit;
