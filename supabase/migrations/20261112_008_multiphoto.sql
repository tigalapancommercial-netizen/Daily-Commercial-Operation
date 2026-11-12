-- v10: each evidence field may contain a single legacy ID/path or a JSON-encoded array
-- of up to 30 individual photo IDs/paths. Backwards compatible with all old records.
-- Run AFTER 20261112_006_dco_parity.sql. No existing row is rewritten.

create or replace function dco.valid_photo(t text)
returns boolean language plpgsql immutable
set search_path = pg_catalog, pg_temp as $$
declare a jsonb; el jsonb; item text;
begin
  if t is null or length(t) > 5500 or btrim(t) = '' then return false; end if;
  if t ~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
    or t ~ '^[A-Za-z0-9_-]{10,}$' then return true; end if;
  if left(btrim(t), 1) <> '[' then return false; end if;
  begin a := t::jsonb; exception when others then return false; end;
  if jsonb_typeof(a) <> 'array' or jsonb_array_length(a) < 1
      or jsonb_array_length(a) > 30 then return false; end if;
  for el in select value from jsonb_array_elements(a) loop
    if jsonb_typeof(el) <> 'string' then return false; end if;
    item := el #>> '{}';
    if not (item ~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
      or item ~ '^[A-Za-z0-9_-]{10,}$') then return false; end if;
  end loop;
  return true;
end $$;

-- Check substring membership so a photo inside a JSON-array string remains protected
-- from deletion. Not just foto_id = path, which only supports one photo.
create or replace function dco.photo_referenced(p text)
returns boolean language sql stable set search_path = pg_catalog, pg_temp as $$
select exists(select 1 from dco.masalah where strpos(foto_id, p) > 0)
    or exists(select 1 from dco.tugas where strpos(foto_id, p) > 0)
    or exists(select 1 from dco.ceklis where strpos(foto_id, p) > 0)
    or exists(select 1 from dco.visit_issue where strpos(foto_id, p) > 0)
    or exists(select 1 from dco.dso where strpos(jawaban, p) > 0)
    or exists(select 1 from dco.visit where strpos(foto, p) > 0)
$$;

-- Path extraction from JSON-encoded photo strings is already performed by
-- dco.photo_paths via regexp_matches; guard trash grants to actual stored paths.
create or replace function dco.grant_trash(paths text[])
returns text[] language plpgsql set search_path = pg_catalog, pg_temp as $$
declare p text; outp text[] := '{}';
begin
  delete from dco.photo_trash where expires_at < now();
  foreach p in array coalesce(paths, '{}') loop
    if p ~ '^\d{4}-\d{2}/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$'
       and not dco.photo_referenced(p) then
      insert into dco.photo_trash(name, expires_at) values (p, now() + interval '15 minutes')
        on conflict (name) do update set expires_at = excluded.expires_at;
      outp := outp || p;
    end if;
  end loop;
  return outp;
end $$;
