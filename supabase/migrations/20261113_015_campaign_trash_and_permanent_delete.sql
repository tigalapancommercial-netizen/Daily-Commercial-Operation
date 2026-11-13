-- DCO v19: Campaign Edit / Sampah / Restore / Hapus Permanen / Backup + foto orphan cleanup.
-- PRASYARAT: 006, 008, 012, 013, 014. Idempotent. Tidak menghapus campaign saat migrasi dijalankan.
-- PERINGATAN: Hapus Permanen diaktifkan melalui fungsi RPC terpisah dengan autentikasi MASTER.
BEGIN;

ALTER TABLE dco.campaigns ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
ALTER TABLE dco.campaigns ADD COLUMN IF NOT EXISTS deleted_by text;
CREATE INDEX IF NOT EXISTS dco_campaign_active_only_idx
  ON dco.campaigns(start_date DESC,id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS dco_campaign_trashed_idx
  ON dco.campaigns(deleted_at DESC,id) WHERE deleted_at IS NOT NULL;

-- Jejak MINIMAL setelah data campaign benar-benar dihapus. Tidak menyimpan payload/prospek.
CREATE TABLE IF NOT EXISTS dco.campaign_purge_log (
 id uuid PRIMARY KEY, campaign_name text NOT NULL, purged_by text NOT NULL,
 purged_at timestamptz NOT NULL DEFAULT now(), records_deleted integer NOT NULL,
 stores_deleted integer NOT NULL, audit_deleted integer NOT NULL,
 photo_cleanup_queued integer NOT NULL DEFAULT 0
);

-- Kandidat foto campaign yang sudah tidak direferensikan. Dihapus lewat Storage API, bukan DELETE storage.objects.
CREATE TABLE IF NOT EXISTS dco.campaign_photo_cleanup (
 path text PRIMARY KEY, campaign_id uuid NOT NULL, queued_at timestamptz NOT NULL DEFAULT now(),
 removed_at timestamptz, skipped_at timestamptz
);
CREATE INDEX IF NOT EXISTS dco_campaign_photo_pending_idx
 ON dco.campaign_photo_cleanup(queued_at) WHERE removed_at IS NULL AND skipped_at IS NULL;
ALTER TABLE dco.campaign_purge_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE dco.campaign_photo_cleanup ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON dco.campaign_purge_log,dco.campaign_photo_cleanup FROM PUBLIC,anon,authenticated;

-- Master-only daftar campaign di Sampah. Toko/SPV tidak bisa membuka fungsi ini.
CREATE OR REPLACE FUNCTION public.dco_campaign_trash_list(p_token text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); result jsonb;
BEGIN
 PERFORM dco.must_master(me);
 SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.deleted_at DESC),'[]'::jsonb)
 INTO result FROM (
  SELECT c.id,c.name,c.status,c.deleted_at,c.deleted_by,c.created_at,
   (SELECT count(*) FROM dco.campaign_stores s WHERE s.campaign_id=c.id) AS stores,
   (SELECT count(*) FROM dco.campaign_records r WHERE r.campaign_id=c.id) AS records,
   (SELECT count(*) FROM dco.campaign_audit a WHERE a.campaign_id=c.id) AS audit_events
  FROM dco.campaigns c WHERE c.deleted_at IS NOT NULL
 ) x;
 RETURN result;
END $fn$;

CREATE OR REPLACE FUNCTION public.dco_campaign_delete_preview(p_token text,p_campaign_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); c dco.campaigns%ROWTYPE;
 nr bigint; ns bigint; na bigint; nphotos bigint; bytes_est bigint;
BEGIN
 PERFORM dco.must_master(me);
 SELECT * INTO c FROM dco.campaigns WHERE id=p_campaign_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Campaign tidak ditemukan'; END IF;
 SELECT count(*),coalesce(sum(pg_column_size(r)),0)::bigint INTO nr,bytes_est FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id;
 SELECT count(*) INTO ns FROM dco.campaign_stores s WHERE s.campaign_id=p_campaign_id;
 SELECT count(*) INTO na FROM dco.campaign_audit a WHERE a.campaign_id=p_campaign_id;
 SELECT count(DISTINCT x.path) INTO nphotos
 FROM dco.campaign_records r
 CROSS JOIN LATERAL unnest(dco.photo_paths(jsonb_build_object('foto_id',r.photo_id,'foto',r.payload::text))) x(path)
 WHERE r.campaign_id=p_campaign_id;
 RETURN jsonb_build_object('id',c.id,'name',c.name,'deleted_at',c.deleted_at,
  'records',nr,'stores',ns,'audit',na,'photo_refs',nphotos,
  'records_estimated_bytes',bytes_est,
  'warning','Penghapusan permanen tidak dapat dibatalkan. Download backup JSON terlebih dahulu.');
END $fn$;

-- Master-only backup data seluruh campaign, termasuk record yang sudah diarsipkan dan audit.
-- Pagination per section. Storage photo binary tidak termasuk di backup JSON.
CREATE OR REPLACE FUNCTION public.dco_campaign_export_section(
 p_token text,p_campaign_id uuid,p_section text,p_limit integer DEFAULT 200,p_offset integer DEFAULT 0
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); n integer:=least(500,greatest(1,coalesce(p_limit,200)));
 offs integer:=greatest(0,coalesce(p_offset,0)); result jsonb; total_rows bigint;
BEGIN
 PERFORM dco.must_master(me);
 IF NOT EXISTS(SELECT 1 FROM dco.campaigns WHERE id=p_campaign_id) THEN RAISE EXCEPTION 'Campaign tidak ditemukan'; END IF;
 IF p_section='campaign' THEN
   SELECT coalesce(jsonb_agg(to_jsonb(x)),'[]'::jsonb),count(*) INTO result,total_rows
   FROM (SELECT c.* FROM dco.campaigns c WHERE c.id=p_campaign_id) x;
 ELSIF p_section='stores' THEN
   SELECT count(*) INTO total_rows FROM dco.campaign_stores s WHERE s.campaign_id=p_campaign_id;
   SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.toko),'[]'::jsonb) INTO result FROM (
    SELECT * FROM dco.campaign_stores s WHERE s.campaign_id=p_campaign_id ORDER BY s.toko LIMIT n OFFSET offs
   ) x;
 ELSIF p_section='records' THEN
   SELECT count(*) INTO total_rows FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id;
   SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.created_at,x.id),'[]'::jsonb) INTO result FROM (
    SELECT * FROM dco.campaign_records r WHERE r.campaign_id=p_campaign_id
    ORDER BY r.created_at,r.id LIMIT n OFFSET offs
   ) x;
 ELSIF p_section='audit' THEN
   SELECT count(*) INTO total_rows FROM dco.campaign_audit a WHERE a.campaign_id=p_campaign_id;
   SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.id),'[]'::jsonb) INTO result FROM (
    SELECT * FROM dco.campaign_audit a WHERE a.campaign_id=p_campaign_id ORDER BY a.id LIMIT n OFFSET offs
   ) x;
 ELSE RAISE EXCEPTION 'Bagian backup tidak dikenal'; END IF;
 RETURN jsonb_build_object('rows',result,'total',total_rows,'offset',offs,'hasMore',offs+jsonb_array_length(result)<total_rows);
END $fn$;

-- Satu pemanggilan RPC = satu transaksi PG. Jika salah satu DELETE gagal, otomatis rollback.
CREATE OR REPLACE FUNCTION public.dco_campaign_manage(
 p_token text,p_campaign_id uuid,p_action text,p_confirm_name text DEFAULT NULL,p_backup_ack boolean DEFAULT false
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); c dco.campaigns%ROWTYPE;
 nr integer; ns integer; na integer; photo_paths text[]:='{}'::text[]; photo_path text;
 queued integer:=0;
BEGIN
 PERFORM dco.must_master(me);
 SELECT * INTO c FROM dco.campaigns WHERE id=p_campaign_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Campaign tidak ditemukan atau sudah dihapus'; END IF;
 IF p_action='trash' THEN
   IF c.deleted_at IS NOT NULL THEN RAISE EXCEPTION 'Campaign sudah di Sampah'; END IF;
   UPDATE dco.campaigns SET deleted_at=now(),deleted_by=me->>'username',updated_at=now()
    WHERE id=c.id;
   RETURN jsonb_build_object('action','trash','id',c.id,'name',c.name,'ok',true);
 ELSIF p_action='restore' THEN
   IF c.deleted_at IS NULL THEN RAISE EXCEPTION 'Campaign belum berada di Sampah'; END IF;
   UPDATE dco.campaigns SET deleted_at=NULL,deleted_by=NULL,updated_at=now() WHERE id=c.id;
   RETURN jsonb_build_object('action','restore','id',c.id,'name',c.name,'ok',true);
 ELSIF p_action<>'purge' THEN RAISE EXCEPTION 'Aksi campaign tidak dikenal'; END IF;

 IF c.deleted_at IS NULL THEN RAISE EXCEPTION 'Pindahkan ke Sampah terlebih dahulu sebelum hapus permanen'; END IF;
 IF p_confirm_name IS DISTINCT FROM c.name THEN RAISE EXCEPTION 'Konfirmasi nama campaign tidak cocok'; END IF;
 IF coalesce(p_backup_ack,false) IS NOT TRUE THEN RAISE EXCEPTION 'Centang konfirmasi backup sebelum hapus permanen'; END IF;

 SELECT count(*) INTO nr FROM dco.campaign_records r WHERE r.campaign_id=c.id;
 SELECT count(*) INTO ns FROM dco.campaign_stores s WHERE s.campaign_id=c.id;
 SELECT count(*) INTO na FROM dco.campaign_audit a WHERE a.campaign_id=c.id;
 SELECT coalesce(array_agg(DISTINCT x.path),'{}'::text[]) INTO photo_paths
  FROM dco.campaign_records r
  CROSS JOIN LATERAL unnest(dco.photo_paths(jsonb_build_object('foto_id',r.photo_id,'foto',r.payload::text))) x(path)
  WHERE r.campaign_id=c.id;
 -- FKs ON DELETE RESTRICT: urutan delete HARUS audit -> records -> stores -> campaign.
 DELETE FROM dco.campaign_audit a WHERE a.campaign_id=c.id;
 DELETE FROM dco.campaign_records r WHERE r.campaign_id=c.id;
 DELETE FROM dco.campaign_stores s WHERE s.campaign_id=c.id;
 DELETE FROM dco.campaigns WHERE id=c.id;

 -- Hanya antre foto yang tidak dipakai modul atau campaign lain.
 FOREACH photo_path IN ARRAY photo_paths LOOP
  IF photo_path ~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
     AND NOT dco.photo_referenced(photo_path)
     AND NOT EXISTS(SELECT 1 FROM dco.campaign_records r WHERE strpos(r.photo_id,photo_path)>0 OR strpos(r.payload::text,photo_path)>0)
     AND NOT EXISTS(SELECT 1 FROM dco.campaign_audit a WHERE strpos(coalesce(a.next_data::text,''),photo_path)>0 OR strpos(coalesce(a.previous_data::text,''),photo_path)>0)
     AND NOT EXISTS(SELECT 1 FROM dco.period_reports pr WHERE strpos(pr.evidence::text,photo_path)>0 OR strpos(pr.payload::text,photo_path)>0)
     AND NOT EXISTS(SELECT 1 FROM dco.period_report_audit pa WHERE strpos(coalesce(pa.next_data::text,''),photo_path)>0 OR strpos(coalesce(pa.previous_data::text,''),photo_path)>0)
  THEN
    INSERT INTO dco.campaign_photo_cleanup(path,campaign_id) VALUES (photo_path,c.id)
    ON CONFLICT (path) DO NOTHING;
    queued:=queued+1;
  END IF;
 END LOOP;
 INSERT INTO dco.campaign_purge_log(id,campaign_name,purged_by,records_deleted,stores_deleted,audit_deleted,photo_cleanup_queued)
 VALUES(c.id,c.name,me->>'username',nr,ns,na,queued);
 RETURN jsonb_build_object('action','purge','ok',true,'id',c.id,'name',c.name,
   'records_deleted',nr,'stores_deleted',ns,'audit_deleted',na,'photos_queued',queued,
   'message','Data Campaign dihapus permanen. File foto yang aman dihapus disiapkan untuk pembersihan Storage.');
END $fn$;

-- Foto dihapus melalui Supabase Storage API dengan izin sementara, bukan dengan SQL langsung ke storage.objects.
CREATE OR REPLACE FUNCTION public.dco_campaign_cleanup_prepare(p_token text,p_limit integer DEFAULT 30)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); rec record; ready text[]:='{}'::text[];
 authorized text[]:='{}'::text[]; pending bigint;
BEGIN
 PERFORM dco.must_master(me);
 FOR rec IN SELECT path FROM dco.campaign_photo_cleanup WHERE removed_at IS NULL AND skipped_at IS NULL
  ORDER BY queued_at LIMIT least(50,greatest(1,coalesce(p_limit,30))) LOOP
   IF dco.photo_referenced(rec.path)
     OR EXISTS(SELECT 1 FROM dco.campaign_records r WHERE strpos(r.photo_id,rec.path)>0 OR strpos(r.payload::text,rec.path)>0)
     OR EXISTS(SELECT 1 FROM dco.campaign_audit a WHERE strpos(coalesce(a.next_data::text,''),rec.path)>0 OR strpos(coalesce(a.previous_data::text,''),rec.path)>0)
     OR EXISTS(SELECT 1 FROM dco.period_reports pr WHERE strpos(pr.evidence::text,rec.path)>0 OR strpos(pr.payload::text,rec.path)>0)
     OR EXISTS(SELECT 1 FROM dco.period_report_audit pa WHERE strpos(coalesce(pa.next_data::text,''),rec.path)>0 OR strpos(coalesce(pa.previous_data::text,''),rec.path)>0)
   THEN
     UPDATE dco.campaign_photo_cleanup SET skipped_at=now() WHERE path=rec.path;
   ELSE ready:=array_append(ready,rec.path); END IF;
 END LOOP;
 authorized:=dco.grant_trash(ready);
 SELECT count(*) INTO pending FROM dco.campaign_photo_cleanup WHERE removed_at IS NULL AND skipped_at IS NULL;
 RETURN jsonb_build_object('paths',to_jsonb(authorized),'pending',pending);
END $fn$;

CREATE OR REPLACE FUNCTION public.dco_campaign_cleanup_confirm(p_token text,p_paths text[])
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); n integer;
BEGIN
 PERFORM dco.must_master(me);
 IF coalesce(array_length(p_paths,1),0)>50 THEN RAISE EXCEPTION 'Konfirmasi file terlalu banyak'; END IF;
 UPDATE dco.campaign_photo_cleanup SET removed_at=now()
  WHERE path=ANY(coalesce(p_paths,'{}'::text[])) AND removed_at IS NULL AND skipped_at IS NULL;
 GET DIAGNOSTICS n=ROW_COUNT;
 DELETE FROM dco.photo_trash WHERE name=ANY(coalesce(p_paths,'{}'::text[]));
 RETURN jsonb_build_object('confirmed',n);
END $fn$;

CREATE OR REPLACE FUNCTION public.dco_campaign_cleanup_count(p_token text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); pending bigint; done bigint; skipped bigint;
BEGIN
 PERFORM dco.must_master(me);
 SELECT count(*) FILTER(WHERE removed_at IS NULL AND skipped_at IS NULL),
        count(*) FILTER(WHERE removed_at IS NOT NULL),count(*) FILTER(WHERE skipped_at IS NOT NULL)
 INTO pending,done,skipped FROM dco.campaign_photo_cleanup;
 RETURN jsonb_build_object('pending',pending,'done',done,'skipped_shared',skipped);
END $fn$;

-- Override RPC 014 di bawah, untuk menyembunyikan campaign di Sampah dari Store/Dashboard.
-- Placeholder replaced by tested generator; do not execute until full file is generated.
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
  WHERE c.deleted_at IS NULL AND ((me->>'is_mgr')::boolean OR EXISTS (
   SELECT 1 FROM dco.campaign_stores cs WHERE cs.campaign_id=c.id AND cs.toko=me->>'toko' AND cs.active
  ))
  ORDER BY c.start_date DESC,c.name
 ) z;
 RETURN rows;
END $fn$;

CREATE OR REPLACE FUNCTION public.dco_campaign_detail(
 p_token text,p_campaign_id uuid,p_store text DEFAULT NULL,p_from date DEFAULT NULL,p_to date DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); c dco.campaigns%ROWTYPE; stores jsonb; metrics jsonb;
 mgr boolean := (me->>'is_mgr')::boolean;
BEGIN
 SELECT * INTO c FROM dco.campaigns WHERE id=p_campaign_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'Campaign tidak ditemukan'; END IF;
 IF c.deleted_at IS NOT NULL AND NOT (me->>'is_master')::boolean THEN RAISE EXCEPTION 'Campaign sudah di Sampah'; END IF;
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

CREATE OR REPLACE FUNCTION public.dco_campaign_records(
 p_token text,p_campaign_id uuid,p_store text DEFAULT NULL,p_kind text DEFAULT NULL,
 p_from date DEFAULT NULL,p_to date DEFAULT NULL,p_limit integer DEFAULT 100,p_offset integer DEFAULT 0
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); mgr boolean := (me->>'is_mgr')::boolean;
 n integer := least(200,greatest(1,coalesce(p_limit,100))); offs integer := greatest(0,coalesce(p_offset,0));
 cnt bigint; records jsonb;
BEGIN
 IF p_kind IS NOT NULL AND p_kind NOT IN ('prospect','activity','plan','order','daily') THEN RAISE EXCEPTION 'Jenis data campaign salah'; END IF;
 IF EXISTS (SELECT 1 FROM dco.campaigns c WHERE c.id=p_campaign_id AND c.deleted_at IS NOT NULL)
   AND NOT (me->>'is_master')::boolean THEN RAISE EXCEPTION 'Campaign berada di Sampah'; END IF;
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
  IF cur.deleted_at IS NOT NULL THEN RAISE EXCEPTION 'Campaign berada di Sampah. Pulihkan sebelum edit'; END IF;
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

CREATE OR REPLACE FUNCTION public.dco_campaign_record_save(p_token text,p_campaign_id uuid,p_kind text,p_data jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE me jsonb := dco.auth(p_token); mgr boolean := (me->>'is_mgr')::boolean;
 cid uuid := p_campaign_id; store_name text; cur dco.campaign_records%ROWTYPE;
 out_row dco.campaign_records%ROWTYPE; rid uuid; op text := coalesce(p_data->>'operation','upsert');
 campaign_status text; campaign_deleted_at timestamptz; ev date; j jsonb;
BEGIN
 IF jsonb_typeof(p_data)<>'object' OR p_kind NOT IN ('prospect','activity','plan','order','daily') THEN RAISE EXCEPTION 'Form campaign tidak dikenal'; END IF;
 SELECT status,deleted_at INTO campaign_status,campaign_deleted_at FROM dco.campaigns WHERE id=cid;
 IF NOT FOUND THEN RAISE EXCEPTION 'Campaign tidak ditemukan'; END IF;
 IF campaign_deleted_at IS NOT NULL THEN RAISE EXCEPTION 'Campaign berada di Sampah. Pulihkan terlebih dahulu'; END IF;
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

REVOKE ALL ON FUNCTION public.dco_campaign_trash_list(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_delete_preview(text,uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_export_section(text,uuid,text,integer,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_manage(text,uuid,text,text,boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_cleanup_prepare(text,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_cleanup_confirm(text,text[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.dco_campaign_cleanup_count(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.dco_campaign_trash_list(text) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_delete_preview(text,uuid) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_export_section(text,uuid,text,integer,integer) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_manage(text,uuid,text,text,boolean) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_cleanup_prepare(text,integer) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_cleanup_confirm(text,text[]) TO anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.dco_campaign_cleanup_count(text) TO anon,authenticated,service_role;

COMMIT;
SELECT 'OK - Campaign v19 Trash/Restore/Purge installed; no campaign data deleted' AS result;
