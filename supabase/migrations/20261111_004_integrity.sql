-- Safety hardening for standalone Supabase deployment (no Google Apps Script).
begin;

-- Prevent a single briefing slot from generating duplicate issue sets on repeated submissions.
create or replace function public.submit_briefing_bundle(p_briefing jsonb,p_issues jsonb)
returns uuid language plpgsql security definer set search_path='' as $$
declare bid uuid; storekey text; rowdata jsonb; issuecount integer; existing_count integer;
begin
 storekey=nullif(trim(p_briefing->>'store_id'),'');
 if storekey is null or not private.can_access_store(storekey) then
   raise exception 'Tidak berhak membuat briefing toko ini' using errcode='42501';
 end if;
 if nullif(p_briefing->>'briefing_date','') is null then raise exception 'Tanggal briefing wajib';end if;
 if jsonb_typeof(p_issues) <> 'array' or jsonb_array_length(p_issues)>50 then
   raise exception 'Format daftar masalah harus array maksimal 50';
 end if;
 issuecount=jsonb_array_length(p_issues);
 if coalesce((p_briefing->>'no_findings')::boolean,false) and issuecount<>0 then
   raise exception 'Briefing NIHIL tidak boleh memuat issue';end if;
 if not coalesce((p_briefing->>'no_findings')::boolean,false) and issuecount=0 then
   raise exception 'Briefing harus berisi minimal satu issue atau memilih NIHIL';end if;
 select id into bid from public.briefings
 where store_id=storekey and briefing_date=(p_briefing->>'briefing_date')::date
 and shift=coalesce(nullif(p_briefing->>'shift',''),'Pagi') for update;
 if bid is not null then
   select count(*) into existing_count from public.issues where briefing_id=bid;
   if existing_count>0 or issuecount>0 then
     raise exception 'Briefing tanggal/shift ini sudah ada. Ubah issue melalui Action Plan agar tidak duplikat';
   end if;
   update public.briefings set leader=trim(coalesce(p_briefing->>'leader','')),
    participants=coalesce((p_briefing->>'participants')::int,0),
    no_findings=true,notes=coalesce(p_briefing->>'notes','') where id=bid;
   return bid;
 end if;
 insert into public.briefings(store_id,briefing_date,shift,leader,participants,no_findings,notes,created_by)
 values(storekey,(p_briefing->>'briefing_date')::date,
  coalesce(nullif(p_briefing->>'shift',''),'Pagi'),
  trim(coalesce(p_briefing->>'leader','')),
  coalesce((p_briefing->>'participants')::int,0),
  coalesce((p_briefing->>'no_findings')::boolean,false),
  coalesce(p_briefing->>'notes',''),auth.uid()) returning id into bid;
 for rowdata in select value from jsonb_array_elements(p_issues) loop
  if length(trim(coalesce(rowdata->>'title','')))<4
   or nullif(trim(coalesce(rowdata->>'action_plan','')),'') is null
   or nullif(trim(coalesce(rowdata->>'pic_name','')),'') is null
   or nullif(rowdata->>'due_date','') is null then
    raise exception 'Masalah, solusi, PIC dan due date wajib untuk setiap issue';end if;
  insert into public.issues(store_id,origin,briefing_id,title,category,root_cause,action_plan,
  pic_name,due_date,priority,status,created_by)
  values(storekey,'briefing',bid,trim(rowdata->>'title'),
   coalesce(nullif(rowdata->>'category',''),'Operasional'),rowdata->>'root_cause',
   trim(rowdata->>'action_plan'),trim(rowdata->>'pic_name'),
   (rowdata->>'due_date')::date,
   coalesce(nullif(rowdata->>'priority',''),'Sedang'),'Open',auth.uid());
 end loop;
 return bid;
end $$;
revoke all on function public.submit_briefing_bundle(jsonb,jsonb) from public,anon;
grant execute on function public.submit_briefing_bundle(jsonb,jsonb) to authenticated;

-- Cross-store pointer integrity: a user may never attach an issue from Store A to a Visit in Store B.
create or replace function private.guard_issue_parent_store() returns trigger
language plpgsql security definer set search_path='' as $$
declare parentstore text;
begin
 if new.visit_id is not null then
  select store_id into parentstore from public.visits where id=new.visit_id;
  if parentstore is distinct from new.store_id then raise exception 'Toko issue dan visit tidak cocok';end if;
 end if;
 if new.briefing_id is not null then
  select store_id into parentstore from public.briefings where id=new.briefing_id;
  if parentstore is distinct from new.store_id then raise exception 'Toko issue dan briefing tidak cocok';end if;
 end if;
 if new.visit_point_id is not null then
  select v.store_id into parentstore from public.visit_points p
  join public.visits v on v.id=p.visit_id where p.id=new.visit_point_id;
  if parentstore is distinct from new.store_id then raise exception 'Toko issue dan checkpoint tidak cocok';end if;
 end if;
 return new;
end $$;
create trigger issue_parent_store_guard before insert or update on public.issues
for each row execute function private.guard_issue_parent_store();

create index if not exists idx_briefing_store_date on public.briefings(store_id,briefing_date desc);
create index if not exists idx_issue_store_due on public.issues(store_id,due_date,status);
create index if not exists idx_check_store_date on public.checklist_entries(store_id,check_date desc);
create index if not exists idx_visit_schedule_store_date on public.visit_schedules(store_id,visit_date desc);
commit;
