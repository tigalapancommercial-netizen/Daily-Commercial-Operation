#!/usr/bin/env python3
"""Non-destructive authenticated Supabase snapshot.
No deletion or archive retention cleanup occurs here. Run on secure operator device.
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, urllib.parse, urllib.request
TABLES=['stores','profiles','spv_store_assignments','briefings','issues','visit_schedules','visits','visit_points','visit_templates','checklist_templates','checklist_entries','dso_form_points','dso_reports','assignments','app_settings','audit_events']

def fetch(url,key,table,offset):
 endpoint=url.rstrip('/')+'/rest/v1/'+table+'?'+urllib.parse.urlencode({'select':'*','limit':500,'offset':offset})
 req=urllib.request.Request(endpoint,headers={'apikey':key,'Authorization':'Bearer '+key})
 with urllib.request.urlopen(req,timeout=60) as response:return json.loads(response.read().decode())

def backup(output,url,key):
 output.mkdir(parents=True,exist_ok=True)
 manifest={'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'tables':{}}
 for table in TABLES:
  allrows=[]
  for i in range(0,1000000,500):
   page=fetch(url,key,table,i);allrows.extend(page)
   if len(page)<500:break
  data=json.dumps(allrows,indent=2,ensure_ascii=False,sort_keys=True).encode('utf-8')
  (output/(table+'.json')).write_bytes(data)
  manifest['tables'][table]={'rows':len(allrows),'sha256':hashlib.sha256(data).hexdigest()}
  print(f'{table}: {len(allrows)} record')
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 return manifest

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('private_backups')/dt.datetime.now().strftime('%Y%m%d_%H%M%S'));a=p.parse_args()
 u=os.environ.get('SUPABASE_URL');k=os.environ.get('SUPABASE_SECRET_KEY')
 if not u or not k:raise SystemExit('SUPABASE_URL + SUPABASE_SECRET_KEY wajib. Jangan letakkan secret di frontend atau GitHub.')
 backup(a.out,u,k)
 print('Backup selesai dan checksum tertulis. Simpan folder di lokasi terenkripsi di luar repository.')
