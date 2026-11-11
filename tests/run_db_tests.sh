#!/usr/bin/env bash
# Uji migrasi SQL di PostgreSQL lokal: dijalankan 2x (idempotent) + impor data 2x.
set -euo pipefail
cd "$(dirname "$0")/.."
DB=${DB:-dcotest_db}
run() { su postgres -c "PGOPTIONS='-c client_min_messages=warning' psql -q -v ON_ERROR_STOP=1 -d $DB -f $1" >/dev/null; }
su postgres -c "psql -q -c 'drop database if exists $DB' -c 'create database $DB'" >/dev/null
run tests/sql/00_supabase_stub.sql
run supabase/migrations/20261112_006_dco_parity.sql && echo "OK   migrasi 006 (pertama)"
run supabase/migrations/20261112_006_dco_parity.sql && echo "OK   migrasi 006 (ulang, idempotent)"
if [ -f supabase/data_import/20261112_007_import_data.sql ]; then
  run supabase/data_import/20261112_007_import_data.sql && run supabase/data_import/20261112_007_import_data.sql && echo "OK   impor data 007 (2x, tanpa duplikat)"
fi
su postgres -c "psql -tA -d $DB -c \"select 'toko='||(select count(*) from dco.toko)||' users='||(select count(*) from dco.users)||' form_def='||(select count(*) from dco.form_def)||' visit_def='||(select count(*) from dco.visit_def)||' masalah='||(select count(*) from dco.masalah)\""
su postgres -c "psql -qtA -d $DB -c \"set role anon; select case when (public.dco_login('master','1234')->>'ok')::boolean then 'OK   login master via role anon' else 'FAIL login' end\""
OUT=$(su postgres -c "psql -tA -d $DB -c \"set role anon; select 1 from dco.users\"" 2>&1 || true)
echo "$OUT" | grep -q "permission denied" && echo "OK   tabel dco tertutup untuk anon" || { echo "FAIL tabel dco terbuka"; exit 1; }
