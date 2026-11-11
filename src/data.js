import {STORES,seedDemo} from './constants.js';

const env=import.meta.env||{};
const endpoint=(env.VITE_SUPABASE_URL||'').trim();
const publishableKey=(env.VITE_SUPABASE_PUBLISHABLE_KEY||'').trim();
// Explicit demo mode only. A production site without configuration must NOT show fabricated operational records.
export const isDemo=env.VITE_DEMO_MODE==='true';
export const isConfigured=isDemo||(!!endpoint&&!!publishableKey);
let client;
let demoData=seedDemo();
const demoProfile={id:'demo',display_name:'Executive Preview',role:'master',store_id:null,storeIds:STORES.map(x=>x.id)};
const configs=[
 ['briefings','briefings','briefing_date'],['issues','issues','created_at'],['schedules','visit_schedules','visit_date'],
 ['visits','visits','visit_date'],['visit_points','visit_points','created_at'],['visit_templates','visit_templates','sort_order'],
 ['checklists','checklist_entries','check_date'],['checklist_templates','checklist_templates','created_at'],
 ['dso','dso_reports','report_date'],['dso_points','dso_form_points','sort_order'],
 ['assignments','assignments','due_date']
];
const err=(error,prefix='')=>{if(error)throw new Error(`${prefix}${error.message||String(error)}`);};
export async function start(){
 if(isDemo)return {profile:demoProfile};
 if(!isConfigured)throw new Error('Konfigurasi Supabase belum terpasang. Atur VITE_SUPABASE_URL dan VITE_SUPABASE_PUBLISHABLE_KEY di hosting.');
 const {createClient}=await import('@supabase/supabase-js');
 client=createClient(endpoint,publishableKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
 const {data,error}=await client.auth.getUser();
 if(error&&error.name!=='AuthSessionMissingError')throw error;
 if(!data?.user)return {profile:null};
 try{return {profile:await getProfile(data.user.id)};}
 catch(e){
  // Remove the incomplete session: avoid a refresh loop on an unregistered user.
  await client.auth.signOut({scope:'local'}).catch(()=>{});
  throw e;
 }
}
export async function login(email,password){
 if(isDemo)return demoProfile;
 if(!client)throw new Error('Supabase belum siap. Muat ulang halaman dan periksa pengaturan proyek.');
 const {data,error}=await client.auth.signInWithPassword({email,password});err(error,'Login: ');
 if(!data?.user?.id)throw new Error('Login tidak menghasilkan sesi pengguna. Silakan coba kembali.');
 try{return await getProfile(data.user.id);}
 catch(e){
  // Auth may succeed before a profile exists; keep the UI in a clean logged-out state.
  await client.auth.signOut({scope:'local'}).catch(()=>{});
  throw e;
 }
}
export async function logout(){if(!isDemo&&client)await client.auth.signOut();}
async function getProfile(id){
 // A missing profile is a setup problem, not an invalid email/password.
 const {data,error}=await client.from('profiles')
  .select('id,display_name,role,store_id,active')
  .eq('id',id).maybeSingle();
 if(error){
  if(error.code==='PGRST205'||error.code==='42P01')
   throw new Error('Tabel profiles belum tersedia. Jalankan migrasi SQL Supabase terlebih dahulu.');
  if(error.code==='42501')
   throw new Error('Supabase menolak akses ke tabel profiles. Periksa GRANT dan kebijakan RLS.');
  err(error,'Profil: ');
 }
 if(!data)throw new Error('Login Supabase Auth berhasil, tetapi profil pengguna belum ditemukan atau tidak terlihat oleh RLS. Minta Master mendaftarkan email Anda pada public.profiles (lihat SQL perbaikan).');
 if(!data.active)throw new Error('Profil pengguna dinonaktifkan. Hubungi Master.');
 if(!['master','spv','store'].includes(data.role))throw new Error('Role profil tidak valid. Hubungi Master.');
 const {data:stores,error:se}=await client.rpc('my_stores');
 if(se){
  if(se.code==='PGRST202'||se.code==='42883')throw new Error('Fungsi my_stores belum dibuat. Jalankan seluruh migrasi SQL Supabase.');
  err(se,'Akses toko: ');
 }
 data.storeIds=(stores||[]).map(s=>s.id);
 if(!data.storeIds.length)throw new Error('Tidak ada toko yang diizinkan untuk akun ini. Periksa role, store_id, master toko, dan kebijakan RLS.');
 return data;
}
async function allRows(table,sort,limit=10000){
 const out=[],PAGE=400;
 for(let offset=0;offset<limit;offset+=PAGE){
  let query=client.from(table).select('*').range(offset,offset+PAGE-1);
  if(sort)query=query.order(sort,{ascending:false});
  const {data,error}=await query;err(error,table+': ');
  out.push(...(data||[])); if(!data||data.length<PAGE)break;
 }
 return out;
}
export async function loadAll(profile){
 if(isDemo)return structuredClone(demoData);
 const pairs=await Promise.all(configs.map(async ([key,table,col])=>[key,await allRows(table,col)]));
 return Object.fromEntries(pairs);
}
async function put(table,item){
 const {id,...rest}=item;
 const req=id?client.from(table).update(rest).eq('id',id):client.from(table).insert(rest);
 const {data,error}=await req.select().single();err(error,table+': ');return data;
}
function demoPut(name,item){
 const val={...item,id:item.id||crypto.randomUUID(),updated_at:new Date().toISOString()};
 const ar=demoData[name];const ix=ar.findIndex(r=>r.id===val.id);
 if(ix<0)ar.unshift(val);else ar[ix]={...ar[ix],...val};return val;
}
const issueFields=['id','store_id','origin','briefing_id','visit_id','visit_point_id','title','category','root_cause','action_plan','pic_name','due_date','priority','status','progress','note','photo_path','verification_notes'];
export async function saveIssue(item){
 const allowed=Object.fromEntries(issueFields.filter(k=>item[k]!==undefined).map(k=>[k,item[k]]));
 if(isDemo)return demoPut('issues',allowed);
 return put('issues',allowed);
}
export async function verifyIssue(id,notes){
 if(isDemo){const r=demoData.issues.find(x=>x.id===id);if(r){r.verified_at=new Date().toISOString();r.verification_notes=notes;}return r;}
 const {data:{user},error:authError}=await client.auth.getUser();err(authError);
 const {data,error}=await client.from('issues').update({verified_by:user.id,verified_at:new Date().toISOString(),verification_notes:notes||null}).eq('id',id).eq('status','Selesai').select().single();err(error);return data;
}
export async function saveBriefing(input){
 const entry={store_id:input.store_id,briefing_date:input.briefing_date,shift:input.shift||'Pagi',leader:input.leader||'',participants:Number(input.participants)||0,no_findings:!!input.no_findings,notes:input.notes||''};
 if(isDemo){const r=demoData.briefings.find(x=>x.store_id===entry.store_id&&x.briefing_date===entry.briefing_date&&x.shift===entry.shift);if(r)Object.assign(r,entry);else demoData.briefings.push({...entry,id:crypto.randomUUID()});return entry;}
 const {data,error}=await client.from('briefings').upsert(entry,{onConflict:'store_id,briefing_date,shift'}).select().single();err(error);return data;
}
export async function saveSchedule(input){
 const item={...input};if(isDemo)return demoPut('schedules',item);
 return put('visit_schedules',item);
}
export async function saveAssignment(input){if(isDemo)return demoPut('assignments',input);return put('assignments',input);}
export async function saveChecklist(input){
 const row={...input,completed_at:input.status==='Selesai'?(input.completed_at||new Date().toISOString()):null};
 if(isDemo)return demoPut('checklists',row);
 const {id,...data}=row;
 if(id)return put('checklist_entries',row);
 const {data:result,error}=await client.from('checklist_entries').upsert(data,{onConflict:'store_id,check_date,template_id'}).select().single();err(error);return result;
}
export async function validateChecklist(id,approved,notes=''){
 if(isDemo){const x=demoData.checklists.find(r=>r.id===id);if(x){x.validated_at=approved?new Date().toISOString():null;x.validation_notes=notes;}return x;}
 const {data:{user}}=await client.auth.getUser();
 const {data,error}=await client.from('checklist_entries').update({validated_by:approved?user.id:null,validated_at:approved?new Date().toISOString():null,validation_notes:notes}).eq('id',id).select().single();err(error);return data;
}
export async function saveDso(input){
 const row={...input};
 if(isDemo){const match=demoData.dso.find(x=>x.store_id===row.store_id&&x.report_date===row.report_date&&x.form_code===row.form_code);if(match)return demoPut('dso',{...match,...row});return demoPut('dso',row);}
 const {data,error}=await client.from('dso_reports').upsert(row,{onConflict:'store_id,report_date,form_code'}).select().single();err(error);return data;
}
export async function validateDso(id,status,notes=''){
 if(isDemo){const r=demoData.dso.find(x=>x.id===id);if(r){r.status=status;r.validation_notes=notes;}return r;}
 const {data:{user}}=await client.auth.getUser();
 const {data,error}=await client.from('dso_reports').update({status,validated_by:user.id,validated_at:new Date().toISOString(),validation_notes:notes}).eq('id',id).select().single();err(error);return data;
}
export async function submitVisitBundle(visit,points,issues){
 if(isDemo){const v=demoPut('visits',{...visit,status:'Selesai'});
   for(const p of points)demoPut('visit_points',{...p,visit_id:v.id});
   for(const i of issues)demoPut('issues',{...i,store_id:visit.store_id,visit_id:v.id,origin:'visit',status:'Open',progress:0});return v.id;
 }
 const {data,error}=await client.rpc('submit_visit_bundle',{p_visit:visit,p_points:points,p_issues:issues});err(error,'Submit visit: ');return data;
}
export async function saveTemplate(table,input){
 const allowed=['visit_templates','dso_form_points','checklist_templates'];if(!allowed.includes(table))throw new Error('Template tidak dikenal');
 const key={visit_templates:'visit_templates',dso_form_points:'dso_points',checklist_templates:'checklist_templates'}[table];
 if(isDemo)return demoPut(key,input);
 return put(table,input);
}
// Compress camera evidence before upload; a WebP blob is shown via a signed URL in HTML.
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
  if(!blob||blob.size>1.5*1024*1024)throw new Error('Foto masih terlalu besar setelah kompresi, gunakan resolusi lebih rendah.');
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
export async function evidenceUrl(path){
 if(!path)return null;
 if(isDemo)return null;
 const {data,error}=await client.storage.from('store-evidence').createSignedUrl(path,60*10);err(error);return data.signedUrl;
}
export function availableStores(profile){
 const ids=profile?.storeIds||(profile?.role==='store'?[profile.store_id]:STORES.map(s=>s.id));
 return STORES.filter(s=>ids.includes(s.id));
}
export async function submitBriefingBundle(entry,issues){
 if(isDemo){await saveBriefing(entry);for(const issue of issues)demoPut('issues',{...issue,store_id:entry.store_id,origin:'briefing',status:'Open',progress:0});return;}
 const {data,error}=await client.rpc('submit_briefing_bundle',{p_briefing:entry,p_issues:issues});err(error,'Submit briefing: ');return data;
}

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
 settings:{table:'app_settings',store:false,order:'key'},
 stores:{table:'stores',store:false,order:'id'},
 profiles:{table:'profiles',store:false,order:'id'},
 spv_store_assignments:{table:'spv_store_assignments',store:true,order:'profile_id'},
 audit_events:{table:'audit_events',date:'changed_at',store:true,order:'id'}
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
  if(def.date&&from){const v=['created_at','changed_at'].includes(def.date)?`${from}T00:00:00+08:00`:from;req=req.gte(def.date,v);}
  if(def.date&&to){if(['created_at','changed_at'].includes(def.date)){const next=new Date(`${to}T00:00:00+08:00`);next.setUTCDate(next.getUTCDate()+1);req=req.lt(def.date,next.toISOString());}else req=req.lte(def.date,to);}
  if(dataset==='issues'&&origin)req=req.eq('origin',origin);
  const {data,error}=await req;err(error,'Export '+dataset+': ');
  rows.push(...(dataset==='settings'?(data||[]).filter(x=>!/secret|token|password|api.?key|private.?key/i.test(x.key||'')):(data||[])));onPage(rows.length);
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
export async function maintenanceDownloadBatch(batch){if(isDemo)throw new Error('Backup tidak tersedia dalam demo.');const out=[];for(let offset=0;offset<100000;offset+=250){const {data,error}=await client.rpc('maintenance_download_batch',{p_batch:batch,p_offset:offset,p_limit:250});err(error,'Unduh arsip: ');out.push(...(data||[]).map(x=>x.row_text));if((data||[]).length<250)break;}return out.join('\n');}
export async function maintenancePurge(batch,sha,phrase){if(isDemo)throw new Error('Hapus tidak tersedia di mode demo.');const {data,error}=await client.rpc('maintenance_purge_archive',{p_batch:batch,p_sha256:sha,p_phrase:phrase});err(error,'Hapus arsip: ');return data;}
