-- Assignment Control Center / Tigalapan Indonesia
-- Initial database model. Review in staging before applying to production.
-- All times use timestamptz (UTC internally). Business dates use DATE, WITA in UI.
begin;
create extension if not exists pgcrypto;
create schema if not exists private;

create table if not exists public.stores (
 id text primary key,
 name text not null unique,
 brand text not null,
 region text not null,
 is_active boolean not null default true,
 created_at timestamptz not null default now()
);
insert into public.stores(id,name,brand,region) values
('t01','TIGALAPANKAOS BTP','Tigalapankaos','Makassar'),
('m02','MAMU BTP','MAMU','Makassar'),
('m03','MAMU PALOPO','MAMU','Palopo'),
('t04','TIGALAPANKAOS PALU','Tigalapankaos','Palu'),
('m05','MAMU TAMALATE','MAMU','Makassar'),
('t06','TIGALAPANKAOS MANADO','Tigalapankaos','Manado'),
('t07','TIGALAPANKAOS SAMARINDA','Tigalapankaos','Samarinda'),
('m08','MAMU KENDARI','MAMU','Kendari'),
('t09','TIGALAPANKAOS POLMAN','Tigalapankaos','Polewali Mandar'),
('t10','TIGALAPANKAOS BONE','Tigalapankaos','Bone'),
('m11','MAMU GOWA','MAMU','Gowa'),
('t12','TIGALAPANKAOS TORAJA','Tigalapankaos','Toraja')
on conflict (id) do update set name=excluded.name,brand=excluded.brand,region=excluded.region;

create table if not exists public.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 display_name text not null,
 role text not null check (role in ('master','spv','store')),
 store_id text references public.stores(id),
 active boolean not null default true,
 created_at timestamptz not null default now(),
 constraint store_profile_requires_store check (role<>'store' or store_id is not null)
);
create table if not exists public.spv_store_assignments (
 profile_id uuid not null references public.profiles(id) on delete cascade,
 store_id text not null references public.stores(id),
 primary key(profile_id,store_id)
);
-- Security definer functions are isolated in the non-exposed 'private' schema.
create or replace function private.role_name() returns text
 language sql stable security definer set search_path = '' as $$
 select p.role from public.profiles p where p.id=(select auth.uid()) and p.active=true limit 1
 $$;
create or replace function private.can_access_store(p_store_id text) returns boolean
 language sql stable security definer set search_path = '' as $$
 select exists (
  select 1 from public.profiles p where p.id=(select auth.uid()) and p.active=true
  and (
    p.role='master'
    or (p.role='spv' and (not exists(select 1 from public.spv_store_assignments a where a.profile_id=p.id)
         or exists(select 1 from public.spv_store_assignments a where a.profile_id=p.id and a.store_id=p_store_id)))
    or (p.role='store' and p.store_id=p_store_id)
  )
 )
 $$;
create or replace function private.is_manager() returns boolean
 language sql stable security definer set search_path = '' as $$
 select coalesce(private.role_name() in ('master','spv'),false)
 $$;
revoke all on schema private from public;
grant usage on schema private to authenticated;
grant execute on function private.role_name() to authenticated;
grant execute on function private.can_access_store(text) to authenticated;
grant execute on function private.is_manager() to authenticated;

create table if not exists public.briefings (
 id uuid primary key default gen_random_uuid(),
 store_id text not null references public.stores(id),
 briefing_date date not null,
 shift text not null default 'Pagi' check (shift in ('Pagi','Siang','Sore','Malam')),
 leader text not null default '',
 participants integer not null default 0 check (participants>=0),
 no_findings boolean not null default false,
 notes text not null default '',
 created_by uuid default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique (store_id,briefing_date,shift)
);
create table if not exists public.visits (
 id uuid primary key default gen_random_uuid(),
 store_id text not null references public.stores(id),
 visit_date date not null,
 evaluator_name text not null,
 visit_type text,
 score numeric(5,2) check (score between 0 and 100),
 status text not null default 'Open' check (status in ('Open','On Progress','Selesai','Dibatalkan')),
 notes text,
 source_id text unique,
 created_by uuid default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists public.visit_points (
 id uuid primary key default gen_random_uuid(),
 visit_id uuid not null references public.visits(id) on delete cascade,
 point_code text not null,
 section text not null,
 item_title text not null,
 result text not null default 'Belum' check(result in ('Sesuai','Tidak Sesuai','N/A','Belum')),
 notes text,
 photo_path text,
 created_at timestamptz not null default now(),
 unique(visit_id,point_code)
);
create table if not exists public.issues (
 id uuid primary key default gen_random_uuid(),
 store_id text not null references public.stores(id),
 origin text not null default 'briefing' check(origin in ('briefing','visit','other')),
 briefing_id uuid references public.briefings(id) on delete set null,
 visit_id uuid references public.visits(id) on delete set null,
 visit_point_id uuid references public.visit_points(id) on delete set null,
 title text not null check(length(trim(title))>=4),
 category text not null default 'Lainnya',
 root_cause text,
 action_plan text,
 pic_name text,
 due_date date,
 priority text not null default 'Sedang' check(priority in ('Kritis','Tinggi','Sedang','Rendah')),
 status text not null default 'Open' check(status in ('Open','On Progress','Pending','Selesai','Dibatalkan')),
 progress integer not null default 0 check(progress between 0 and 100),
 note text,
 photo_path text,
 legacy_source_id text unique,
 closed_at timestamptz,
 created_by uuid default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists public.visit_schedules (
 id uuid primary key default gen_random_uuid(),
 store_id text not null references public.stores(id),
 visit_date date not null,
 start_time time not null,
 end_time time not null,
 pic_name text not null,
 agenda text not null,
 status text not null default 'Rencana' check(status in ('Rencana','Selesai','Batal')),
 notes text,
 source_id text unique,
 created_by uuid default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 constraint visit_time_forward check(end_time>start_time)
);
create table if not exists public.checklist_templates (
 id uuid primary key default gen_random_uuid(),
 store_id text references public.stores(id),
 title text not null,
 description text,
 category text,
 frequency text not null default 'Harian',
 priority text not null default 'Sedang',
 active boolean not null default true,
 source_id text unique,
 created_at timestamptz not null default now()
);
create table if not exists public.checklist_entries (
 id uuid primary key default gen_random_uuid(),
 store_id text not null references public.stores(id),
 check_date date not null,
 template_id uuid references public.checklist_templates(id),
 title text not null,
 status text not null default 'Belum' check(status in ('Belum','Selesai')),
 note text,
 photo_path text,
 completed_at timestamptz,
 validated_by uuid references auth.users(id),
 validated_at timestamptz,
 source_id text unique,
 created_by uuid default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(store_id,check_date,template_id)
);
create table if not exists public.dso_reports (
 id uuid primary key default gen_random_uuid(),
 store_id text not null references public.stores(id),
 report_date date not null,
 form_code text not null check(form_code in ('OPENING','DURING','CLOSING','LAMPU')),
 status text not null default 'Submitted' check(status in ('Submitted','Approved','Rejected')),
 answers jsonb not null default '{}'::jsonb,
 notes text,
 submitted_at timestamptz not null default now(),
 validated_by uuid references auth.users(id),
 validated_at timestamptz,
 validation_notes text,
 source_id text unique,
 created_by uuid default auth.uid() references auth.users(id),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(store_id,report_date,form_code)
);
create table if not exists public.audit_events (
 id bigint generated always as identity primary key,
 entity text not null,
 entity_id uuid,
 operation text not null,
 store_id text,
 actor_id uuid,
 changed_at timestamptz not null default now(),
 changed_fields jsonb not null default '{}'::jsonb
);

create or replace function private.touch_updated_at() returns trigger
 language plpgsql set search_path='' as $$
 begin new.updated_at=now();return new;end $$;
create or replace function private.guard_checklist_validation() returns trigger
 language plpgsql security definer set search_path='' as $$
 begin
 if not private.is_manager() and (new.validated_by is distinct from old.validated_by or new.validated_at is distinct from old.validated_at)
 then raise exception 'Validation requires manager role' using errcode='42501';end if;
 return new;
 end $$;
create or replace function private.guard_dso_validation() returns trigger
 language plpgsql security definer set search_path='' as $$
 begin
 if not private.is_manager() and (new.validated_by is distinct from old.validated_by or new.validated_at is distinct from old.validated_at or new.validation_notes is distinct from old.validation_notes or new.status in ('Approved','Rejected'))
 then raise exception 'DSO validation requires manager role' using errcode='42501';end if;
 return new;
 end $$;
create or replace function private.handle_issue_completion() returns trigger
 language plpgsql set search_path='' as $$
 begin
 if new.status='Selesai' and (tg_op='INSERT' or old.status is distinct from new.status) then
  new.progress=100;new.closed_at=now();
 elsif new.status<>'Selesai' and tg_op='UPDATE' and old.status='Selesai' then new.closed_at=null;
 end if;
 return new;
 end $$;

create trigger briefings_touch before update on public.briefings for each row execute function private.touch_updated_at();
create trigger visits_touch before update on public.visits for each row execute function private.touch_updated_at();
create trigger issues_touch before update on public.issues for each row execute function private.touch_updated_at();
create trigger schedules_touch before update on public.visit_schedules for each row execute function private.touch_updated_at();
create trigger checklists_touch before update on public.checklist_entries for each row execute function private.touch_updated_at();
create trigger dso_touch before update on public.dso_reports for each row execute function private.touch_updated_at();
create trigger issues_complete before insert or update on public.issues for each row execute function private.handle_issue_completion();
create trigger checklist_validation_guard before update on public.checklist_entries for each row execute function private.guard_checklist_validation();
create trigger dso_validation_guard before update on public.dso_reports for each row execute function private.guard_dso_validation();

create index if not exists idx_briefings_date_store on public.briefings(briefing_date desc,store_id);
create index if not exists idx_issue_store_status_due on public.issues(store_id,status,due_date);
create index if not exists idx_issue_priority on public.issues(priority,due_date) where status not in ('Selesai','Dibatalkan');
create index if not exists idx_visit_date on public.visits(visit_date desc,store_id);
create index if not exists idx_schedule_date on public.visit_schedules(visit_date,store_id);
create index if not exists idx_checklist_date on public.checklist_entries(check_date desc,store_id);
create index if not exists idx_dso_date on public.dso_reports(report_date desc,store_id);

-- Revocation first. Never grant anonymous access to operational data.
revoke all on all tables in schema public from anon;
revoke all on all tables in schema public from authenticated;
grant select on public.stores to authenticated;
grant select on public.profiles to authenticated;
grant select on public.spv_store_assignments to authenticated;
grant select,insert,update on public.briefings, public.visits, public.visit_points, public.issues,
 public.visit_schedules, public.checklist_entries, public.dso_reports to authenticated;
grant select on public.checklist_templates to authenticated;
grant select on public.audit_events to authenticated;

alter table public.stores enable row level security;
alter table public.profiles enable row level security;
alter table public.spv_store_assignments enable row level security;
alter table public.briefings enable row level security;
alter table public.visits enable row level security;
alter table public.visit_points enable row level security;
alter table public.issues enable row level security;
alter table public.visit_schedules enable row level security;
alter table public.checklist_templates enable row level security;
alter table public.checklist_entries enable row level security;
alter table public.dso_reports enable row level security;
alter table public.audit_events enable row level security;

create policy store_catalog on public.stores for select to authenticated using (true);
create policy profiles_read on public.profiles for select to authenticated using (id=(select auth.uid()) or (select private.is_manager()));
create policy assignments_read on public.spv_store_assignments for select to authenticated using (profile_id=(select auth.uid()) or (select private.is_manager()));
create policy templates_read on public.checklist_templates for select to authenticated using (store_id is null or (select private.can_access_store(store_id)));
create policy audit_read on public.audit_events for select to authenticated using (store_id is null and (select private.is_manager()) or (select private.can_access_store(store_id)));

create policy briefing_read on public.briefings for select to authenticated using ((select private.can_access_store(store_id)));
create policy briefing_add on public.briefings for insert to authenticated with check ((select private.can_access_store(store_id)));
create policy briefing_edit on public.briefings for update to authenticated using ((select private.can_access_store(store_id))) with check ((select private.can_access_store(store_id)));
create policy visit_read on public.visits for select to authenticated using ((select private.can_access_store(store_id)));
create policy visit_add on public.visits for insert to authenticated with check ((select private.is_manager()) and (select private.can_access_store(store_id)));
create policy visit_edit on public.visits for update to authenticated using ((select private.is_manager()) and (select private.can_access_store(store_id))) with check ((select private.is_manager()) and (select private.can_access_store(store_id)));
create policy points_read on public.visit_points for select to authenticated using (exists(select 1 from public.visits v where v.id=visit_id and (select private.can_access_store(v.store_id))));
create policy points_add on public.visit_points for insert to authenticated with check ((select private.is_manager()) and exists(select 1 from public.visits v where v.id=visit_id and (select private.can_access_store(v.store_id))));
create policy points_edit on public.visit_points for update to authenticated using ((select private.is_manager()) and exists(select 1 from public.visits v where v.id=visit_id and (select private.can_access_store(v.store_id)))) with check ((select private.is_manager()) and exists(select 1 from public.visits v where v.id=visit_id and (select private.can_access_store(v.store_id))));
create policy issues_read on public.issues for select to authenticated using ((select private.can_access_store(store_id)));
create policy issues_add on public.issues for insert to authenticated with check ((select private.can_access_store(store_id)));
create policy issues_edit on public.issues for update to authenticated using ((select private.can_access_store(store_id))) with check ((select private.can_access_store(store_id)));
create policy schedules_read on public.visit_schedules for select to authenticated using ((select private.can_access_store(store_id)));
create policy schedules_add on public.visit_schedules for insert to authenticated with check ((select private.is_manager()) and (select private.can_access_store(store_id)));
create policy schedules_edit on public.visit_schedules for update to authenticated using ((select private.is_manager()) and (select private.can_access_store(store_id))) with check ((select private.is_manager()) and (select private.can_access_store(store_id)));
create policy checklists_read on public.checklist_entries for select to authenticated using ((select private.can_access_store(store_id)));
create policy checklists_add on public.checklist_entries for insert to authenticated with check ((select private.can_access_store(store_id)));
create policy checklists_edit on public.checklist_entries for update to authenticated using ((select private.can_access_store(store_id))) with check ((select private.can_access_store(store_id)));
create policy dso_read on public.dso_reports for select to authenticated using ((select private.can_access_store(store_id)));
create policy dso_add on public.dso_reports for insert to authenticated with check ((select private.can_access_store(store_id)));
create policy dso_edit on public.dso_reports for update to authenticated using ((select private.can_access_store(store_id))) with check ((select private.can_access_store(store_id)));

-- Supabase Storage: PRIVATE bucket; path convention store_id/module/yyyy-mm/uuid.jpg.
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
 values ('store-evidence','store-evidence',false,8388608,array['image/jpeg','image/png','image/webp'])
 on conflict (id) do nothing;
create policy store_evidence_read on storage.objects for select to authenticated
 using(bucket_id='store-evidence' and (select private.can_access_store(split_part(name,'/',1))));
create policy store_evidence_add on storage.objects for insert to authenticated
 with check(bucket_id='store-evidence' and (select private.can_access_store(split_part(name,'/',1))));
create policy store_evidence_edit on storage.objects for update to authenticated
 using(bucket_id='store-evidence' and (select private.can_access_store(split_part(name,'/',1))))
 with check(bucket_id='store-evidence' and (select private.can_access_store(split_part(name,'/',1))));

commit;
