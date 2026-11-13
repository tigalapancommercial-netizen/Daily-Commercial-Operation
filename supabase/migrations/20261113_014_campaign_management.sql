-- DCO v18: Campaign Management. School Campaign is an example, not a fixed template.
-- Requires 006 dco parity; independent from routine/checklist and periodic reports.
-- Preserves all previous rows. No historical photo migration. Safe to re-run.
BEGIN;

CREATE TABLE IF NOT EXISTS dco.campaigns (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 name text NOT NULL CHECK (length(btrim(name)) BETWEEN 3 AND 180),
 category text NOT NULL DEFAULT 'Sales',
 objective text NOT NULL DEFAULT '',
 description text NOT NULL DEFAULT '',
 pic text NOT NULL DEFAULT '',
 start_date date NOT NULL,
 end_date date NOT NULL,
 status text NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft','Active','Paused','Closed')),
 created_by text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT dco_campaign_dates CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS dco_campaign_dates_idx ON dco.campaigns(start_date DESC,end_date);

CREATE TABLE IF NOT EXISTS dco.campaign_stores (
 campaign_id uuid NOT NULL REFERENCES dco.campaigns(id) ON DELETE RESTRICT,
 toko text NOT NULL,
 pic text NOT NULL DEFAULT '',
 target_leads integer NOT NULL DEFAULT 0 CHECK (target_leads>=0),
 target_visits integer NOT NULL DEFAULT 0 CHECK (target_visits>=0),
 target_activities integer NOT NULL DEFAULT 0 CHECK (target_activities>=0),
 target_orders integer NOT NULL DEFAULT 0 CHECK (target_orders>=0),
 target_qty integer NOT NULL DEFAULT 0 CHECK (target_qty>=0),
 target_revenue numeric(16,2) NOT NULL DEFAULT 0 CHECK (target_revenue>=0),
 active boolean NOT NULL DEFAULT true,
 updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(campaign_id,toko)
);
CREATE INDEX IF NOT EXISTS dco_campaign_stores_by_toko ON dco.campaign_stores(toko,campaign_id) WHERE active;

CREATE TABLE IF NOT EXISTS dco.campaign_records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 campaign_id uuid NOT NULL REFERENCES dco.campaigns(id) ON DELETE RESTRICT,
 toko text NOT NULL,
 kind text NOT NULL CHECK (kind IN ('prospect','activity','plan','order','daily')),
 event_date date NOT NULL,
 title text NOT NULL DEFAULT '',
 status text NOT NULL DEFAULT '',
 pic text NOT NULL DEFAULT '',
 target numeric(16,2) NOT NULL DEFAULT 0 CHECK(target>=0),
 actual numeric(16,2) NOT NULL DEFAULT 0 CHECK(actual>=0),
 qty integer NOT NULL DEFAULT 0 CHECK(qty>=0),
 amount numeric(16,2) NOT NULL DEFAULT 0 CHECK(amount>=0),
 followup_date date,
 notes text NOT NULL DEFAULT '',
 payload jsonb NOT NULL DEFAULT '{}'::jsonb,
 photo_id text NOT NULL DEFAULT '',
 created_by text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_by text NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT now(),
 archived_at timestamptz,
 FOREIGN KEY(campaign_id,toko) REFERENCES dco.campaign_stores(campaign_id,toko) ON DELETE RESTRICT,
 CONSTRAINT dco_campaign_payload_object CHECK (jsonb_typeof(payload)='object'),
 CONSTRAINT dco_campaign_photo_max CHECK (length(photo_id)<10000)
);
CREATE INDEX IF NOT EXISTS dco_campaign_rec_filter ON dco.campaign_records(campaign_id,toko,kind,event_date DESC) WHERE archived_at IS NULL;
CREATE INDEX IF NOT EXISTS dco_campaign_rec_due ON dco.campaign_records(campaign_id,followup_date) WHERE archived_at IS NULL;
-- A store has one monitoring form per day, but may log multiple prospects/activities/orders.
CREATE UNIQUE INDEX IF NOT EXISTS dco_campaign_one_daily_per_store_date
ON dco.campaign_records(campaign_id,toko,event_date) WHERE kind='daily' AND archived_at IS NULL;

CREATE TABLE IF NOT EXISTS dco.campaign_audit (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 campaign_id uuid NOT NULL REFERENCES dco.campaigns(id) ON DELETE RESTRICT,
 record_id uuid,
 actor text NOT NULL,
 event text NOT NULL,
 previous_data jsonb,
 next_data jsonb,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dco_campaign_audit_idx ON dco.campaign_audit(campaign_id,created_at DESC);

ALTER TABLE dco.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE dco.campaign_stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE dco.campaign_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE dco.campaign_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON dco.campaigns,dco.campaign_stores,dco.campaign_records,dco.campaign_audit FROM PUBLIC,anon,authenticated;
REVOKE ALL ON SEQUENCE dco.campaign_audit_id_seq FROM PUBLIC,anon,authenticated;

-- Authenticated-by-DCO-token list. Store may only see active campaigns assigned to its store.
CREATE OR REPLACE FUNCTION public.dco_campaign_list(p_token text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); rows jsonb;
BEGIN
 SELECT coalesce(jsonb_agg(to_jsonb(z) ORDER BY z.start_date DESC,z.name),'[]'::jsonb) INTO rows FROM (
  SELECT c.*, 
    (SELECT count(*) FROM dco.campaign_stores cs WHERE cs.campaign_id=c.id AND cs.active AND ((me->>'is_mgr')::boolean OR cs.toko=me->>'toko')) AS store_count,
    (SELECT coalesce(sum(cs.target_revenue),0) FROM dco.campaign_stores cs WHERE cs.campaign_id=c.id AND cs.active AND ((me->>'is_mgr')::boolean OR cs.toko=me->>'toko')) AS target_revenue,
    (SELECT coalesce(sum(r.amount),0) FROM dco.campaign_records r WHERE r.campaign_id=c.id AND r.kind='order'
     AND r.status IN ('Lunas','Terkirim') AND r.archived_at IS NULL AND ((me->>'is_mgr')::boolean OR r.toko=me->>'toko')) AS realized_revenue
  FROM dco.campaigns c
  WHERE (me->>'is_mgr')::boolean OR EXISTS (
   SELECT 1 FROM dco.campaign_stores cs WHERE cs.campaign_id=c.id AND cs.toko=me->>'toko' AND cs.active
  )
  ORDER BY c.start_date DESC,c.name
 ) z;
 RETURN rows;
END $fn$;

-- Full campaign metadata and store scorecard; dates control realized metrics, not targets.
CREATE OR REPLACE FUNCTION public.dco_campaign_detail(
 p_token text,p_campaign_id uuid,p_store text DEFAULT NULL,p_from date DEFAULT NULL,p_to date DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); c dco.campaigns%ROWTYPE; stores jsonb; metrics jsonb;
 mgr boolean := (me->>'is_mgr')::boolean;
BEGIN
 SELECT * INTO c FROM dco.campaigns WHERE id=p_campaign_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Campaign tidak ditemukan'; END IF;
 IF NOT mgr AND NOT EXISTS(SELECT 1 FROM dco.campaign_stores s WHERE s.campaign_id=p_campaign_id AND s.toko=me->>'toko' AND s.active)
 THEN RAISE EXCEPTION 'Anda tidak memiliki akses campaign ini'; END IF;
 SELECT coalesce(jsonb_agg(to_jsonb(s) ORDER BY s.toko),'[]'::jsonb) INTO stores
 FROM dco.campaign_stores s WHERE s.campaign_id=p_campaign_id AND s.active
 AND (CASE WHEN mgr THEN (p_store IS NULL OR p_store='SEMUA' OR s.toko=p_store) ELSE s.toko=me->>'toko' END);
 SELECT coalesce(jsonb_agg(jsonb_build_object(
  'toko',s.toko,'pic',s.pic,'target_leads',s.target_leads,'target_visits',s.target_visits,
  'target_activities',s.target_activities,'target_orders',s.target_orders,'target_qty',s.target_qty,
  'target_revenue',s.target_revenue,
  'leads',(SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='prospect' AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'closing',(SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='prospect' AND r.status='Closing' AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'activities',(SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='activity' AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'visits',(SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='activity' AND r.payload->>'activity_type' IN ('Visit','Canvassing','School Visit') AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'orders',(SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='order' AND r.status<>'Batal' AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'qty',(SELECT coalesce(sum(r.qty),0) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='order' AND r.status IN ('Lunas','Terkirim') AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'revenue',(SELECT coalesce(sum(r.amount),0) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='order' AND r.status IN ('Lunas','Terkirim') AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'plans',(SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='plan' AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)),
  'plans_done',(SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.toko=s.toko AND r.kind='plan' AND r.status='Selesai' AND r.archived_at IS NULL AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to))
 ) ORDER BY s.toko),'[]'::jsonb) INTO metrics FROM dco.campaign_stores s
 WHERE s.campaign_id=p_campaign_id AND s.active
 AND (CASE WHEN mgr THEN (p_store IS NULL OR p_store='SEMUA' OR s.toko=p_store) ELSE s.toko=me->>'toko' END);
 RETURN jsonb_build_object('campaign',to_jsonb(c),'stores',stores,'scorecard',metrics);
END $fn$;

-- Pagination prevents truncated history; each call checks store authorization.
CREATE OR REPLACE FUNCTION public.dco_campaign_records(
 p_token text,p_campaign_id uuid,p_store text DEFAULT NULL,p_kind text DEFAULT NULL,
 p_from date DEFAULT NULL,p_to date DEFAULT NULL,p_limit integer DEFAULT 100,p_offset integer DEFAULT 0
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); mgr boolean := (me->>'is_mgr')::boolean;
 n integer := least(200,greatest(1,coalesce(p_limit,100))); offs integer := greatest(0,coalesce(p_offset,0));
 cnt bigint; records jsonb;
BEGIN
 IF p_kind IS NOT NULL AND p_kind NOT IN ('prospect','activity','plan','order','daily') THEN RAISE EXCEPTION 'Jenis data campaign salah'; END IF;
 IF NOT EXISTS(SELECT 1 FROM dco.campaigns c WHERE c.id=p_campaign_id) THEN RAISE EXCEPTION 'Campaign tidak ditemukan'; END IF;
 IF NOT mgr AND NOT EXISTS(SELECT 1 FROM dco.campaign_stores s WHERE s.campaign_id=p_campaign_id AND s.toko=me->>'toko' AND s.active) THEN RAISE EXCEPTION 'Tidak memiliki akses campaign'; END IF;
 IF p_from IS NOT NULL AND p_to IS NOT NULL AND p_from>p_to THEN RAISE EXCEPTION 'Rentang tanggal terbalik'; END IF;
 SELECT count(*) INTO cnt FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.archived_at IS NULL
   AND (p_kind IS NULL OR r.kind=p_kind) AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)
   AND (CASE WHEN mgr THEN (p_store IS NULL OR p_store='SEMUA' OR r.toko=p_store) ELSE r.toko=me->>'toko' END);
 SELECT coalesce(jsonb_agg(to_jsonb(a) ORDER BY a.event_date DESC,a.created_at DESC),'[]'::jsonb) INTO records FROM (
  SELECT r.* FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id AND r.archived_at IS NULL
    AND (p_kind IS NULL OR r.kind=p_kind) AND (p_from IS NULL OR r.event_date>=p_from) AND (p_to IS NULL OR r.event_date<=p_to)
    AND (CASE WHEN mgr THEN (p_store IS NULL OR p_store='SEMUA' OR r.toko=p_store) ELSE r.toko=me->>'toko' END)
  ORDER BY r.event_date DESC,r.created_at DESC,r.id DESC LIMIT n OFFSET offs
 ) a;
 RETURN jsonb_build_object('rows',records,'total',cnt,'offset',offs,'limit',n,'hasMore',offs+n<cnt);
END $fn$;

-- Campaign setup and store targets can only be edited by Master/SPV.
CREATE OR REPLACE FUNCTION public.dco_campaign_save(p_token text,p_data jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); cid uuid; cur dco.campaigns%ROWTYPE;
 out_row dco.campaigns%ROWTYPE; t jsonb; nam text; targets jsonb;
BEGIN
 PERFORM dco.must_mgr(me);
 IF jsonb_typeof(p_data) <> 'object' THEN RAISE EXCEPTION 'Data campaign tidak valid'; END IF;
 IF length(btrim(coalesce(p_data->>'name','')))<3 OR length(p_data->>'name')>180 THEN RAISE EXCEPTION 'Nama campaign minimal 3 karakter'; END IF;
 IF (p_data->>'start_date')::date > (p_data->>'end_date')::date THEN RAISE EXCEPTION 'Tanggal campaign tidak valid'; END IF;
 IF coalesce(p_data->>'status','Draft') NOT IN ('Draft','Active','Paused','Closed') THEN RAISE EXCEPTION 'Status campaign tidak dikenal'; END IF;
 targets := coalesce(p_data->'targets','[]'::jsonb);
 IF jsonb_typeof(targets)<>'array' OR jsonb_array_length(targets)=0 THEN RAISE EXCEPTION 'Pilih minimal satu toko target'; END IF;
 IF jsonb_array_length(targets)>50 THEN RAISE EXCEPTION 'Toko target terlalu banyak'; END IF;
 IF nullif(p_data->>'id','') IS NOT NULL THEN
  cid := (p_data->>'id')::uuid;
  SELECT * INTO cur FROM dco.campaigns c WHERE c.id=cid FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Campaign untuk edit tidak ditemukan'; END IF;
  UPDATE dco.campaigns SET name=btrim(p_data->>'name'),category=left(coalesce(p_data->>'category','Sales'),80),
    objective=left(coalesce(p_data->>'objective',''),1200),description=left(coalesce(p_data->>'description',''),4000),
    pic=left(coalesce(p_data->>'pic',''),180),start_date=(p_data->>'start_date')::date,end_date=(p_data->>'end_date')::date,
    status=coalesce(p_data->>'status','Draft'),updated_at=now() WHERE id=cid RETURNING * INTO out_row;
 ELSE
  INSERT INTO dco.campaigns(name,category,objective,description,pic,start_date,end_date,status,created_by)
  VALUES(btrim(p_data->>'name'),left(coalesce(p_data->>'category','Sales'),80),left(coalesce(p_data->>'objective',''),1200),
     left(coalesce(p_data->>'description',''),4000),left(coalesce(p_data->>'pic',''),180),
     (p_data->>'start_date')::date,(p_data->>'end_date')::date,coalesce(p_data->>'status','Draft'),me->>'username')
  RETURNING * INTO out_row; cid:=out_row.id;
 END IF;
 UPDATE dco.campaign_stores SET active=false,updated_at=now() WHERE campaign_id=cid;
 FOR t IN SELECT value FROM jsonb_array_elements(targets) LOOP
  nam := btrim(coalesce(t->>'toko',''));
  IF nam='' OR NOT EXISTS (SELECT 1 FROM dco.toko x WHERE x.nama=nam AND x.aktif<>'N') THEN
   RAISE EXCEPTION 'Toko campaign tidak dikenal: %',nam; END IF;
  INSERT INTO dco.campaign_stores(campaign_id,toko,pic,target_leads,target_visits,target_activities,target_orders,target_qty,target_revenue,active)
  VALUES(cid,nam,left(coalesce(t->>'pic',''),180),coalesce(nullif(t->>'target_leads','')::integer,0),
   coalesce(nullif(t->>'target_visits','')::integer,0),coalesce(nullif(t->>'target_activities','')::integer,0),
   coalesce(nullif(t->>'target_orders','')::integer,0),coalesce(nullif(t->>'target_qty','')::integer,0),
   coalesce(nullif(t->>'target_revenue','')::numeric,0),true)
  ON CONFLICT(campaign_id,toko) DO UPDATE SET pic=excluded.pic,target_leads=excluded.target_leads,
   target_visits=excluded.target_visits,target_activities=excluded.target_activities,target_orders=excluded.target_orders,
   target_qty=excluded.target_qty,target_revenue=excluded.target_revenue,active=true,updated_at=now();
 END LOOP;
 INSERT INTO dco.campaign_audit(campaign_id,actor,event,previous_data,next_data)
 VALUES(cid,me->>'username',CASE WHEN cur.id IS NULL THEN 'CREATE_CAMPAIGN' ELSE 'UPDATE_CAMPAIGN' END,
 CASE WHEN cur.id IS NULL THEN NULL ELSE to_jsonb(cur) END,to_jsonb(out_row));
 RETURN to_jsonb(out_row);
END $fn$;

-- Store can only create/edit its own assigned records. Archive instead of hard-delete.
CREATE OR REPLACE FUNCTION public.dco_campaign_record_save(p_token text,p_campaign_id uuid,p_kind text,p_data jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); mgr boolean := (me->>'is_mgr')::boolean;
 cid uuid := p_campaign_id; store_name text; cur dco.campaign_records%ROWTYPE;
 out_row dco.campaign_records%ROWTYPE; rid uuid; op text := coalesce(p_data->>'operation','upsert');
 campaign_status text; ev date; j jsonb;
BEGIN
 IF jsonb_typeof(p_data)<>'object' OR p_kind NOT IN ('prospect','activity','plan','order','daily') THEN RAISE EXCEPTION 'Form campaign tidak dikenal'; END IF;
 SELECT status INTO campaign_status FROM dco.campaigns WHERE id=cid;
 IF NOT FOUND THEN RAISE EXCEPTION 'Campaign tidak ditemukan'; END IF;
 IF campaign_status='Closed' AND NOT (me->>'is_master')::boolean THEN RAISE EXCEPTION 'Campaign sudah ditutup'; END IF;
 store_name := CASE WHEN mgr THEN btrim(coalesce(p_data->>'toko','')) ELSE me->>'toko' END;
 IF NOT EXISTS(SELECT 1 FROM dco.campaign_stores cs WHERE cs.campaign_id=cid AND cs.toko=store_name AND cs.active)
 THEN RAISE EXCEPTION 'Toko tidak ditugaskan ke campaign ini'; END IF;
 IF nullif(p_data->>'id','') IS NOT NULL THEN
  rid := (p_data->>'id')::uuid;
  SELECT * INTO cur FROM dco.campaign_records r WHERE r.id=rid AND r.campaign_id=cid AND r.kind=p_kind FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Data campaign untuk edit tidak ditemukan'; END IF;
  IF cur.toko<>store_name OR cur.archived_at IS NOT NULL THEN RAISE EXCEPTION 'Data toko berbeda atau sudah diarsipkan'; END IF;
 END IF;
 IF op='archive' THEN
  IF cur.id IS NULL THEN RAISE EXCEPTION 'Data untuk arsip tidak ditemukan'; END IF;
  UPDATE dco.campaign_records SET archived_at=now(),updated_by=me->>'username',updated_at=now() WHERE id=cur.id RETURNING * INTO out_row;
 ELSE
  ev := coalesce(nullif(p_data->>'event_date','')::date,(now() AT TIME ZONE 'Asia/Makassar')::date);
  IF ev<DATE '2020-01-01' OR ev>current_date+interval '2 years' THEN RAISE EXCEPTION 'Tanggal laporan tidak valid'; END IF;
  j := coalesce(p_data->'payload','{}'::jsonb);
  IF jsonb_typeof(j)<>'object' OR length(j::text)>12000 THEN RAISE EXCEPTION 'Detail laporan tidak valid / terlalu panjang'; END IF;
  IF length(coalesce(p_data->>'title',''))>400 OR length(coalesce(p_data->>'notes',''))>5000 THEN RAISE EXCEPTION 'Teks laporan terlalu panjang'; END IF;
  IF p_kind='daily' AND cur.id IS NULL AND EXISTS(
   SELECT 1 FROM dco.campaign_records r WHERE r.campaign_id=cid AND r.toko=store_name
     AND r.kind='daily' AND r.event_date=ev AND r.archived_at IS NULL
  ) THEN RAISE EXCEPTION 'Monitoring tanggal ini sudah ada. Gunakan Edit untuk memperbarui'; END IF;
  IF p_kind='order' AND (coalesce(nullif(p_data->>'qty','')::integer,0)<=0 OR coalesce(nullif(p_data->>'amount','')::numeric,0)<0) THEN
   RAISE EXCEPTION 'Order wajib mempunyai QTY dan nilai nonnegatif'; END IF;
  IF p_kind='prospect' AND btrim(coalesce(p_data->>'title',''))='' THEN RAISE EXCEPTION 'Nama prospek / mitra wajib'; END IF;
  IF p_kind='plan' AND btrim(coalesce(p_data->>'title',''))='' THEN RAISE EXCEPTION 'Nama aktivitas rencana wajib'; END IF;
  IF length(coalesce(p_data->>'photo_id',''))>0 AND NOT dco.valid_photo(p_data->>'photo_id') THEN RAISE EXCEPTION 'Referensi foto tidak valid'; END IF;
  IF cur.id IS NOT NULL THEN
   UPDATE dco.campaign_records SET event_date=ev,title=left(coalesce(p_data->>'title',''),400),
    status=left(coalesce(p_data->>'status',''),64),pic=left(coalesce(p_data->>'pic',''),180),
    target=coalesce(nullif(p_data->>'target','')::numeric,0),actual=coalesce(nullif(p_data->>'actual','')::numeric,0),
    qty=coalesce(nullif(p_data->>'qty','')::integer,0),amount=coalesce(nullif(p_data->>'amount','')::numeric,0),
    followup_date=nullif(p_data->>'followup_date','')::date,notes=coalesce(p_data->>'notes',''),payload=j,
    photo_id=left(coalesce(p_data->>'photo_id',''),9999),updated_by=me->>'username',updated_at=now()
   WHERE id=cur.id RETURNING * INTO out_row;
  ELSE
   INSERT INTO dco.campaign_records(campaign_id,toko,kind,event_date,title,status,pic,target,actual,qty,amount,followup_date,notes,payload,photo_id,created_by,updated_by)
   VALUES(cid,store_name,p_kind,ev,left(coalesce(p_data->>'title',''),400),left(coalesce(p_data->>'status',''),64),
    left(coalesce(p_data->>'pic',''),180),coalesce(nullif(p_data->>'target','')::numeric,0),
    coalesce(nullif(p_data->>'actual','')::numeric,0),coalesce(nullif(p_data->>'qty','')::integer,0),
    coalesce(nullif(p_data->>'amount','')::numeric,0),nullif(p_data->>'followup_date','')::date,
    coalesce(p_data->>'notes',''),j,left(coalesce(p_data->>'photo_id',''),9999),me->>'username',me->>'username')
   RETURNING * INTO out_row;
  END IF;
 END IF;
 INSERT INTO dco.campaign_audit(campaign_id,record_id,actor,event,previous_data,next_data)
 VALUES(cid,out_row.id,me->>'username',CASE WHEN op='archive' THEN 'ARCHIVE_'||upper(p_kind)
 ELSE CASE WHEN cur.id IS NULL THEN 'CREATE_' ELSE 'UPDATE_' END||upper(p_kind) END,
 CASE WHEN cur.id IS NULL THEN NULL ELSE to_jsonb(cur) END,to_jsonb(out_row));
 RETURN to_jsonb(out_row);
END $fn$;

REVOKE ALL ON FUNCTION public.dco_campaign_list(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_detail(text,uuid,text,date,date) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_records(text,uuid,text,text,date,date,integer,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_save(text,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_record_save(text,uuid,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dco_campaign_list(text) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_detail(text,uuid,text,date,date) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_records(text,uuid,text,text,date,date,integer,integer) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_save(text,jsonb) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_record_save(text,uuid,text,jsonb) TO anon,authenticated,service_role;

COMMIT;
SELECT 'OK - Campaign Management 014 installed, existing rows untouched' AS result;
