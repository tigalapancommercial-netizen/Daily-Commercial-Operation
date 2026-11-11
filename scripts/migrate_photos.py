#!/usr/bin/env python3
"""Upload local files exported from legacy Google Drive to private Supabase Storage.
Input CSV: store_id,module,legacy_drive_id,local_file. Never guesses Drive file IDs.
Outputs map JSON for follow-up reconciliation of references in tables.
"""
import argparse,csv,json,os,pathlib,mimetypes,uuid,urllib.request,urllib.error
MODULES={'checklist','dso','visit','issue'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('photo_migration_map.json'));args=p.parse_args()
 data=list(csv.DictReader(args.manifest.open(encoding='utf-8-sig',newline='')))
 result=[];errors=[]
 for i,r in enumerate(data,2):
  st=r.get('store_id','').strip();module=r.get('module','').strip();old=r.get('legacy_drive_id','').strip();rel=r.get('local_file','').strip()
  file=(args.root/rel).resolve()
  if not st or module not in MODULES or not old or not file.is_file() or not file.is_relative_to(args.root.resolve()):errors.append({'line':i,'error':'Invalid store/module/legacy ID/file'});continue
  mimetype=mimetypes.guess_type(file.name)[0]
  if mimetype not in ('image/png','image/jpeg','image/webp'):errors.append({'line':i,'error':'Unsupported image'});continue
  suffix={ 'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[mimetype]
  target=f'{st}/{module}/legacy/{uuid.uuid5(uuid.NAMESPACE_URL,old)}.{suffix}'
  result.append({'legacy_drive_id':old,'path':target,'file':rel,'size':file.stat().st_size,'module':module,'store_id':st})
  if args.apply:
   url=os.environ.get('SUPABASE_URL');secret=os.environ.get('SUPABASE_SECRET_KEY')
   if not url or not secret:raise SystemExit('Missing SUPABASE_URL / SUPABASE_SECRET_KEY')
   req=urllib.request.Request(url.rstrip('/')+'/storage/v1/object/store-evidence/'+target,data=file.read_bytes(),method='POST',headers={'apikey':secret,'Authorization':'Bearer '+secret,'Content-Type':mimetype,'x-upsert':'true'})
   try:urllib.request.urlopen(req,timeout=60).close()
   except urllib.error.HTTPError as e:errors.append({'line':i,'error':f'HTTP {e.code} {e.read().decode()[:200]}'})
 args.output.write_text(json.dumps({'mode':'APPLY' if args.apply else 'DRY_RUN','mapped':result,'errors':errors},indent=2,ensure_ascii=False),encoding='utf-8')
 print(f'{len(result)} foto terpetakan; {len(errors)} error. Manifest: {args.output}')
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
