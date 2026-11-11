-- Full operational modules. Apply AFTER 20261111_001_initial.sql.
-- Supabase Auth identities are provisioned separately; never migrate legacy PINs.
begin;

alter table public.issues add column if not exists verified_by uuid references auth.users(id);
alter table public.issues add column if not exists verified_at timestamptz;
alter table public.issues add column if not exists verification_notes text;
alter table public.issues add column if not exists completed_at timestamptz;
alter table public.visits add column if not exists schedule_id uuid references public.visit_schedules(id) on delete set null;
alter table public.visits add column if not exists approved_by uuid references auth.users(id);
alter table public.visits add column if not exists approved_at timestamptz;
alter table public.visits add column if not exists rating text;
alter table public.visits add column if not exists leader_name text;
alter table public.visit_points add column if not exists template_id uuid;
alter table public.checklist_entries add column if not exists validation_notes text;
alter table public.dso_reports add column if not exists submitted_by uuid references auth.users(id);

create table if not exists public.visit_templates (
 id uuid primary key default gen_random_uuid(),
 point_code text not null unique,
 section text not null,
 item_title text not null,
 description text not null default '',
 sort_order integer not null default 0,
 active boolean not null default true,
 requires_photo boolean not null default false,
 created_at timestamptz not null default now()
);
create table if not exists public.dso_form_points (
 id uuid primary key default gen_random_uuid(),
 form_code text not null check(form_code in ('OPENING','DURING','CLOSING','LAMPU')),
 point_code text not null,
 label text not null,
 description text not null default '',
 sort_order integer not null default 0,
 required boolean not null default true,
 require_photo boolean not null default true,
 active boolean not null default true,
 unique(form_code,point_code)
);
create table if not exists public.assignments (
 id uuid primary key default gen_random_uuid(),
 store_id text not null references public.stores(id),
 title text not null,
 description text,
 pic_name text not null,
 due_date date not null,
 priority text not null default 'Sedang' check(priority in ('Kritis','Tinggi','Sedang','Rendah')),
 status text not null default 'Open' check(status in ('Open','On Progress','Pending','Selesai','Dibatalkan')),
 progress integer not null default 0 check(progress between 0 and 100),
 source_id text unique,
 created_by uuid default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists public.app_settings (
 key text primary key,
 value jsonb not null,
 updated_at timestamptz not null default now()
);
-- Archive snapshots are not exposed to users. Only server-side service role can read them.
create table if not exists private.archive_batches (
 id uuid primary key default gen_random_uuid(),
 table_name text not null,
 cutoff_date date not null,
 row_count integer not null,
 sha256 text not null,
 payload jsonb not null,
 archived_at timestamptz not null default now(),
 deleted_at timestamptz,
 note text
);

insert into public.visit_templates (point_code,section,item_title,sort_order) values
('FIN-01','Finance','Cash on hand cocok dengan sistem',1),
('FIN-02','Finance','Dokumen kas, invoice, dan setoran tertib',2),
('FIN-03','Finance','Administrasi pembayaran dan petty cash',3),
('GA-01','Asset & GA','Kondisi listrik dan lampu toko',4),
('GA-02','Asset & GA','Peralatan, aset dan inventaris layak',5),
('GA-03','Asset & GA','Kebersihan, toilet dan area umum',6),
('MER-01','Merchandise','Penataan display sesuai planogram',7),
('MER-02','Merchandise','Label harga dan signage akurat',8),
('MER-03','Merchandise','Ketersediaan size/warna fast moving',9),
('HR-01','Human Resources','Kehadiran dan jadwal tim sesuai',10),
('HR-02','Human Resources','Seragam dan disiplin kerja',11),
('HR-03','Human Resources','Briefing harian dan pemahaman SOP',12),
('WH-01','Warehouse','Akurasi penempatan dan stok',13),
('WH-02','Warehouse','Area gudang rapi dan aman',14),
('WH-03','Warehouse','Alur penerimaan, transfer dan retur',15)
on conflict(point_code) do nothing;

insert into public.dso_form_points (form_code,point_code,label,sort_order) values
('OPENING','FACADE','Foto fasad / pintu masuk',1),
('OPENING','CASHIER','Foto kondisi kasir opening',2),
('OPENING','DISPLAY','Foto display area utama',3),
('DURING','SHOPFLOOR','Foto shop floor saat operasional',1),
('DURING','CUSTOMER','Foto area pelayanan pelanggan',2),
('DURING','STOCK','Foto kondisi stok / gudang',3),
('CLOSING','CASHIER','Foto kasir closing',1),
('CLOSING','SHOPFLOOR','Foto kondisi shop floor saat tutup',2),
('CLOSING','SAFETY','Foto pintu dan pengamanan',3),
('LAMPU','FRONT','Foto pencahayaan depan',1),
('LAMPU','INSIDE','Foto pencahayaan dalam',2)
on conflict(form_code,point_code) do nothing;

insert into public.app_settings(key,value) values
('dso_deadlines','{"OPENING":"09:30","DURING":"15:00","CLOSING":"23:30","LAMPU":"18:30"}'::jsonb),
('office_timezone','"Asia/Makassar"'::jsonb),
('application_name','"Assignment Control Center"'::jsonb)
on conflict(key) do nothing;

create or replace function private.guard_issue_verification() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if not private.is_manager() then
   if tg_op='UPDATE' and old.verified_at is not null then
     raise exception 'Issue sudah tervalidasi; hubungi SPV untuk revisi' using errcode='42501';
   end if;
   if new.verified_by is not null or new.verified_at is not null or new.verification_notes is not null then
     raise exception 'Hanya SPV/Master dapat memvalidasi issue' using errcode='42501';
   end if;
 end if;
 if new.verified_at is not null and new.status <> 'Selesai' then
   raise exception 'Hanya issue berstatus Selesai dapat divalidasi';
 end if;
 return new;
end $$;
create trigger issues_verify_guard before insert or update on public.issues
for each row execute function private.guard_issue_verification();

create or replace function private.audit_operational_change() returns trigger
language plpgsql security definer set search_path='' as $$
declare currentrow jsonb; formerrow jsonb; storekey text; recordid uuid;
begin
 currentrow=case when tg_op='DELETE' then null else to_jsonb(new) end;
 formerrow=case when tg_op='INSERT' then null else to_jsonb(old) end;
 storekey=coalesce(currentrow->>'store_id',formerrow->>'store_id');
 recordid=coalesce((currentrow->>'id')::uuid,(formerrow->>'id')::uuid);
 insert into public.audit_events(entity,entity_id,operation,store_id,actor_id,changed_fields)
 values (tg_table_name,recordid,tg_op,storekey,auth.uid(),jsonb_build_object('old',formerrow,'new',currentrow));
 return case when tg_op='DELETE' then old else new end;
end $$;
create trigger issue_audit after insert or update or delete on public.issues for each row execute function private.audit_operational_change();
create trigger visit_audit after insert or update or delete on public.visits for each row execute function private.audit_operational_change();
create trigger checklist_audit after insert or update or delete on public.checklist_entries for each row execute function private.audit_operational_change();
create trigger dso_audit after insert or update or delete on public.dso_reports for each row execute function private.audit_operational_change();
create trigger assignment_audit after insert or update or delete on public.assignments for each row execute function private.audit_operational_change();
create trigger assignments_touch before update on public.assignments for each row execute function private.touch_updated_at();

create index if not exists idx_assignment_store_due on public.assignments(store_id,due_date);
create index if not exists idx_visit_points_visit on public.visit_points(visit_id,point_code);
create index if not exists idx_issue_visit on public.issues(visit_id) where visit_id is not null;
create index if not exists idx_issue_verify on public.issues(verified_at) where status='Selesai';

revoke all on public.visit_templates,public.dso_form_points,public.assignments,public.app_settings from anon;
grant select on public.visit_templates,public.dso_form_points,public.app_settings to authenticated;
grant insert,update,delete on public.visit_templates,public.dso_form_points,public.app_settings to authenticated;
grant select,insert,update on public.assignments,public.checklist_templates to authenticated;
alter table public.visit_templates enable row level security;
alter table public.dso_form_points enable row level security;
alter table public.assignments enable row level security;
alter table public.app_settings enable row level security;
create policy vt_read on public.visit_templates for select to authenticated using(true);
create policy vt_write on public.visit_templates for all to authenticated using((select private.role_name())='master') with check((select private.role_name())='master');
create policy dp_read on public.dso_form_points for select to authenticated using(true);
create policy dp_write on public.dso_form_points for all to authenticated using((select private.role_name())='master') with check((select private.role_name())='master');
create policy as_read on public.assignments for select to authenticated using((select private.can_access_store(store_id)));
create policy as_add on public.assignments for insert to authenticated with check((select private.can_access_store(store_id)));
create policy as_edit on public.assignments for update to authenticated using((select private.can_access_store(store_id))) with check((select private.can_access_store(store_id)));
create policy set_read on public.app_settings for select to authenticated using(true);
create policy set_write on public.app_settings for all to authenticated using((select private.role_name())='master') with check((select private.role_name())='master');
create policy checklist_template_write on public.checklist_templates for all to authenticated using((select private.role_name())='master') with check((select private.role_name())='master');

-- Server-validated atomic submission: visit + point observations + related issues.
create or replace function public.submit_visit_bundle(p_visit jsonb,p_points jsonb,p_issues jsonb)
returns uuid language plpgsql security definer set search_path='' as $$
declare vid uuid; point jsonb; issue jsonb; storekey text; pointid uuid; answer_count integer:=0;
begin
 storekey=nullif(trim(p_visit->>'store_id'),'');
 if storekey is null or not private.is_manager() or not private.can_access_store(storekey) then
  raise exception 'Tidak berhak membuat visit untuk toko ini' using errcode='42501';
 end if;
 if jsonb_typeof(p_points) <> 'array' or jsonb_array_length(p_points)=0 or jsonb_array_length(p_points)>100 then
  raise exception 'Form visit harus berisi 1-100 checkpoint';
 end if;
 if jsonb_typeof(p_issues) <> 'array' or jsonb_array_length(p_issues)>150 then
  raise exception 'Format issue visit tidak valid (maksimal 150)';
 end if;
 insert into public.visits(store_id,visit_date,evaluator_name,visit_type,status,notes,leader_name,created_by)
 values(storekey,(p_visit->>'visit_date')::date,trim(p_visit->>'evaluator_name'),nullif(p_visit->>'visit_type',''),'Selesai',p_visit->>'notes',p_visit->>'leader_name',auth.uid()) returning id into vid;
 for point in select value from jsonb_array_elements(p_points) loop
  if (point->>'result') not in ('Sesuai','Tidak Sesuai','N/A','Belum') then
   raise exception 'Status checkpoint tidak valid';
  end if;
  if nullif(point->>'point_code','') is null or nullif(point->>'item_title','') is null then
   raise exception 'Kode dan judul checkpoint wajib';
  end if;
  if point->>'result' <> 'Belum' then answer_count:=answer_count+1;end if;
  if nullif(point->>'photo_path','') is not null and split_part(point->>'photo_path','/',1)<>storekey then
   raise exception 'Path foto tidak sesuai toko';
  end if;
  insert into public.visit_points(visit_id,point_code,section,item_title,result,notes,photo_path)
  values(vid,point->>'point_code',coalesce(point->>'section','General'),point->>'item_title',point->>'result',point->>'notes',point->>'photo_path');
 end loop;
 if answer_count=0 then raise exception 'Jawab minimal satu checkpoint visit';end if;
 for issue in select value from jsonb_array_elements(p_issues) loop
  if nullif(trim(issue->>'title'),'') is null or nullif(trim(issue->>'pic_name'),'') is null or nullif(issue->>'due_date','') is null then
   raise exception 'Issue visit wajib memuat temuan, PIC dan due date';
  end if;
  pointid=null;
  if nullif(issue->>'point_code','') is not null then
   select id into pointid from public.visit_points where visit_id=vid and point_code=(issue->>'point_code');
   if pointid is null then raise exception 'Point issue tidak cocok dengan visit';end if;
  end if;
  insert into public.issues(store_id,origin,visit_id,visit_point_id,title,category,root_cause,action_plan,pic_name,due_date,priority,status,progress,note,created_by)
  values(storekey,'visit',vid,pointid,trim(issue->>'title'),coalesce(nullif(issue->>'category',''),'Operasional'),issue->>'root_cause',issue->>'action_plan',trim(issue->>'pic_name'),(issue->>'due_date')::date,coalesce(nullif(issue->>'priority',''),'Sedang'),'Open',0,issue->>'note',auth.uid());
 end loop;
 -- Enforce Pending Matter for every checklist item marked tidak sesuai.
 if exists (select 1 from public.visit_points p where p.visit_id=vid and p.result='Tidak Sesuai'
             and not exists(select 1 from public.issues i where i.visit_point_id=p.id)) then
  raise exception 'Setiap point Tidak Sesuai wajib memiliki issue + PIC + due date';
 end if;
 update public.visits set score=(select round(100.0*count(*) filter(where result='Sesuai')/nullif(count(*) filter(where result in ('Sesuai','Tidak Sesuai')),0),2)
                                 from public.visit_points where visit_id=vid)
 where id=vid;
 return vid;
end $$;
revoke all on function public.submit_visit_bundle(jsonb,jsonb,jsonb) from public,anon;
grant execute on function public.submit_visit_bundle(jsonb,jsonb,jsonb) to authenticated;

-- Return signed-in user's access rights to a store, never grant access via UI alone.
create or replace function public.my_stores() returns setof public.stores
language sql stable security invoker set search_path='' as $$
 select s.* from public.stores s where private.can_access_store(s.id) and s.is_active=true order by s.name;
$$;
grant execute on function public.my_stores() to authenticated;

commit;
