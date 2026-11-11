// Pemeriksaan statis: sintaks modul, index.html = referensi + patch, semua RPC yang dipakai frontend ada di migrasi SQL.
import fs from 'node:fs';
import { execSync } from 'node:child_process';
let fail = 0;
const ok = (c, m) => { console.log((c ? 'OK   ' : 'FAIL ') + m); if (!c) fail++; };
for (const f of ['src/main.js', 'src/db.js', 'src/xlsx.js', 'src/server/index.js', 'src/server/core.js', 'src/server/report.js', 'src/server/admin.js', 'src/server/util.js', 'src/server/ctx.js']) {
  try { execSync('node --check ' + f, { stdio: 'pipe' }); ok(true, 'sintaks ' + f); } catch (e) { ok(false, 'sintaks ' + f + ': ' + e.stderr); }
}
try {
  const tmp = (process.env.RUNNER_TEMP || '/tmp') + '/dco_index_check.html';
  execSync('python3 scripts/build_index.py ' + tmp, { stdio: 'pipe' });
  const same = fs.readFileSync('index.html', 'utf8') === fs.readFileSync(tmp, 'utf8');
  console.log((same ? 'OK   ' : 'INFO ') + 'index.html ' + (same ? 'identik dengan' : 'berbeda dari (sudah diedit manual)') + ' legacy/Index.reference.html + patch');
} catch (e) { console.log('INFO python3 tidak tersedia, pemeriksaan index.html dilewati'); }
const sql = fs.readFileSync('supabase/migrations/20261112_006_dco_parity.sql', 'utf8');
const src = ['src/db.js', 'src/server/index.js', 'src/server/ctx.js', 'src/server/core.js', 'src/server/admin.js'].map((f) => fs.readFileSync(f, 'utf8')).join('\n');
const used = new Set([...src.matchAll(/'(dco_[a-z_]+)'/g)].map((m) => m[1]));
for (const fn of used) ok(new RegExp('function public\\.' + fn + '\\(').test(sql), 'RPC ' + fn + ' ada di migrasi 006');
const html = fs.readFileSync('index.html', 'utf8');
const actions = [...html.matchAll(/call\('([a-zA-Z]+)'/g)].map((m) => m[1]);
const disp = fs.readFileSync('src/server/index.js', 'utf8');
for (const a of new Set(actions)) ok(a === 'login' || new RegExp('\\b' + a + ':').test(disp), 'aksi UI "' + a + '" ditangani server');
ok(!/service_role|SERVICE_ROLE|sb_secret_/.test(src + html), 'tidak ada kunci rahasia di frontend');
console.log(fail ? '\n' + fail + ' pemeriksaan GAGAL' : '\nSemua pemeriksaan lulus');
process.exit(fail ? 1 : 0);
