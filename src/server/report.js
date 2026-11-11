// Port Code.gs v6: Tracking, Scorecard, Notifikasi, Ringkasan 12 toko, Export
import { today_, addDays_, daysBetween_, hm_, mustMaster_ } from './util.js';
import { getCfg_, tokoAktif_, rutinBerlaku_, list_, issueList_ } from './core.js';

// dataSemua_ Code.gs — dibaca per kebutuhan rentang tanggal agar ringan
async function data_(ctx, opt) {
  const o = opt || {};
  const [masalah, rutin, ceklis, dso, visit, jadwal] = await Promise.all([
    ctx.read('MASALAH', o.masalah || {}), ctx.read('RUTIN'), ctx.read('CEKLIS', o.ceklis || {}), ctx.read('DSO', o.dso || {}),
    o.noVisit ? Promise.resolve([]) : ctx.read('VISIT', o.visit || {}), ctx.read('JADWAL', o.jadwal || {}),
  ]);
  let dsoAll = dso;
  if (o.dsoPending) {   // laporan DSO menunggu validasi (semua tanggal)
    const pend = await ctx.read('DSO', { pending: true }), seen = {};
    dsoAll = dso.concat(pend).filter((x) => (seen[x.id] ? false : (seen[x.id] = true)));
  }
  return { masalah, rutin, ceklis, dso: dsoAll, visit, jadwal };
}

export async function tracking_(ctx, from, to, tokoF) {
  const me = ctx.me, cfg = await getCfg_(ctx), td = today_(); to = to || td; from = from || addDays_(to, -6); if (daysBetween_(from, to) > 31) from = addDays_(to, -30);
  let tokoList = me.isMgr ? await tokoAktif_(ctx) : [me.toko]; if (me.isMgr && tokoF && tokoF !== 'SEMUA') tokoList = [tokoF];
  const dates = []; for (let d = from; d <= to; d = addDays_(d, 1)) dates.push(d);
  const D = await data_(ctx, { ceklis: { from, to }, dso: { from, to }, jadwal: { from: td, to: addDays_(td, 6) } });
  const grid = {}, score = {}, forms = cfg.dsoForms.map((f) => f.id), nDays = dates.filter((x) => x <= td).length || 1;
  tokoList.forEach((t) => {
    grid[t] = {}; const agg = { ckD: 0, ckT: 0, lapor: 0, dsoS: 0, dsoOT: 0, dsoA: 0, dsoExp: 0 };
    dates.forEach((dt) => {
      const tot = D.rutin.filter((r) => rutinBerlaku_(r, dt, t)).length, done = D.ceklis.filter((c) => c.tanggal === dt && c.toko === t && c.status === 'Selesai').length;
      const ms = D.masalah.filter((m) => m.tanggal === dt && m.toko === t);
      const dso = {}; D.dso.filter((x) => x.tanggal === dt && x.toko === t).forEach((x) => { dso[x.form] = (x.validasi === 'Approved' ? 'A' : x.validasi === 'Rejected' ? 'R' : 'S') + (x.slaSubmit === 'Terlambat' ? '!' : ''); });
      grid[t][dt] = { ckTot: tot, ckDone: done, msLapor: ms.length, msNihil: ms.some((m) => /^nihil$/i.test(String(m.masalah).trim())), dso };
      if (dt <= td) { agg.ckD += done; agg.ckT += tot; if (ms.length) agg.lapor++; agg.dsoExp += forms.length; forms.forEach((f) => { const v = dso[f]; if (v) { agg.dsoS++; if (v.indexOf('!') < 0) agg.dsoOT++; if (v[0] === 'A') agg.dsoA++; } }); }
    });
    const msT = D.masalah.filter((m) => m.toko === t), op = msT.filter((m) => m.status !== 'Selesai' && m.status !== 'Dibatalkan'), ov = op.filter((m) => m.dueDate && m.dueDate < td);
    const vis = D.visit.filter((v) => v.toko === t).sort((a, b) => (a.tanggal < b.tanggal ? 1 : -1)), visR = vis.filter((v) => v.tanggal >= from && v.tanggal <= to);
    const visAvg = visR.length ? visR.reduce((a, v) => a + (+v.finalScore || 0), 0) / visR.length : (vis[0] ? +vis[0].finalScore : null);
    const pct = (a, b) => (b ? Math.round(a * 100 / b) : null);
    const sc = { ceklis: pct(agg.ckD, agg.ckT), lapor: pct(agg.lapor, nDays), dso: pct(agg.dsoS, agg.dsoExp), dsoOnTime: pct(agg.dsoOT, agg.dsoS), dsoApproved: pct(agg.dsoA, agg.dsoS),
      visit: visAvg != null ? Math.round(visAvg) : null, visitN: visR.length, visitTgl: vis[0] ? vis[0].tanggal : '', visitRating: vis[0] ? vis[0].rating : '', msOpen: op.length, msOverdue: ov.length, msTotal: msT.length,
      masalah: op.length ? Math.max(0, Math.round(100 - ov.length * 100 / op.length)) : 100 };
    const w = cfg.bobot; let tw = 0, ts = 0; ['ceklis', 'lapor', 'dso', 'visit', 'masalah'].forEach((k) => { if (sc[k] != null && w[k]) { tw += w[k]; ts += sc[k] * w[k]; } });
    sc.total = tw ? Math.round(ts / tw) : null; score[t] = sc;
  });
  const visR = D.visit.filter((v) => v.tanggal >= from && v.tanggal <= to && tokoList.indexOf(v.toko) >= 0), rd = {};
  visR.forEach((v) => { rd[v.rating] = (rd[v.rating] || 0) + 1; });
  const jd = D.jadwal.filter((j) => j.tanggal === td && tokoList.indexOf(j.toko) >= 0).sort((a, b) => (a.jamMulai < b.jamMulai ? -1 : 1));
  return { from, to, dates, toko: tokoList, grid, score, forms: cfg.dsoForms, bobot: cfg.bobot,
    visit: { n: visR.length, avg: visR.length ? Math.round(visR.reduce((a, v) => a + (+v.finalScore || 0), 0) / visR.length) : null, rating: rd, pending: D.visit.filter((v) => !v.validasi).length },
    rutinAktif: D.rutin.filter((r) => r.aktif !== 'N').length, jadwalHariIni: jd,
    jadwalMinggu: D.jadwal.filter((j) => j.tanggal >= td && j.tanggal <= addDays_(td, 6) && tokoList.indexOf(j.toko) >= 0).length };
}

function pendingToko_(t, td, D, cfg) {
  const open = (r) => r.status !== 'Selesai' && r.status !== 'Dibatalkan', ms = D.masalah.filter((r) => r.toko === t);
  const ckTot = D.rutin.filter((r) => rutinBerlaku_(r, td, t)).length, ckDone = D.ceklis.filter((c) => c.tanggal === td && c.toko === t && c.status === 'Selesai').length;
  const h = hm_().split(':'), nowMin = (+h[0]) * 60 + (+h[1]), dsoToday = D.dso.filter((x) => x.tanggal === td && x.toko === t);
  const dsoBelum = cfg.dsoForms.filter((f) => { const bm = f.batas.split(':'); return nowMin > (+bm[0]) * 60 + (+bm[1]) && !dsoToday.some((x) => x.form === f.id); }).map((f) => f.nama);
  const dsoRejected = dsoToday.filter((x) => x.validasi === 'Rejected').map((x) => x.form);
  return { toko: t, ckBelum: Math.max(ckTot - ckDone, 0), ckTot, belumLapor: !ms.some((m) => m.tanggal === td), dsoBelum, dsoRejected,
    dsoPending: D.dso.filter((x) => x.toko === t && !x.validasi).length, msTerlambat: ms.filter((r) => open(r) && r.dueDate && r.dueDate < td).length, msOpen: ms.filter(open).length };
}

export async function notif_(ctx) {
  const me = ctx.me, td = today_(), cfg = await getCfg_(ctx), items = [];
  const D = await data_(ctx, { ceklis: { tanggal: td }, dso: { tanggal: td }, dsoPending: true, jadwal: { tanggal: td }, noVisit: !me.isMaster, visit: { pending: true } });
  const add = (n, teks, tab, f, lvl) => { if (n > 0) items.push({ n, teks, tab, f: f || {}, lvl: lvl || 'warn' }); };
  if (!me.isMgr) {
    const p = pendingToko_(me.toko, td, D, cfg);
    add(p.dsoBelum.length, 'Daily Store Operation belum dikirim (lewat batas): ' + p.dsoBelum.join(', '), 'dso', {}, 'danger');
    add(p.dsoRejected.length, 'Laporan DSO ditolak SPV, perbaiki & kirim ulang: ' + p.dsoRejected.join(', '), 'dso', {}, 'danger');
    add(p.ckBelum, 'Checklist harian belum dicentang', 'ceklis', {}, 'warn');
    add(p.belumLapor ? 1 : 0, 'Belum lapor briefing / masalah hari ini (isi NIHIL jika tidak ada)', 'MASALAH', { tambah: 1 }, 'warn');
    add(p.msTerlambat, 'Masalah melewati due date', 'MASALAH', { khusus: 'terlambat' }, 'danger');
    add(p.msOpen - p.msTerlambat, 'Masalah masih open', 'MASALAH', { khusus: 'open' }, 'info');
    const jdS = D.jadwal.filter((j) => j.tanggal === td && j.toko === me.toko && j.status !== 'Batal');
    add(jdS.length, 'Kunjungan SPV hari ini: ' + jdS.map((j) => j.pic + ' ' + j.jamMulai + '–' + j.jamSelesai).join(', '), 'jadwal', {}, 'info');
  } else {
    const jdM = D.jadwal.filter((j) => j.tanggal === td && j.pic === me.nama && j.status === 'Rencana');
    add(jdM.length, 'Jadwal visit Anda hari ini: ' + jdM.map((j) => j.toko + ' ' + j.jamMulai + '–' + j.jamSelesai).join(', '), 'jadwal', {}, 'info');
    const ps = (await tokoAktif_(ctx)).map((t) => pendingToko_(t, td, D, cfg)), nm = (a) => a.map((p) => p.toko).join(', ');
    const dsoB = ps.filter((p) => p.dsoBelum.length), lap = ps.filter((p) => p.belumLapor), ck = ps.filter((p) => p.ckBelum > 0);
    const pend = ps.reduce((a, p) => a + p.dsoPending, 0);
    add(pend, 'Laporan DSO menunggu validasi SPV', 'dso', { riwayat: 1 }, 'warn');
    add(dsoB.length, 'Toko belum kirim DSO (lewat batas): ' + dsoB.map((p) => p.toko + ' (' + p.dsoBelum.join('/') + ')').join(', '), 'dash', {}, 'danger');
    add(lap.length, 'Toko belum lapor briefing hari ini: ' + nm(lap), 'dash', {}, 'warn');
    add(ck.length, 'Toko checklist belum lengkap: ' + ck.map((p) => p.toko + ' (' + p.ckBelum + ')').join(', '), 'dash', {}, 'warn');
    add(ps.reduce((a, p) => a + p.msTerlambat, 0), 'Masalah melewati due date', 'MASALAH', { khusus: 'terlambat' }, 'danger');
    if (me.isMaster) add(D.visit.filter((v) => !v.validasi).length, 'Visiting check point menunggu validasi Manager', 'visit', {}, 'info');
  }
  return { today: td, items, total: items.filter((i) => i.lvl !== 'info').reduce((a, i) => a + i.n, 0) };
}

// Export selalu dari data server terbaru dan mengikuti batas role (tidak pernah memuat PIN)
export async function exportData_(ctx, module, f) {
  const me = ctx.me; f = f || {};
  const types = ['MASALAH', 'TUGAS', 'CEKLIS', 'DSO', 'VISIT', 'VISIT_ISSUE', 'JADWAL', 'RUTIN'];
  if (module === 'TOKO') { mustMaster_(me); return { module, rows: (await ctx.read('TOKO')).map((x) => ({ toko: x.nama, area: x.area, aktif: x.aktif })) }; }
  if (module === 'PENGATURAN') {
    mustMaster_(me); const rows = [];
    (await ctx.read('TOKO')).forEach((x) => { rows.push({ kelompok: 'TOKO', kode: x.nama, keterangan: x.area || '', nilai: x.aktif }); });
    (await ctx.read('USERS')).forEach((x) => { rows.push({ kelompok: 'USER', kode: x.username, keterangan: x.nama || '', nilai: x.role + ' / ' + x.toko }); });
    (await ctx.read('CONFIG')).forEach((x) => { rows.push({ kelompok: 'CONFIG', kode: x.key, keterangan: '', nilai: x.value }); });
    return { module, rows };
  }
  if (types.indexOf(module) < 0) throw new Error('Modul export tidak dikenal');
  if (module === 'RUTIN' && !me.isMgr) throw new Error('Hanya SPV dan Master');
  const rows = module === 'VISIT_ISSUE' ? await issueList_(ctx, f) : await list_(ctx, module, f);
  return { module, rows, max: rows.length };
}

// Kepatuhan per modul 12 toko (Master & SPV) — data apa adanya
export async function storeSummary_(ctx, date) {
  const me = ctx.me, day = /^\d{4}-\d{2}-\d{2}$/.test(String(date || '')) ? date : today_(), stores = me.isMgr ? await tokoAktif_(ctx) : [me.toko];
  const f = { tanggal: day };
  const D = await data_(ctx, { masalah: f, ceklis: f, dso: f, visit: f, jadwal: f }), cfg = await getCfg_(ctx), issues = me.isMgr ? await ctx.read('VISIT_ISSUE') : [];
  return stores.map((t) => {
    const c = D.ceklis.filter((x) => x.tanggal === day && x.toko === t), r = D.rutin.filter((x) => rutinBerlaku_(x, day, t));
    const done = c.filter((x) => x.status === 'Selesai').length, dso = D.dso.filter((x) => x.tanggal === day && x.toko === t), ms = D.masalah.filter((x) => x.tanggal === day && x.toko === t && String(x.masalah || '').trim());
    const visits = D.visit.filter((x) => x.tanggal === day && x.toko === t), plans = D.jadwal.filter((x) => x.tanggal === day && x.toko === t && x.status !== 'Batal');
    return { toko: t, tanggal: day, checklist: { total: r.length, done, valid: c.filter((x) => x.validasi === 'Y').length },
      dso: { total: cfg.dsoForms.length, submitted: dso.length, approved: dso.filter((x) => x.validasi === 'Approved').length },
      masalah: { lapor: ms.length, nihil: ms.some((x) => /^nihil$/i.test(String(x.masalah).trim())), open: ms.filter((x) => x.status !== 'Selesai' && x.status !== 'Dibatalkan').length },
      visit: { planned: plans.length, completed: visits.length }, issues: { pending: issues.filter((x) => x.toko === t && x.status !== 'Dibatalkan' && (x.status !== 'Selesai' || x.validasi !== 'Y')).length } };
  });
}
