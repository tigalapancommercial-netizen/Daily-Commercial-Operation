-- Harden validation and make multi-issue briefing an atomic operation.
begin;
create or replace function private.guard_dso_validation() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if not private.is_manager() then
  if tg_op='UPDATE' and (old.status='Approved' or old.status='Rejected') then
   if old.status='Approved' then raise exception 'Laporan approved hanya dapat diperbarui manajer' using errcode='42501'; end if;
   -- Rejected report can be resubmitted, but manager validation metadata must reset.
   if new.status <> 'Submitted' or new.validated_by is not null or new.validated_at is not null or new.validation_notes is not null then
    raise exception 'Resubmit rejected report harus mengosongkan validasi' using errcode='42501';
   end if;
  elsif new.validated_by is distinct from old.validated_by or new.validated_at is distinct from old.validated_at
      or new.validation_notes is distinct from old.validation_notes or new.status in ('Approved','Rejected') then
   raise exception 'Validasi DSO memerlukan SPV / Master' using errcode='42501';
  end if;
 end if;
 return new;
end $$;
create or replace function private.guard_checklist_validation() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if not private.is_manager() then
  if old.validated_at is not null then raise exception 'Checklist tervalidasi tidak bisa diubah oleh toko' using errcode='42501';end if;
  if new.validated_by is distinct from old.validated_by or new.validated_at is distinct from old.validated_at
      or new.validation_notes is distinct from old.validation_notes then
   raise exception 'Validasi checklist hanya untuk SPV/Master' using errcode='42501';
  end if;
 end if;
 return new;
end $$;

create or replace function public.submit_briefing_bundle(p_briefing jsonb,p_issues jsonb)
returns uuid language plpgsql security definer set search_path='' as $$
declare bid uuid; storekey text; rowdata jsonb; issuecount integer;
begin
 storekey=nullif(trim(p_briefing->>'store_id'),'');
 if storekey is null or not private.can_access_store(storekey) then raise exception 'Akses briefing ditolak' using errcode='42501'; end if;
 if jsonb_typeof(p_issues)<>'array' or jsonb_array_length(p_issues)>50 then raise exception 'Format list issue tidak sesuai';end if;
 issuecount=jsonb_array_length(p_issues);
 if coalesce((p_briefing->>'no_findings')::boolean,false) and issuecount>0 then raise exception 'NIHIL tidak boleh memiliki issue';end if;
 if not coalesce((p_briefing->>'no_findings')::boolean,false) and issuecount=0 then raise exception 'Setidaknya satu masalah diperlukan';end if;
 insert into public.briefings(store_id,briefing_date,shift,leader,participants,no_findings,notes,created_by)
 values(storekey,(p_briefing->>'briefing_date')::date,coalesce(nullif(p_briefing->>'shift',''),'Pagi'),
 trim(p_briefing->>'leader'),coalesce((p_briefing->>'participants')::int,0),
 coalesce((p_briefing->>'no_findings')::boolean,false),coalesce(p_briefing->>'notes',''),auth.uid())
 on conflict(store_id,briefing_date,shift) do update set leader=excluded.leader,participants=excluded.participants,
   no_findings=excluded.no_findings,notes=excluded.notes,updated_at=now()
 returning id into bid;
 for rowdata in select value from jsonb_array_elements(p_issues) loop
  if length(trim(coalesce(rowdata->>'title','')))<4 or nullif(trim(rowdata->>'action_plan'),'') is null
    or nullif(trim(rowdata->>'pic_name'),'') is null or nullif(rowdata->>'due_date','') is null then
    raise exception 'Setiap temuan wajib memiliki masalah, action plan, PIC dan due date';
  end if;
  insert into public.issues(store_id,origin,briefing_id,title,category,action_plan,pic_name,due_date,priority,status,created_by)
  values(storekey,'briefing',bid,trim(rowdata->>'title'),coalesce(nullif(rowdata->>'category',''),'Operasional'),
   trim(rowdata->>'action_plan'),trim(rowdata->>'pic_name'),(rowdata->>'due_date')::date,
   coalesce(nullif(rowdata->>'priority',''),'Sedang'),'Open',auth.uid());
 end loop;
 return bid;
end $$;
revoke all on function public.submit_briefing_bundle(jsonb,jsonb) from public,anon;
grant execute on function public.submit_briefing_bundle(jsonb,jsonb) to authenticated;
commit;
