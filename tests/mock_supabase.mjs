// Server uji lokal: meniru endpoint Supabase yang dipakai aplikasi (PostgREST /rest/v1/rpc + Storage)
// di atas PostgreSQL lokal, SEMUA query dijalankan sebagai role "anon" (RLS & GRANT berlaku seperti di Supabase).
// Juga menyajikan folder dist/ (hasil build). Pemakaian: node tests/mock_supabase.mjs <port> <database> <distDir>
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import pg from 'pg';

const PORT = +(process.argv[2] || 54321), DB = process.argv[3] || 'dcotest', DIST = path.resolve(process.argv[4] || 'dist');
const STORE = path.resolve('tests/.storage'); fs.mkdirSync(STORE, { recursive: true });
const pool = new pg.Pool({ host: '/var/run/postgresql', database: DB, user: 'postgres', max: 8 });
const argTypes = new Map();

async function fnArgs(fn) {
  if (argTypes.has(fn)) return argTypes.get(fn);
  const r = await pool.query(`select p.proargnames as names, array(select format_type(t, null) from unnest(p.proargtypes) t) as types
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.proname = $1`, [fn]);
  const m = r.rows[0] ? { names: r.rows[0].names, types: r.rows[0].types } : null; argTypes.set(fn, m); return m;
}
async function asAnon(sql, params) {
  const c = await pool.connect();
  try { await c.query('begin'); await c.query('set local role anon'); const r = await c.query(sql, params); await c.query('commit'); return r; }
  catch (e) { await c.query('rollback').catch(() => {}); throw e; } finally { c.release(); }
}
const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS' };
function send(res, status, body, headers) {
  const isBuf = Buffer.isBuffer(body);
  res.writeHead(status, Object.assign({ 'Content-Type': isBuf ? 'application/octet-stream' : 'application/json' }, cors, headers || {}));
  res.end(isBuf ? body : JSON.stringify(body));
}
const readBody = (req) => new Promise((ok) => { const ch = []; req.on('data', (c) => ch.push(c)); req.on('end', () => ok(Buffer.concat(ch))); });
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' };

http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (req.method === 'OPTIONS') return send(res, 204, {});
  try {
    // ---------- PostgREST RPC ----------
    let m = u.pathname.match(/^\/rest\/v1\/rpc\/([a-z0-9_]+)$/);
    if (m && req.method === 'POST') {
      const fn = m[1], meta = await fnArgs(fn);
      if (!meta) return send(res, 404, { code: 'PGRST202', message: 'Could not find the function public.' + fn });
      const body = JSON.parse((await readBody(req)).toString() || '{}'), parts = [], vals = [];
      (meta.names || []).forEach((n, i) => {
        if (!(n in body)) return;
        let v = body[n]; const t = meta.types[i];
        if (t === 'jsonb' || t === 'json') v = v === null ? null : JSON.stringify(v);
        vals.push(v); parts.push(`${n} => $${vals.length}::${t}`);
      });
      const r = await asAnon(`select public.${fn}(${parts.join(', ')}) as r`, vals);
      return send(res, 200, r.rows[0].r);
    }
    // ---------- Storage: upload ----------
    m = u.pathname.match(/^\/storage\/v1\/object\/([^/]+)\/(.+)$/);
    if (m && req.method === 'POST' && m[1] !== 'public') {
      const bucket = m[1], name = decodeURIComponent(m[2]); let data = await readBody(req);
      const ct = String(req.headers['content-type'] || ''), bm = ct.match(/boundary=(.+)$/);
      if (/multipart\/form-data/.test(ct) && bm) {   // storage-js mengirim Blob sebagai multipart
        const sep = Buffer.from('--' + bm[1]); let pos = 0; const parts = [];
        while ((pos = data.indexOf(sep, pos)) >= 0) { const next = data.indexOf(sep, pos + sep.length); if (next < 0) break; parts.push(data.subarray(pos + sep.length + 2, next - 2)); pos = next; }
        const filePart = parts.find((p) => /content-type:\s*image\//i.test(p.subarray(0, Math.max(0, p.indexOf('\r\n\r\n'))).toString()));
        if (!filePart) return send(res, 400, { statusCode: '415', error: 'invalid_mime_type', message: 'mime type not supported' });
        data = filePart.subarray(filePart.indexOf('\r\n\r\n') + 4);
      }
      try { await asAnon('insert into storage.objects(bucket_id, name, metadata) values ($1, $2, $3)', [bucket, name, JSON.stringify({ size: data.length, mimetype: req.headers['content-type'] })]); }
      catch (e) { return send(res, 400, { statusCode: '403', error: 'Unauthorized', message: 'new row violates row-level security policy (' + e.message + ')' }); }
      const fp = path.join(STORE, bucket, name); fs.mkdirSync(path.dirname(fp), { recursive: true }); fs.writeFileSync(fp, data);
      return send(res, 200, { Key: bucket + '/' + name, Id: name });
    }
    // ---------- Storage: hapus ----------
    m = u.pathname.match(/^\/storage\/v1\/object\/([^/]+)\/?$/);
    if (m && req.method === 'DELETE') {
      const bucket = m[1], body = JSON.parse((await readBody(req)).toString() || '{}');
      const r = await asAnon('delete from storage.objects where bucket_id = $1 and name = any($2) returning name', [bucket, body.prefixes || []]);
      r.rows.forEach((x) => { try { fs.unlinkSync(path.join(STORE, bucket, x.name)); } catch (e) {} });
      return send(res, 200, r.rows.map((x) => ({ name: x.name, bucket_id: bucket })));
    }
    // ---------- Storage: URL publik ----------
    m = u.pathname.match(/^\/storage\/v1\/object\/public\/([^/]+)\/(.+)$/);
    if (m && req.method === 'GET') {
      const pub = await pool.query('select public from storage.buckets where id = $1', [m[1]]);
      const fp = path.join(STORE, m[1], decodeURIComponent(m[2]));
      if (!pub.rows[0] || !pub.rows[0].public || !fs.existsSync(fp)) return send(res, 404, { message: 'Object not found' });
      return send(res, 200, fs.readFileSync(fp), { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
    }
    // ---------- File statis (dist) ----------
    let fp = path.join(DIST, decodeURIComponent(u.pathname));
    if (!fp.startsWith(DIST)) return send(res, 403, {});
    if (fs.existsSync(fp) && fs.statSync(fp).isDirectory()) fp = path.join(fp, 'index.html');
    if (!fs.existsSync(fp)) return send(res, 404, { message: 'not found' });
    res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' }); res.end(fs.readFileSync(fp));
  } catch (e) {
    send(res, 400, { code: e.code || 'P0001', message: e.message, details: null, hint: null });
  }
}).listen(PORT, () => console.log('mock supabase on', PORT, 'db', DB));
