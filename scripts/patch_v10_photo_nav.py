"""Patch UI v9 to camera + separate multi-photo evidence + route audit v10.
Idempotent: if marker is present, the output is returned unchanged.
Called by build_index.py so regenerated HTML retains this patch.
"""
from pathlib import Path
import sys

MARKER = 'DCO_V10_CAMERA_GALLERY_PATCH'
CSS = r'''
/* DCO_V10_CAMERA_GALLERY_PATCH: evidence is visible, mobile-first */
.evidence-panel{min-width:0;display:flex;flex-direction:column;gap:7px;background:#f6f8ff;border:1px solid #d8dff5;border-radius:12px;padding:9px;margin-top:9px}
.evidence-panel.compact{padding:7px;min-width:180px;flex:1}
.evidence-header{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:space-between;font-size:11.5px;color:#485675;font-weight:700}
.evidence-gallery{display:flex;flex-wrap:wrap;gap:7px;align-items:center;min-height:33px}
.evidence-thumb{position:relative;width:64px;height:64px;flex:0 0 64px;border-radius:10px;border:1px solid #cbd5e1;background:white;overflow:hidden}
.evidence-thumb img{width:100%!important;height:100%!important;object-fit:cover;border:0;margin:0;cursor:zoom-in}
.evidence-thumb .evidence-remove{position:absolute;top:2px;right:2px;width:22px;height:22px;border-radius:50%;border:0;background:#b91c1c;color:white;font-size:17px;font-weight:700;display:grid;place-items:center;cursor:pointer}
.evidence-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.evidence-actions .btn{padding:8px 10px;min-height:37px;white-space:normal;text-align:center;font-size:12px}
.evidence-actions label{display:inline-flex;align-items:center;justify-content:center;cursor:pointer}
.evidence-empty,.evidence-help{font-size:11px;color:#64748b}
.evidence-busy{font-size:11px;font-weight:700;color:#4338ca}
.ck-evidence{margin-top:8px}
.ckrow .evidence-panel{margin-bottom:5px}
.dsoit{flex-wrap:wrap}
.dsoit>.evidence-panel{flex-basis:100%;margin-top:4px}
.dsoit .ph{cursor:default}
.visit-point-photo{max-width:100%;flex:1 1 220px}
.visit-point-photo .evidence-panel{width:100%;margin:0;min-width:170px}
.visit-issue-fields .evidence-panel{margin:0;grid-column:1/-1}
.vitem{gap:9px;align-items:flex-start}
.vitem>span{min-width:165px}
.evidence-row-action{cursor:pointer}
#dcoCameraModal{position:fixed;inset:0;z-index:95;background:rgba(9,17,39,.87);display:none;align-items:center;justify-content:center;padding:14px;backdrop-filter:blur(5px)}
#dcoCameraModal.on{display:flex}
#dcoCameraModal .camera-sheet{width:min(620px,100%);max-height:95dvh;overflow:auto;background:#fff;border-radius:19px;padding:15px;display:flex;flex-direction:column;gap:11px}
#dcoCameraModal video{background:#111827;width:100%;max-height:min(62vh,480px);aspect-ratio:4/3;object-fit:contain;border-radius:12px}
#dcoCameraModal .cam-buttons{display:flex;gap:8px;flex-wrap:wrap}
#dcoCameraModal .cam-buttons .btn{flex:1 1 125px;min-height:44px}
#dcoCameraModal .cam-preview{display:flex;gap:6px;flex-wrap:wrap}
#dcoCameraModal .cam-preview img{width:72px;height:72px;object-fit:cover;border-radius:9px}
@media(max-width:650px){.evidence-actions .btn{flex:1 1 132px}.evidence-thumb{width:58px;height:58px;flex-basis:58px}.ckrow{flex-wrap:wrap}.ckrow .evidence-panel{width:100%}.visit-point-photo{flex-basis:100%}.vitem .vopt{margin-left:auto}}
'''
MODAL = r'''
<div id="dcoCameraModal" role="dialog" aria-modal="true" aria-label="Ambil foto bukti langsung">
 <div class="camera-sheet">
   <div style="display:flex;align-items:center;justify-content:space-between;gap:8px"><strong>📷 Kamera Bukti</strong><button type="button" class="btn s" onclick="closeEvidenceCamera()">✕ Tutup</button></div>
   <video id="evidenceCameraVideo" autoplay muted playsinline></video>
   <div class="evidence-help">Izinkan akses kamera. Foto tetap terpisah dan dikompres sebelum diunggah. Bisa mengambil beberapa foto.</div>
   <div id="evidenceCameraPreview" class="cam-preview"></div>
   <div class="cam-buttons"><button type="button" class="btn p" onclick="captureEvidenceFrame()">📸 Ambil foto</button><button type="button" class="btn" onclick="switchEvidenceCamera()">↻ Ganti kamera</button><label class="btn">📱 Kamera HP<input type="file" accept="image/*" capture="environment" multiple style="display:none" onchange="nativeEvidencePhoto(this)"></label><button type="button" class="btn g" id="evidenceCameraSave" onclick="saveEvidenceCamera()">✔ Gunakan foto</button></div>
 </div>
</div>
'''
JS = r'''
// DCO_V10_CAMERA_GALLERY_PATCH - Supabase Storage stores WebP images; HTML renders independent thumbnails.
var DCO_EVIDENCE_LIMIT = 30, evidenceBusy = {}, cameraEvidence = {stream:null,files:[],kind:'',key:'',facing:'environment',urls:[]};
function photoList(v){
 var arr=[];
 function add(x){
  if(Array.isArray(x)){x.forEach(add);return;}
  if(typeof x!=='string'||!x||x==='…')return;
  if(x.trim().charAt(0)==='['){try{var a=JSON.parse(x);if(Array.isArray(a)){add(a);return;}}catch(e){}}
  if(validId(x)&&arr.indexOf(x)<0)arr.push(x);
 }
 add(v);return arr;
}
function photoPack(ids){ids=photoList(ids);return !ids.length?'':ids.length===1?ids[0]:JSON.stringify(ids);}
thumbs=function(ids,w){var all=photoList(ids);return all.map(function(id){return '<img class="thumb" loading="lazy" decoding="async" alt="Foto bukti; ketuk untuk memperbesar" style="width:'+(w||52)+'px;height:'+(w||52)+'px" src="'+esc(fotoUrl(id,320))+'" data-id="'+esc(id)+'" onclick="lightbox(this)" onerror="fotoFallback(this)">';}).join(' ');};
function evidenceId(kind,key){key=String(key);if(kind==='ck')return S.ckRows&&S.ckRows[+key]&&S.ckRows[+key].fotoId;
 if(kind==='dso')return S.dsJaw&&S.dsJaw[key]; if(kind==='form')return S.fotoTmp;
 if(kind==='point'||kind==='seksi')return S.vis&&S.vis.foto&&S.vis.foto[key];
 if(kind==='visitIssue')return S.vis&&S.vis.issuesList&&S.vis.issuesList[+key]&&S.vis.issuesList[+key].fotoId;
 if(kind==='issue')return S.issueFotoTemp;return '';}
function evidenceLock(kind,key){if(kind==='ck'){var r=S.ckRows&&S.ckRows[+key];return !r||(r.validasi==='Y'&&!isMgr());}
 if(kind==='dso'){var r=typeof dsoCur==='function'?dsoCur():null;return !!(r&&r.validasi==='Approved'&&!isMgr());}
 if(kind==='point'||kind==='visitIssue'||kind==='seksi')return !S.vis||!!S.vis._view;
 return false;}
function evidencePanel(kind,key,small){key=String(key);var ids=photoList(evidenceId(kind,key)),lock=evidenceLock(kind,key),busy=!!evidenceBusy[kind+':'+key];
 var h='<div class="evidence-panel'+(small?' compact':'')+'" data-evidence-kind="'+esc(kind)+'" data-evidence-key="'+esc(key)+'"><div class="evidence-header"><span>📎 Bukti Foto <span style="font-weight:500">('+ids.length+' foto)</span></span>'+(busy?'<span class="evidence-busy">⏳ Mengunggah…</span>':'')+'</div><div class="evidence-gallery">';
 if(!ids.length)h+='<span class="evidence-empty">Belum ada bukti foto</span>';
 ids.forEach(function(id){h+='<div class="evidence-thumb"><img loading="lazy" src="'+esc(fotoUrl(id,320))+'" data-id="'+esc(id)+'" alt="Bukti foto" onclick="lightbox(this)" onerror="fotoFallback(this)">';
  if(!lock&&!busy)h+='<button type="button" class="evidence-remove" aria-label="Hapus foto" title="Hapus foto dari laporan" data-kind="'+esc(kind)+'" data-key="'+esc(key)+'" data-id="'+esc(id)+'" onclick="removeEvidencePhoto(this.dataset.kind,this.dataset.key,this.dataset.id)">×</button>';h+='</div>';});
 h+='</div>';
 if(!lock)h+='<div class="evidence-actions"><button type="button" class="btn s p" '+(busy?'disabled':'')+' data-kind="'+esc(kind)+'" data-key="'+esc(key)+'" onclick="openEvidenceCamera(this.dataset.kind,this.dataset.key)">📷 Foto langsung</button><label class="btn s" '+(busy?'style="opacity:.55"':'')+'>📱 Kamera HP<input type="file" accept="image/*" capture="environment" '+(busy?'disabled ':'')+'style="display:none" data-kind="'+esc(kind)+'" data-key="'+esc(key)+'" onchange="handleEvidenceInput(this)"></label><label class="btn s" '+(busy?'style="opacity:.55"':'')+'>🖼 Dari galeri<input type="file" accept="image/*" multiple '+(busy?'disabled ':'')+'style="display:none" data-kind="'+esc(kind)+'" data-key="'+esc(key)+'" onchange="handleEvidenceInput(this)"></label></div>';
 if(!small)h+='<div class="evidence-help">Bisa beberapa foto; WebP otomatis, ketuk foto untuk melihat jelas.</div>';
 return h+'</div>';
}
function updateEvidencePanel(kind,key){document.querySelectorAll('[data-evidence-kind][data-evidence-key]').forEach(function(el){if(el.dataset.evidenceKind===String(kind)&&el.dataset.evidenceKey===String(key)){el.outerHTML=evidencePanel(kind,key,el.classList.contains('compact'));}});}
function evidenceFileToDataURL(file){return new Promise(function(resolve,reject){
 if(!file||!String(file.type||'').startsWith('image/'))return reject(new Error('Hanya file gambar yang didukung'));
 if(file.size>25*1024*1024)return reject(new Error('Foto melebihi 25 MB; pilih foto yang lebih kecil'));
 var img=new Image(),url=URL.createObjectURL(file),finished=false;
 var clean=function(){if(!finished){finished=true;URL.revokeObjectURL(url);}};
 img.onerror=function(){clean();reject(new Error('Gambar tidak dapat dibaca'))};
 img.onload=function(){try{var maxSide=1600,scale=Math.min(1,maxSide/Math.max(img.naturalWidth,img.naturalHeight)),c=document.createElement('canvas');
  c.width=Math.max(1,Math.round(img.naturalWidth*scale));c.height=Math.max(1,Math.round(img.naturalHeight*scale));c.getContext('2d').drawImage(img,0,0,c.width,c.height);
  var data='',quality=.82;
  for(var z=0;z<5;z++){data=c.toDataURL('image/webp',quality);if(!data.startsWith('data:image/webp;'))data=c.toDataURL('image/jpeg',quality);
   if(data.length*0.75<500*1024||z===4)break;
   quality=Math.max(.60,quality-.07);if(z>=2){var out=document.createElement('canvas');out.width=Math.max(1,Math.round(c.width*.87));out.height=Math.max(1,Math.round(c.height*.87));out.getContext('2d').drawImage(c,0,0,out.width,out.height);c=out;}
  }clean();resolve(data);
 }catch(e){clean();reject(e);}};img.src=url;});}
function evidenceStateSave(kind,key,packed){key=String(key);var old=evidenceId(kind,key);if(kind==='ck')return ckSend(+key,{fotoId:packed}).then(function(){if(evidenceId(kind,key)!==packed)throw new Error('Server belum menyimpan foto checklist');});
 if(kind==='dso'){S.dsJaw[key]=packed;var cur=dsoCur();if(!cur){updateEvidencePanel(kind,key);return Promise.resolve();}
   return call('dsoPatch',{id:cur.id,itemId:key,fotoId:packed},true).then(function(r){cur.jawaban=r.jawaban;},function(e){S.dsJaw[key]=old;throw e;});}
 if(kind==='form'){S.fotoTmp=packed;return Promise.resolve();}
 if(kind==='issue'){S.issueFotoTemp=packed;return Promise.resolve();}
 if(kind==='point'||kind==='seksi'){S.vis.foto[key]=packed;return Promise.resolve();}
 if(kind==='visitIssue'){if(!S.vis.issuesList[+key])throw new Error('Issue tidak tersedia');S.vis.issuesList[+key].fotoId=packed;return Promise.resolve();}
 return Promise.reject(new Error('Menu foto tidak diketahui: '+kind));}
async function processEvidenceFiles(kind,key,files){key=String(key);var k=kind+':'+key;if(evidenceBusy[k])return toast('Upload sebelumnya masih berjalan',true);
 files=Array.from(files||[]);if(!files.length)return;if(evidenceLock(kind,key))return toast('Data telah dikunci, foto tidak dapat diubah',true);
 var old=photoList(evidenceId(kind,key)),remain=DCO_EVIDENCE_LIMIT-old.length;
 if(files.length>remain)return toast('Maksimal '+DCO_EVIDENCE_LIMIT+' foto per bukti; tersisa '+Math.max(0,remain)+' slot',true);
 evidenceBusy[k]=true;updateEvidencePanel(kind,key);var result=old.slice(),failed=0,reason='';
 try{for(var i=0;i<files.length;i++){
   try{var data=await evidenceFileToDataURL(files[i]);var sent=await call('uploadFoto',{dataUrl:data,nama:kind+'_'+Date.now()},true);
    if(!sent||!validId(sent.id))throw new Error('ID foto tidak valid');if(result.indexOf(sent.id)<0)result.push(sent.id);
   }catch(e){failed++;reason=e&&e.message||String(e);}
  }
  if(result.length>old.length){await evidenceStateSave(kind,key,photoPack(result));toast((result.length-old.length)+' foto '+(['form','issue','point','seksi','visitIssue'].indexOf(kind)>=0?'siap. Simpan formulir untuk mencatatnya.':'tersimpan')+(failed?' · '+failed+' gagal':''),'ok');}
  else toast(reason||'Upload foto gagal',true);
 }catch(e){toast('Foto belum tersimpan: '+(e&&e.message||e),true);}finally{delete evidenceBusy[k];updateEvidencePanel(kind,key);}
}
function handleEvidenceInput(input){var files=Array.from(input.files||[]),kind=input.dataset.kind,key=input.dataset.key;input.value='';return processEvidenceFiles(kind,key,files);}
function nativeEvidencePhoto(input){var files=Array.from(input.files||[]),kind=cameraEvidence.kind,key=cameraEvidence.key;input.value='';closeEvidenceCamera();return processEvidenceFiles(kind,key,files);}
async function removeEvidencePhoto(kind,key,id){if(evidenceBusy[kind+':'+key])return;if(!confirm('Hapus foto ini dari laporan?'))return;
 var current=photoList(evidenceId(kind,key));try{await evidenceStateSave(kind,key,photoPack(current.filter(function(x){return x!==id;})));updateEvidencePanel(kind,key);toast('Foto dilepas dari laporan','ok');}catch(e){toast('Gagal melepas foto: '+(e.message||e),true);}}
function renderEvidenceInDso(){if(!S.meta||!S.dsRows||!S.dsJaw)return;var toko=isMgr()?$('dsToko').value:S.me.toko;if(toko==='SEMUA'||S.dsMode!=='isi')return;
 var items=S.meta.formDef.filter(function(d){return d.form===S.dsForm&&d.aktif!=='N';});var nodes=document.querySelectorAll('#dsBody .dsoit');nodes.forEach(function(node,i){var it=items[i];if(!it)return;
  var ph=node.querySelector('.ph');if(ph){var ids=photoList(S.dsJaw[it.id]);ph.outerHTML='<div class="ph" title="Bukti '+esc(it.label)+'">'+(ids.length?'<img loading="lazy" src="'+esc(fotoUrl(ids[0],320))+'" data-id="'+esc(ids[0])+'" onclick="lightbox(this)" onerror="fotoFallback(this)">':'📷')+(ids.length>1?'<span class="num">'+ids.length+' foto</span>':'')+'</div>';}
  var del=node.querySelector('button[onclick^="dsoHapusFoto"]');if(del)del.remove();
  node.insertAdjacentHTML('beforeend',evidencePanel('dso',it.id,true));});}
// Keep new photo controls outside the hidden three-dots menu in Assignment Checklist.
var renderCeklisBeforeCamera=renderCeklis;
renderCeklis=function(){renderCeklisBeforeCamera();document.querySelectorAll('#ckIsi .ckrow').forEach(function(row){var i=Number(row.id.slice(2));if(!Number.isInteger(i))return;
 var old=row.querySelector('.ck-evidence');if(old)old.remove();var target=row.querySelector('.more');if(!target)return;
 Array.from(target.querySelectorAll('label')).filter(function(x){return !!x.querySelector('input[type=file]');}).forEach(function(x){x.remove();});
 Array.from(target.querySelectorAll('img.thumb')).forEach(function(x){x.remove();});
 Array.from(target.querySelectorAll('button')).filter(function(x){return (x.getAttribute('onclick')||'').indexOf('fotoId')>=0;}).forEach(function(x){x.remove();});
 target.insertAdjacentHTML('beforebegin','<div class="ck-evidence">'+evidencePanel('ck',i)+'</div>');
 });};
var renderDsoBeforeCamera=renderDso;
renderDso=function(){renderDsoBeforeCamera();renderEvidenceInDso();};
var renderVisitBeforeCamera=renderVisit;
renderVisit=function(){renderVisitBeforeCamera();if(!S.vis||!S.meta)return;
 Array.from(document.querySelectorAll('#vBody .vitem')).forEach(function(node){var code=node.querySelector('b');if(!code)return;
  var def=S.meta.visitDef.find(function(x){return x.kode===code.textContent.trim();});if(!def)return;
  var place=node.querySelector('.visit-point-photo');if(place)place.innerHTML=evidencePanel('point',def.id,true);
 });
 Array.from(document.querySelectorAll('#vBody .visit-issue-card')).forEach(function(node,i){var div=node.querySelector('.visit-issue-fields > div:last-child');if(div)div.innerHTML=evidencePanel('visitIssue',i,true);});
};
var openFormBeforeCamera=openForm;
openForm=function(){openFormBeforeCamera.apply(this,arguments);var prev=$('fotoPrev');if(prev&&prev.parentElement)prev.parentElement.innerHTML=evidencePanel('form','main');};
var editVisitIssueBeforeCamera=editVisitIssue;
editVisitIssue=function(){editVisitIssueBeforeCamera.apply(this,arguments);var prev=$('issuePrev');if(prev&&prev.parentElement)prev.parentElement.innerHTML=evidencePanel('issue','main');};
var dsoDetailBeforeCamera=dsoDetail;
dsoDetail=function(i){dsoDetailBeforeCamera(i);var r=S.rows[i],def=S.meta.formDef.filter(function(d){return d.form===r.form;}),grid=Array.from($('dBody').children).find(function(x){return x.style.display==='grid';});
 if(!grid)return;Array.from(grid.children).forEach(function(node,j){if(!def[j])return;var photos=thumbs([r.jawaban[def[j].id]],88);node.innerHTML='<div class="evidence-gallery">'+(photos||'<span class="evidence-empty">Belum ada foto</span>')+'</div><div style="margin-top:5px;font-weight:700">'+esc(def[j].label)+'</div>';});};
// Photo controls were previously hidden inside other forms or only allowed one image.
ckFoto=function(i,input){return handleEvidenceInput(input);};
dsoFoto=function(id,input){return handleEvidenceInput(input);};
visitPointFoto=function(id,input){return handleEvidenceInput(input);};
visitIssuePhoto=function(i,input){return handleEvidenceInput(input);};
issuePickFoto=function(input){return handleEvidenceInput(input);};
pickFoto=function(input){return handleEvidenceInput(input);};
visitFoto=function(id,input){return handleEvidenceInput(input);};
// Camera preview with repeated shutter. Requires HTTPS and a browser granting camera permission.
async function startEvidenceStream(){if(cameraEvidence.stream){cameraEvidence.stream.getTracks().forEach(function(t){t.stop();});cameraEvidence.stream=null;}
 var stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:cameraEvidence.facing},width:{ideal:1280},height:{ideal:960}},audio:false});
 cameraEvidence.stream=stream;var v=$('evidenceCameraVideo');v.srcObject=stream;await v.play();}
async function openEvidenceCamera(kind,key){if(evidenceLock(kind,key))return toast('Foto bukti terkunci',true);
 cameraEvidence.kind=kind;cameraEvidence.key=String(key);cameraEvidence.facing='environment';cameraEvidence.files=[];
 $('evidenceCameraPreview').innerHTML='';$('dcoCameraModal').classList.add('on');
 if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){toast('Kamera web tidak tersedia. Pilih galeri atau gunakan kamera melalui pemilih file.',true);return;}
 try{await startEvidenceStream();}catch(e){toast('Akses kamera ditolak / tidak tersedia. Izinkan kamera di browser atau pilih galeri.',true);}}
function captureEvidenceFrame(){var v=$('evidenceCameraVideo');if(!v.videoWidth)return toast('Kamera belum siap. Periksa izin kamera.',true);
 if(cameraEvidence.files.length>=DCO_EVIDENCE_LIMIT)return toast('Maksimal '+DCO_EVIDENCE_LIMIT+' foto',true);
 var c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);
 c.toBlob(function(blob){if(!blob)return toast('Foto gagal ditangkap',true);var file=new File([blob],'kamera_'+Date.now()+'.jpg',{type:blob.type||'image/jpeg'});
  cameraEvidence.files.push(file);var url=URL.createObjectURL(file);cameraEvidence.urls.push(url);
  $('evidenceCameraPreview').insertAdjacentHTML('beforeend','<img alt="Foto dari kamera" src="'+url+'">');
  $('evidenceCameraSave').textContent='✔ Gunakan '+cameraEvidence.files.length+' foto';
 },'image/jpeg',.88);}
async function switchEvidenceCamera(){cameraEvidence.facing=cameraEvidence.facing==='environment'?'user':'environment';try{await startEvidenceStream();}catch(e){toast('Tidak dapat mengganti kamera',true);}}
function closeEvidenceCamera(){if(cameraEvidence.stream){cameraEvidence.stream.getTracks().forEach(function(t){t.stop();});cameraEvidence.stream=null;}
 cameraEvidence.urls.forEach(function(u){URL.revokeObjectURL(u);});cameraEvidence.urls=[];cameraEvidence.files=[];
 $('dcoCameraModal').classList.remove('on');$('evidenceCameraVideo').srcObject=null;$('evidenceCameraSave').textContent='✔ Gunakan foto';}
function saveEvidenceCamera(){if(!cameraEvidence.files.length)return toast('Ambil foto terlebih dahulu',true);
 var kind=cameraEvidence.kind,key=cameraEvidence.key,files=cameraEvidence.files.slice();closeEvidenceCamera();return processEvidenceFiles(kind,key,files);}
// Dash Kepatuhan: rows are actual links to their respective modules.
var renderDashBeforeNavFix=renderDash;
renderDash=function(ms,tr){renderDashBeforeNavFix(ms,tr);
 var rows=document.querySelectorAll('#pDash .v6-status-table tbody tr');rows.forEach(function(row){
  var store=row.querySelector('td');if(!store)return;var name=store.textContent.trim(),tabs=['ceklis','dso','MASALAH','jadwal','issues'];
  Array.from(row.cells).slice(1).forEach(function(cell,i){cell.classList.add('evidence-row-action');cell.setAttribute('title','Buka '+tabs[i]+' untuk '+name);
   cell.addEventListener('click',function(){if(tabs[i]==='issues'){goIssues('pending');$('isToko').value=name;loadIssues();}
    else if(tabs[i]==='jadwal'){go('jadwal');$('jdStore').value=name;loadJadwal();}
    else goWith(tabs[i],{toko:name,tanggal:S.dashDate||S.meta.today,periode:'hari'});});
  });
 });};
// Avoid silent wrong-module actions when user navigates with Store privileges.
var goBeforeNavFix=go;
go=function(tab){if($('dcoCameraModal')&&$('dcoCameraModal').classList.contains('on'))closeEvidenceCamera();if(!TITLE[tab])return toast('Menu '+tab+' belum tersedia',true);
 if(S.me&&!isMgr()&&STORE_TABS.indexOf(tab)<0)return toast('Menu '+TITLE[tab]+' hanya tersedia untuk Master / SPV',true);
 return goBeforeNavFix(tab);};
// Show helpful errors instead of swallowing async navigation faults.
window.addEventListener('unhandledrejection',function(e){if(e&&e.reason&&e.reason.message)toast('Gagal memuat menu: '+e.reason.message,true);});
'''

def patch_html(src: str) -> str:
    if MARKER in src:
        return src
    if '</style>' not in src or '</script>\n</body>' not in src:
        raise ValueError('Struktur index.html berubah: tidak menemukan style/script penutup')
    src=src.replace('</style>', CSS+'\n</style>',1)
    src=src.replace('</script>\n</body>',JS+'\n</script>\n'+MODAL+'\n</body>',1)
    return src

if __name__=='__main__':
    p=Path(sys.argv[1])
    p.write_text(patch_html(p.read_text(encoding='utf-8')),encoding='utf-8')
    print('Patched',p)
