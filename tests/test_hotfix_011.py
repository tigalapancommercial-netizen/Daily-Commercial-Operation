from pathlib import Path
r=Path(__file__).resolve().parents[1]
m10=(r/'supabase/migrations/20261113_010_dso_photo_audit.sql').read_text()
m11=(r/'supabase/migrations/20261113_011_fix_photo_ticket_ambiguity.sql').read_text()
db=(r/'src/db.js').read_text()
for s in (m10,m11):
 assert '  v_ticket text;' in s
 assert 'v_ticket := substr(p_path,9,32);' in s
 assert 'WHERE t.ticket = v_ticket AND t.username' in s
 assert 'WHERE t.ticket = ticket' not in s
 assert 'CREATE OR REPLACE FUNCTION public.dco_photo_register(' in s
import re
assert not re.search(r'(?im)^\s*(?:DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE)\s+', m11)
assert '20261113_011_fix_photo_ticket_ambiguity.sql' in db
print('PASS: SQL 010/011 and client diagnostics are consistent; no destructive SQL.')
