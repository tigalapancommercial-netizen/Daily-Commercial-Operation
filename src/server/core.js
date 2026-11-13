// Port Code.gs v6: CRUD, Daily Routine, Checklist, DSO, Visiting, Issue, Jadwal
import { removePhotos, toCamel } from '../db.js';
import { DEFAULT_CFG, STORE_EDIT, keys_, today_, now_, hm_, addDays_, daysBetween_, isoWeekYmd_, pad_, parseJ_, mustMgr_, mustMaster_ } from './util.js';

// ================= CONFIG =================
export async function getCfg_(ctx) {
  const cfg = JSON.parse(JSON.stringify(DEFAULT_CFG));
  (await ctx.read('CONFIG')).forEach((r) => { try { cfg[r.key] = JSON.parse(r.value); } catch (e) {} });
  return cfg;
}
export async function tokoAktif_(ctx) { return (await ctx.read('TOKO')).filter((r) => String(r.aktif).toUpperCase() !== 'N').map((r) => r.nama); }

export async function meta_(ctx) {
  const me = ctx.me, cfg = await getCfg_(ctx), users = await ctx.read('USERS');
  const fd = (await ctx.read('FORM_DEF')).sort((a, b) => ((a.form + pad_(a.urutan, 3)) < (b.form + pad_(b.urutan, 3)) ? -1 : 1));
  return {
    toko: me.isMgr ? await tokoAktif_(ctx) : [me.toko], tokoAll: me.isMaster ? await ctx.read('TOKO') : [], cfg, today: today_(), now: now_(), timezone: 'Asia/Makassar',
    formDef: fd, visitDef: await ctx.read('VISIT_DEF'),
    users: me.isMaster ? users.map((u) => ({ username: u.username, role: u.role, toko: u.toko, nama: u.nama, email: u.email })) : [],
    spvList: users.filter((u) => /SPV|MASTER/.test(String(u.role).toUpperCase())).map((u) => u.nama || u.username),
  };
}

// ================= CRUD GENERIK =================
export async function list_(ctx, type, f) {
  const me = ctx.me; f = f || {};
  if (['MASALAH', 'TUGAS', 'CEKLIS', 'DSO', 'VISIT', 'JADWAL', 'RUTIN'].indexOf(type) < 0) throw new Error('Menu tidak diizinkan');
  if (type === 'RUTIN') { mustMgr_(me); return ctx.read('RUTIN'); }
  if (type === 'VISIT') mustMgr_(me);
  const sf = {}; if (f.from) sf.from = f.from; if (f.to) sf.to = f.to; if (me.isMgr && f.toko && f.toko !== 'SEMUA') sf.toko = f.toko;
  let rows = await ctx.read(type, sf);
  if (type === 'VISIT') rows.forEach((r) => { ['jawaban', 'catatan', 'foto', 'skor', 'updateTemuan'].forEach((k) => { r[k] = parseJ_(r[k]); }); });
  if (type === 'DSO') rows.forEach((r) => { r.jawaban = parseJ_(r.jawaban); });
  if (type === 'JADWAL' && f.pic && f.pic !== 'SEMUA') rows = rows.filter((r) => r.pic === f.pic);
  if (!me.isMgr) rows = rows.filter((r) => r.toko === me.toko);
  else if (f.toko && f.toko !== 'SEMUA') rows = rows.filter((r) => r.toko === f.toko);
  if (f.from) rows = rows.filter((r) => r.tanggal >= f.from);
  if (f.to) rows = rows.filter((r) => r.tanggal <= f.to);
  if (f.form) rows = rows.filter((r) => r.form === f.form);
  if (f.status && f.status !== 'SEMUA') rows = rows.filter((r) => r.status === f.status);
  if (f.validasi === 'Y') rows = rows.filter((r) => r.validasi === 'Y' || r.validasi === 'Approved');
  if (f.validasi === 'N') rows = rows.filter((r) => !(r.validasi === 'Y' || r.validasi === 'Approved'));
  const td = today_(), open = (r) => r.status !== 'Selesai' && r.status !== 'Dibatalkan';
  if (f.khusus === 'terlambat') rows = rows.filter((r) => r.dueDate && r.dueDate < td && open(r));
  if (f.khusus === 'hariIni') rows = rows.filter((r) => r.dueDate === td && open(r));
  if (f.khusus === 'open') rows = rows.filter(open);
  if (f.khusus === 'belumValid') rows = rows.filter((r) => r.status === 'Selesai' && r.validasi !== 'Y');
  if (f.khusus === 'kritis') rows = rows.filter((r) => /Kritis|Tinggi/.test(r.prioritas) && open(r));
  if (f.q) { const q = String(f.q).toLowerCase(); rows = rows.filter((r) => JSON.stringify(r).toLowerCase().indexOf(q) >= 0); }
  if (type === 'JADWAL') rows.sort((a, b) => ((a.tanggal + a.jamMulai) < (b.tanggal + b.jamMulai) ? -1 : 1));
  else rows.sort((a, b) => (a.tanggal < b.tanggal ? 1 : a.tanggal > b.tanggal ? -1 : (a.id < b.id ? 1 : -1)));
  return rows;
}

export async function add_(ctx, type, data, tokoList) {
  const me = ctx.me; data = data || {};
  if (['MASALAH', 'TUGAS'].indexOf(type) < 0) throw new Error('Tipe form tidak diizinkan');
  const keys = keys_(type);
  if (!me.isMgr) tokoList = [me.toko];
  if (!tokoList || !tokoList.length) throw new Error('Pilih minimal satu toko');
  const now = now_();
  const out = tokoList.map((t) => {
    const r = {}; keys.forEach((k) => { r[k] = data[k] != null ? data[k] : ''; });
    r.id = ''; r.toko = t; r.tanggal = data.tanggal || today_(); r.status = r.status || 'Open';
    r.progress = r.progress || (r.status === 'Selesai' ? 100 : 0); r.validasi = ''; r.validasiOleh = ''; r.validasiTgl = ''; r.dibuatOleh = me.nama; r.updateTgl = now; r.updateOleh = me.nama;
    return r;
  });
  await ctx.save(type, out, 'insert');
  return { jumlah: out.length };
}

export async function update_(ctx, type, id, data) {
  const me = ctx.me; data = Object.assign({}, data || {});
  // CEKLIS ditambahkan (di Apps Script v6 edit riwayat checklist ditolak "Tipe edit tidak diizinkan")
  if (['MASALAH', 'TUGAS', 'CEKLIS'].indexOf(type) < 0) throw new Error('Tipe edit tidak diizinkan');
  const keys = keys_(type), cur = (await ctx.read(type, { ids: [id] }))[0];
  if (!cur) throw new Error(me.isMgr ? 'Data tidak ditemukan: ' + id : 'Bukan data toko Anda / data tidak ditemukan: ' + id);
  if (!me.isMgr) {
    if (cur.toko !== me.toko) throw new Error('Bukan data toko Anda');
    if (cur.validasi === 'Y') throw new Error('Sudah divalidasi SPV, tidak bisa diubah toko');
    Object.keys(data).forEach((k) => { if ((STORE_EDIT[type] || []).indexOf(k) < 0) delete data[k]; });
  }
  Object.keys(data).forEach((k) => { if (keys.indexOf(k) >= 0 && k !== 'id') cur[k] = data[k]; });
  if (type === 'MASALAH' || type === 'TUGAS') { if (cur.status === 'Selesai') { cur.progress = 100; if (!cur.tglSelesai) cur.tglSelesai = today_(); } if (cur.status !== 'Selesai' && data.status) cur.tglSelesai = ''; }
  if (type === 'CEKLIS' && data.status != null) cur.jam = cur.status === 'Selesai' ? (cur.jam || hm_()) : '';
  cur.updateTgl = now_(); cur.updateOleh = me.nama;
  return (await ctx.save(type, [cur], 'update'))[0];
}

export async function bulk_(ctx, type, ids, op, value) {
  const me = ctx.me;
  if (['MASALAH', 'TUGAS', 'CEKLIS'].indexOf(type) < 0) throw new Error('Tipe bulk tidak diizinkan');
  if (!ids || !ids.length) throw new Error('Tidak ada data terpilih');
  if (op !== 'status' && op !== 'hapus') mustMgr_(me);
  if (op === 'hapus') { const r = await ctx.del(type, ids); await removePhotos(r.photos); return { jumlah: r.jumlah }; }
  const keys = keys_(type), now = now_(), rows = await ctx.read(type, { ids }), out = [];
  rows.forEach((row) => {
    if (!me.isMgr && row.toko !== me.toko) return;
    const u = { id: row.id };
    if (op === 'validasi') { u.validasi = 'Y'; u.validasiOleh = me.nama; u.validasiTgl = now; }
    else if (op === 'batalValidasi') { u.validasi = ''; u.validasiOleh = ''; u.validasiTgl = ''; }
    else if (op === 'status') {
      if (!me.isMgr && row.validasi === 'Y') return;
      u.status = value; if (value === 'Selesai' && keys.indexOf('progress') >= 0) { u.progress = 100; u.tglSelesai = today_(); }
    } else return;
    u.updateTgl = now; u.updateOleh = me.nama; out.push(u);
  });
  await ctx.save(type, out, 'update');
  return { jumlah: out.length };
}

// ================= DAILY ROUTINE & CHECKLIST HARIAN STORE =================
export async function rutinSave_(ctx, d) {
  const me = ctx.me; d = d || {}; mustMgr_(me); if (!d.judul) throw new Error('Judul wajib diisi');
  const r = { id: d.id || '', judul: d.judul, deskripsi: d.deskripsi || '', kategori: d.kategori || '', prioritas: d.prioritas || 'Sedang', pic: d.pic || '',
    frekuensi: d.frekuensi || 'Harian', hari: d.hari || '', toko: d.toko || 'SEMUA', aktif: d.aktif === 'N' ? 'N' : 'Y', dibuatOleh: d.dibuatOleh || me.nama, updateTgl: now_(),
    interval: d.interval || '', mulai: d.mulai || '' };
  const saved = (await ctx.save('RUTIN', [r], 'upsert'))[0];
  r.id = saved.id; r.updateTgl = saved.updateTgl; return r;
}
export async function rutinHapus_(ctx, id) { mustMgr_(ctx.me); if (id) await ctx.del('RUTIN', [id]); return { ok: true }; }
// Apakah template rutin berlaku pada tanggal & toko tertentu
export function rutinBerlaku_(rt, tgl, toko) {
  if (String(rt.aktif).toUpperCase() === 'N') return false;
  const tk = String(rt.toko || 'SEMUA'); if (tk !== 'SEMUA' && tk.split('|').indexOf(toko) < 0) return false;
  if (rt.mulai && tgl < rt.mulai) return false;
  const d = new Date(tgl + 'T00:00:00Z'), list = String(rt.hari || '').split(',').map((x) => x.trim()).filter(String);
  switch (rt.frekuensi) {
    case 'Mingguan': return list.indexOf(String(d.getUTCDay())) >= 0;
    case 'Bulanan': return list.indexOf(String(d.getUTCDate())) >= 0;
    case 'Tahunan': return list.indexOf(pad_(d.getUTCDate(), 2) + '-' + pad_(d.getUTCMonth() + 1, 2)) >= 0;
    case 'Periodik': { const n = parseInt(rt.interval, 10) || 1, m = rt.mulai || tgl; return daysBetween_(m, tgl) % n === 0; }
    default: return true;
  }
}
export async function ceklisHari_(ctx, tgl, toko) {
  const me = ctx.me; tgl = tgl || today_(); toko = me.isMgr ? toko : me.toko; if (!toko || toko === 'SEMUA') throw new Error('Pilih toko');
  const rutin = (await ctx.read('RUTIN')).filter((r) => rutinBerlaku_(r, tgl, toko)), real = {};
  (await ctx.read('CEKLIS', { tanggal: tgl, toko })).forEach((c) => { if (c.tanggal === tgl && c.toko === toko) real[c.rutinId] = c; });
  return rutin.map((r) => { const c = real[r.id] || {}; return { rutinId: r.id, judul: r.judul, deskripsi: r.deskripsi, kategori: r.kategori, prioritas: r.prioritas, pic: r.pic, frekuensi: r.frekuensi,
    id: c.id || '', status: c.status || 'Belum', jam: c.jam || '', catatan: c.catatan || '', fotoId: c.fotoId || '', validasi: c.validasi || '', validasiOleh: c.validasiOleh || '' }; });
}
export async function ceklisSet_(ctx, p) {
  const me = ctx.me, tgl = p.tanggal || today_(), toko = me.isMgr ? p.toko : me.toko;
  if (!me.isMgr && tgl < addDays_(today_(), -1)) throw new Error('Checklist hanya bisa diisi untuk hari ini / kemarin');
  if (!toko || toko === 'SEMUA') throw new Error('Pilih toko');
  let cur = null;
  if (p.id) cur = (await ctx.read('CEKLIS', { ids: [p.id] }))[0] || null;
  if (!cur) { const all = (await ctx.read('CEKLIS', { tanggal: tgl, toko })).filter((c) => c.tanggal === tgl && c.toko === toko && c.rutinId === p.rutinId); cur = all[all.length - 1] || null; }
  cur = cur || {};
  if (cur.validasi === 'Y' && !me.isMgr) throw new Error('Sudah divalidasi SPV');
  cur.id = cur.id || ''; cur.tanggal = tgl; cur.toko = toko; cur.rutinId = p.rutinId || cur.rutinId || ''; cur.judul = p.judul || cur.judul || '';
  if (p.status != null) { cur.status = p.status ? 'Selesai' : 'Belum'; cur.jam = p.status ? hm_() : ''; }
  if (p.catatan != null) cur.catatan = p.catatan; if (p.fotoId != null) cur.fotoId = p.fotoId;
  cur.validasi = cur.validasi || ''; cur.validasiOleh = cur.validasiOleh || ''; cur.validasiTgl = cur.validasiTgl || ''; cur.updateTgl = now_(); cur.updateOleh = me.nama;
  return (await ctx.save('CEKLIS', [cur], 'upsert'))[0];
}

// ================= DAILY STORE OPERATION =================
export async function dsoHari_(ctx, tgl, toko) {
  const me = ctx.me; tgl = tgl || today_(); toko = me.isMgr ? toko : me.toko;
  const f = { tanggal: tgl }; if (toko && toko !== 'SEMUA') f.toko = toko;
  const rows = (await ctx.read('DSO', f)).filter((r) => r.tanggal === tgl && (toko === 'SEMUA' || r.toko === toko));
  rows.forEach((r) => { r.jawaban = parseJ_(r.jawaban); });
  return rows;
}
const dsoOut = (row) => { const r = Object.assign({}, row); r.jawaban = parseJ_(r.jawaban); return r; };
export async function dsoSubmit_(ctx, p) {
  const row = await ctx.call('dco_dso_submit', { p: { form: p.form, tanggal: p.tanggal || '', toko: p.toko || '', jawaban: p.jawaban || {}, keterangan: p.keterangan || '', oleh: p.oleh || '' } });
  ctx.invalidate('DSO'); return dsoOut(toCamel(row));
}
export async function dsoValidasi_(ctx, p) {
  mustMgr_(ctx.me);
  const q = { id: p.id }; if ('validasi' in p) q.validasi = p.validasi == null ? 'Approved' : p.validasi; if (p.ketSpv != null) q.ketSpv = p.ketSpv;
  const row = await ctx.call('dco_dso_validate', { p: q }); ctx.invalidate('DSO'); return dsoOut(toCamel(row));
}
export async function dsoPatch_(ctx, p) {
  const q = { id: p.id }; if (p.itemId) { q.itemId = p.itemId; q.fotoId = p.fotoId || ''; } if (p.keterangan != null) q.keterangan = p.keterangan; if (p.oleh != null) q.oleh = p.oleh;
  const r = await ctx.call('dco_dso_patch', { p: q }); ctx.invalidate('DSO'); await removePhotos(r.photos);
  return dsoOut(toCamel(r.row));
}
export async function dsoHapus_(ctx, id) { const r = await ctx.del('DSO', [id]); await removePhotos(r.photos); return { ok: true }; }

// ================= VISITING CHECK POINT (SPV / MASTER) =================
export async function hitungVisit_(ctx, jaw, cfg) {
  const def = (await ctx.read('VISIT_DEF')).filter((d) => d.aktif !== 'N'), skor = {}; let tp = 0, tdn = 0;
  cfg.visitSeksi.forEach((s) => {
    const items = def.filter((d) => d.seksi === s.kode); let pass = 0, dn = 0;
    items.forEach((it) => { const v = jaw[it.id]; if (v === 'Sesuai') { pass++; dn++; } else if (v === 'Tidak Sesuai') dn++; });
    skor[s.kode] = { pass, dinilai: dn, score: dn ? Math.round(pass * 10000 / dn) / 100 : null }; tp += pass; tdn += dn;
  });
  const fs = tdn ? Math.round(tp * 10000 / tdn) / 100 : 0, th = cfg.rating; let rating = 'Critical';
  if (fs >= th.Excellent) rating = 'Excellent'; else if (fs >= th.Good) rating = 'Good'; else if (fs >= th['Need Improvement']) rating = 'Need Improvement';
  return { skor, finalScore: fs, rating, totalPass: tp, totalDinilai: tdn };
}
export async function visitSave_(ctx, d) {
  const me = ctx.me; mustMgr_(me);
  if (!d || !d.toko || !/^\d{4}-\d{2}-\d{2}$/.test(String(d.tanggal || ''))) throw new Error('Toko dan tanggal visit wajib benar');
  if ((await tokoAktif_(ctx)).indexOf(d.toko) < 0) throw new Error('Toko tidak tersedia');
  const cfg = await getCfg_(ctx); let cur = {};
  if (d.id) { cur = (await ctx.read('VISIT', { ids: [d.id] }))[0]; if (!cur) throw new Error('Visit tidak ditemukan; muat ulang data'); }
  if (cur.validasi === 'Approved' && !me.isMaster) throw new Error('Visit sudah diapprove Manager');
  const jaw = d.jawaban || {}, h = await hitungVisit_(ctx, jaw, cfg);
  if (!h.totalDinilai) throw new Error('Isi minimal satu point visit sebelum menyimpan');
  const proposed = Array.isArray(d.issuesList) ? d.issuesList.filter((i) => String(i.issue || '').trim()) : null;
  if (proposed !== null) {
    const fail = (await ctx.read('VISIT_DEF')).filter((x) => x.aktif !== 'N' && jaw[x.id] === 'Tidak Sesuai');
    fail.forEach((point) => {
      if (!proposed.some((i) => i.pointId === point.id && i.status !== 'Dibatalkan'))
        throw new Error('Point ' + point.id + ' Tidak Sesuai harus memiliki issue/action plan, PIC dan due date');
    });
    proposed.forEach((i) => {
      if (!String(i.action || '').trim() || !String(i.pic || '').trim() || !/^\d{4}-\d{2}-\d{2}$/.test(String(i.dueDate || '')))
        throw new Error('Setiap issue terisi wajib mempunyai action, PIC, dan due date yang valid');
    });
  }
  const r = { id: cur.id || '', tanggal: d.tanggal, minggu: isoWeekYmd_(d.tanggal), toko: d.toko, leader: d.leader || '', evaluator: d.evaluator || me.nama,
    tipe: d.tipe || 'Offline Visit', jawaban: JSON.stringify(jaw), catatan: JSON.stringify(d.catatan || {}), foto: JSON.stringify(d.foto || {}),
    issues: proposed === null ? (d.issues || cur.issues || '') : proposed.map((i) => i.issue).join('\n'), skor: JSON.stringify(h.skor),
    finalScore: h.finalScore, rating: h.rating, totalPass: h.totalPass, totalDinilai: h.totalDinilai,
    validasi: cur.validasi || '', validasiOleh: cur.validasiOleh || '', validasiTgl: cur.validasiTgl || '',
    updateTemuan: JSON.stringify(d.updateTemuan || parseJ_(cur.updateTemuan)), keterangan: d.keterangan != null ? d.keterangan : cur.keterangan || '', updateTgl: now_(), updateOleh: me.nama };
  const saved = (await ctx.save('VISIT', [r], 'upsert'))[0];
  r.id = saved.id; r.updateTgl = saved.updateTgl; r.updateOleh = saved.updateOleh;
  if (proposed !== null) await syncVisitIssues_(ctx, r, proposed);
  return r;
}
async function syncVisitIssues_(ctx, visit, issues) {
  const me = ctx.me, existing = (await ctx.read('VISIT_ISSUE')).filter((i) => i.visitId === visit.id);
  const byId = {}, used = {}; existing.forEach((i) => { byId[i.id] = i; });
  const upd = [], adds = [];
  issues.forEach((input) => {
    const prev = input.id ? byId[input.id] : existing.filter((x) => !used[x.id] && x.pointId === (input.pointId || '') && x.issue === String(input.issue || '').trim())[0] || null;
    if (input.id && !prev) throw new Error('Issue ' + input.id + ' tidak ada dalam visit ini');
    if (prev) used[prev.id] = true;
    if (prev && prev.validasi === 'Y' && !me.isMaster) throw new Error('Issue tervalidasi, hanya Master dapat mengubah');
    const item = { id: prev ? prev.id : '', visitId: visit.id, tanggal: visit.tanggal, toko: visit.toko,
      pointId: input.pointId || '', seksi: input.seksi || '', issue: String(input.issue || '').trim(), akar: input.akar || '', action: input.action || '',
      pic: input.pic || '', dueDate: input.dueDate || '', prioritas: input.prioritas || 'Sedang', status: input.status || 'Open',
      progress: input.status === 'Selesai' ? 100 : Math.min(99, Math.max(0, Number(input.progress) || 0)),
      fotoId: input.fotoId || (prev && prev.fotoId) || (parseJ_(visit.foto)[input.pointId] || ''),
      fotoAfter: input.fotoAfter !== undefined ? input.fotoAfter : (prev && prev.fotoAfter) || '',
      updateNote: input.updateNote !== undefined ? input.updateNote : (prev && prev.updateNote) || '',
      validasi: prev ? prev.validasi : '', validasiOleh: prev ? prev.validasiOleh : '', validasiTgl: prev ? prev.validasiTgl : '', updateTgl: now_(), updateOleh: me.nama };
    (prev ? upd : adds).push(item);
  });
  await ctx.save('VISIT_ISSUE', upd.concat(adds), 'upsert');
}
export async function issueList_(ctx, f) {
  mustMgr_(ctx.me); f = f || {}; const td = today_();
  const sf = {}; if (f.from) sf.from = f.from; if (f.to) sf.to = f.to; if (f.toko && f.toko !== 'SEMUA') sf.toko = f.toko;
  let rows = await ctx.read('VISIT_ISSUE', sf);
  if (f.toko && f.toko !== 'SEMUA') rows = rows.filter((r) => r.toko === f.toko);
  if (f.from) rows = rows.filter((r) => r.tanggal >= f.from);
  if (f.to) rows = rows.filter((r) => r.tanggal <= f.to);
  if (f.status && f.status !== 'SEMUA') rows = rows.filter((r) => (f.status === 'Pending' ? r.status !== 'Dibatalkan' && (r.status !== 'Selesai' || r.validasi !== 'Y') : r.status === f.status));
  if (f.prioritas && f.prioritas !== 'SEMUA') rows = rows.filter((r) => r.prioritas === f.prioritas);
  if (f.khusus === 'overdue') rows = rows.filter((r) => r.status !== 'Selesai' && r.status !== 'Dibatalkan' && r.dueDate && r.dueDate < td);
  if (f.q) { const q = String(f.q).toLowerCase(); rows = rows.filter((r) => [r.toko, r.issue, r.action, r.pic, r.pointId].join(' ').toLowerCase().indexOf(q) >= 0); }
  rows.sort((a, b) => (a.dueDate === b.dueDate ? (a.id < b.id ? -1 : 1) : (!a.dueDate ? 1 : !b.dueDate ? -1 : a.dueDate < b.dueDate ? -1 : 1)));
  return rows;
}
export async function issueUpdate_(ctx, d) {
  const me = ctx.me; mustMgr_(me); if (!d || !d.id) throw new Error('Issue ID wajib');
  const cur = (await ctx.read('VISIT_ISSUE', { ids: [d.id] }))[0]; if (!cur) throw new Error('Issue tidak ditemukan');
  if (cur.validasi === 'Y' && !me.isMaster) throw new Error('Issue sudah divalidasi; hubungi Master');
  ['akar', 'action', 'pic', 'dueDate', 'prioritas', 'status', 'progress', 'fotoId', 'fotoAfter', 'updateNote'].forEach((k) => { if (d[k] !== undefined) cur[k] = d[k]; });
  if (!String(cur.pic || '').trim() || !String(cur.action || '').trim() || !/^\d{4}-\d{2}-\d{2}$/.test(String(cur.dueDate || ''))) throw new Error('PIC, action dan due date wajib');
  if (d.validasi !== undefined) { if (cur.status !== 'Selesai' && d.validasi === 'Y') throw new Error('Selesaikan issue sebelum validasi'); cur.validasi = d.validasi === 'Y' ? 'Y' : ''; cur.validasiOleh = cur.validasi ? me.nama : ''; cur.validasiTgl = cur.validasi ? now_() : ''; }
  cur.progress = cur.status === 'Selesai' ? 100 : Math.max(0, Math.min(99, Number(cur.progress) || 0)); cur.updateTgl = now_(); cur.updateOleh = me.nama;
  return (await ctx.save('VISIT_ISSUE', [cur], 'update'))[0];
}
export async function visitValidasi_(ctx, p) {
  const me = ctx.me; mustMaster_(me);
  const cur = (await ctx.read('VISIT', { ids: [p.id] }))[0]; if (!cur) throw new Error('Data tidak ditemukan');
  const u = { id: p.id, validasi: p.validasi ? 'Approved' : '', validasiOleh: p.validasi ? me.nama : '', validasiTgl: p.validasi ? now_() : '', updateTgl: now_(), updateOleh: me.nama };
  if (p.keterangan != null) u.keterangan = p.keterangan;
  await ctx.save('VISIT', [u], 'update'); return { ok: true };
}
export async function visitHapus_(ctx, id) { mustMgr_(ctx.me); const r = await ctx.del('VISIT', [id]); return { ok: true, linkedIssues: r.linkedIssues || 0 }; }

// ================= JADWAL VISIT =================
export async function jadwalSave_(ctx, d) {
  const me = ctx.me; d = d || {}; mustMgr_(me);
  if (!d.tanggal || !d.toko || !d.jamMulai || !d.jamSelesai) throw new Error('Tanggal, toko, jam mulai & selesai wajib');
  if (d.jamSelesai <= d.jamMulai) throw new Error('Jam selesai harus setelah jam mulai');
  let cur = {}; if (d.id) cur = (await ctx.read('JADWAL', { ids: [d.id] }))[0] || {};
  if (cur.id && cur.pic !== me.nama && !me.isMaster) throw new Error('Hanya pembuat jadwal atau Master yang bisa mengubah');
  const r = { id: cur.id || '', tanggal: d.tanggal, toko: d.toko, pic: d.pic || cur.pic || me.nama, jamMulai: d.jamMulai, jamSelesai: d.jamSelesai, agenda: d.agenda || '',
    status: d.status || cur.status || 'Rencana', catatan: d.catatan != null ? d.catatan : (cur.catatan || ''), dibuatOleh: cur.dibuatOleh || me.nama, updateTgl: now_() };
  const saved = (await ctx.save('JADWAL', [r], 'upsert'))[0]; r.id = saved.id; r.updateTgl = saved.updateTgl; return r;
}
export async function jadwalHapus_(ctx, id) { mustMgr_(ctx.me); await ctx.del('JADWAL', [id]); return { ok: true }; }
