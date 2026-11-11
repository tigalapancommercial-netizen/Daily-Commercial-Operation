#!/usr/bin/env bash
# Uji lokal penuh: PostgreSQL lokal + stub Supabase + migrasi 006 + impor 007 + build + Playwright.
# Butuh: PostgreSQL 16 (psql via user postgres), Node 20+, Python3 + playwright + Google Chrome.
set -euo pipefail
cd "$(dirname "$0")/.."
DB=${DB:-dcotest}; PORT=${PORT:-54321}
psql_() { su postgres -c "psql -q -v ON_ERROR_STOP=1 -d $1 -f $2" >/dev/null; }
su postgres -c "psql -q -c 'drop database if exists $DB' -c 'create database $DB'" >/dev/null
psql_ $DB tests/sql/00_supabase_stub.sql
psql_ $DB supabase/migrations/20261112_006_dco_parity.sql
if [ -f supabase/data_import/20261112_007_import_data.sql ]; then psql_ $DB supabase/data_import/20261112_007_import_data.sql; fi
rm -rf tests/.storage tests/screenshots
VITE_SUPABASE_URL=http://localhost:$PORT VITE_SUPABASE_PUBLISHABLE_KEY=local-test-key npm run build >/dev/null
node tests/mock_supabase.mjs $PORT $DB dist > /tmp/dco_mock.log 2>&1 &
MOCK=$!; trap "kill $MOCK 2>/dev/null || true" EXIT
sleep 1.5
E2E_URL=http://localhost:$PORT python3 tests/e2e_test.py
