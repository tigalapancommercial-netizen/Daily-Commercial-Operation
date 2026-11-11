// Port Code.gs v6: Foto, Pengaturan, Toko & User, Backup/Arsip/Hapus, Sinkron Rekap Masalah
import { rpc, toCamel, uploadPhoto, removePhotos, photoUrl, STORAGE_PATH_RE } from '../db.js';
import { DEFAULT_CFG, SCHEMA, TOKO_AWAL, SRC_MASALAH_ID, keys_, now_, stamp_, parseTglId_, mustMgr_, mustMaster_ } from './util.js';
import { getCfg_ } from './core.js';
import { buildXlsx, inspectXlsx, u8ToB64, b64ToU8, sha256Hex, downloadBytes } from '../xlsx.js';

// ================= FOTO =================
export async function uploadFoto_(ctx, dataUrl) { return { id: await uploadPhoto(ctx.token, dataUrl) }; }
export async function fotoB64_(id) {
  id = String(id || '');
  if (!STORAGE_PATH_RE.test(id)) return '';   // ID Drive lama: tampil via thumbnail Drive; tidak bisa diambil dari browser
  try {
    const res = await fetch(photoUrl(id)); if (!res.ok) return '';
    const blob = await res.blob();
    return await new Promise((ok) => { const fr = new FileReader(); fr.onload = () => ok(String(fr.result || '')); fr.onerror = () => ok(''); fr.readAsDataURL(blob); });
  } catch (e) { return ''; }
}

// ================= PENGATURAN =================
export async function cfgSave_(ctx, key, value) {
  mustMaster_(ctx.me); if (!(key in DEFAULT_CFG)) throw new Error('Key tidak dikenal: ' + key);
  await ctx.save('CONFIG', [{ key, value: JSON.stringify(value) }], 'upsert');
  return getCfg_(ctx);
}
export async function defSave_(ctx, type, d) {
  mustMaster_(ctx.me); d = d || {}; if (['FORM_DEF', 'VISIT_DEF'].indexOf(type) < 0) throw new Error('Tipe salah');
  const keys = keys_(type), r = {};
  keys.forEach((k) => { r[k] = d[k] != null ? d[k] : ''; });
  if (!r.label) throw new Error('Label wajib diisi');
  r.aktif = r.aktif === 'N' ? 'N' : 'Y';
  if (type === 'FORM_DEF') { r.multi = r.multi === 'Y' ? 'Y' : 'N'; r.wajib = r.wajib === 'N' ? 'N' : 'Y'; r.urutan = Number(r.urutan) || 99; }
  let saved = (await ctx.save(type, [r], 'upsert'))[0];
  if (type === 'VISIT_DEF' && !saved.kode) saved = (await ctx.save(type, [{ id: saved.id, kode: saved.id }], 'update'))[0];
  return saved;
}
export async function defHapus_(ctx, type, id) { mustMaster_(ctx.me); if (['FORM_DEF', 'VISIT_DEF'].indexOf(type) < 0) throw new Error('Tipe salah'); if (id) await ctx.del(type, [id]); return { ok: true }; }

// ================= TOKO & USER =================
export async function addToko_(ctx, nama, area) { mustMaster_(ctx.me); const r = await ctx.call('dco_toko_add', { p_nama: nama || '', p_area: area || '' }); ctx.invalidate('TOKO'); ctx.invalidate('USERS'); return r; }
export async function tokoSave_(ctx, p) {
  mustMaster_(ctx.me);
  if (!(await ctx.read('TOKO')).some((t) => t.nama === p.nama)) throw new Error('Toko tidak ditemukan');
  await ctx.save('TOKO', [{ nama: p.nama, area: p.area || '', aktif: p.aktif === 'N' ? 'N' : 'Y' }], 'update');
  return { ok: true };
}
export async function userSave_(ctx, p) {
  mustMaster_(ctx.me);
  return ctx.call('dco_user_save', { p: { username: p.username || '', pin: p.pin ? String(p.pin) : '', role: p.role || '', toko: p.toko || '', nama: p.nama || '', email: p.email || '' } });
}
export async function hapusUser_(ctx, username) { mustMaster_(ctx.me); return ctx.call('dco_user_delete', { p_username: username || '' }); }
export async function gantiPin_(ctx, pinLama, pinBaru) { return ctx.call('dco_change_pin', { p_old: String(pinLama || ''), p_new: String(pinBaru || '') }); }

// ================= BACKUP (file Excel tersimpan di Supabase) & HAPUS =================
const BACKUP_TYPES = ['MASALAH', 'TUGAS', 'CEKLIS', 'DSO', 'VISIT', 'VISIT_ISSUE', 'JADWAL'];
function archiveTypes_(scope) { if (scope === 'SEMUA') return BACKUP_TYPES.slice(); if (BACKUP_TYPES.indexOf(scope) < 0) throw new Error('Jenis data tidak valid'); return scope === 'VISIT' ? ['VISIT', 'VISIT_ISSUE'] : [scope]; }
export async function archivePreview_(ctx, scope, from, to) {
  mustMaster_(ctx.me); if (from && to && from > to) throw new Error('Tanggal Dari tidak boleh melebihi Sampai');
  return ctx.call('dco_archive_preview', { p_types: archiveTypes_(scope), p_from: from || '', p_to: to || '' });
}
export async function backup_(ctx, scope, from, to, hapus) {
  const me = ctx.me; mustMaster_(me); if (from && to && from > to) throw new Error('Rentang tanggal salah');
  const types = archiveTypes_(scope), raw = await ctx.call('dco_archive_rows', { p_types: types, p_from: from || '', p_to: to || '' });
  const plans = {}, counts = {}; let total = 0;
  types.forEach((t) => { plans[t] = (raw[t] || []).map(toCamel); counts[t] = plans[t].length; total += counts[t]; });
  if (!total) throw new Error('Tidak ada data untuk periode yang dipilih');
  if (hapus) ['MASALAH', 'TUGAS', 'VISIT_ISSUE'].forEach((t) => {
    const plan = plans[t]; if (!plan) return; const pending = plan.filter((r) => r.status !== 'Selesai' && r.status !== 'Dibatalkan');
    if (pending.length) throw new Error('Tidak boleh mengarsipkan ' + pending.length + ' ' + t + ' yang masih open/pending. Selesaikan dulu atau pilih mode Salin saja.');
  });
  const name = 'BACKUP_' + scope + '_' + (from || 'AWAL') + '_sd_' + (to || 'AKHIR') + '_' + stamp_();
  const sheets = [{ name: 'INFO', rows: [['Backup', name], ['Dibuat', now_()], ['Oleh', me.nama], ['Scope', scope], ['Rentang', (from || 'awal') + ' sampai ' + (to || 'akhir')],
    ['Mode', hapus ? 'ARSIP (hapus data aktif setelah verifikasi)' : 'SALIN SAJA'], ['Jumlah baris', String(total)]] }];
  types.forEach((t) => { const keys = keys_(t); sheets.push({ name: t, rows: [SCHEMA[t].map((c) => c[1])].concat(plans[t].map((r) => keys.map((k) => (r[k] == null ? '' : r[k])))) }); });
  const file = buildXlsx(sheets);
  // Verifikasi isi file SEBELUM disimpan / sebelum data aktif dihapus (jumlah, ID awal & akhir)
  const chk = inspectXlsx(file);
  types.forEach((t) => {
    const n = plans[t].length, c = chk[t];
    if (!c || c.rows !== n) throw new Error('Verifikasi backup gagal untuk ' + t + '; tidak ada data aktif yang dihapus');
    if (n && String(c.firstId) !== String(plans[t][0].id)) throw new Error('ID awal backup ' + t + ' tidak cocok');
    if (n && String(c.lastId) !== String(plans[t][n - 1].id)) throw new Error('ID akhir backup ' + t + ' tidak cocok');
  });
  const hash = await sha256Hex(file);
  const saved = await ctx.call('dco_backup_save', { p_nama: name, p_info: { scope, from: from || '', to: to || '', counts, total, mode: hapus ? 'ARSIP' : 'SALIN' }, p_b64: u8ToB64(file) });
  if (saved.sha256 !== hash || saved.size !== file.length) throw new Error('Verifikasi backup tersimpan gagal; tidak ada data aktif yang dihapus');
  let deleted = {};
  if (hapus) {
    const ids = {}; types.forEach((t) => { ids[t] = plans[t].map((r) => r.id); });
    const r = await ctx.call('dco_archive_delete', { p_types: types, p_from: from || '', p_to: to || '', p_ids: ids, p_block_open: true, p_collect_photos: false, p_confirm: '' });
    deleted = r.deleted || {}; types.forEach((t) => ctx.invalidate(t));
  }
  return { nama: name, url: '#dco-backup:' + saved.id, counts, total, deleted, dihapus: !!hapus };
}
export async function backupList_(ctx) {
  mustMaster_(ctx.me);
  return (await ctx.call('dco_backup_list')).map((b) => ({ nama: b.nama, url: '#dco-backup:' + b.id, tgl: b.tgl, id: b.id, size: b.size }));
}
export async function downloadBackup(token, id) {
  const b = await rpc('dco_backup_get', { p_token: token, p_id: Number(id) });
  const u8 = b64ToU8(b.b64);
  if ((await sha256Hex(u8)) !== b.sha256) throw new Error('File backup rusak (checksum tidak cocok)');
  downloadBytes(u8, b.nama + '.xlsx');
  return b.nama;
}
export async function wipe_(ctx, scope, from, to, hapusFoto, confirm, allTime) {
  mustMaster_(ctx.me); if (confirm !== 'HAPUS PERMANEN') throw new Error('Ketik HAPUS PERMANEN untuk konfirmasi');
  if (!from && !to && !allTime) throw new Error('Pilih rentang tanggal atau konfirmasi semua waktu');
  if (from && to && from > to) throw new Error('Rentang tanggal salah');
  const types = archiveTypes_(scope);
  const r = await ctx.call('dco_archive_delete', { p_types: types, p_from: from || '', p_to: to || '', p_ids: null, p_block_open: false, p_collect_photos: !!hapusFoto, p_confirm: confirm });
  types.forEach((t) => ctx.invalidate(t));
  const del = r.deleted || {}, photos = r.photos || [], trashed = hapusFoto ? await removePhotos(photos) : 0;
  return { jumlah: types.reduce((a, t) => a + (del[t] || 0), 0), byType: types.map((t) => ({ type: t, count: del[t] || 0 })), fotoTrashed: trashed, fotoErrors: Math.max(0, photos.length - trashed) };
}

// ================= SINKRON REKAP MASALAH (sheet sumber REKAP GLOBAL) =================
function parseCsv(text) {
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) { if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; }
    else if (ch === '"') q = true;
    else if (ch === ',') { row.push(cell); cell = ''; }
    else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += ch;
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows;
}
async function sourceValues_() {
  const key = import.meta.env.VITE_GOOGLE_API_KEY;
  const sheet = 'REKAP GLOBAL';
  try {
    if (key) {
      const res = await fetch('https://sheets.googleapis.com/v4/spreadsheets/' + SRC_MASALAH_ID + '/values/' + encodeURIComponent(sheet) + '?valueRenderOption=FORMATTED_VALUE&key=' + encodeURIComponent(key));
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return (await res.json()).values || [];
    }
    const res = await fetch('https://docs.google.com/spreadsheets/d/' + SRC_MASALAH_ID + '/gviz/tq?tqx=out:csv&headers=1&sheet=' + encodeURIComponent(sheet));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const txt = await res.text();
    if (/^\s*</.test(txt)) throw new Error('bukan CSV');
    return parseCsv(txt);
  } catch (e) {
    throw new Error('Sheet sumber Rekap Masalah tidak bisa dibaca (' + (e.message || e) + '). Pastikan sheet dibagikan "Siapa saja yang memiliki link: Viewer" atau isi VITE_GOOGLE_API_KEY.');
  }
}
export async function syncMasalah_(ctx) {
  mustMgr_(ctx.me);
  const values = await sourceValues_(), keys = keys_('MASALAH'), current = await ctx.read('MASALAH'), byOld = {};
  current.forEach((r) => { if (r.idLama) byOld[r.idLama] = r; });
  const fresh = [], update = [], seen = {}, now = now_();
  values.slice(1).forEach((v) => {
    const g = (i) => (v[i] == null ? '' : String(v[i]));
    const oldId = g(19).trim(), desc = g(6).trim();
    if (!oldId || !desc || seen[oldId]) return; seen[oldId] = true;
    const m = oldId.match(/^[TM](\d{2})-/), toko = m && TOKO_AWAL[+m[1] - 1] ? TOKO_AWAL[+m[1] - 1] : g(1).trim();
    const obj = { tanggal: parseTglId_(g(0)), toko, sesi: g(2), pemimpin: g(3), peserta: g(4), kategori: g(5) || 'Lainnya',
      masalah: g(6), akar: g(7), solusi: g(8), pic: g(9), dueDate: parseTglId_(g(10)), prioritas: g(11) || 'Sedang',
      status: g(12) || 'Open', progress: g(13) !== '' ? g(13).replace('%', '') : (g(12) === 'Selesai' ? 100 : 0), tglSelesai: parseTglId_(g(14)), update: g(15), linkBukti: g(16) };
    const existing = byOld[oldId];
    if (!existing) {
      const r = { id: '', validasi: '', validasiOleh: '', validasiTgl: '', fotoId: '', dibuatOleh: 'SYNC_SOURCE', updateTgl: now, updateOleh: 'SYNC_SOURCE', idLama: oldId };
      Object.keys(obj).forEach((k) => { r[k] = obj[k]; }); keys.forEach((k) => { if (r[k] == null) r[k] = ''; }); fresh.push(r); return;
    }
    if (existing.updateOleh !== 'MIGRASI' && existing.updateOleh !== 'SYNC_SOURCE') return;   // data yang sudah diedit di aplikasi tidak disentuh
    let diff = false; const u = { id: existing.id };
    Object.keys(obj).forEach((k) => { if (String(obj[k] || '') !== String(existing[k] || '')) { if (obj[k] !== '' || ['status', 'progress'].indexOf(k) >= 0) { u[k] = obj[k]; diff = true; } } });
    if (diff) { u.updateOleh = 'SYNC_SOURCE'; update.push(u); }
  });
  if (update.length) await ctx.save('MASALAH', update, 'update');
  if (fresh.length) await ctx.save('MASALAH', fresh, 'insert');
  return { added: fresh.length, updated: update.length, existing: current.length, sourceValid: Object.keys(seen).length };
}
