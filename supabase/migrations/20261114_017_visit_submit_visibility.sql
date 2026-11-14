-- DCO v22: atomic Visiting Checklist + Issue submit, no destructive schema changes.
-- REQUIREMENTS: migration 006 (dco.* tables and public.dco_save), migration 009 (foto_after).
-- Execute once in Supabase SQL Editor. Re-running is safe.
BEGIN;

CREATE OR REPLACE FUNCTION public.dco_visit_submit(
  p_token text,
  p_visit jsonb,
  p_issues jsonb DEFAULT '[]'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
  me jsonb := dco.auth(p_token);
  saved_visit jsonb;
  saved_rows jsonb;
  issue_row jsonb;
  prepared jsonb;
  issue_id text;
  visit_id text;
  matched_id text;
  total_issues integer := 0;
BEGIN
  PERFORM dco.must_mgr(me);
  IF p_visit IS NULL OR jsonb_typeof(p_visit) <> 'object' THEN
    RAISE EXCEPTION 'Format data Visiting tidak valid';
  END IF;
  IF p_issues IS NULL OR jsonb_typeof(p_issues) <> 'array' THEN
    RAISE EXCEPTION 'Format daftar issue Visiting tidak valid';
  END IF;
  IF jsonb_array_length(p_issues) > 1000 THEN
    RAISE EXCEPTION 'Maksimal 1000 issue per Visit';
  END IF;
  IF coalesce(p_visit->>'toko','') = '' OR coalesce(p_visit->>'tanggal','') !~ '^\d{4}-\d{2}-\d{2}$' THEN
    RAISE EXCEPTION 'Toko atau tanggal Visit tidak valid';
  END IF;

  -- Preflight all issue fields BEFORE touching parent visit.
  FOR issue_row IN SELECT value FROM jsonb_array_elements(p_issues) LOOP
    IF jsonb_typeof(issue_row) <> 'object' THEN
      RAISE EXCEPTION 'Format salah pada issue Visit';
    END IF;
    IF btrim(coalesce(issue_row->>'issue','')) = '' THEN
      RAISE EXCEPTION 'Nama issue Visit tidak boleh kosong';
    END IF;
    IF btrim(coalesce(issue_row->>'action','')) = '' OR btrim(coalesce(issue_row->>'pic','')) = ''
       OR coalesce(issue_row->>'due_date','') !~ '^\d{4}-\d{2}-\d{2}$' THEN
      RAISE EXCEPTION 'Action Plan, PIC dan Due Date wajib pada setiap issue Visit';
    END IF;
  END LOOP;

  -- Both parent and children are written inside THIS ONE PostgreSQL transaction.
  -- Any error in child records rolls the parent insert/update back.
  saved_rows := public.dco_save(p_token, 'VISIT', jsonb_build_array(p_visit), 'upsert');
  saved_visit := saved_rows->0;
  visit_id := saved_visit->>'id';
  IF coalesce(visit_id,'') = '' THEN RAISE EXCEPTION 'ID Visit tidak dikembalikan database'; END IF;

  FOR issue_row IN SELECT value FROM jsonb_array_elements(p_issues) LOOP
    issue_id := nullif(btrim(coalesce(issue_row->>'id','')), '');
    matched_id := null;
    IF issue_id IS NOT NULL THEN
      SELECT i.id INTO matched_id FROM dco.visit_issue i
       WHERE i.id = issue_id AND i.visit_id = visit_id;
      IF matched_id IS NULL THEN
        RAISE EXCEPTION 'Issue % tidak terdaftar pada Visit %', issue_id, visit_id;
      END IF;
    ELSE
      -- On edits made before linked issues finish loading, reuse the same issue.
      SELECT i.id INTO matched_id FROM dco.visit_issue i
       WHERE i.visit_id = visit_id
         AND i.point_id = coalesce(issue_row->>'point_id','')
         AND i.issue = btrim(issue_row->>'issue')
       ORDER BY i._seq LIMIT 1;
    END IF;
    prepared := issue_row || jsonb_build_object(
      'id',coalesce(matched_id,''),
      'visit_id',visit_id,
      'tanggal',saved_visit->>'tanggal',
      'toko',saved_visit->>'toko'
    );
    -- Do not overwrite an existing approval timestamp or approver when editing.
    prepared := prepared - 'validasi' - 'validasi_oleh' - 'validasi_tgl';
    PERFORM public.dco_save(p_token, 'VISIT_ISSUE', jsonb_build_array(prepared), 'upsert');
    total_issues := total_issues + 1;
  END LOOP;

  RETURN jsonb_build_object('visit',saved_visit,'issues_saved',total_issues,'atomic',true);
END;
$$;

REVOKE ALL ON FUNCTION public.dco_visit_submit(text,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dco_visit_submit(text,jsonb,jsonb) TO anon, authenticated, service_role;
NOTIFY pgrst, 'reload schema';
COMMIT;

-- The SELECT below is an optional, read-only diagnostic after installation:
-- SELECT id,tanggal,toko,final_score,rating,validasi,update_tgl FROM dco.visit ORDER BY _seq DESC LIMIT 20;
