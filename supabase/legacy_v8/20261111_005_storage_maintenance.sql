-- Assignment Control Center: safe exports, archival and controlled cleanup.
-- Execute after migrations 001-004. NO existing records are deleted by this migration.
begin;

create table if not exists private.maintenance_batches (
 id uuid primary key default gen_random_uuid(),
 source_table text not null,
 store_id text,
 cutoff_date date not null,
 row_count integer not null check(row_count>=0),
 sha256 text,
 status text not null default 'archived' check(status in ('archived','purged')),
 archived_by uuid,
 archived_at timestamptz not null default now(),
 purged_at timestamptz,
 note text
);
create table if not exists private.maintenance_rows (
 batch_id uuid not null references private.maintenance_batches(id) on delete cascade,
 source_id uuid not null,
 row_text text not null,
 primary key(batch_id,source_id)
);
create index if not exists idx_maintenance_batches_created on private.maintenance_batches(archived_at desc);

-- Only completed, validated and sufficiently old rows qualify for archive.
-- Referential parent tables (briefings/visits) and master/config data are excluded.
create or replace function private.maintenance_eligible_ids(
 p_table text,p_cutoff date,p_store_id text default null
) returns setof uuid language plpgsql stable security definer set search_path='' as $$
begin
 case p_table
  when 'issues' then
   return query select t.id from public.issues t
   where t.status='Selesai' and t.verified_at is not null
     and coalesce(t.closed_at::date,t.updated_at::date)<p_cutoff
     and (p_store_id is null or t.store_id=p_store_id);
  when 'checklist_entries' then
   return query select t.id from public.checklist_entries t
   where t.status='Selesai' and t.validated_at is not null
     and t.check_date<p_cutoff and (p_store_id is null or t.store_id=p_store_id);
  when 'dso_reports' then
   return query select t.id from public.dso_reports t
   where t.status='Approved' and t.validated_at is not null
     and t.report_date<p_cutoff and (p_store_id is null or t.store_id=p_store_id);
  when 'visit_schedules' then
   return query select t.id from public.visit_schedules t
   where t.status in ('Selesai','Batal') and t.visit_date<p_cutoff
     and (p_store_id is null or t.store_id=p_store_id);
  when 'assignments' then
   return query select t.id from public.assignments t
   where t.status='Selesai' and t.progress=100 and t.due_date<p_cutoff
     and (p_store_id is null or t.store_id=p_store_id);
  else
   raise exception 'Dataset tidak diizinkan untuk arsip: %',p_table using errcode='22023';
 end case;
end $$;
revoke all on function private.maintenance_eligible_ids(text,date,text) from public,anon,authenticated;

create or replace function private.maintenance_guard(p_table text,p_cutoff date)
returns void language plpgsql stable security definer set search_path='' as $$
begin
 if private.role_name() is distinct from 'master' then
   raise exception 'Hanya Master yang dapat melakukan manajemen arsip' using errcode='42501';
 end if;
 if p_table not in ('issues','checklist_entries','dso_reports','visit_schedules','assignments') then
   raise exception 'Dataset tidak dikenal' using errcode='22023';
 end if;
 if p_cutoff is null or p_cutoff>(now() at time zone 'Asia/Makassar')::date - 90 then
   raise exception 'Batas arsip harus minimal 90 hari sebelum hari ini' using errcode='22023';
 end if;
end $$;
revoke all on function private.maintenance_guard(text,date) from public,anon,authenticated;

create or replace function public.maintenance_preview(
 p_table text,p_cutoff date,p_store_id text default null
) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare n bigint;
begin
 perform private.maintenance_guard(p_table,p_cutoff);
 if p_store_id is not null and not exists(select 1 from public.stores s where s.id=p_store_id) then
  raise exception 'Toko tidak ditemukan' using errcode='22023';
 end if;
 select count(*) into n from private.maintenance_eligible_ids(p_table,p_cutoff,p_store_id);
 return jsonb_build_object('table',p_table,'cutoff',p_cutoff,'store',p_store_id,
   'eligible',n,'max_per_batch',2000,'minimum_retention_days',90,
   'notice','Hanya data selesai dan memenuhi syarat. Data aktif dan master tidak termasuk.');
end $$;

create or replace function public.maintenance_archive(
 p_table text,p_cutoff date,p_store_id text,p_expected integer,p_phrase text
) returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare n integer; copied integer; deleted integer; bid uuid; hash text;
begin
 perform private.maintenance_guard(p_table,p_cutoff);
 if p_phrase is distinct from 'ARSIP DATA SELESAI' then
   raise exception 'Konfirmasi arsip tidak sesuai' using errcode='22023';
 end if;
 if p_store_id is not null and not exists(select 1 from public.stores where id=p_store_id) then
   raise exception 'Toko tidak dikenal' using errcode='22023';
 end if;
 -- Concurrency lock. It is short and atomic; failed verification rolls back all changes.
 perform pg_advisory_xact_lock(hashtext('tigalapan:archive:' || p_table));
 execute format('lock table public.%I in share row exclusive mode',p_table);
 select count(*) into n from private.maintenance_eligible_ids(p_table,p_cutoff,p_store_id);
 if n=0 then raise exception 'Tidak ada data yang memenuhi kriteria arsip';end if;
 if n>2000 then raise exception 'Terlalu banyak data (%). Perkecil periode atau pilih satu toko (maks. 2000)',n;end if;
 if p_expected is distinct from n then
   raise exception 'Jumlah berubah dari preview (% menjadi %). Jalankan Preview ulang.',p_expected,n;
 end if;
 insert into private.maintenance_batches(source_table,store_id,cutoff_date,row_count,archived_by)
 values(p_table,p_store_id,p_cutoff,n,auth.uid()) returning id into bid;
 execute format($q$
  insert into private.maintenance_rows(batch_id,source_id,row_text)
  select $1,t.id,to_jsonb(t)::text from public.%I t
  join private.maintenance_eligible_ids($2,$3,$4) as e(eligible_id) on e.eligible_id=t.id
 $q$,p_table) using bid,p_table,p_cutoff,p_store_id;
 get diagnostics copied=row_count;
 if copied<>n then raise exception 'Salinan tidak lengkap (% dari %), perubahan dibatalkan',copied,n;end if;
 select encode(sha256(convert_to(coalesce(string_agg(row_text,E'\n' order by source_id),''),'UTF8')),'hex')
 into hash from private.maintenance_rows where batch_id=bid;
 update private.maintenance_batches set sha256=hash where id=bid;
 execute format($q$
  delete from public.%I t using private.maintenance_rows snap
  where snap.batch_id=$1 and snap.source_id=t.id
 $q$,p_table) using bid;
 get diagnostics deleted=row_count;
 if deleted<>n then raise exception 'Jumlah terhapus tidak sama dengan backup (% vs %), rollback',deleted,n;end if;
 return jsonb_build_object('batch_id',bid,'archived',n,'sha256',hash,
    'status','archived','notice','Backup sementara ada di database. Export JSONL sebelum melakukan purge permanen.');
end $$;

create or replace function public.maintenance_history()
returns table(batch_id uuid,source_table text,store_id text,cutoff_date date,
 row_count integer,sha256 text,status text,archived_at timestamptz,purged_at timestamptz)
language plpgsql stable security definer set search_path='' as $$
begin
 if private.role_name() is distinct from 'master' then
  raise exception 'Hanya Master dapat melihat histori arsip' using errcode='42501';
 end if;
 return query select b.id,b.source_table,b.store_id,b.cutoff_date,b.row_count,b.sha256,b.status,b.archived_at,b.purged_at
  from private.maintenance_batches b order by b.archived_at desc limit 100;
end $$;

-- Export is paginated. The SQL string is the original canonical JSON snapshot.
-- It can be SHA256 checked before final deletion; file includes paths, not photo binary.
create or replace function public.maintenance_download_batch(
 p_batch uuid,p_offset integer default 0,p_limit integer default 250
) returns table(line_no bigint,row_text text)
language plpgsql stable security definer set search_path='' as $$
begin
 if private.role_name() is distinct from 'master' then
  raise exception 'Hanya Master dapat mengunduh arsip' using errcode='42501';
 end if;
 if p_offset<0 or p_limit<1 or p_limit>500 then
  raise exception 'Parameter halaman tidak valid' using errcode='22023';
 end if;
 return query select row_number() over(order by m.source_id)+p_offset,m.row_text
  from (select r.source_id,r.row_text from private.maintenance_rows r
        where r.batch_id=p_batch order by r.source_id offset p_offset limit p_limit) m;
end $$;

-- Physical purge only of archived copies, never of active records.
-- 24h safety delay and exact hash + typed confirmation required.
create or replace function public.maintenance_purge_archive(
 p_batch uuid,p_sha256 text,p_phrase text
) returns jsonb language plpgsql volatile security definer set search_path='' as $$
declare b private.maintenance_batches%rowtype; checksum text; removed integer;
begin
 if private.role_name() is distinct from 'master' then
   raise exception 'Hanya Master dapat menghapus arsip' using errcode='42501';
 end if;
 select * into b from private.maintenance_batches where id=p_batch for update;
 if not found or b.status<>'archived' then raise exception 'Arsip tidak ditemukan / sudah dihapus';end if;
 if b.archived_at>now()-interval '24 hours' then
   raise exception 'Arsip hanya boleh dihapus minimal 24 jam setelah dibuat';
 end if;
 if p_phrase is distinct from 'HAPUS ARSIP PERMANEN' then
   raise exception 'Kalimat konfirmasi tidak sesuai';end if;
 if p_sha256 is distinct from b.sha256 then
   raise exception 'SHA256 backup tidak cocok. Unduh dan verifikasi ulang.';end if;
 select encode(sha256(convert_to(coalesce(string_agg(row_text,E'\n' order by source_id),''),'UTF8')),'hex')
 into checksum from private.maintenance_rows where batch_id=p_batch;
 if checksum is distinct from b.sha256 then raise exception 'Integritas arsip gagal';end if;
 delete from private.maintenance_rows where batch_id=p_batch;
 get diagnostics removed=row_count;
 if removed<>b.row_count then raise exception 'Arsip tidak lengkap, rollback';end if;
 update private.maintenance_batches set status='purged',purged_at=now() where id=p_batch;
 return jsonb_build_object('purged',removed,'batch_id',p_batch,'hash',checksum);
end $$;

-- Counts are deliberately approximate for physical bytes, exact for row totals.
create or replace function public.maintenance_usage()
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare r jsonb; photo_bytes bigint; archive_bytes bigint;
begin
 if private.role_name() is distinct from 'master' then
  raise exception 'Hanya Master dapat melihat penyimpanan' using errcode='42501';end if;
 select jsonb_build_object(
  'issues', (select count(*) from public.issues),
  'briefings',(select count(*) from public.briefings),
  'visits',(select count(*) from public.visits),
  'visit_points',(select count(*) from public.visit_points),
  'checklists',(select count(*) from public.checklist_entries),
  'dso',(select count(*) from public.dso_reports),
  'schedules',(select count(*) from public.visit_schedules),
  'assignments',(select count(*) from public.assignments),
  'archive_batches',(select count(*) from private.maintenance_batches where status='archived'),
  'archive_rows',(select count(*) from private.maintenance_rows)
 ) into r;
 select coalesce(sum(nullif(metadata->>'size','')::bigint),0) into photo_bytes
  from storage.objects where bucket_id='store-evidence';
 archive_bytes:=pg_total_relation_size('private.maintenance_rows'::regclass);
 return jsonb_build_object('rows',r,'photo_bytes',photo_bytes,'archive_table_bytes',archive_bytes,
  'active_table_bytes',pg_total_relation_size('public.issues'::regclass)
     +pg_total_relation_size('public.checklist_entries'::regclass)
     +pg_total_relation_size('public.dso_reports'::regclass)
     +pg_total_relation_size('public.visit_schedules'::regclass)
     +pg_total_relation_size('public.assignments'::regclass),
  'photo_notice','Foto hanya boleh dihapus setelah dipastikan tidak direferensikan data aktif maupun arsip.');
end $$;

revoke all on function public.maintenance_preview(text,date,text) from public,anon;
revoke all on function public.maintenance_archive(text,date,text,integer,text) from public,anon;
revoke all on function public.maintenance_history() from public,anon;
revoke all on function public.maintenance_download_batch(uuid,integer,integer) from public,anon;
revoke all on function public.maintenance_purge_archive(uuid,text,text) from public,anon;
revoke all on function public.maintenance_usage() from public,anon;
grant execute on function public.maintenance_preview(text,date,text) to authenticated;
grant execute on function public.maintenance_archive(text,date,text,integer,text) to authenticated;
grant execute on function public.maintenance_history() to authenticated;
grant execute on function public.maintenance_download_batch(uuid,integer,integer) to authenticated;
grant execute on function public.maintenance_purge_archive(uuid,text,text) to authenticated;
grant execute on function public.maintenance_usage() to authenticated;
commit;
