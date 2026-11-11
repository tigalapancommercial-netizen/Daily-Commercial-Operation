#!/usr/bin/env python3
"""Membuat file SQL impor data dari spreadsheet lama (Apps Script) ke Supabase (schema dco).

Sumber (pilih salah satu):
  1) Snapshot JSON  : python3 scripts/import_sheets.py supabase/data_import/sheet_snapshot_2026-11-12.json
  2) Folder CSV     : di Google Sheets  File > Download > CSV  untuk tiap tab (MASALAH.csv, TUGAS.csv, RUTIN.csv,
                      CEKLIS.csv, DSO.csv, VISIT.csv, VISIT_ISSUE.csv, JADWAL.csv, CONFIG.csv, TOKO.csv,
                      FORM_DEF.csv, VISIT_DEF.csv), taruh di satu folder, lalu:
                      python3 scripts/import_sheets.py folder_csv/
Opsi:
  --overwrite   : baris dengan ID sama DITIMPA nilai spreadsheet (default: dilewati / tidak menimpa)
  --out FILE    : nama file SQL (default supabase/data_import/20261112_007_import_data.sql)

Tab USERS sengaja TIDAK diimpor (berisi PIN). Akun dibuat oleh migrasi 006 (PIN awal 1234, wajib diganti),
atau atur lewat menu Pengaturan > User. File SQL hasil berisi data operasional internal: JANGAN di-commit
ke repository publik (folder supabase/data_import/ sudah ada di .gitignore).
"""
import csv, json, os, sys, re

SCHEMA = {
  'TOKO': ['nama', 'area', 'aktif'],
  'CONFIG': ['key', 'value'],
  'MASALAH': ['id','tanggal','toko','sesi','pemimpin','peserta','kategori','masalah','akar','solusi','pic','dueDate','prioritas','status','progress','tglSelesai','update','linkBukti','fotoId','validasi','validasiOleh','validasiTgl','dibuatOleh','updateTgl','updateOleh','idLama'],
  'TUGAS': ['id','tanggal','toko','judul','deskripsi','kategori','prioritas','dueDate','pic','status','progress','tglSelesai','catatan','fotoId','validasi','validasiOleh','validasiTgl','dibuatOleh','updateTgl','updateOleh'],
  'RUTIN': ['id','judul','deskripsi','kategori','prioritas','pic','frekuensi','hari','toko','aktif','dibuatOleh','updateTgl','interval','mulai'],
  'CEKLIS': ['id','tanggal','toko','rutinId','judul','status','jam','catatan','fotoId','validasi','validasiOleh','validasiTgl','updateTgl','updateOleh'],
  'FORM_DEF': ['id','form','urutan','label','deskripsi','multi','wajib','aktif'],
  'DSO': ['id','tanggal','toko','form','waktuSubmit','oleh','jawaban','keterangan','slaSubmit','validasi','validasiOleh','validasiTgl','ketSpv','slaValidasi','updateTgl','updateOleh'],
  'VISIT_DEF': ['id','seksi','kode','label','aktif'],
  'JADWAL': ['id','tanggal','toko','pic','jamMulai','jamSelesai','agenda','status','catatan','dibuatOleh','updateTgl'],
  'VISIT': ['id','tanggal','minggu','toko','leader','evaluator','tipe','jawaban','catatan','foto','issues','skor','finalScore','rating','totalPass','totalDinilai','validasi','validasiOleh','validasiTgl','updateTemuan','keterangan','updateTgl','updateOleh'],
  'VISIT_ISSUE': ['id','visitId','tanggal','toko','pointId','seksi','issue','akar','action','pic','dueDate','prioritas','status','progress','fotoId','validasi','validasiOleh','validasiTgl','updateTgl','updateOleh'],
}
ORDER = ['TOKO','CONFIG','FORM_DEF','VISIT_DEF','RUTIN','MASALAH','TUGAS','CEKLIS','DSO','VISIT','VISIT_ISSUE','JADWAL']
TABLE = {k: k.lower() for k in SCHEMA}
PK = {'TOKO': 'nama', 'CONFIG': 'key'}
UNIQUE = {'CEKLIS': '(tanggal, toko, rutin_id)', 'DSO': '(tanggal, toko, form)'}
snake = lambda k: re.sub(r'[A-Z]', lambda m: '_' + m.group(0).lower(), k)
q = lambda s: "'" + str('' if s is None else s).replace("'", "''") + "'"
col = lambda c: '"%s"' % c if c in ('update', 'interval') else c

def norm(v, k):
    s = '' if v is None else str(v)
    if k in ('jam', 'jamMulai', 'jamSelesai'):
        m = re.search(r'(?:^| )(\d{1,2}:\d{2})(?::\d{2})?$', s)
        if m: s = ('0' + m.group(1))[-5:]
    return s

def load(src):
    data = {}
    if os.path.isdir(src):
        for t in SCHEMA:
            fp = os.path.join(src, t + '.csv')
            if not os.path.exists(fp):
                alt = [f for f in os.listdir(src) if f.upper().endswith(' - ' + t + '.CSV')]
                fp = os.path.join(src, alt[0]) if alt else None
            if not fp: continue
            with open(fp, encoding='utf-8-sig', newline='') as f:
                rows = list(csv.reader(f))
            keys = SCHEMA[t]
            data[t] = [dict(zip(keys, (r + [''] * len(keys))[:len(keys)])) for r in rows[1:] if r and r[0].strip()]
    else:
        js = json.load(open(src, encoding='utf-8'))
        for t, rows in js.items():
            if t not in SCHEMA or not rows: continue
            hdr = rows[0]
            data[t] = [dict(zip(hdr, r)) for r in rows[1:] if r and str(r[0]).strip()]
    return data

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args: sys.exit(__doc__)
    overwrite = '--overwrite' in sys.argv
    out = 'supabase/data_import/20261112_007_import_data.sql'
    if '--out' in sys.argv: out = sys.argv[sys.argv.index('--out') + 1]
    data = load(args[0])
    lines = ['-- IMPOR DATA DARI SPREADSHEET LAMA (dibuat scripts/import_sheets.py). Jalankan SETELAH 006.',
             '-- Mode: ' + ('TIMPA baris dengan ID sama' if overwrite else 'lewati baris yang sudah ada'), 'begin;']
    total = 0
    for t in ORDER:
        rows = data.get(t) or []
        if not rows: continue
        keys = [k for k in SCHEMA[t]]
        cols = [col(snake(k)) for k in keys]
        pk = PK.get(t, 'id')
        vals = ',\n'.join('  (' + ', '.join(q(norm(r.get(k, ''), k)) for k in keys) + ')' for r in rows)
        conflict = ('on conflict (%s) do update set ' % pk + ', '.join('%s = excluded.%s' % (c, c) for c in cols if c != pk)) if overwrite else 'on conflict do nothing'
        lines.append('-- %s: %d baris' % (t, len(rows)))
        lines.append('insert into dco.%s (%s) values\n%s\n%s;' % (TABLE[t], ', '.join(cols), vals, conflict))
        total += len(rows)
    lines.append('commit;')
    lines.append("select 'masalah' as tabel, count(*) from dco.masalah union all select 'rutin', count(*) from dco.rutin union all select 'ceklis', count(*) from dco.ceklis"
                 " union all select 'dso', count(*) from dco.dso union all select 'visit', count(*) from dco.visit union all select 'tugas', count(*) from dco.tugas;")
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('SQL dibuat:', out, '| baris:', total, '|', ', '.join('%s=%d' % (t, len(data.get(t) or [])) for t in ORDER if data.get(t)))

if __name__ == '__main__':
    main()
