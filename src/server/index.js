// Dispatcher api(action, p, sesi) — sama persis dengan fungsi api() di Code.gs v6.
// Hasil berupa string JSON {ok,data} / {ok:false,error} seperti google.script.run.
import { rpc, setServerNow } from '../db.js';
import { Ctx, auth_, forgetToken } from './ctx.js';
import * as C from './core.js';
import * as R from './report.js';
import * as A from './admin.js';
import * as P from './period.js';

async function login_(username, pin) {
  const r = await rpc('dco_login', { p_username: String(username || ''), p_pin: String(pin == null ? '' : pin) });
  if (!r || !r.ok) throw new Error((r && r.error) || 'Username atau PIN salah');
  return r.data;
}

export async function api(action, p, sesi) {
  try {
    p = p || {};
    if (action === 'login') return JSON.stringify({ ok: true, data: await login_(p.username, p.pin) });
    const me = await auth_(sesi), ctx = new Ctx(me, sesi);
    const fn = {
      meta: () => C.meta_(ctx),
      periodList: () => P.list_(ctx, p),
      periodSubmit: () => P.submit_(ctx, p),
      periodValidate: () => P.validate_(ctx, p),
      periodSummary: () => P.summary_(ctx, p),
      list: () => C.list_(ctx, p.type, p.filter),
      storeSummary: () => R.storeSummary_(ctx, p.tanggal),
      issueList: () => C.issueList_(ctx, p.filter),
      issueUpdate: () => C.issueUpdate_(ctx, p.data),
      exportData: () => R.exportData_(ctx, p.module, p.filter),
      archivePreview: () => A.archivePreview_(ctx, p.scope, p.from, p.to),
      syncMasalah: () => A.syncMasalah_(ctx),
      add: () => C.add_(ctx, p.type, p.data, p.tokoList),
      update: () => C.update_(ctx, p.type, p.id, p.data),
      bulk: () => C.bulk_(ctx, p.type, p.ids, p.op, p.value),
      ceklisHari: () => C.ceklisHari_(ctx, p.tanggal, p.toko),
      ceklisSet: () => C.ceklisSet_(ctx, p),
      rutinSave: () => C.rutinSave_(ctx, p.data),
      rutinHapus: () => C.rutinHapus_(ctx, p.id),
      dsoHari: () => C.dsoHari_(ctx, p.tanggal, p.toko),
      dsoSubmit: () => C.dsoSubmit_(ctx, p),
      dsoValidasi: () => C.dsoValidasi_(ctx, p),
      visitSave: () => C.visitSave_(ctx, p.data),
      visitValidasi: () => C.visitValidasi_(ctx, p),
      visitHapus: () => C.visitHapus_(ctx, p.id),
      dsoPatch: () => C.dsoPatch_(ctx, p),
      dsoHapus: () => C.dsoHapus_(ctx, p.id),
      jadwalSave: () => C.jadwalSave_(ctx, p.data),
      jadwalHapus: () => C.jadwalHapus_(ctx, p.id),
      tracking: () => R.tracking_(ctx, p.from, p.to, p.toko),
      notif: () => R.notif_(ctx),
      uploadFoto: () => A.uploadFoto_(ctx, p.dataUrl, {source:p.captureSource || 'galeri', context:p.context || p.nama || ''}),
      fotoB64: () => A.fotoB64_(p.id),
      fotoReceipt: () => A.photoReceipt_(ctx, p.id),
      cfgSave: () => A.cfgSave_(ctx, p.key, p.value),
      defSave: () => A.defSave_(ctx, p.type, p.data),
      defHapus: () => A.defHapus_(ctx, p.type, p.id),
      addToko: () => A.addToko_(ctx, p.nama, p.area),
      tokoSave: () => A.tokoSave_(ctx, p),
      userSave: () => A.userSave_(ctx, p),
      hapusUser: () => A.hapusUser_(ctx, p.username),
      gantiPin: () => A.gantiPin_(ctx, p.pinLama, p.pinBaru).then((u) => { forgetToken(sesi); return u; }),
      backup: () => A.backup_(ctx, p.scope, p.from, p.to, p.hapus),
      backupList: () => A.backupList_(ctx),
      wipe: () => A.wipe_(ctx, p.scope, p.from, p.to, p.hapusFoto, p.confirm, p.allTime),
    }[action];
    if (!fn) throw new Error('Aksi tidak dikenal: ' + action);
    return JSON.stringify({ ok: true, data: await fn() });
  } catch (e) {
    const msg = String((e && e.message) || e);
    if (/login ulang/.test(msg)) forgetToken(sesi);
    return JSON.stringify({ ok: false, error: msg });
  }
}

export async function logoutToken(token) { forgetToken(token); try { await rpc('dco_logout', { p_token: token }); } catch (e) {} }
export async function ping() { const r = await rpc('dco_ping', {}); setServerNow(r.now_ms); return r; }
export { A };
