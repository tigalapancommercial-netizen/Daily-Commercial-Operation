#!/usr/bin/env python3
"""Uji end-to-end: UI referensi + port Code.gs + RPC Supabase (PostgreSQL lokal via tests/mock_supabase.mjs).
Jalankan lewat: bash tests/run_e2e.sh   (database di-reset: stub Supabase + migrasi 006 + impor 007)"""
import asyncio, json, os, sys, io, zipfile, urllib.request, datetime
from playwright.async_api import async_playwright

BASE = os.environ.get('E2E_URL', 'http://localhost:54321')
SHOTS = os.environ.get('E2E_SHOTS', 'tests/screenshots')
os.makedirs(SHOTS, exist_ok=True)
results = []
def check(name, cond, info=''):
    results.append((bool(cond), name, info))
    print(('  PASS ' if cond else '  FAIL ') + name + ('' if cond else '  -> ' + str(info)[:300]))

def rpc(fn, args):
    req = urllib.request.Request(BASE + '/rest/v1/rpc/' + fn, data=json.dumps(args).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req) as r: return True, json.loads(r.read())
    except urllib.error.HTTPError as e: return False, json.loads(e.read())

API = """async ([a,p]) => JSON.parse(await window.__dcoApi(a, p, (window.S && S.me) ? S.me.token : ''))"""
async def api(page, a, p=None): return await page.evaluate(API, [a, p or {}])
MKIMG = """async (txt) => { const c=document.createElement('canvas'); c.width=640; c.height=480; const g=c.getContext('2d');
  const gr=g.createLinearGradient(0,0,640,480); gr.addColorStop(0,'#4f46e5'); gr.addColorStop(1,'#db2777'); g.fillStyle=gr; g.fillRect(0,0,640,480);
  g.fillStyle='#fff'; g.font='bold 42px sans-serif'; g.fillText(txt,40,250); return c.toDataURL('image/jpeg',0.6); }"""

async def login(page, user, pin='1234'):
    await page.goto(BASE + '/')
    await page.evaluate("()=>{try{localStorage.clear()}catch(e){}}")
    await page.goto(BASE + '/')
    await page.fill('#lUser', user); await page.fill('#lPin', pin); await page.click('#lgBtn')
    await page.wait_for_function("() => window.S && S.me && S.meta", timeout=15000)
    await page.wait_for_timeout(600)

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', args=['--no-sandbox'])
        errors = []
        async def newpage(vw=1366, vh=860, mobile=False):
            ctx = await browser.new_context(viewport={'width': vw, 'height': vh}, is_mobile=mobile, has_touch=mobile, accept_downloads=True)
            pg = await ctx.new_page()
            pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
            pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
            return pg

        # ================= A. LOGIN =================
        print('A. Login & sesi')
        ok, r = rpc('dco_login', {'p_username': 'master', 'p_pin': '9999'})
        check('PIN salah ditolak', r.get('ok') is False and 'PIN salah' in r.get('error', ''), r)
        for i in range(5): rpc('dco_login', {'p_username': 'tk-toraja', 'p_pin': '0000'})
        ok, r = rpc('dco_login', {'p_username': 'tk-toraja', 'p_pin': '1234'})
        check('Akun terkunci setelah 5x salah', r.get('ok') is False and 'Coba lagi' in r.get('error', ''), r)
        ok, r = rpc('dco_rows', {'p_token': 'palsu', 'p_type': 'MASALAH', 'p_filter': {}})
        check('Token palsu ditolak', not ok and 'login ulang' in r.get('message', ''), r)

        M = await newpage(); await login(M, 'master')
        check('Master login & dashboard', await M.inner_text('#pageTitle') == 'Dashboard')
        meta = M and await M.evaluate('() => S.meta')
        check('meta: 12 toko', len(meta['toko']) == 12, meta['toko'])
        check('meta: FORM_DEF 33 urut form+urutan', len(meta['formDef']) == 33 and meta['formDef'][0]['form'] == 'CLOSING' and meta['formDef'][0]['urutan'] == 1, meta['formDef'][:2])
        check('meta: VISIT_DEF 35', len(meta['visitDef']) == 35)
        check('meta: 14 user tanpa PIN', len(meta['users']) == 14 and all('pin' not in u and 'pinHash' not in u for u in meta['users']), meta['users'][:2])
        check('meta: spvList', meta['spvList'] == ['Master', 'SPV Area'], meta['spvList'])
        td = meta['today']; check('meta: today WITA', td == (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=8)).strftime('%Y-%m-%d'), td)

        # ================= B. MASTER: Rekap Masalah =================
        print('B. Rekap Masalah (Master)')
        r = await api(M, 'list', {'type': 'MASALAH', 'filter': {}})
        check('list MASALAH hasil migrasi = 33', r['ok'] and len(r['data']) == 33, r.get('error'))
        check('urutan list: tanggal desc, id desc', r['data'][0]['id'] == 'MS-00033', r['data'][0]['id'] if r['ok'] else '')
        r = await api(M, 'list', {'type': 'MASALAH', 'filter': {'khusus': 'open', 'toko': 'MAMU PALOPO'}})
        check('filter toko + open', r['ok'] and len(r['data']) == 4 and all(x['toko'] == 'MAMU PALOPO' for x in r['data']), [x['id'] for x in r['data']] if r['ok'] else r)
        r = await api(M, 'add', {'type': 'MASALAH', 'data': {'kategori': 'Operasional', 'masalah': 'Uji master multi toko', 'prioritas': 'Tinggi', 'pic': 'Ari', 'dueDate': td}, 'tokoList': ['TIGALAPANKAOS BTP', 'MAMU GOWA']})
        check('add MASALAH ke 2 toko', r['ok'] and r['data']['jumlah'] == 2, r)
        r = await api(M, 'list', {'type': 'MASALAH', 'filter': {'q': 'Uji master multi'}})
        ids = sorted(x['id'] for x in r['data']) if r['ok'] else []
        check('ID berurutan MS-00034/35', ids == ['MS-00034', 'MS-00035'], ids)
        r = await api(M, 'update', {'type': 'MASALAH', 'id': 'MS-00035', 'data': {'status': 'Selesai'}})
        check('update status Selesai -> progress 100 & tglSelesai', r['ok'] and r['data']['progress'] == 100 and r['data']['tglSelesai'] == td and r['data']['updateOleh'] == 'Master', r)
        r = await api(M, 'bulk', {'type': 'MASALAH', 'ids': ['MS-00004', 'MS-00009'], 'op': 'validasi'})
        check('bulk validasi', r['ok'] and r['data']['jumlah'] == 2, r)
        r = await api(M, 'list', {'type': 'MASALAH', 'filter': {'validasi': 'Y'}})
        check('filter validasi Y', r['ok'] and sorted(x['id'] for x in r['data']) == ['MS-00004', 'MS-00009'] and r['data'][0]['validasiOleh'] == 'Master', r.get('data', [])[:1])

        # ================= C. STORE =================
        print('C. Store (tk-btp)')
        T = await newpage(); await login(T, 'tk-btp')
        smeta = await T.evaluate('() => S.meta')
        check('store meta toko = tokonya', smeta['toko'] == ['TIGALAPANKAOS BTP'] and smeta['users'] == [] and smeta['tokoAll'] == [], smeta['toko'])
        r = await api(T, 'list', {'type': 'MASALAH', 'filter': {}})
        check('store hanya melihat tokonya', r['ok'] and len(r['data']) == 3 and all(x['toko'] == 'TIGALAPANKAOS BTP' for x in r['data']), [x['id'] for x in r.get('data', [])])
        r = await api(T, 'update', {'type': 'MASALAH', 'id': 'MS-00002', 'data': {'status': 'Selesai'}})
        check('store tidak bisa ubah toko lain', not r['ok'] and 'bukan data toko' in r['error'].lower(), r)
        await api(M, 'bulk', {'type': 'MASALAH', 'ids': ['MS-00028'], 'op': 'validasi'})
        r = await api(T, 'update', {'type': 'MASALAH', 'id': 'MS-00028', 'data': {'status': 'Selesai'}})
        check('store tidak bisa ubah data tervalidasi', not r['ok'] and 'divalidasi' in r['error'], r)
        r = await api(T, 'update', {'type': 'MASALAH', 'id': 'MS-00001', 'data': {'status': 'On Progress', 'progress': 40, 'validasi': 'Y', 'toko': 'MAMU BTP', 'update': 'FU IC'}})
        check('store edit: hanya kolom STORE_EDIT', r['ok'] and r['data']['status'] == 'On Progress' and r['data']['validasi'] == '' and r['data']['toko'] == 'TIGALAPANKAOS BTP' and r['data']['update'] == 'FU IC', r)
        r = await api(T, 'add', {'type': 'MASALAH', 'data': {'masalah': 'NIHIL', 'kategori': 'Lainnya', 'validasi': 'Y'}, 'tokoList': ['MAMU GOWA', 'MAMU BTP']})
        check('store add: toko dipaksa tokonya', r['ok'] and r['data']['jumlah'] == 1, r)
        r = await api(T, 'list', {'type': 'MASALAH', 'filter': {'q': 'NIHIL'}})
        nihil = r['data'][0] if r['ok'] and r['data'] else {}
        check('store add tersimpan benar', nihil.get('toko') == 'TIGALAPANKAOS BTP' and nihil.get('validasi') == '' and nihil.get('dibuatOleh') == 'TIGALAPANKAOS BTP', nihil)
        r = await api(T, 'bulk', {'type': 'MASALAH', 'ids': [nihil.get('id'), 'MS-00028', 'MS-00002'], 'op': 'hapus'})
        check('store bulk hapus: hanya miliknya & belum valid', r['ok'] and r['data']['jumlah'] == 1, r)
        r = await api(T, 'list', {'type': 'VISIT', 'filter': {}})
        check('store tidak boleh Visiting', not r['ok'] and 'SPV Area / Master' in r['error'], r)
        r = await api(T, 'issueList', {'filter': {}})
        check('store tidak boleh Issue Visit', not r['ok'], r)

        # Checklist harian
        r = await api(T, 'ceklisHari', {'tanggal': td})
        check('ceklisHari: routine harian muncul', r['ok'] and len(r['data']) == 1 and r['data'][0]['rutinId'] == 'RT-0001', r)
        r = await api(T, 'ceklisSet', {'rutinId': 'RT-0001', 'judul': 'Story WA Focus Selling', 'tanggal': td, 'status': True})
        check('ceklisSet centang -> Selesai + jam server', r['ok'] and r['data']['status'] == 'Selesai' and len(r['data']['jam']) == 5 and r['data']['id'].startswith('CK-'), r)
        ck_id = r['data']['id'] if r['ok'] else ''
        check('ID checklist lanjut dari data lama (CK-000003)', ck_id == 'CK-000003', ck_id)
        img = await T.evaluate(MKIMG, 'CHECKLIST')
        r = await api(T, 'uploadFoto', {'dataUrl': img, 'nama': 'CK_' + td})
        check('upload foto ke Storage', r['ok'] and r['data']['id'].count('/') == 1 and r['data']['id'].endswith('.jpg'), r)
        foto1 = r['data']['id'] if r['ok'] else ''
        with urllib.request.urlopen(BASE + '/storage/v1/object/public/dco-foto/' + foto1) as resp:
            check('foto bisa dibuka via URL publik', resp.status == 200 and len(resp.read()) > 1000)
        r = await api(T, 'ceklisSet', {'id': ck_id, 'rutinId': 'RT-0001', 'tanggal': td, 'fotoId': foto1, 'catatan': 'sudah posting'})
        check('ceklisSet foto + catatan', r['ok'] and r['data']['fotoId'] == foto1 and r['data']['catatan'] == 'sudah posting' and r['data']['status'] == 'Selesai', r)
        old = (datetime.date.fromisoformat(td) - datetime.timedelta(days=3)).isoformat()
        r = await api(T, 'ceklisSet', {'rutinId': 'RT-0001', 'tanggal': old, 'status': True})
        check('store tidak bisa isi checklist > kemarin', not r['ok'] and 'hari ini / kemarin' in r['error'], r)

        # DSO
        r = await api(T, 'dsoSubmit', {'form': 'LAMPU', 'tanggal': td, 'jawaban': {'FD-031': foto1}})
        check('DSO wajib foto lengkap', not r['ok'] and 'Foto wajib belum lengkap' in r['error'] and 'Lampu neon box menyala' in r['error'], r)
        photos = {}
        for fid in ['FD-031', 'FD-032', 'FD-033']:
            u = await api(T, 'uploadFoto', {'dataUrl': await T.evaluate(MKIMG, fid), 'nama': 'DSO'})
            photos[fid] = u['data']['id']
        r = await api(T, 'dsoSubmit', {'form': 'LAMPU', 'tanggal': td, 'jawaban': photos, 'keterangan': 'aman', 'oleh': 'Yuyu'})
        now_min = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=8))
        exp_sla = 'Tepat Waktu' if now_min.hour * 60 + now_min.minute <= 18 * 60 + 30 else 'Terlambat'
        check('DSO submit + SLA kirim server', r['ok'] and r['data']['slaSubmit'] == exp_sla and r['data']['id'] == 'DS-000001' and r['data']['jawaban']['FD-031'] == photos['FD-031'], r)
        dso_id = r['data']['id'] if r['ok'] else ''
        r = await api(T, 'dsoPatch', {'id': dso_id, 'keterangan': 'aman terkendali'})
        check('dsoPatch keterangan tanpa submit ulang', r['ok'] and r['data']['keterangan'] == 'aman terkendali', r)
        r = await api(T, 'dsoHari', {'tanggal': td})
        check('dsoHari store', r['ok'] and len(r['data']) == 1 and isinstance(r['data'][0]['jawaban'], dict), r)
        r = await api(T, 'notif', {})
        check('notif store berjalan', r['ok'] and isinstance(r['data']['items'], list), r)
        r = await api(T, 'tracking', {'from': td, 'to': td})
        check('tracking store: 1 toko & skor', r['ok'] and r['data']['toko'] == ['TIGALAPANKAOS BTP'] and r['data']['score']['TIGALAPANKAOS BTP']['ceklis'] == 100, r.get('data', {}).get('score') if r['ok'] else r)

        # ================= D. SPV =================
        print('D. SPV: validasi DSO, Visiting, Issue, Jadwal, Routine')
        P = await newpage(); await login(P, 'spv')
        r = await api(P, 'dsoValidasi', {'id': dso_id, 'validasi': 'Approved', 'ketSpv': 'OK'})
        check('SPV approve DSO + SLA validasi', r['ok'] and r['data']['validasi'] == 'Approved' and r['data']['slaValidasi'] in ('Tepat Waktu', 'Terlambat') and r['data']['validasiOleh'] == 'SPV Area', r)
        r = await api(T, 'dsoPatch', {'id': dso_id, 'keterangan': 'ubah'})
        check('store tidak bisa ubah DSO approved', not r['ok'] and 'approve' in r['error'], r)
        r = await api(T, 'dsoSubmit', {'form': 'LAMPU', 'tanggal': td, 'jawaban': photos})
        check('store tidak bisa submit ulang DSO approved', not r['ok'] and 'approve' in r['error'], r)
        r = await api(P, 'dsoValidasi', {'id': dso_id, 'validasi': 'Rejected', 'ketSpv': 'foto buram'})
        r2 = await api(T, 'dsoSubmit', {'form': 'LAMPU', 'tanggal': td, 'jawaban': photos})
        check('DSO ditolak -> store kirim ulang, validasi reset', r['ok'] and r2['ok'] and r2['data']['validasi'] == '' and r2['data']['ketSpv'] == 'foto buram', r2)

        defs = meta['visitDef']
        jaw = {d['id']: 'Sesuai' for d in defs}; jaw['A01'] = 'Tidak Sesuai'; jaw['C03'] = 'NA'
        r = await api(P, 'visitSave', {'data': {'tanggal': td, 'toko': 'MAMU GOWA', 'leader': 'Sasa', 'jawaban': jaw, 'issuesList': []}})
        check('visit: point Tidak Sesuai wajib issue', not r['ok'] and 'A01' in r['error'], r)
        vfoto = (await api(P, 'uploadFoto', {'dataUrl': await P.evaluate(MKIMG, 'VISIT A'), 'nama': 'VISIT'}))['data']['id']
        r = await api(P, 'visitSave', {'data': {'tanggal': td, 'toko': 'MAMU GOWA', 'leader': 'Sasa', 'jawaban': jaw, 'catatan': {'A': 'selisih kas'}, 'foto': {'A': vfoto},
            'issuesList': [{'pointId': 'A01', 'seksi': 'A', 'issue': 'Selisih kas 50rb', 'action': 'Audit ulang', 'pic': 'Sasa', 'dueDate': td, 'prioritas': 'Tinggi'}]}})
        exp_fs = round(33 * 10000 / 34) / 100
        check('visitSave skor & rating', r['ok'] and r['data']['finalScore'] == exp_fs and r['data']['rating'] == 'Excellent' and r['data']['id'] == 'VS-00001' and r['data']['totalDinilai'] == 34, r)
        vid = r['data']['id'] if r['ok'] else ''
        r = await api(P, 'issueList', {'filter': {'status': 'Pending'}})
        check('issue visit dibuat', r['ok'] and len(r['data']) == 1 and r['data'][0]['id'] == 'VI-000001' and r['data'][0]['visitId'] == vid, r)
        r = await api(P, 'visitHapus', {'id': vid})
        check('visit tidak bisa dihapus bila issue open', not r['ok'] and 'Pending Matter' in r['error'], r)
        r = await api(P, 'issueUpdate', {'data': {'id': 'VI-000001', 'validasi': 'Y'}})
        check('issue harus selesai sebelum validasi', not r['ok'] and 'Selesaikan issue' in r['error'], r)
        r = await api(P, 'issueUpdate', {'data': {'id': 'VI-000001', 'status': 'Selesai'}})
        r2 = await api(P, 'issueUpdate', {'data': {'id': 'VI-000001', 'validasi': 'Y'}})
        check('issue selesai & tervalidasi', r['ok'] and r['data']['progress'] == 100 and r2['ok'] and r2['data']['validasi'] == 'Y', (r, r2))
        r = await api(P, 'visitValidasi', {'id': vid, 'validasi': True})
        check('SPV tidak bisa approve visit (khusus Master)', not r['ok'] and 'Master' in r['error'], r)
        r = await api(M, 'visitValidasi', {'id': vid, 'validasi': True, 'keterangan': 'ok'})
        r2 = await api(P, 'visitSave', {'data': {'id': vid, 'tanggal': td, 'toko': 'MAMU GOWA', 'jawaban': jaw}})
        check('Master approve visit; SPV tidak bisa ubah', r['ok'] and not r2['ok'] and 'diapprove' in r2['error'], (r, r2))
        r = await api(P, 'list', {'type': 'VISIT', 'filter': {}})
        check('list VISIT (JSON ter-parse)', r['ok'] and isinstance(r['data'][0]['jawaban'], dict) and r['data'][0]['validasi'] == 'Approved' and r['data'][0]['minggu'] > 0, r)

        r = await api(P, 'jadwalSave', {'data': {'tanggal': td, 'toko': 'TIGALAPANKAOS BTP', 'jamMulai': '10:00', 'jamSelesai': '12:00', 'agenda': 'Cek VM'}})
        check('jadwalSave', r['ok'] and r['data']['id'] == 'JD-00001' and r['data']['pic'] == 'SPV Area' and r['data']['status'] == 'Rencana', r)
        r = await api(P, 'jadwalSave', {'data': {'tanggal': td, 'toko': 'MAMU BTP', 'jamMulai': '13:00', 'jamSelesai': '12:00'}})
        check('jadwal jam selesai > mulai', not r['ok'], r)
        r = await api(T, 'notif', {})
        check('store mendapat notif kunjungan SPV', r['ok'] and any('Kunjungan SPV hari ini' in i['teks'] for i in r['data']['items']), r)
        r = await api(P, 'notif', {})
        check('SPV mendapat notif jadwal saya', r['ok'] and any('Jadwal visit Anda' in i['teks'] for i in r['data']['items']), r)
        r = await api(P, 'rutinSave', {'data': {'judul': 'Cek APAR', 'frekuensi': 'Mingguan', 'hari': '1,4', 'toko': 'MAMU GOWA|MAMU BTP', 'prioritas': 'Sedang'}})
        check('rutinSave Mingguan', r['ok'] and r['data']['id'] == 'RT-0002', r)
        r = await api(T, 'rutinSave', {'data': {'judul': 'x'}})
        check('store tidak bisa buat routine', not r['ok'], r)
        r = await api(P, 'tracking', {'from': td, 'to': td})
        check('tracking SPV 12 toko', r['ok'] and len(r['data']['toko']) == 12 and r['data']['visit']['n'] == 1, r.get('error'))
        r = await api(P, 'storeSummary', {'tanggal': td})
        check('storeSummary 12 toko', r['ok'] and len(r['data']) == 12, r.get('error'))
        r = await api(P, 'exportData', {'module': 'VISIT_ISSUE', 'filter': {}})
        check('export VISIT_ISSUE', r['ok'] and len(r['data']['rows']) == 1, r)

        # ================= E. MASTER: Pengaturan =================
        print('E. Pengaturan & Backup (Master)')
        r = await api(M, 'cfgSave', {'key': 'slaValidasiJam', 'value': 4})
        check('cfgSave', r['ok'] and r['data']['slaValidasiJam'] == 4, r)
        r = await api(M, 'cfgSave', {'key': 'hack', 'value': 1})
        check('cfgSave key tidak dikenal ditolak', not r['ok'], r)
        r = await api(M, 'defSave', {'type': 'FORM_DEF', 'data': {'form': 'LAMPU', 'urutan': 4, 'label': 'Lampu parkir menyala', 'deskripsi': 'Foto lampu parkir', 'wajib': 'N'}})
        check('defSave FORM_DEF -> FD-034', r['ok'] and r['data']['id'] == 'FD-034' and r['data']['wajib'] == 'N', r)
        r = await api(M, 'defSave', {'type': 'VISIT_DEF', 'data': {'seksi': 'A', 'label': 'Brankas terkunci'}})
        check('defSave VISIT_DEF -> A10 (kode=id)', r['ok'] and r['data']['id'] == 'A10' and r['data']['kode'] == 'A10', r)
        r = await api(M, 'defHapus', {'type': 'VISIT_DEF', 'id': 'A10'})
        check('defHapus', r['ok'])
        r = await api(P, 'defSave', {'type': 'FORM_DEF', 'data': {'label': 'x'}})
        check('SPV tidak bisa ubah form', not r['ok'], r)
        r = await api(M, 'addToko', {'nama': 'mamu test', 'area': 'Sulsel'})
        check('addToko + user otomatis', r['ok'] and r['data'] == {'nama': 'MAMU TEST', 'username': 'mamu-test'}, r)
        r = await api(M, 'tokoSave', {'nama': 'MAMU TEST', 'area': 'Sulsel', 'aktif': 'N'})
        m2 = await api(M, 'meta', {})
        check('tokoSave nonaktif -> hilang dari daftar aktif', r['ok'] and 'MAMU TEST' not in m2['data']['toko'] and any(t['nama'] == 'MAMU TEST' for t in m2['data']['tokoAll']), r)
        r = await api(M, 'userSave', {'username': 'SPV2', 'pin': '4321', 'role': 'SPV', 'nama': 'SPV Dua'})
        ok, lg = rpc('dco_login', {'p_username': 'spv2', 'p_pin': '4321'})
        check('userSave user baru & bisa login', r['ok'] and r['data']['mode'] == 'baru' and lg.get('ok') and lg['data']['role'] == 'SPV', (r, lg))
        r = await api(M, 'hapusUser', {'username': 'master'})
        check('tidak bisa hapus diri sendiri', not r['ok'] and 'diri sendiri' in r['error'], r)
        r = await api(M, 'userSave', {'username': 'master', 'role': 'SPV'})
        check('Master terakhir tidak bisa diturunkan', not r['ok'] and 'Master' in r['error'], r)
        r = await api(M, 'hapusUser', {'username': 'spv2'})
        ok, rr = rpc('dco_whoami', {'p_token': lg['data']['token']})
        check('hapus user -> sesinya tidak berlaku', r['ok'] and not ok, rr)
        r = await api(M, 'exportData', {'module': 'PENGATURAN', 'filter': {}})
        check('export PENGATURAN tanpa PIN', r['ok'] and '1234' not in json.dumps(r['data']) and any(x['kelompok'] == 'USER' for x in r['data']['rows']), r.get('error'))
        r = await api(P, 'exportData', {'module': 'PENGATURAN', 'filter': {}})
        check('export PENGATURAN khusus Master', not r['ok'], r)

        # Ganti PIN (store)
        r = await api(T, 'gantiPin', {'pinLama': '0000', 'pinBaru': '5678'})
        check('ganti PIN: PIN lama salah', not r['ok'] and 'PIN lama salah' in r['error'], r)
        old_tok = await T.evaluate('() => S.me.token')
        r = await api(T, 'gantiPin', {'pinLama': '1234', 'pinBaru': '5678'})
        ok, rr = rpc('dco_whoami', {'p_token': old_tok})
        check('ganti PIN: token baru, sesi lama dicabut', r['ok'] and r['data']['token'] != old_tok and not ok, r)
        await T.evaluate('(u) => { S.me = u; localStorage.setItem("ac_me", JSON.stringify(u)); }', r['data'])

        # Backup / arsip / hapus
        r = await api(M, 'archivePreview', {'scope': 'SEMUA', 'from': '', 'to': ''})
        check('archivePreview SEMUA', r['ok'] and r['data']['counts']['MASALAH'] == 35 and r['data']['blocked']['MASALAH'] > 0, r)
        r = await api(M, 'backup', {'scope': 'MASALAH', 'from': '2026-11-10', 'to': '2026-11-10', 'hapus': True})
        check('arsip ditolak jika masih ada open', not r['ok'] and 'open/pending' in r['error'], r)
        r = await api(M, 'backup', {'scope': 'SEMUA', 'from': '', 'to': '', 'hapus': False})
        check('backup SEMUA (salin)', r['ok'] and r['data']['nama'].startswith('BACKUP_SEMUA_AWAL_sd_AKHIR_') and r['data']['url'].startswith('#dco-backup:') and not r['data']['dihapus'], r)
        bk = r['data'] if r['ok'] else {}
        r = await api(M, 'backupList', {})
        check('backupList', r['ok'] and len(r['data']) == 1 and r['data'][0]['nama'] == bk.get('nama'), r)
        async with M.expect_download() as dl:
            await M.evaluate('(u) => window.open(u, "_blank", "noopener")', bk.get('url', ''))
        d = await dl.value; path = await d.path()
        zf = zipfile.ZipFile(path); names = zf.namelist()
        wb = zf.read('xl/workbook.xml').decode()
        check('file backup .xlsx valid (INFO + 7 tab)', d.suggested_filename == bk.get('nama') + '.xlsx' and wb.count('<sheet ') == 8 and 'name="MASALAH"' in wb, (d.suggested_filename, names))
        s_mas = zf.read('xl/worksheets/sheet2.xml').decode()
        check('isi backup MASALAH 35 baris + header', s_mas.count('<row ') == 36 and 'Tanggal Briefing' in s_mas, s_mas.count('<row '))
        r = await api(M, 'backup', {'scope': 'CEKLIS', 'from': '2026-11-11', 'to': '2026-11-11', 'hapus': True})
        check('arsip CEKLIS (backup lalu hapus)', r['ok'] and r['data']['deleted'] == {'CEKLIS': 1} and r['data']['dihapus'], r)
        r = await api(M, 'wipe', {'scope': 'JADWAL', 'from': '', 'to': '', 'hapusFoto': True, 'confirm': 'HAPUS', 'allTime': True})
        check('wipe butuh HAPUS PERMANEN', not r['ok'], r)
        r = await api(M, 'wipe', {'scope': 'JADWAL', 'from': '', 'to': '', 'hapusFoto': True, 'confirm': 'HAPUS PERMANEN', 'allTime': True})
        check('wipe JADWAL', r['ok'] and r['data']['jumlah'] == 1, r)

        # Hapus data -> foto ikut terhapus dari storage
        u = await api(T, 'uploadFoto', {'dataUrl': await T.evaluate(MKIMG, 'HAPUS'), 'nama': 'MS'})
        tfoto = u['data']['id']
        await api(T, 'add', {'type': 'TUGAS', 'data': {'judul': 'Tugas foto', 'fotoId': tfoto}, 'tokoList': []})
        tr = await api(T, 'list', {'type': 'TUGAS', 'filter': {}})
        tid = tr['data'][0]['id'] if tr['ok'] and tr['data'] else ''
        r = await api(T, 'bulk', {'type': 'TUGAS', 'ids': [tid], 'op': 'hapus'})
        try:
            urllib.request.urlopen(BASE + '/storage/v1/object/public/dco-foto/' + tfoto); gone = False
        except urllib.error.HTTPError: gone = True
        check('hapus data -> file foto ikut terhapus', r['ok'] and r['data']['jumlah'] == 1 and gone, r)

        # ================= F. KEAMANAN RPC LANGSUNG =================
        print('F. Keamanan (panggilan RPC langsung, melewati UI)')
        stok = await T.evaluate('() => S.me.token')
        ok, r = rpc('dco_rows', {'p_token': stok, 'p_type': 'MASALAH', 'p_filter': {'toko': 'MAMU GOWA'}})
        check('RPC: store tidak bisa baca toko lain', ok and all(x['toko'] == 'TIGALAPANKAOS BTP' for x in r), r[:1] if ok else r)
        ok, r = rpc('dco_rows', {'p_token': stok, 'p_type': 'USERS', 'p_filter': {}})
        check('RPC: store hanya lihat nama SPV/Master, tanpa hash PIN', ok and all(x['role'] in ('SPV', 'MASTER') for x in r) and 'pin_hash' not in json.dumps(r), r)
        ok, r = rpc('dco_save', {'p_token': stok, 'p_type': 'MASALAH', 'p_rows': [{'id': 'MS-00002', 'status': 'Selesai'}], 'p_mode': 'update'})
        check('RPC: store tidak bisa ubah toko lain', not ok, r)
        ok, r = rpc('dco_save', {'p_token': stok, 'p_type': 'MASALAH', 'p_rows': [{'id': 'MS-00001', 'validasi': 'Y', 'validasi_oleh': 'Hacker', 'status': 'Selesai'}], 'p_mode': 'update'})
        check('RPC: store tidak bisa memvalidasi sendiri', ok and r[0]['validasi'] == '' and r[0]['status'] == 'Selesai', r)
        ok, r = rpc('dco_save', {'p_token': stok, 'p_type': 'RUTIN', 'p_rows': [{'judul': 'x'}]})
        check('RPC: store tidak bisa tulis RUTIN', not ok, r)
        ok, r = rpc('dco_save', {'p_token': stok, 'p_type': 'CONFIG', 'p_rows': [{'key': 'bobot', 'value': '{}'}]})
        check('RPC: store tidak bisa ubah CONFIG', not ok, r)
        ok, r = rpc('dco_rows', {'p_token': stok, 'p_type': 'VISIT', 'p_filter': {}})
        check('RPC: store hanya kolom ringkas VISIT tokonya', ok and all(set(x.keys()) <= {'id', 'tanggal', 'toko', 'final_score', 'rating', 'validasi'} and x['toko'] == 'TIGALAPANKAOS BTP' for x in r), r)
        ok, r = rpc('dco_rows', {'p_token': stok, 'p_type': 'VISIT_ISSUE', 'p_filter': {}})
        check('RPC: store tidak bisa baca VISIT_ISSUE', not ok, r)
        ok, r = rpc('dco_archive_rows', {'p_token': stok, 'p_types': ['MASALAH'], 'p_from': '', 'p_to': ''})
        check('RPC: store tidak bisa ambil arsip', not ok, r)
        ok, r = rpc('dco_backup_get', {'p_token': stok, 'p_id': 1})
        check('RPC: store tidak bisa unduh backup', not ok, r)
        ok, r = rpc('dco_dso_validate', {'p_token': stok, 'p': {'id': dso_id, 'validasi': 'Approved'}})
        check('RPC: store tidak bisa approve DSO', not ok, r)
        req = urllib.request.Request(BASE + '/storage/v1/object/dco-foto/2026-11/' + 'a' * 32 + '_abcdefgh.jpg', data=b'xx', headers={'Content-Type': 'image/jpeg'}, method='POST')
        try: urllib.request.urlopen(req); up_ok = True
        except urllib.error.HTTPError: up_ok = False
        check('Storage: upload tanpa tiket ditolak', not up_ok)
        req = urllib.request.Request(BASE + '/storage/v1/object/dco-foto', data=json.dumps({'prefixes': [foto1]}).encode(), headers={'Content-Type': 'application/json'}, method='DELETE')
        with urllib.request.urlopen(req) as resp: deleted = json.loads(resp.read())
        check('Storage: hapus foto tanpa izin server ditolak', deleted == [], deleted)

        # ================= G. TAMPILAN SEMUA MENU =================
        print('G. Render semua menu (desktop & mobile) tanpa error')
        async def tour(page, who, tabs):
            for t in tabs:
                n0 = len(errors)
                await page.evaluate('(t) => go(t)', t)
                await page.wait_for_timeout(1300)
                err_toast = await page.evaluate("() => { const t=document.getElementById('toast'); return t.className.indexOf('err')>=0 ? t.textContent : ''; }")
                check('%s menu %s tampil tanpa error' % (who, t), len(errors) == n0 and not err_toast, errors[n0:] + [err_toast])
                await page.screenshot(path='%s/%s_%s.png' % (SHOTS, who, t), full_page=False)
        await tour(M, 'master', ['dash', 'ceklis', 'dso', 'MASALAH', 'jadwal', 'visit', 'issues', 'rutin', 'set'])
        for st in ['umum', 'dso', 'visit', 'toko', 'user', 'backup']:
            n0 = len(errors); await M.evaluate('(s) => { S.setTab = s; renderSet(); }', st); await M.wait_for_timeout(700)
            check('master pengaturan tab %s' % st, len(errors) == n0, errors[n0:])
        await M.screenshot(path=SHOTS + '/master_set_backup.png')
        dash_tabs = await M.evaluate("() => Array.from(document.querySelectorAll('#pDash button')).map(b=>b.textContent).filter(t=>/^0\\d/.test(t))")
        await M.evaluate("() => go('dash')"); await M.wait_for_timeout(1500)
        for i in range(5):
            n0 = len(errors)
            await M.evaluate("(i) => { const b = Array.from(document.querySelectorAll('#pDash button')).filter(x=>/^0\\d/.test(x.textContent))[i]; if (b) b.click(); }", i)
            await M.wait_for_timeout(900)
            check('dashboard tab %d' % (i + 1), len(errors) == n0, errors[n0:])
            await M.screenshot(path='%s/master_dash_tab%d.png' % (SHOTS, i + 1))
        await tour(P, 'spv', ['dash', 'dso', 'visit', 'issues', 'jadwal'])
        await T.goto(BASE + '/'); await T.wait_for_function("() => window.S && S.me && S.meta", timeout=15000)
        check('store langsung masuk ke Assignment Checklist Store', await T.evaluate('() => S.tab') == 'ceklis', await T.evaluate('() => S.tab'))
        await tour(T, 'store', ['ceklis', 'dso', 'MASALAH'])
        nav = await T.evaluate("() => Array.from(new Set(Array.from(document.querySelectorAll('#sideNav [data-t], #bnav [data-t]')).map(b=>b.dataset.t)))")
        check('menu store hanya Checklist, DSO, Rekap Masalah', sorted(nav) == sorted(['ceklis', 'dso', 'MASALAH']), nav)
        await T.evaluate("() => go('jadwal')"); await T.wait_for_timeout(600)
        check('store tidak bisa membuka menu lain (dialihkan)', await T.evaluate('() => S.tab') == 'ceklis')
        pnav = await P.evaluate("() => Array.from(new Set(Array.from(document.querySelectorAll('#sideNav [data-t]')).map(b=>b.dataset.t)))")
        check('menu SPV semua kecuali Pengaturan', 'set' not in pnav and all(t in pnav for t in ['dash', 'ceklis', 'dso', 'MASALAH', 'jadwal', 'visit', 'issues', 'rutin']), pnav)
        mnav = await M.evaluate("() => Array.from(new Set(Array.from(document.querySelectorAll('#sideNav [data-t]')).map(b=>b.dataset.t)))")
        check('menu Master lengkap (9 menu)', len(mnav) == 9 and 'set' in mnav, mnav)
        await M.evaluate("() => go('dash')"); await M.wait_for_timeout(1200)
        check('banner Executive Control Center dihapus', await M.evaluate("() => !document.querySelector('#pDash .exec-hero') && !!document.querySelector('#pDash .exec-nav')"))
        await P.evaluate("() => go('visit')"); await P.wait_for_timeout(1200)
        await P.evaluate("() => openVisit()"); await P.wait_for_timeout(900)
        vinfo = await P.evaluate("() => ({notes: document.querySelectorAll('#vBody .v9-note textarea').length, fotoSeksi: document.getElementById('vBody').textContent.indexOf('kolase maks 4') >= 0, w: (document.querySelector('#vBody .v9-note textarea')||{}).offsetWidth, bw: document.getElementById('vBody').offsetWidth})")
        check('Visiting: catatan seksi lebar penuh, foto seksi dihapus', vinfo['notes'] == 5 and not vinfo['fotoSeksi'] and vinfo['w'] > vinfo['bw'] * 0.8, vinfo)
        await P.screenshot(path=SHOTS + '/spv_visit_form.png')
        await P.evaluate("() => closeM('mVisit')")
        # foto checklist tampil dari Storage
        await T.evaluate("() => go('ceklis')"); await T.wait_for_timeout(1500)
        imgs = await T.evaluate("() => Array.from(document.querySelectorAll('#pCeklis img.thumb')).map(i=>[i.naturalWidth, i.src.slice(0,80)])")
        check('foto checklist tampil (Supabase Storage)', any(w > 0 for w, s in imgs), imgs)
        await T.screenshot(path=SHOTS + '/store_ceklis_foto.png')

        L = await newpage(); await L.goto(BASE + '/'); await L.wait_for_timeout(900)
        check('halaman login baru tampil', await L.evaluate("() => !!document.querySelector('#vLogin .lg-hero') && !!document.getElementById('lgBtn') && /WITA/.test(document.getElementById('lgClock').textContent)"))
        await L.screenshot(path=SHOTS + '/login_desktop.png')
        await L.fill('#lPin', '1234'); await L.click('.lg-eye')
        check('tombol lihat PIN berfungsi', await L.evaluate("() => document.getElementById('lPin').type") == 'text')
        await L.fill('#lUser', 'master'); await L.fill('#lPin', '0000'); await L.click('#lgBtn'); await L.wait_for_timeout(1200)
        check('login gagal: pesan error & tombol kembali normal', 'PIN salah' in await L.inner_text('#toast') and not await L.evaluate("() => document.getElementById('lgBtn').classList.contains('busy')"))
        Lm = await newpage(390, 844, True); await Lm.goto(BASE + '/'); await Lm.wait_for_timeout(900)
        await Lm.screenshot(path=SHOTS + '/login_mobile.png', full_page=True)
        Mo = await newpage(390, 844, True); await login(Mo, 'spv')
        for t in ['dash', 'dso', 'MASALAH', 'jadwal']:
            n0 = len(errors); await Mo.evaluate('(t) => go(t)', t); await Mo.wait_for_timeout(1300)
            check('mobile SPV menu %s' % t, len(errors) == n0, errors[n0:])
            await Mo.screenshot(path='%s/mobile_spv_%s.png' % (SHOTS, t))
        # Logout mencabut sesi
        tok = await Mo.evaluate('() => S.me.token')
        await Mo.evaluate('() => logout()'); await Mo.wait_for_timeout(800)
        ok, r = rpc('dco_whoami', {'p_token': tok})
        check('logout mencabut sesi di server', not ok, r)
        await browser.close()

    n_fail = sum(1 for r in results if not r[0])
    print('\nHASIL: %d lulus, %d gagal dari %d uji' % (len(results) - n_fail, n_fail, len(results)))
    json.dump([{'ok': a, 'uji': b} for a, b, c in results], open(os.path.join(SHOTS, 'hasil_uji.json'), 'w'), indent=1, ensure_ascii=False)
    sys.exit(1 if n_fail else 0)

asyncio.run(main())
