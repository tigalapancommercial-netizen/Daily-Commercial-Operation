#!/usr/bin/env python3
"""Idempotent Google Sheets CSV -> Supabase REST migration. No Apps Script.

Input: CSV exports of old DASHBOARD ASSIGNMENT tabs in --source directory.
Default is dry-run: no network write and no Supabase secrets required.
Never import USERS/PIN. The operator must provision Supabase Auth accounts separately.
"""
import argparse, csv, datetime as dt, json, os, pathlib, re, sys, urllib.request, urllib.error, uuid

STORES = [
 ('t01','TIGALAPANKAOS BTP'), ('m02','MAMU BTP'), ('m03','MAMU PALOPO'),
 ('t04','TIGALAPANKAOS PALU'), ('m05','MAMU TAMALATE'), ('t06','TIGALAPANKAOS MANADO'),
 ('t07','TIGALAPANKAOS SAMARINDA'), ('m08','MAMU KENDARI'), ('t09','TIGALAPANKAOS POLMAN'),
 ('t10','TIGALAPANKAOS BONE'), ('m11','MAMU GOWA'), ('t12','TIGALAPANKAOS TORAJA')
]
NAME_TO_ID = {name: key for key, name in STORES}
NAME_TO_ID.update({'TIGALAPANKAOS MAKASSAR':'t01','TIGALAPANKAOS POLEWALI MANDAR':'t09'})
MONTHS = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MEI':5,'JUN':6,'JUL':7,'AGU':8,'SEP':9,'OKT':10,'NOV':11,'DES':12}

def normalized(s): return re.sub(r'\s+',' ',str(s or '').strip()).upper()
def store_id(s):
 v=NAME_TO_ID.get(normalized(s))
 if not v and normalized(s) in dict(STORES): v=normalized(s)
 if not v: raise ValueError('Nama toko tidak dikenal: '+str(s))
 return v

def date(s):
 s=str(s or '').strip()
 if not s:return None
 if re.match(r'^\d{4}-\d{2}-\d{2}',s):return s[:10]
 m=re.match(r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$',s)
 if m:
  mm=MONTHS.get(m.group(2)[:3].upper())
  if mm:return f'{int(m.group(3)):04d}-{mm:02d}-{int(m.group(1)):02d}'
 m=re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$',s)
 if m:return f'{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
 raise ValueError('Tanggal tidak valid: '+s)

def time(s):
 s=str(s or '').strip();m=re.match(r'^(\d{1,2}):(\d{2})',s)
 if m and int(m.group(1))<24 and int(m.group(2))<60:return f'{int(m.group(1)):02d}:{m.group(2)}:00'
 if not s:return None
 raise ValueError('Jam tidak valid: '+s)

def num(s,default=0):
 try:return int(float(str(s).replace('%','').strip()))
 except (ValueError,TypeError):return default

def read(path):
 if not path.exists():return []
 with path.open(encoding='utf-8-sig',newline='') as f:return [{str(k).strip():str(v or '').strip() for k,v in r.items() if k} for r in csv.DictReader(f)]
def get(r,*keys):
 for k in keys:
  if r.get(k):return r[k]
 return ''
def uid(table,source):return str(uuid.uuid5(uuid.NAMESPACE_URL,'tigalapan/v7/'+table+'/'+source))
def js(s,fallback=None):
 if not s:return fallback if fallback is not None else {}
 try:return json.loads(s)
 except (ValueError,TypeError):return fallback if fallback is not None else {}
def mapped(source):
 """Yield batches in FK-safe order. Only supported historical columns are transformed."""
 routines=[]
 for r in read(source/'RUTIN.csv'):
  code=get(r,'ID','Id')
  if not code:continue
  routines.append({'id':uid('checklist_template',code),'source_id':code,'store_id':store_id(get(r,'Toko')) if get(r,'Toko') and normalized(get(r,'Toko'))!='SEMUA' else None,
   'title':get(r,'Judul','Nama Tugas','Nama','Item'),'description':get(r,'Deskripsi'),
   'category':get(r,'Kategori'),'frequency':get(r,'Frekuensi') or 'Harian',
   'priority':get(r,'Prioritas') or 'Sedang','active':get(r,'Aktif').upper()!='N'})
 yield 'checklist_templates',routines,'source_id'
 briefs={};issues=[]
 for r in read(source/'MASALAH.csv'):
  code=get(r,'ID');title=get(r,'Masalah / Temuan','Masalah')
  if not code or not title or normalized(title)=='NIHIL':continue
  st=store_id(get(r,'Toko'));day=date(get(r,'Tanggal Briefing','Tanggal'))
  if not day:continue
  shift=get(r,'Sesi / Jam','Sesi') or 'Pagi'; bk=f'{st}/{day}/{shift}'
  briefs[bk]={'id':uid('briefing',bk),'store_id':st,'briefing_date':day,'shift':shift,
  'leader':get(r,'Pemimpin Briefing','Pemimpin'), 'participants':num(get(r,'Peserta / Jumlah','Peserta')),'no_findings':False}
  status=get(r,'Status') or 'Open'
  issues.append({'id':uid('issue',code),'legacy_source_id':code,'store_id':st,'origin':'briefing',
   'briefing_id':uid('briefing',bk),'title':title,'category':get(r,'Kategori') or 'Lainnya',
   'root_cause':get(r,'Akar Penyebab'),'action_plan':get(r,'Solusi / Action Plan','Solusi'),
   'pic_name':get(r,'PIC'),'due_date':date(get(r,'Due Date')),'priority':get(r,'Prioritas') or 'Sedang',
   'status':status,'progress':100 if status=='Selesai' else num(get(r,'Progress (%)','Progress')),
   'note':get(r,'Update / Kendala / Follow-up'), 'photo_path':None})
 yield 'briefings',list(briefs.values()),'id'
 schedules=[]
 for r in read(source/'JADWAL.csv'):
  code=get(r,'ID');day=date(get(r,'Tanggal'));st=get(r,'Toko')
  if not code or not day or not st:continue
  a,b=time(get(r,'Jam Mulai')),time(get(r,'Jam Selesai'))
  if not a or not b or b<=a:continue
  schedules.append({'id':uid('schedule',code),'source_id':code,'store_id':store_id(st),
   'visit_date':day,'start_time':a,'end_time':b,'pic_name':get(r,'PIC') or 'SPV Area',
   'agenda':get(r,'Agenda / Tugas di Toko') or 'Visit','status':get(r,'Status') or 'Rencana',
   'notes':get(r,'Catatan Hasil')})
 yield 'visit_schedules',schedules,'source_id'
 visits=[];points=[]
 for r in read(source/'VISIT.csv'):
  code=get(r,'ID');st=get(r,'Store');day=date(get(r,'Visit Date'))
  if not code or not st or not day:continue
  id=uid('visit',code)
  visits.append({'id':id,'source_id':code,'store_id':store_id(st),'visit_date':day,
   'evaluator_name':get(r,'Evaluator') or 'SPV Area','leader_name':get(r,'Leader In Charge'),
   'visit_type':get(r,'Visit Type') or 'Store Visit','score':float(get(r,'Final Score')) if get(r,'Final Score') else None,
   'rating':get(r,'Rating'),'status':'Selesai','notes':get(r,'Keterangan')})
  answers=js(get(r,'Jawaban (JSON)'),{})
  if isinstance(answers,dict):
   for codepoint,result in answers.items():
    if not isinstance(result,(str,int,float)):continue
    status={'S':'Sesuai','T':'Tidak Sesuai','N':'N/A','B':'Belum'}.get(str(result),str(result))
    if status not in ('Sesuai','Tidak Sesuai','N/A','Belum'):continue
    points.append({'id':uid('visit_point',code+'/'+str(codepoint)),'visit_id':id,
      'point_code':str(codepoint),'section':'Legacy','item_title':str(codepoint),
      'result':status,'notes':''})
 yield 'visits',visits,'source_id'
 yield 'visit_points',points,'id'
 for r in read(source/'VISIT_ISSUE.csv'):
  code=get(r,'Issue ID');st=get(r,'Toko');vid=get(r,'Visit ID');title=get(r,'Temuan / Issue')
  if not code or not st or not title:continue
  status=get(r,'Status') or 'Open'
  issues.append({'id':uid('visit_issue',code),'legacy_source_id':'VISIT-'+code,'store_id':store_id(st),
   'origin':'visit','visit_id':uid('visit',vid) if vid else None,'title':title,
   'category':get(r,'Seksi') or 'Operasional','root_cause':get(r,'Akar Penyebab'),
   'action_plan':get(r,'Action Plan'),'pic_name':get(r,'PIC'),
   'due_date':date(get(r,'Due Date')),'priority':get(r,'Prioritas') or 'Sedang',
   'status':status,'progress':100 if status=='Selesai' else num(get(r,'Progress (%)'))})
 yield 'issues',issues,'legacy_source_id'
 checks=[]
 for r in read(source/'CEKLIS.csv'):
  code=get(r,'ID');st=get(r,'Toko');day=date(get(r,'Tanggal'))
  if not code or not st or not day:continue
  routine=get(r,'Rutin ID')
  checks.append({'id':uid('checklist',code),'source_id':code,'store_id':store_id(st),'check_date':day,
   'template_id':uid('checklist_template',routine) if routine and any(x['source_id']==routine for x in routines) else None,
   'title':get(r,'Judul') or 'Checklist','status':get(r,'Status') or 'Belum',
   'note':get(r,'Catatan') or '','completed_at':None})
 yield 'checklist_entries',checks,'source_id'
 dso=[]
 for r in read(source/'DSO.csv'):
  code=get(r,'ID');st=get(r,'Toko');day=date(get(r,'Tanggal','Report Date'))
  if not code or not st or not day:continue
  form=get(r,'Form') or 'OPENING';valid=get(r,'Validasi SPV','Validasi')
  stat={'Approved':'Approved','Rejected':'Rejected'}.get(valid,'Submitted')
  dso.append({'id':uid('dso',code),'source_id':code,'store_id':store_id(st),
    'report_date':day,'form_code':form,'status':stat,
    'answers':js(get(r,'Jawaban (JSON)'),{}),'notes':get(r,'Keterangan')})
 yield 'dso_reports',dso,'source_id'

def post(url,secret,table,chunk,conflict):
 data=json.dumps(chunk,ensure_ascii=False).encode()
 req=urllib.request.Request(url.rstrip('/')+'/rest/v1/'+table+'?on_conflict='+conflict,data=data,method='POST',headers={
   'apikey':secret,'Authorization':'Bearer '+secret,'Content-Type':'application/json',
   'Prefer':'resolution=merge-duplicates,return=minimal'})
 try:
  with urllib.request.urlopen(req,timeout=40) as resp: return resp.status
 except urllib.error.HTTPError as e:raise RuntimeError(f'{table}: HTTP {e.code}: {e.read().decode()[:1200]}') from e

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=pathlib.Path,required=True,help='Folder CSV per tab: MASALAH.csv, CEKLIS.csv, VISIT.csv, JADWAL.csv...');p.add_argument('--apply',action='store_true',help='WRITE to Supabase; default dry-run');p.add_argument('--batch-size',type=int,default=100);args=p.parse_args()
 if not args.source.is_dir():p.error('Folder tidak ada')
 operations=list(mapped(args.source));total=0
 for table,items,conflict in operations:
  print(f'{table:22s} {len(items):5d} rows');total+=len(items)
 print('TOTAL:',total,'rows | mode:', 'APPLY' if args.apply else 'DRY RUN')
 if not args.apply:return
 url=os.environ.get('SUPABASE_URL');secret=os.environ.get('SUPABASE_SECRET_KEY')
 if not url or not secret:raise SystemExit('SUPABASE_URL dan SUPABASE_SECRET_KEY harus di environment, bukan .env frontend.')
 for table,items,conflict in operations:
  for i in range(0,len(items),args.batch_size):
   post(url,secret,table,items[i:i+args.batch_size],conflict)
  if items:print('OK:',table,len(items))
 print('Selesai. Bandingkan jumlah record dan relasi di Supabase sebelum cutover.')
if __name__=='__main__':main()
