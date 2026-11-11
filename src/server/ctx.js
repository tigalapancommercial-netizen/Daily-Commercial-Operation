// Konteks satu panggilan API: identitas user + cache baca (pengganti readAll_/sheet_ Code.gs)
import { rpc, toCamel, toSnake, setServerNow } from '../db.js';

const meCache = new Map(); // token -> {me, t}
export function forgetToken(token) { meCache.delete(token); }

export async function auth_(token) {
  if (!token) throw new Error('Sesi habis, silakan login ulang');
  const c = meCache.get(token);
  if (c && Date.now() - c.t < 5 * 60000) return c.me;
  let w;
  try { w = await rpc('dco_whoami', { p_token: token }); } catch (e) { meCache.delete(token); throw e; }
  setServerNow(w.now_ms);
  const me = { username: w.username, role: w.role, toko: w.toko, nama: w.nama, email: w.email || '', isMaster: !!w.is_master, isMgr: !!w.is_mgr };
  meCache.set(token, { me, t: Date.now() });
  return me;
}

export class Ctx {
  constructor(me, token) { this.me = me; this.token = token; this.cache = new Map(); }
  async read(type, filter) {
    const key = type + '|' + JSON.stringify(filter || {});
    if (!this.cache.has(key)) {
      this.cache.set(key, rpc('dco_rows', { p_token: this.token, p_type: type, p_filter: filter || {} }).then((rows) => (rows || []).map(toCamel)));
    }
    // salinan agar perubahan objek tidak merusak cache
    return (await this.cache.get(key)).map((r) => Object.assign({}, r));
  }
  invalidate(type) { for (const k of Array.from(this.cache.keys())) if (k.indexOf(type + '|') === 0) this.cache.delete(k); }
  async save(type, rows, mode) {
    if (!rows.length) return [];
    const out = [];
    for (let i = 0; i < rows.length; i += 500) {
      const part = await rpc('dco_save', { p_token: this.token, p_type: type, p_rows: rows.slice(i, i + 500).map(toSnake), p_mode: mode || 'upsert' });
      (part || []).forEach((r) => out.push(toCamel(r)));
    }
    this.invalidate(type);
    return out;
  }
  async del(type, ids) {
    const r = await rpc('dco_delete', { p_token: this.token, p_type: type, p_ids: ids });
    this.invalidate(type);
    return r;
  }
  call(fn, args) { return rpc(fn, Object.assign({ p_token: this.token }, args || {})); }
}
