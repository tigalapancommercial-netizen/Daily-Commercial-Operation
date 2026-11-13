-- DCO v16: 4 new store-owned reporting forms; no historical photo or CSV data migration.
-- Requires 006 parity migration, 010 receipts, 011 ticket hotfix.
-- Idempotent; never deletes existing operational rows or Storage objects.
BEGIN;

CREATE TABLE IF NOT EXISTS dco.period_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_type text NOT NULL CHECK (report_type IN ('WEEKLY_SALES','WEEKLY_GENSET','MONTHLY_SALES','MONTHLY_APAR')),
  toko text NOT NULL,
  period_key text NOT NULL,
  period_start date NOT NULL,
  period_end date NOT NULL,
  report_date date NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'Submitted' CHECK (status IN ('Submitted','Approved','Rejected')),
  validation_status text NOT NULL DEFAULT 'Pending' CHECK (validation_status IN ('Pending','Approved','Rejected')),
  validation_note text NOT NULL DEFAULT '',
  submitted_by text NOT NULL,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  validated_by text NOT NULL DEFAULT '',
  validated_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (report_type, toko, period_start)
);
CREATE INDEX IF NOT EXISTS dco_period_report_index ON dco.period_reports(report_type, period_start DESC, toko);
CREATE INDEX IF NOT EXISTS dco_period_report_pending ON dco.period_reports(validation_status, updated_at DESC);
CREATE TABLE IF NOT EXISTS dco.period_report_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  report_id uuid NOT NULL REFERENCES dco.period_reports(id) ON DELETE RESTRICT,
  actor text NOT NULL,
  event text NOT NULL,
  previous_data jsonb,
  next_data jsonb NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS period_audit_by_report ON dco.period_report_audit(report_id, recorded_at DESC);
ALTER TABLE dco.period_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE dco.period_report_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON dco.period_reports, dco.period_report_audit FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE dco.period_report_audit_id_seq FROM PUBLIC, anon, authenticated;

-- Returns paginated records. Store role is constrained at the database, not by UI filters.
CREATE OR REPLACE FUNCTION public.dco_period_list(
 p_token text, p_type text DEFAULT NULL, p_store text DEFAULT NULL,
 p_from date DEFAULT NULL, p_to date DEFAULT NULL,
 p_limit integer DEFAULT 100, p_offset integer DEFAULT 0
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $fn$
DECLARE
 me jsonb := dco.auth(p_token); mgr boolean := (me->>'is_mgr')::boolean;
 n integer := LEAST(200, GREATEST(1, COALESCE(p_limit,100)));
 offs integer := GREATEST(0,COALESCE(p_offset,0));
 total_count bigint; result_rows jsonb;
BEGIN
 IF p_type IS NOT NULL AND p_type NOT IN ('WEEKLY_SALES','WEEKLY_GENSET','MONTHLY_SALES','MONTHLY_APAR') THEN
    RAISE EXCEPTION 'Jenis laporan tidak dikenal'; END IF;
 SELECT count(*) INTO total_count FROM dco.period_reports r
 WHERE (p_type IS NULL OR r.report_type=p_type)
   AND (CASE WHEN mgr THEN (p_store IS NULL OR p_store='SEMUA' OR r.toko=p_store)
             ELSE r.toko=me->>'toko' END)
   AND (p_from IS NULL OR r.period_start >= p_from)
   AND (p_to IS NULL OR r.period_start <= p_to);
 SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY t.period_start DESC, t.updated_at DESC),'[]'::jsonb)
 INTO result_rows FROM (
   SELECT r.* FROM dco.period_reports r
   WHERE (p_type IS NULL OR r.report_type=p_type)
     AND (CASE WHEN mgr THEN (p_store IS NULL OR p_store='SEMUA' OR r.toko=p_store)
               ELSE r.toko=me->>'toko' END)
     AND (p_from IS NULL OR r.period_start >= p_from)
     AND (p_to IS NULL OR r.period_start <= p_to)
   ORDER BY r.period_start DESC, r.updated_at DESC, r.id DESC
   LIMIT n OFFSET offs
 ) t;
 RETURN jsonb_build_object('rows',result_rows,'total',total_count,'offset',offs,'limit',n,'hasMore',(offs+n)<total_count);
END $fn$;

-- Store-owned upsert per week/month. Every resubmit creates an audit event, not duplicate reports.
CREATE OR REPLACE FUNCTION public.dco_period_submit(
 p_token text, p_type text, p_store text, p_report_date date,
 p_payload jsonb DEFAULT '{}'::jsonb, p_evidence jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $fn$
DECLARE
 me jsonb := dco.auth(p_token); mgr boolean := (me->>'is_mgr')::boolean;
 is_master boolean := (me->>'is_master')::boolean;
 store_name text; start_date date; end_date date; pkey text;
 cur dco.period_reports%ROWTYPE; updated dco.period_reports%ROWTYPE;
 entry record; photo text; photo_count integer; old_doc jsonb;
 vals text[] := ARRAY['physical','oil','fuel','cooling','starter','cables','safety','running'];
 checks text[] := ARRAY['pressure','seal','pin','rust','placement','access'];
 k text;
BEGIN
 IF coalesce(p_type,'') NOT IN ('WEEKLY_SALES','WEEKLY_GENSET','MONTHLY_SALES','MONTHLY_APAR') THEN
   RAISE EXCEPTION 'Jenis laporan tidak dikenali'; END IF;
 IF p_report_date IS NULL OR p_report_date > ((now() at time zone 'Asia/Makassar')::date + 1)
    OR p_report_date < DATE '2020-01-01' THEN RAISE EXCEPTION 'Tanggal periode tidak valid'; END IF;
 store_name := CASE WHEN mgr THEN btrim(coalesce(p_store,'')) ELSE me->>'toko' END;
 IF store_name = '' OR store_name = 'SEMUA' OR NOT EXISTS(
  SELECT 1 FROM dco.toko WHERE nama=store_name AND aktif<>'N') THEN
  RAISE EXCEPTION 'Pilih toko yang aktif'; END IF;
 IF jsonb_typeof(p_payload) IS DISTINCT FROM 'object' OR jsonb_typeof(p_evidence) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'Isi laporan atau daftar bukti foto tidak valid'; END IF;
 IF length(p_payload::text)>100000 THEN RAISE EXCEPTION 'Isi laporan terlalu besar'; END IF;
 IF length(p_evidence::text)>20000 THEN RAISE EXCEPTION 'Daftar foto terlalu besar'; END IF;

 -- Validate every photo reference. Never store a historical filename as if it were a Storage image.
 FOR entry IN SELECT key, value FROM jsonb_each(p_evidence) LOOP
   photo := CASE WHEN jsonb_typeof(entry.value)='string' THEN entry.value #>> '{}'
                 WHEN jsonb_typeof(entry.value)='array' THEN entry.value::text ELSE '' END;
   IF photo <> '' AND NOT dco.valid_photo(photo) THEN
     RAISE EXCEPTION 'Bukti foto % tidak valid atau belum selesai diunggah', entry.key; END IF;
 END LOOP;
 IF p_type IN ('WEEKLY_SALES','MONTHLY_SALES') THEN
   IF btrim(coalesce(p_payload->>'achievement',''))='' THEN RAISE EXCEPTION 'Isi Achievement Sales'; END IF;
   IF btrim(coalesce(p_payload->>'reason',''))='' THEN RAISE EXCEPTION 'Isi alasan pencapaian sales'; END IF;
   IF btrim(coalesce(p_payload->>'issues',''))='' THEN RAISE EXCEPTION 'Isi issue operasional (boleh NIHIL)'; END IF;
   IF btrim(coalesce(p_payload->>'followup',''))='' THEN RAISE EXCEPTION 'Isi follow-up issue sebelumnya (boleh NIHIL)'; END IF;
 ELSIF p_type='WEEKLY_GENSET' THEN
   IF coalesce(p_payload->>'has_genset','') NOT IN ('Ada Genset','Tidak ada Genset') THEN
     RAISE EXCEPTION 'Pilih apakah toko memiliki genset'; END IF;
   IF p_payload->>'has_genset'='Ada Genset' THEN
     FOREACH k IN ARRAY vals LOOP
       IF btrim(coalesce(p_evidence->>k,''))='' THEN
         RAISE EXCEPTION 'Foto pemeriksaan genset % belum lengkap', k; END IF;
     END LOOP;
   END IF;
 ELSIF p_type='MONTHLY_APAR' THEN
   FOREACH k IN ARRAY checks LOOP
     IF coalesce(p_payload->>k,'') NOT IN ('1','0') THEN
       RAISE EXCEPTION 'Pemeriksaan APAR % belum diisi', k; END IF;
   END LOOP;
   IF coalesce(p_payload->>'expired_date','') !~ '^\d{4}-\d{2}-\d{2}$' THEN
     RAISE EXCEPTION 'Tanggal kedaluwarsa APAR tidak valid'; END IF;
   IF btrim(coalesce(p_evidence->>'attachment',''))='' THEN
     RAISE EXCEPTION 'Foto bukti APAR wajib diunggah'; END IF;
 END IF;

 IF left(p_type,6)='WEEKLY' THEN
   start_date := date_trunc('week', p_report_date::timestamp)::date;
   end_date := start_date + 6;
   pkey := to_char(start_date,'IYYY-"W"IW');
 ELSE
   start_date := date_trunc('month', p_report_date::timestamp)::date;
   end_date := (start_date + interval '1 month' - interval '1 day')::date;
   pkey := to_char(start_date,'YYYY-MM');
 END IF;
 PERFORM pg_advisory_xact_lock(hashtext('dco:period:'||p_type||':'||store_name||':'||start_date::text));
 SELECT * INTO cur FROM dco.period_reports r
  WHERE r.report_type=p_type AND r.toko=store_name AND r.period_start=start_date FOR UPDATE;
 IF found AND cur.validation_status='Approved' AND NOT is_master THEN
   RAISE EXCEPTION 'Laporan periode ini sudah di-approve dan dikunci'; END IF;
 old_doc := CASE WHEN found THEN to_jsonb(cur) ELSE NULL END;
 IF found THEN
   UPDATE dco.period_reports r SET report_date=p_report_date, payload=p_payload, evidence=p_evidence,
       status='Submitted',validation_status='Pending',validation_note='',validated_by='',validated_at=NULL,
       submitted_by=me->>'username',submitted_at=now(),updated_at=now()
     WHERE r.id=cur.id RETURNING * INTO updated;
 ELSE
   INSERT INTO dco.period_reports(report_type,toko,period_key,period_start,period_end,report_date,payload,evidence,
       status,validation_status,submitted_by)
   VALUES (p_type,store_name,pkey,start_date,end_date,p_report_date,p_payload,p_evidence,'Submitted','Pending',me->>'username')
   RETURNING * INTO updated;
 END IF;
 INSERT INTO dco.period_report_audit(report_id,actor,event,previous_data,next_data)
 VALUES (updated.id,me->>'username',CASE WHEN old_doc IS NULL THEN 'SUBMIT' ELSE 'RESUBMIT' END,old_doc,to_jsonb(updated));
 RETURN to_jsonb(updated);
END $fn$;

CREATE OR REPLACE FUNCTION public.dco_period_validate(p_token text, p_id uuid, p_action text, p_note text DEFAULT '')
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); cur dco.period_reports%ROWTYPE; upd dco.period_reports%ROWTYPE;
BEGIN
 PERFORM dco.must_mgr(me);
 IF p_action NOT IN ('Approved','Rejected') THEN RAISE EXCEPTION 'Status validasi tidak dikenal'; END IF;
 SELECT * INTO cur FROM dco.period_reports WHERE id=p_id FOR UPDATE;
 IF NOT found THEN RAISE EXCEPTION 'Laporan tidak ditemukan'; END IF;
 IF cur.validation_status='Approved' AND NOT (me->>'is_master')::boolean THEN
   RAISE EXCEPTION 'Validasi yang telah disahkan hanya dapat diubah Master'; END IF;
 UPDATE dco.period_reports SET validation_status=p_action,status=p_action,
   validation_note=left(coalesce(p_note,''),2000), validated_by=me->>'username', validated_at=now(),updated_at=now()
 WHERE id=p_id RETURNING * INTO upd;
 INSERT INTO dco.period_report_audit(report_id,actor,event,previous_data,next_data)
 VALUES (upd.id,me->>'username',p_action,to_jsonb(cur),to_jsonb(upd));
 RETURN to_jsonb(upd);
END $fn$;

-- Current-period matrix, all 12 active stores; store role sees its store only.
CREATE OR REPLACE FUNCTION public.dco_period_summary(p_token text, p_date date DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); w date; m date; refdate date;
 out_rows jsonb;
BEGIN
 refdate := coalesce(p_date,(now() at time zone 'Asia/Makassar')::date);
 w := date_trunc('week',refdate::timestamp)::date;
 m := date_trunc('month',refdate::timestamp)::date;
 SELECT coalesce(jsonb_agg(jsonb_build_object(
    'toko',q.nama,'type',types.kind,'periodKey',
    CASE WHEN types.freq='WEEKLY' THEN to_char(w,'IYYY-"W"IW') ELSE to_char(m,'YYYY-MM') END,
    'periodStart',CASE WHEN types.freq='WEEKLY' THEN w ELSE m END,
    'periodEnd',CASE WHEN types.freq='WEEKLY' THEN w+6 ELSE (m+interval '1 month'-interval '1 day')::date END,
    'status',CASE WHEN r.id IS NULL THEN
       CASE WHEN (CASE WHEN types.freq='WEEKLY' THEN w+6 ELSE (m+interval '1 month'-interval '1 day')::date END)
          < (now() at time zone 'Asia/Makassar')::date THEN 'Terlewat' ELSE 'Belum Submit' END
       WHEN r.validation_status='Approved' THEN 'Selesai'
       WHEN r.validation_status='Rejected' THEN 'Perlu Revisi'
       ELSE 'Menunggu Validasi' END,
    'id',r.id,'submittedAt',r.submitted_at,'validatedAt',r.validated_at,'validationStatus',r.validation_status
   ) ORDER BY q.nama,types.kind),'[]'::jsonb) INTO out_rows
 FROM dco.toko q
 CROSS JOIN (VALUES ('WEEKLY_SALES','WEEKLY'),('WEEKLY_GENSET','WEEKLY'),('MONTHLY_SALES','MONTHLY'),('MONTHLY_APAR','MONTHLY')) AS types(kind,freq)
 LEFT JOIN dco.period_reports r ON r.toko=q.nama AND r.report_type=types.kind
    AND r.period_start=CASE WHEN types.freq='WEEKLY' THEN w ELSE m END
 WHERE q.aktif<>'N' AND ((me->>'is_mgr')::boolean OR q.nama=me->>'toko');
 RETURN jsonb_build_object('date',refdate,'items',out_rows);
END $fn$;

REVOKE ALL ON FUNCTION public.dco_period_list(text,text,text,date,date,integer,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_period_submit(text,text,text,date,jsonb,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_period_validate(text,uuid,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_period_summary(text,date) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dco_period_list(text,text,text,date,date,integer,integer) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_period_submit(text,text,text,date,jsonb,jsonb) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_period_validate(text,uuid,text,text) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_period_summary(text,date) TO anon,authenticated,service_role;
COMMIT;
