// Lapisan akses Supabase: RPC dco_* + Storage foto. Tidak ada kunci rahasia di sini.
import { createClient } from '@supabase/supabase-js';

export const SUPABASE_URL = String(import.meta.env.VITE_SUPABASE_URL || '').replace(/\/+$/, '');
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY || '';
export const CONFIGURED = !!(SUPABASE_URL && SUPABASE_KEY);
export const BUCKET = 'dco-foto';

export const sb = CONFIGURED ? createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false, storageKey: 'dco-v9-auth' },
}) : null;

// Kolom angka (di spreadsheet tersimpan sebagai angka)
const NUMERIC = { progress: 1, urutan: 1, minggu: 1, finalScore: 1, totalPass: 1, totalDinilai: 1 };
const camel = (k) => k.replace(/_([a-z0-9])/g, (m, c) => c.toUpperCase());
const snake = (k) => k.replace(/[A-Z]/g, (c) => '_' + c.toLowerCase());
export function toCamel(row) {
  if (!row || typeof row !== 'object' || Array.isArray(row)) return row;
  const o = {};
  for (const k of Object.keys(row)) {
    const ck = camel(k); let v = row[k];
    if (NUMERIC[ck] && typeof v === 'string' && /^-?\d+(\.\d+)?$/.test(v)) v = Number(v);
    o[ck] = v;
  }
  return o;
}
export function toSnake(row) {
  const o = {};
  for (const k of Object.keys(row || {})) {
    let v = row[k];
    if (v === undefined) continue;
    if (v !== null && typeof v === 'object') v = JSON.stringify(v);
    o[snake(k)] = v == null ? '' : v;
  }
  return o;
}

function friendly(err) {
  const msg = String((err && (err.message || err.error_description || err.error)) || err || '');
  if (/Failed to fetch|NetworkError|Load failed|fetch failed/i.test(msg)) return 'Server tidak terhubung. Periksa koneksi internet lalu coba lagi.';
  if ((err && err.code === 'PGRST202') || /Could not find the function/i.test(msg))
    return 'Database belum terpasang: jalankan file supabase/migrations/20261112_006_dco_parity.sql di Supabase SQL Editor.';
  if (/JWT|Invalid API key|No API key/i.test(msg)) return 'Konfigurasi Supabase salah (URL / publishable key). Periksa GitHub Secrets.';
  return msg || 'Server tidak dapat memproses permintaan';
}

export async function rpc(fn, args) {
  if (!CONFIGURED) throw new Error('Aplikasi belum dikonfigurasi: isi VITE_SUPABASE_URL dan VITE_SUPABASE_PUBLISHABLE_KEY.');
  let res;
  try { res = await sb.rpc(fn, args || {}); } catch (e) { throw new Error(friendly(e)); }
  if (res.error) throw new Error(friendly(res.error));
  return res.data;
}

// ---- Jam server (WITA) ----
let offsetMs = 0;
export function setServerNow(ms) { if (ms) offsetMs = Number(ms) - Date.now(); }
export function serverNow() { return Date.now() + offsetMs; }

// ---- Foto ----
let ticketCache = null;
async function getTicket(token, force) {
  if (!force && ticketCache && ticketCache.token === token && ticketCache.expires_ms - serverNow() > 120000) return ticketCache;
  const t = await rpc('dco_upload_ticket', { p_token: token });
  ticketCache = Object.assign({ token }, t);
  return ticketCache;
}
function dataUrlToBlob(dataUrl) {
  const m = String(dataUrl || '').match(/^data:(image\/(jpeg|jpg|png|webp));base64,(.+)$/);
  if (!m) throw new Error('Format foto tidak valid');
  const bin = atob(m[3]); const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return { blob: new Blob([u8], { type: m[1] === 'image/jpg' ? 'image/jpeg' : m[1] }), ext: m[2] === 'jpeg' || m[2] === 'jpg' ? 'jpg' : m[2] };
}
function rand(n) {
  const a = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', u = new Uint8Array(n); crypto.getRandomValues(u);
  return Array.from(u, (x) => a[x % a.length]).join('');
}
export async function uploadPhoto(token, dataUrl) {
  const { blob, ext } = dataUrlToBlob(dataUrl);
  for (let attempt = 0; attempt < 2; attempt++) {
    const t = await getTicket(token, attempt > 0);
    const path = t.bulan + '/' + t.ticket + '_' + rand(10) + '.' + ext;
    const { error } = await sb.storage.from(BUCKET).upload(path, blob, { contentType: blob.type, upsert: false, cacheControl: '31536000' });
    if (!error) return path;
    if (attempt === 1 || !/row-level security|Unauthorized|403|policy/i.test(String(error.message || error))) {
      throw new Error('Gagal mengunggah foto: ' + friendly(error));
    }
  }
  throw new Error('Gagal mengunggah foto');
}
export async function removePhotos(paths) {
  const list = (paths || []).filter((p) => /^\d{4}-\d{2}\/[0-9a-f]{32}_/.test(String(p)));
  if (!list.length || !sb) return 0;
  try { const { data } = await sb.storage.from(BUCKET).remove(list); return (data || []).length; } catch (e) { return 0; }
}
export const STORAGE_PATH_RE = /^\d{4}-\d{2}\/[0-9a-f]{32}_[A-Za-z0-9]{4,16}\.(jpg|jpeg|png|webp)$/;
export function photoUrl(id, w) {
  id = String(id || '');
  if (STORAGE_PATH_RE.test(id)) return SUPABASE_URL + '/storage/v1/object/public/' + BUCKET + '/' + id;
  return 'https://drive.google.com/thumbnail?id=' + encodeURIComponent(id) + '&sz=w' + (w || 800);
}
