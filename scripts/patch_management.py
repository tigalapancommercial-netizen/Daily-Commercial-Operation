from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=root/'src/data.js'
s=p.read_text()
a=s.index('export async function uploadEvidence(')
b=s.index('export async function evidenceUrl(',a)
s=s[:a]+'''// Compress camera evidence before upload; a WebP blob is shown via a signed URL in HTML.
export async function compressEvidence(file,{maxEdge=1600,targetBytes=450*1024}={}){
 if(!file)return null;
 if(!['image/jpeg','image/png','image/webp'].includes(file.type))
  throw new Error('Gunakan foto JPG, PNG, atau WebP. Format HEIC perlu dikonversi terlebih dahulu.');
 if(file.size>30*1024*1024)throw new Error('Ukuran foto asal maksimal 30 MB.');
 let image;
 try{image=await createImageBitmap(file,{imageOrientation:'from-image'});}
 catch(_){throw new Error('Foto tidak bisa dibuka. Simpan ulang sebagai JPG lalu unggah.');}
 try{
  let w=image.width,h=image.height;
  const factor=Math.min(1,maxEdge/Math.max(w,h));
  w=Math.max(1,Math.round(w*factor));h=Math.max(1,Math.round(h*factor));
  if(w*h>8_000_000)throw new Error('Resolusi foto tidak didukung.');
  let blob=null;
  for(let attempt=0;attempt<5;attempt++){
    const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;
    const ctx=canvas.getContext('2d',{alpha:false});
    if(!ctx)throw new Error('Browser tidak mendukung kompresi gambar.');
    ctx.fillStyle='#ffffff';ctx.fillRect(0,0,w,h);ctx.drawImage(image,0,0,w,h);
    const quality=Math.max(0.49,0.80-attempt*0.075);
    blob=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('Gagal kompres foto.')),'image/webp',quality));
    if(blob.type!=='image/webp')throw new Error('Browser tidak mendukung format WebP.');
    if(blob.size<=targetBytes||attempt===4)break;
    const scale=attempt<2?0.92:0.84;
    w=Math.max(480,Math.round(w*scale));h=Math.max(480,Math.round(h*scale));
  }
  if(!blob||blob.size>8*1024*1024)throw new Error('Foto belum cukup kecil, pilih gambar lain.');
  return blob;
 }finally{image.close?.();}
}
export async function uploadEvidence(storeId,module,file){
 if(!file)return null;
 if(isDemo)return `${storeId}/${module}/${new Date().toISOString().slice(0,7)}/${crypto.randomUUID()}.webp`;
 const compressed=await compressEvidence(file);
 const now=new Date(),month=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Makassar',year:'numeric',month:'2-digit'}).format(now);
 const path=`${storeId}/${module}/${month}/${crypto.randomUUID()}.webp`;
 const {error}=await client.storage.from('store-evidence').upload(path,compressed,{contentType:'image/webp',upsert:false,cacheControl:'3600'});
 err(error,'Upload foto: ');return path;
}
''' + s[b:]
s+='''
// Complete export: pages directly from Supabase (not the first 10,000 rows loaded on screen).
// Supabase RLS still applies to each query. No Auth password or secret is ever exported.
export const EXPORT_DATASETS={
 issues:{table:'issues',date:'created_at',store:true,order:'id'},
 briefings:{table:'briefings',date:'briefing_date',store:true,order:'id'},
 visits:{table:'visits',date:'visit_date',store:true,order:'id'},
 visit_points:{table:'visit_points',store:false,order:'id'},
 schedules:{table:'visit_schedules',date:'visit_date',store:true,order:'id'},
 checklists:{table:'checklist_entries',date:'check_date',store:true,order:'id'},
 dso:{table:'dso_reports',date:'report_date',store:true,order:'id'},
 assignments:{table:'assignments',date:'due_date',store:true,order:'id'},
 visit_templates:{table:'visit_templates',store:false,order:'id'},
 checklist_templates:{table:'checklist_templates',store:true,order:'id'},
 dso_points:{table:'dso_form_points',store:false,order:'id'},
 settings:{table:'app_settings',store:false,order:'key'}
};
export async function fetchCompleteRows(dataset,{store='all',from='',to='',origin=''}={},onPage=()=>{}){
 const def=EXPORT_DATASETS[dataset];if(!def)throw new Error('Dataset export tidak dikenal.');
 if(isDemo){
  const key={checklists:'checklists',schedules:'schedules',dso_points:'dso_points',visit_templates:'visit_templates',settings:'settings'}[dataset]||dataset;
  const records=demoData[key]||[];
  return records.filter(x=>(store==='all'||!def.store||x.store_id===store)&&(!from||!def.date||x[def.date]>=from)&&(!to||!def.date||x[def.date]<=to));
 }
 if(!client)throw new Error('Belum terhubung ke Supabase.');
 if(!['all',...STORES.map(s=>s.id)].includes(store))throw new Error('Pilihan toko tidak valid.');
 const PAGE=500,rows=[];let offset=0;
 while(true){
  let req=client.from(def.table).select('*').order(def.order,{ascending:true}).range(offset,offset+PAGE-1);
  if(def.store&&store!=='all')req=req.eq('store_id',store);
  if(def.date&&from)req=req.gte(def.date,from);
  if(def.date&&to)req=req.lte(def.date,to);
  if(dataset==='issues'&&origin)req=req.eq('origin',origin);
  const {data,error}=await req;err(error,'Export '+dataset+': ');
  rows.push(...(data||[]));onPage(rows.length);
  if(!data||data.length<PAGE)break;
  offset+=PAGE;
  if(offset>500000)throw new Error('Export melebihi 500.000 baris. Bagi berdasarkan tanggal agar tidak membebani browser.');
 }
 return rows;
}
export async function maintenanceUsage(){if(isDemo)return {rows:{issues:demoData.issues.length,briefings:demoData.briefings.length,visits:demoData.visits.length,checklists:demoData.checklists.length,archive_rows:0,archive_batches:0},photo_bytes:0,archive_table_bytes:0};const {data,error}=await client.rpc('maintenance_usage');err(error,'Statistik: ');return data;}
export async function maintenancePreview(table,cutoff,store){if(isDemo)return {eligible:0,table,cutoff,store};const {data,error}=await client.rpc('maintenance_preview',{p_table:table,p_cutoff:cutoff,p_store_id:store==='all'?null:store});err(error,'Preview arsip: ');return data;}
export async function maintenanceArchive(table,cutoff,store,count,phrase){if(isDemo)throw new Error('Arsip tidak tersedia di mode demo.');const {data,error}=await client.rpc('maintenance_archive',{p_table:table,p_cutoff:cutoff,p_store_id:store==='all'?null:store,p_expected:count,p_phrase:phrase});err(error,'Arsip: ');return data;}
export async function maintenanceHistory(){if(isDemo)return [];const {data,error}=await client.rpc('maintenance_history');err(error,'Histori: ');return data||[];}
export async function maintenanceDownloadBatch(batch){if(isDemo)throw new Error('Backup tidak tersedia dalam demo.');const out=[];for(let offset=0;offset<100000;offset+=250){const {data,error}=await client.rpc('maintenance_download_batch',{p_batch:batch,p_offset:offset,p_limit:250});err(error,'Unduh arsip: ');out.push(...(data||[]).map(x=>x.row_text));if((data||[]).length<250)break;}return out.join('\\n');}
export async function maintenancePurge(batch,sha,phrase){if(isDemo)throw new Error('Hapus tidak tersedia di mode demo.');const {data,error}=await client.rpc('maintenance_purge_archive',{p_batch:batch,p_sha256:sha,p_phrase:phrase});err(error,'Hapus arsip: ');return data;}
'''
p.write_text(s)
