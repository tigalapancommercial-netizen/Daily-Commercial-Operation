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
 return {profile:data?.user?await getProfile(data.user.id):null};
}
export async function login(email,password){
 if(isDemo)return demoProfile;
 const {data,error}=await client.auth.signInWithPassword({email,password});err(error);
 return getProfile(data.user.id);
}
export async function logout(){if(!isDemo&&client)await client.auth.signOut();}
async function getProfile(id){
 const {data,error}=await client.from('profiles').select('id,display_name,role,store_id,active').eq('id',id).single();err(error,'Profil: ');
 if(!data.active)throw new Error('Akun telah dinonaktifkan. Hubungi Master.');
 const {data:stores,error:se}=await client.rpc('my_stores');err(se,'Akses toko: ');
 data.storeIds=(stores||[]).map(s=>s.id);
 if(!data.storeIds.length)throw new Error('Tidak ada toko yang diizinkan untuk akun ini.');
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
export async function uploadEvidence(storeId,module,file){
 if(!file)return null;
 if(file.size>8*1024*1024)throw new Error('Foto maksimal 8 MB. Kompres foto dahulu.');
 if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw new Error('Format foto harus JPG, PNG atau WebP.');
 const ext={'image/jpeg':'jpg','image/png':'png','image/webp':'webp'}[file.type];
 const now=new Date(),month=now.toISOString().slice(0,7);
 const path=`${storeId}/${module}/${month}/${crypto.randomUUID()}.${ext}`;
 if(isDemo)return path;
 const {error}=await client.storage.from('store-evidence').upload(path,file,{contentType:file.type,upsert:false,cacheControl:'3600'});err(error,'Upload foto: ');return path;
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
