/**
 * DCO v25 - per-user offline drafts and pending photographs.
 * No credentials or auth token are persisted in drafts.  Drafts are device-local.
 * A draft is NEVER considered a successful server submit.
 */
const DB_NAME = 'tigalapan-dco-drafts-v25';
const DB_VERSION = 1;
const STORE_DRAFTS = 'drafts';
const STORE_PHOTOS = 'photos';
const LOCAL_PREFIX = 'draftphoto-';
const MAX_PHOTO_BYTES = 5 * 1024 * 1024;
const MAX_LOCAL_BYTES = 100 * 1024 * 1024;
const WRITE_ACTIONS = new Set(['add','update','bulk','ceklisSet','dsoSubmit','dsoPatch','dsoValidasi','dsoHapus','visitSave','visitValidasi','visitHapus','issueUpdate','rutinSave','rutinHapus','jadwalSave','jadwalHapus','periodSubmit','periodValidate','campaignSave','campaignRecordSave','campaignManage','campaignCleanup','validationUndo','cfgSave','defSave','defHapus','addToko','tokoSave','userSave','hapusUser','gantiPin','wipe','archiveRows','archiveDelete','backup','syncMasalah']);
const CACHE_READS = new Set(['meta','ceklisHari','dsoHari','periodList','campaignList','campaignDetail','campaignRecords','list','issueList','tracking','storeSummary','notif']);
const writeResult = (ok, data, error) => JSON.stringify(ok ? {ok:true,data} : {ok:false,error});
const isOkay = raw => {try { const r = typeof raw==='string'?JSON.parse(raw):raw;return r && r.ok ? r.data : null; }catch{return null;}};
const deepCopy = x => x == null ? x : JSON.parse(JSON.stringify(x));
const qs = s => document.querySelector(s);
const user = () => { const m=window.S?.me; return m ? String(m.username||m.user||m.nama||m.toko||'').toLowerCase() : ''; };
const cleanName = value => String(value||'').replace(/[^\w@.\-]/g,'_').slice(0,100);
const nowLabel = () => new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Makassar',hour:'2-digit',minute:'2-digit'}).format(new Date());
const online = () => navigator.onLine!==false && !window.__dcoForceOffline;
let openPromise;
function db(){
 if(!('indexedDB' in window))return Promise.reject(new Error('IndexedDB tidak tersedia pada browser ini'));
 if(!openPromise) openPromise = new Promise((resolve,reject)=>{
  const req=indexedDB.open(DB_NAME,DB_VERSION);
  req.onupgradeneeded=()=>{const d=req.result;if(!d.objectStoreNames.contains(STORE_DRAFTS))d.createObjectStore(STORE_DRAFTS,{keyPath:'key'});
   if(!d.objectStoreNames.contains(STORE_PHOTOS))d.createObjectStore(STORE_PHOTOS,{keyPath:'id'});};
  req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error||new Error('IndexedDB gagal dibuka'));
 }).catch(e=>{openPromise=null;throw e;});
 return openPromise;
}
async function tx(store,mode,operation){const d=await db();return new Promise((resolve,reject)=>{
 const t=d.transaction(store,mode);let result;
 t.oncomplete=()=>resolve(result);t.onabort=()=>reject(t.error||new Error('Transaksi draft dibatalkan'));
 t.onerror=()=>{};
 try{const r=operation(t.objectStore(store));if(r)r.onsuccess=()=>{result=r.result;};}
 catch(e){try{t.abort();}catch{}reject(e);}
});}
const put = (store,value)=>tx(store,'readwrite',s=>s.put(value));
const del = (store,key)=>tx(store,'readwrite',s=>s.delete(key));
const get = (store,key)=>tx(store,'readonly',s=>s.get(key));
const getAll = store=>tx(store,'readonly',s=>s.getAll());
let lastKey='',lastCaptureAt=0,saveTimer=null,locked=false,uiReady=false,lastUser='',lastError='',flushInProgress=null;
const images=new Map(), refs=new Map(), photoIndex=new Map();
let photoIndexAccount=null;
let originalApi,originalPhotoUrl;
function localRef(v){return typeof v==='string'&&v.startsWith(LOCAL_PREFIX);}
function isPending(v){return localRef(v)&&!refs.has(v);}
function pendingIdsIn(obj){const out=new Set();const walk=x=>{
 if(typeof x==='string'){for(const v of x.match(/draftphoto-[\w-]{20,}/g)||[])if(isPending(v))out.add(v);}
 else if(Array.isArray(x))x.forEach(walk);else if(x&&typeof x==='object')Object.values(x).forEach(walk);
 };walk(obj);return [...out];}
function remapString(s){if(typeof s!=='string'||s.indexOf(LOCAL_PREFIX)<0)return s;return s.replace(/draftphoto-[\w-]{20,}/g,id=>refs.get(id)||id);}
function remap(obj){if(typeof obj==='string')return remapString(obj);
 if(Array.isArray(obj))return obj.map(remap);
 if(obj&&typeof obj==='object')return Object.fromEntries(Object.entries(obj).map(([k,v])=>[k,remap(v)]));return obj;}
function replaceInPlace(obj){if(!obj||typeof obj!=='object')return;
 for(const k of Object.keys(obj)){
  const v=obj[k];if(typeof v==='string')obj[k]=remapString(v);
  else if(v&&typeof v==='object')replaceInPlace(v);
 }}
function toast(text,err){try{window.toast(text,err===true?true:'ok');}catch{console.info('DCO draft:',text);}}
function notify(message,warning=false){lastError=warning?message:'';paint();if(warning)toast(message,true);}
function isVisible(el){return !!(el&&el.isConnected&&el.getClientRects().length&&!el.closest('.hid'))}
function activeModal(){return [...document.querySelectorAll('.modal.on')].find(m=>m.id!=='mPin')||null;}
function fieldState(root){if(!root)return [];
 return [...root.querySelectorAll('input,textarea,select')].filter(e=>{
  const type=(e.type||'').toLowerCase();return e.id!=='lPin'&&e.id!=='pOld'&&e.id!=='pNew'&&type!=='password'&&type!=='hidden'&&type!=='file'&&!e.disabled&&!e.readOnly&&isVisible(e);
 }).map((e,index)=>({id:e.id||'',name:e.name||'',index,value:e.type==='checkbox'||e.type==='radio'?!!e.checked:e.value}));}
function applyFields(root,fields){if(!root||!Array.isArray(fields))return 0;
 const all=[...root.querySelectorAll('input,textarea,select')].filter(e=>e.type!=='hidden'&&e.type!=='file'&&e.type!=='password'&&!e.disabled&&!e.readOnly&&isVisible(e));let n=0;
 fields.forEach(f=>{let el=f.id&&[...all].find(e=>e.id===f.id);
 if(!el&&f.name)el=[...all].find(e=>e.name===f.name);
 if(!el)el=all[f.index];if(!el)return;
 if(el.type==='checkbox'||el.type==='radio')el.checked=!!f.value;
 else if(el.tagName==='SELECT'&&![...el.options].some(o=>o.value===String(f.value)))return;
 else el.value=f.value==null?'':String(f.value);
 n++;
 });return n;}
function context(){const S=window.S,acc=user();if(!S||!acc)return null;
 const modal=activeModal(),tab=S.tab||'dash';let kind='',id='',root=modal||document.getElementById('p'+(tab==='dso'?'Dso':tab==='ceklis'?'Ceklis':tab==='period'?'Period':tab==='visit'?'Visit':tab==='rutin'?'Rutin':tab==='campaign'?'Campaign':tab==='jadwal'?'Jadwal':tab==='issues'?'Issues':tab==='set'?'Set':tab==='MASALAH'?'List':'Dash'));
 if(modal){kind=modal.id;id=String(S.editId||S.vis?.id||S.rt?.id||S.issueEditingItem?.id||'baru')+'|'+(modal.querySelector('h3')?.textContent||'').slice(0,90);}
 else if(tab==='dso')id=['dso',qs('#dsTgl')?.value,qs('#dsToko')?.value,S.dsForm].join('|');
 else if(tab==='ceklis')id=['ceklis',qs('#ckTgl')?.value,qs('#ckToko')?.value].join('|');
 else if(tab==='period')id=['period',qs('#prType')?.value,qs('#prToko')?.value,qs('#prDate')?.value].join('|');
 else if(tab==='campaign')id=['campaign',qs('#cpSelect')?.value,qs('#cpKind')?.value].join('|');
 else id=tab;
 if(!root||!isVisible(root))return null;
 return {account:acc,key:'dco25|'+acc+'|'+tab+'|'+kind+'|'+id,tab,modalId:modal?.id||'',title:(modal?.querySelector('h3')?.textContent||document.getElementById('pageTitle')?.textContent||tab).slice(0,120),root};
}
function capture(){const ctx=context();if(!ctx)return null;const S=window.S,tab=ctx.tab;
 const model={};
 if(tab==='dso'){model.dsJaw=remap(deepCopy(S.dsJaw||{}));model.dsForm=S.dsForm;model.dsMode=S.dsMode;}
 if(tab==='ceklis')model.ckRows=(S.ckRows||[]).map(r=>({id:r.id,rutinId:r.rutinId,judul:r.judul,catatan:r.catatan,fotoId:r.fotoId,status:r.status,validasi:r.validasi}));
 if(tab==='period')model.periodDraft=remap(deepCopy(S.periodDraft||{}));
 if(ctx.modalId==='mVisit')model.vis=remap(deepCopy(S.vis||{}));
 if(ctx.modalId==='mRutin')model.rt=deepCopy(S.rt||{});
 if(ctx.modalId==='mForm'){model.editId=S.editId;model.fotoTmp=remapString(S.fotoTmp||'');}
 if(ctx.modalId==='mGen'){model.issueFotoTemp=remapString(S.issueFotoTemp||'');model.issueAfterTemp=remapString(S.issueAfterTemp||'');model.issueId=S.issueEditingItem?.id||null;if(typeof window.__dcoCampaignDraftContext==='function')model.campaign=deepCopy(window.__dcoCampaignDraftContext());}
 const fields=fieldState(ctx.root);
 if(!fields.length&&!Object.keys(model).length)return null;
 return {key:ctx.key,account:ctx.account,tab,modalId:ctx.modalId,title:ctx.title,context:{date:qs('#dsTgl')?.value,store:qs('#dsToko')?.value,form:S.dsForm,ckDate:qs('#ckTgl')?.value,ckStore:qs('#ckToko')?.value,prType:qs('#prType')?.value,prStore:qs('#prToko')?.value,prDate:qs('#prDate')?.value},fields,model,updatedAt:Date.now()};
}
async function save(snapshot){if(!snapshot)return;
 try{await put(STORE_DRAFTS,snapshot);lastKey=snapshot.key;lastCaptureAt=snapshot.updatedAt;lastError='';paint();}
 catch(e){notify('Draft tidak bisa disimpan di perangkat (kemungkinan penyimpanan penuh): '+(e.message||e),true);}}
function syncFallback(s){if(!s)return;try{const k='dco25-fast-'+cleanName(s.account);const compact=JSON.stringify(s);if(compact.length<65000)localStorage.setItem(k,compact);}catch{}}
function forgetFastDraft(key,account=user()){try{const k='dco25-fast-'+cleanName(account);const value=localStorage.getItem(k);if(value&&JSON.parse(value).key===key)localStorage.removeItem(k);}catch{}}
function captureNow(){if(locked)return Promise.resolve();const snap=capture();syncFallback(snap);return save(snap);}
function schedule(delay=350){if(locked)return;clearTimeout(saveTimer);saveTimer=setTimeout(()=>{saveTimer=null;captureNow();},delay);}
function scopeRows(){return getAll(STORE_DRAFTS).then(a=>a.filter(x=>x.account===user()&&x.kind!=='cache').sort((a,b)=>b.updatedAt-a.updatedAt));}
async function rows(){const a=await scopeRows();const fallback=localStorage.getItem('dco25-fast-'+cleanName(user()));if(fallback){try{const x=JSON.parse(fallback);if(x.account===user()&&!a.find(y=>y.key===x.key))a.unshift(x);}catch{}}return a;}
async function photoRows(){
 const acc=user();if(photoIndexAccount===acc)return [...photoIndex.values()];
 const all=await getAll(STORE_PHOTOS);photoIndex.clear();
 for(const record of all)if(record.account===acc)photoIndex.set(record.id,record);
 photoIndexAccount=acc;return [...photoIndex.values()];
}
async function putPhoto(record){await put(STORE_PHOTOS,record);if(record.account===photoIndexAccount)photoIndex.set(record.id,record);}
async function deletePhoto(id){await del(STORE_PHOTOS,id);photoIndex.delete(id);images.delete(id);refs.delete(id);} 
async function prime(){const a=await photoRows();for(const r of a){if(r.state==='synced'&&r.remoteId)refs.set(r.id,r.remoteId);else if(r.dataUrl)images.set(r.id,r.dataUrl);}}
function photoSize(data){return Math.floor((data.length-data.indexOf(',')-1)*3/4);}
async function storePhoto(p){const account=user();if(!account)throw new Error('Login diperlukan sebelum foto disimpan sebagai draft');
 const size=photoSize(p.dataUrl||'');if(!size||size>MAX_PHOTO_BYTES)throw new Error('Foto terlalu besar untuk draft. Kompres foto lebih dulu.');
 const items=await photoRows();const used=items.filter(x=>x.state==='pending'||x.state==='staged').reduce((n,x)=>n+(x.bytes||0),0);
 if(used+size>MAX_LOCAL_BYTES)throw new Error('Draft foto sudah melebihi 100 MB perangkat. Sinkronkan dahulu.');
 const id=LOCAL_PREFIX+(crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(36).slice(2));
 const record={id,account,state:'pending',dataUrl:p.dataUrl,bytes:size,nama:p.nama||'Bukti foto',captureSource:p.captureSource||'galeri',context:p.context||'',createdAt:Date.now()};
 await putPhoto(record);images.set(id,p.dataUrl);return record;
}
async function stageCamera(file,kind,key){
 if(!file||!file.type?.startsWith('image/'))return;
 const account=user();if(!account)return;
 const id='camerastage-'+(crypto.randomUUID?crypto.randomUUID():Date.now());
 if(file.size>MAX_PHOTO_BYTES)return notify('Foto kamera terlalu besar untuk draft lokal, gunakan foto terlebih dahulu.',true);
 const dataUrl=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.readAsDataURL(file);});
 await putPhoto({id,account,state:'staged',dataUrl,bytes:file.size,context:String(kind)+':'+String(key),createdAt:Date.now(),captureSource:'kamera_live'});
 paint();return id;
}
async function getStagedFiles(kind,key){const keyText=String(kind)+':'+String(key);
 const staged=(await photoRows()).filter(x=>x.state==='staged'&&x.context===keyText);
 return staged.map((r)=>{const [,mime,b64]=r.dataUrl.match(/^data:([^;]+);base64,(.*)$/)||[];
   if(!mime)return null;
   const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
   const f=new File([bytes],r.id+'.webp',{type:mime});f.__dcoCaptureSource='kamera_live';return f;
 }).filter(Boolean);
}
async function clearStaged(kind,key){const staged=(await photoRows()).filter(x=>x.state==='staged'&&x.context===String(kind)+':'+String(key));
 for(const x of staged)await deletePhoto(x.id);paint();
}
async function uploadPhoto(p,sesi){let r;
 try{r=await storePhoto(p);}catch(e){notify('Penyimpanan foto lokal gagal: '+(e.message||e),true);return writeResult(false,null,'Foto belum tersimpan di perangkat: '+(e.message||e));}
 if(!online()){paint();return writeResult(true,{id:r.id,draft:true});}
 try{const raw=await originalApi('uploadFoto',p,sesi),response=isOkay(raw);
  if(!response?.id)throw new Error((typeof raw==='string'&&JSON.parse(raw).error)||'Upload belum dikonfirmasi server');
  refs.set(r.id,response.id);images.delete(r.id);await putPhoto({id:r.id,account:r.account,state:'synced',remoteId:response.id,createdAt:r.createdAt,bytes:0});paint();return raw;
 }catch(e){notify('Foto disimpan sebagai draft lokal; upload belum berhasil. '+(e.message||e),true);return writeResult(true,{id:r.id,draft:true});}
}
async function syncPhotos(){if(flushInProgress)return flushInProgress;
 if(!online()){notify('Masih offline. Foto aman di draft perangkat dan belum dikirim.',true);return {synced:0,pending:0};}
 flushInProgress=(async()=>{const pending=(await photoRows()).filter(x=>x.state==='pending');let succeeded=0,failed=0;
  for(const item of pending){try{
    const raw=await originalApi('uploadFoto',{dataUrl:item.dataUrl,nama:item.nama,captureSource:item.captureSource,context:item.context},window.S?.me?.token||'');
    const result=isOkay(raw);if(!result?.id)throw new Error('Supabase menolak foto');
    refs.set(item.id,result.id);images.delete(item.id);await putPhoto({id:item.id,account:item.account,state:'synced',remoteId:result.id,bytes:0,createdAt:item.createdAt});succeeded++;
   }catch(e){failed++;lastError=String(e.message||e);}}
  if(window.S)replaceInPlace(window.S);
  const all=await scopeRows();for(const d of all){const v={...d,model:remap(d.model)};await put(STORE_DRAFTS,v);}
  if(typeof window.__dcoRemapCampaignPhoto==='function')window.__dcoRemapCampaignPhoto(remapString);
  if(succeeded)toast(succeeded+' foto draft berhasil diunggah; kirim formulir untuk mencatatnya.','ok');
  if(failed)notify(failed+' foto masih tersimpan di draft; periksa koneksi/izin lalu ulangi sinkronisasi.',true);
  paint();return {synced:succeeded,pending:failed};
 })().finally(()=>{flushInProgress=null;});return flushInProgress;
}
async function beforeWrite(action,p){if(!online())return 'Perangkat offline. Data masih berupa draft lokal; hubungkan internet sebelum mengirim.';
 if(pendingIdsIn(p).length){await syncPhotos();if(pendingIdsIn(p).some(id=>!refs.has(id)))return 'Ada foto draft belum terunggah. Foto tetap aman di perangkat; klik Sinkronkan Foto.';}
 return '';
}
function dashboard(){if(!document.body||!window.S?.me)return;
 if(!qs('#dcoDraftStatus')){
  const bar=document.createElement('div');bar.id='dcoDraftStatus';bar.setAttribute('role','status');bar.style.cssText='position:fixed;right:8px;bottom:78px;z-index:15;background:#fff;box-shadow:0 8px 20px #1e1b4b25;border:1px solid #c7d2fe;border-radius:12px;padding:5px 8px;display:flex;gap:5px;align-items:center;flex-wrap:nowrap;max-width:calc(100vw - 16px);color:#1e293b;font:11px system-ui';
  bar.innerHTML='<strong id="dcoDraftText">Draft lokal</strong><button id="dcoDraftOpen" style="border:1px solid #a5b4fc;background:#eef2ff;color:#3730a3;border-radius:8px;padding:7px 8px;cursor:pointer">📋 Draft</button><button id="dcoDraftSync" style="border:1px solid #a5b4fc;background:#eef2ff;color:#3730a3;border-radius:8px;padding:7px 8px;cursor:pointer">⇧ Foto</button>';
  document.body.appendChild(bar);qs('#dcoDraftOpen').onclick=()=>window.__dcoDraft.open();qs('#dcoDraftSync').onclick=()=>syncPhotos();
 }
 if(!qs('#dcoDraftModal')){
  const modal=document.createElement('div');modal.id='dcoDraftModal';modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.style.cssText='display:none;position:fixed;inset:0;z-index:60;background:#0f172ac9;align-items:center;justify-content:center;padding:12px;';
  modal.innerHTML='<div style="background:white;border-radius:18px;padding:18px;width:min(100%,630px);max-height:85vh;overflow:auto;color:#0f172a"><div style="display:flex;justify-content:space-between;align-items:center"><h2 style="margin:0;font-size:18px">Draft Tersimpan di Perangkat</h2><button id="dcoDraftClose" class="btn">✕</button></div><p style="color:#64748b">Tersimpan hanya di browser/perangkat ini. Belum menjadi laporan Supabase. Gunakan akun yang sama untuk memulihkan.</p><div id="dcoDraftRows"></div><p id="dcoDraftStorageMessage" style="font-size:12px;color:#64748b"></p></div>';
  document.body.appendChild(modal);qs('#dcoDraftClose').onclick=()=>{modal.style.display='none';};modal.addEventListener('click',e=>{if(e.target===modal)modal.style.display='none';});
 }
}
async function paint(){if(!window.S?.me)return;dashboard();const bar=qs('#dcoDraftStatus');if(!bar)return;
 try{const [d,p]=await Promise.all([scopeRows(),photoRows()]);const pending=p.filter(x=>x.state==='pending').length,staged=p.filter(x=>x.state==='staged').length;
  qs('#dcoDraftText').textContent=(online()?'☁':'⚠ Offline')+' '+d.length+' draft · '+pending+' foto';
  bar.title='Draft lokal akun '+user()+': '+d.length+' formulir, '+pending+' foto belum terkirim, '+staged+' foto kamera belum digunakan'+(lastCaptureAt?'. Disimpan '+nowLabel()+' WITA':'');
  qs('#dcoDraftSync').disabled=!online()||pending===0;
  if(!window.indexedDB)bar.title='Penyimpanan draft tidak tersedia';
 }catch(e){qs('#dcoDraftText').textContent='⚠ Draft belum bisa disimpan';bar.title=String(e.message||e);}
}
async function openPanel(){dashboard();const modal=qs('#dcoDraftModal');if(!modal)return;modal.style.display='flex';const rowsWrap=qs('#dcoDraftRows');
 try{const d=await rows(),p=await photoRows(),pending=p.filter(x=>x.state==='pending'),staged=p.filter(x=>x.state==='staged');rowsWrap.innerHTML=d.length?d.map(row=>{
  const date=new Date(row.updatedAt).toLocaleString('id-ID',{timeZone:'Asia/Makassar'});return '<div style="border:1px solid #e2e8f0;border-radius:12px;padding:10px;margin:8px 0"><b>'+escapeHtml(row.title||row.tab)+'</b> <small style="color:#64748b">'+escapeHtml(date)+' WITA</small><div style="display:flex;gap:8px;margin-top:9px;flex-wrap:wrap"><button class="btn s p" data-restore="'+escapeHtml(row.key)+'">Pulihkan</button><button class="btn s r" data-remove="'+escapeHtml(row.key)+'">Hapus Draft</button></div></div>';
  }).join(''):'<div style="padding:15px;background:#f8fafc;border-radius:12px">Belum ada draft formulir.</div>';
  if(staged.length)rowsWrap.insertAdjacentHTML('beforeend','<p><b>'+staged.length+' foto kamera belum digunakan.</b> Buka kembali tombol Foto pada form asal untuk memulihkannya secara otomatis.</p>');
  if(pending.length)rowsWrap.insertAdjacentHTML('beforeend','<p><b>'+pending.length+' foto menunggu sinkronisasi.</b> Foto tidak hilang ketika aplikasi ditutup. Setelah online, klik Sinkronkan Foto lalu periksa formulir sebelum menekan Kirim.</p>');
  qs('#dcoDraftStorageMessage').textContent='Draft bukan backup cloud. Jika data browser dihapus, browser mode privat digunakan, atau perangkat diganti, draft bisa hilang.';
  rowsWrap.onclick=async e=>{const b=e.target.closest('button');if(!b)return;
   if(b.dataset.restore){const x=d.find(y=>y.key===b.dataset.restore);if(x)await restore(x);}
   if(b.dataset.remove){if(confirm('Hapus draft ini dari perangkat? Laporan Supabase tidak berubah.')){const removed=d.find(x=>x.key===b.dataset.remove);
    await del(STORE_DRAFTS,b.dataset.remove);forgetFastDraft(b.dataset.remove);
    if(removed){
      const referencedInOthers=JSON.stringify(d.filter(x=>x.key!==removed.key).map(x=>x.model));
      const candidates=String(JSON.stringify(removed.model||{})).match(/draftphoto-[\w-]{20,}/g)||[];
      for(const id of new Set(candidates)){
        const photo=photoIndex.get(id);
        if(photo?.state==='pending'&&!referencedInOthers.includes(id))await deletePhoto(id);
      }
    }
    openPanel();paint();}}
  };
 }catch(e){rowsWrap.textContent='Tidak dapat membaca draft: '+String(e.message||e);}
}
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function restore(d){if(!window.S?.me||d.account!==user()){notify('Draft berasal dari akun lain.',true);return;}
 locked=true;try{
 const S=window.S,x=remap(d.model||{}),c=d.context||{};
 if(d.tab==='dso'){if(c.date)qs('#dsTgl').value=c.date;if(c.store&&qs('#dsToko'))qs('#dsToko').value=c.store;if(x.dsForm)S.dsForm=x.dsForm;S.dsMode=x.dsMode||'isi';}
 if(d.tab==='ceklis'){if(c.ckDate)qs('#ckTgl').value=c.ckDate;if(c.ckStore&&qs('#ckToko'))qs('#ckToko').value=c.ckStore;S.ckMode='isi';}
 if(d.tab==='period'){if(c.prType)qs('#prType').value=c.prType;if(c.prStore&&qs('#prToko'))qs('#prToko').value=c.prStore;if(c.prDate)qs('#prDate').value=c.prDate;}
 if(d.tab!==S.tab&&typeof window.go==='function')window.go(d.tab);
 // go() starts its refresh asynchronously; await the most recent request before overlaying draft.
 if(d.tab==='dso'&&typeof window.loadDso==='function')await window.loadDso();
 if(d.tab==='ceklis'&&typeof window.loadCeklis==='function')await window.loadCeklis();
 if(d.tab==='period'&&typeof window.loadPeriodReports==='function')await window.loadPeriodReports();
 if(d.tab==='dso'){S.dsJaw=x.dsJaw||{};S.dsJaw._key=(S.dsForm||'')+'|'+(qs('#dsToko')?.value||S.me.toko||'')+'|'+(qs('#dsTgl')?.value||'');if(typeof window.renderDso==='function')window.renderDso();}
 if(d.tab==='ceklis'&&Array.isArray(x.ckRows)){
  const rows=S.ckRows||[];x.ckRows.forEach(v=>{const r=rows.find(y=>y.id&&y.id===v.id||y.rutinId&&y.rutinId===v.rutinId&&y.judul===v.judul);
   if(r&&r.validasi!=='Y'){r.catatan=v.catatan;r.fotoId=v.fotoId;if(pendingIdsIn(v).length)r._draftStatus=v.status;}});
  if(typeof window.renderCeklis==='function')window.renderCeklis();
 }
 if(d.tab==='period'&&x.periodDraft){S.periodDraft=x.periodDraft;if(typeof window.__dcoRenderPeriodDraft==='function')window.__dcoRenderPeriodDraft();}
 if(d.modalId==='mVisit'&&x.vis){S.vis=x.vis;typeof window.renderVisit==='function'&&window.renderVisit();qs('#mVisit')?.classList.add('on');}
 if(d.modalId==='mRutin'&&x.rt){S.rt=x.rt;typeof window.renderRutinForm==='function'&&window.renderRutinForm();qs('#mRutin')?.classList.add('on');}
 if(d.modalId==='mForm'){S.editId=x.editId||null;S.fotoTmp=x.fotoTmp||'';
  if(typeof window.openForm==='function')window.openForm(S.editId||undefined);
 }
 if(d.modalId==='mGen'){window.__dcoDraftPendingModal={title:d.title,fields:d.fields,model:x};
  if(d.tab==='campaign'&&typeof window.__dcoOpenCampaignDraft==='function')await window.__dcoOpenCampaignDraft(d);
  else if(typeof window.__dcoRestoreGen==='function')window.__dcoRestoreGen(d);}
 const root=d.modalId?qs('#'+d.modalId):document.getElementById('p'+(d.tab==='dso'?'Dso':d.tab==='ceklis'?'Ceklis':d.tab==='period'?'Period':d.tab==='visit'?'Visit':d.tab==='rutin'?'Rutin':d.tab==='campaign'?'Campaign':d.tab==='jadwal'?'Jadwal':d.tab==='issues'?'Issues':d.tab==='set'?'Set':d.tab==='MASALAH'?'List':'Dash'));
 const n=applyFields(root,d.fields);
 if(d.modalId==='mForm'){if(S.fotoTmp&&typeof window.thumbs==='function'&&qs('#fotoPrev'))qs('#fotoPrev').innerHTML=window.thumbs([S.fotoTmp],70);}
 qs('#dcoDraftModal').style.display='none';toast('Draft dipulihkan ('+n+' isian). Periksa kembali, lalu kirim saat online.','ok');
 }catch(e){notify('Tidak dapat memulihkan draft: '+(e.message||e),true);}
 finally{locked=false;setTimeout(()=>captureNow(),800);}
}
async function clearCurrent(){const ctx=context();if(ctx){await del(STORE_DRAFTS,ctx.key);forgetFastDraft(ctx.key,ctx.account);lastKey='';paint();}}
function offlinePhotoMessage(){return online()?'Foto tersimpan sebagai draft lokal; tekan Sinkronkan Foto.':'Foto aman pada perangkat (offline). Belum terkirim ke server.';}
function hookEvents(){
 document.addEventListener('input',e=>{if(e.target.closest('#vLogin, #mPin,#dcoDraftModal'))return;schedule(350);},true);
 document.addEventListener('change',e=>{if(e.target.closest('#vLogin, #mPin,#dcoDraftModal'))return;
  // File inputs are handled by the existing compressors, but ensure the form text is captured.
  schedule(80);
 },true);
 document.addEventListener('click',e=>{if(e.target.closest('#vLogin,#dcoDraftStatus,#dcoDraftModal,#mPin'))return;
  const b=e.target.closest('button,.cb,.vopt,.seg,input[type=checkbox]');if(!b)return;
  if(b.closest('.modal')||b.closest('#pCeklis,#pDso,#pPeriod,#pCampaign,#pVisit,#pRutin,#pJadwal,#pIssues,#pList,#pSet')){
   const before=capture();if(before)save(before);schedule(100);
  }
 },true);
 window.addEventListener('pagehide',()=>{clearTimeout(saveTimer);const s=capture();syncFallback(s);save(s);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden){clearTimeout(saveTimer);const s=capture();syncFallback(s);save(s);}});
 window.addEventListener('online',()=>{lastError='';paint();toast('Online kembali. Draft aman; sinkronkan foto dan kirim formulir.','ok');});
 window.addEventListener('offline',()=>{paint();toast('Offline: input tetap menjadi draft lokal, belum dikirim.',true);});
}
async function warm(){let current='';setInterval(async()=>{const a=user();if(a!==current){current=a;lastUser=a;images.clear();refs.clear();photoIndex.clear();photoIndexAccount=null;if(a){try{await prime();dashboard();await paint();}catch(e){notify('Penyimpanan draft tidak tersedia: '+e.message,true);}}else{qs('#dcoDraftStatus')?.remove();qs('#dcoDraftModal')?.remove();}}
 },1100);}
export function installDrafts(backend){originalApi=backend;originalPhotoUrl=window.__dcoFotoUrl;
 window.__dcoDraft={captureNow,open:openPanel,syncPhotos,rows,photoRows,clearCurrent,isPending,containsPending:x=>pendingIdsIn(x).length>0,remap,photoUrl:id=>images.get(id)||null,offlinePhotoMessage,notify,stageCamera,getStagedFiles,clearStaged,applyFields};
 window.__dcoFotoUrl=(id,width)=>{if(refs.has(id))return originalPhotoUrl(refs.get(id),width);return images.get(id)||originalPhotoUrl(id,width);};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{hookEvents();warm();});else{hookEvents();warm();}
 const wrapped=async(action,p,sesi)=>{
  if(action==='uploadFoto')return uploadPhoto(p||{},sesi);
  if(WRITE_ACTIONS.has(action)){
   // Save BEFORE every write. In case the page crashes after pressing Submit, the draft is retained.
   await captureNow();const err=await beforeWrite(action,p||{});if(err)return writeResult(false,null,err);
   p=remap(deepCopy(p||{}));
  }
  if(CACHE_READS.has(action)&&!online()){
   const key='dco25-cache|'+user()+'|'+action+'|'+JSON.stringify(p||{});
   const cached=await get(STORE_DRAFTS,key).catch(()=>null);
   return cached?cached.response:writeResult(false,null,'Offline: data awal menu belum pernah dibuka saat online. Draft yang sudah ada tetap aman.');
  }
  const raw=await backend(action,p,sesi);
  if(CACHE_READS.has(action)&&isOkay(raw)!=null){
   const key='dco25-cache|'+user()+'|'+action+'|'+JSON.stringify(p||{});
   // Stored separately (same table) but filtered out of Draft list by key prefix.
   put(STORE_DRAFTS,{key,account:user(),kind:'cache',response:raw,updatedAt:Date.now()}).catch(()=>{});
  }
  if(WRITE_ACTIONS.has(action)&&isOkay(raw)!=null&&['periodSubmit','campaignSave','campaignRecordSave','rutinSave','jadwalSave','add','update','issueUpdate'].includes(action)){
   // Do not purge a draft whose photo is still pending / not yet linked to a server record.
   if(!pendingIdsIn(p||{}).length)clearCurrent().catch(()=>{});
  }
  return raw;
 };
 return wrapped;
}
