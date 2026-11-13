#!/usr/bin/env python3
"""V11 patch: single photo entry point, compact checklist/visiting, short A-E section labels.
Re-runnable and applied after v10 by scripts/build_index.py.
"""
from pathlib import Path
import sys

MARKER = 'DCO_V11_COMPACT_EVIDENCE_AND_SECTIONS'

CSS = r'''
/* DCO_V11_COMPACT_EVIDENCE_AND_SECTIONS */
.visit-seksi-head{min-width:88px;text-align:center!important;white-space:normal!important;vertical-align:middle}
.visit-seksi-head b{font-size:12px;display:block;color:#392e94;line-height:1.2}
.visit-seksi-head small{display:block;font-size:10.5px;text-transform:none;font-weight:650;line-height:1.25;margin-top:3px;color:#64748b;letter-spacing:0}
.evidence-panel,.evidence-panel.compact{display:inline-flex;flex:0 0 auto;width:auto;min-width:0!important;max-width:100%;padding:0!important;margin:0!important;background:transparent!important;border:0!important;box-shadow:none!important;vertical-align:middle}
.photo-chip{display:inline-flex;justify-content:center;align-items:center;gap:8px;min-height:37px;max-width:100%;padding:7px 11px;background:#f6f7ff;border:1px solid #ccd3ff;border-radius:11px;color:#4037bb;cursor:pointer;font-weight:750;font-size:12px;white-space:nowrap;line-height:1.15;transition:border-color .16s,background .16s,transform .16s}
.photo-chip:hover{border-color:#7569eb;background:#eeecff;transform:translateY(-1px)}
.photo-chip:focus-visible{outline:3px solid #c4b5fd;outline-offset:2px}
.photo-chip:disabled{cursor:wait;opacity:.7;transform:none}
.photo-chip b{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:19px;padding:0 5px;border-radius:999px;background:#e1deff;color:#4338ca;font-size:10px}
.photo-chip.has-pictures{background:#ecfdf5;border-color:#9ee7c0;color:#11734e}
.photo-chip.has-pictures b{background:#c9f7df;color:#11734e}
.ckrow{display:grid;grid-template-columns:48px minmax(0,1fr) auto 36px;gap:10px;align-items:center;padding:11px 14px}
.ckrow .cb{width:44px;height:44px;flex-basis:44px;font-size:24px}
.ckrow .t{font-size:14px;line-height:1.35}
.ckrow .ck-evidence{margin:0;justify-self:end}
.ckrow>button:last-child{min-width:34px;justify-self:end}
.ckrow .more{flex-wrap:wrap}
.dsoit{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;padding:13px}
.dsoit>.ph{display:none!important}
.dsoit>.evidence-panel{flex:0 0 auto;min-width:0;margin:0!important}
.dsoit>div[style*="flex:1"]{min-width:0}
.visit-point-photo{flex:0 0 auto!important;min-width:0!important;width:auto!important;max-width:100%;margin-left:4px}
.visit-point-photo .evidence-panel{min-width:0!important;width:auto!important}
.vitem{display:grid;grid-template-columns:33px minmax(0,1fr) 138px auto;gap:9px;align-items:center;padding:10px 0}
.vitem>span{min-width:0!important;line-height:1.4}
.vitem .vopt{margin:0;justify-content:center}
.vitem .vopt button{min-width:36px;min-height:33px;padding:6px 8px}
.visit-issue-fields .evidence-panel{grid-column:auto;width:max-content}
#dcoCameraModal .camera-sheet{width:min(680px,100%);gap:14px}
#dcoCameraModal .hub-title{display:flex;justify-content:space-between;align-items:center;gap:8px}
#dcoCameraModal .hub-description{font-size:12px;color:#64748b;line-height:1.45}
#dcoCameraModal .hub-photos{display:flex;flex-wrap:wrap;gap:8px;min-height:72px;padding:11px;border-radius:13px;border:1px solid #e1e7f1;background:#f8faff;max-height:250px;overflow:auto}
#dcoCameraModal .hub-photos .evidence-empty{align-self:center;font-size:12px}
#dcoCameraModal .hub-photos .evidence-thumb{width:84px;height:84px;flex:0 0 84px}
#dcoCameraModal .hub-photos .evidence-thumb img{width:100%;height:100%;object-fit:cover}
#dcoCameraModal .hub-actions{display:flex;flex-wrap:wrap;gap:9px}
#dcoCameraModal .hub-actions .btn{flex:1 1 150px;min-height:43px;padding:9px 12px;cursor:pointer}
#dcoCameraModal .hub-actions label{display:inline-flex;align-items:center;justify-content:center}
#dcoCameraModal .hub-camera{display:flex;flex-direction:column;gap:9px}
#dcoCameraModal .hub-camera[hidden]{display:none!important}
#dcoCameraModal .hub-status{font-size:12px;color:#6b7280}
#dcoCameraModal .hub-photos .evidence-remove{width:26px;height:26px;line-height:1}
#lb{z-index:120}
@media(max-width:650px){
 .ckrow{grid-template-columns:42px minmax(0,1fr) 36px;gap:8px;padding:10px}
 .ckrow .cb{width:39px;height:39px;flex-basis:39px;font-size:21px}
 .ckrow>.ck-evidence{grid-column:2/3;grid-row:2;justify-self:start}
 .ckrow>button:last-child{grid-column:3;grid-row:1}
 .ckrow .t{font-size:13.5px}
 .dsoit{grid-template-columns:minmax(0,1fr) auto}
 .vitem{grid-template-columns:30px minmax(0,1fr);gap:7px}
 .vitem .vopt{grid-column:2;grid-row:2;justify-content:flex-start}
 .vitem .visit-point-photo{grid-column:2;grid-row:3;margin:0}
 #dcoCameraModal .hub-actions .btn{flex:1 1 125px}
 .visit-seksi-head{min-width:82px}
}
'''

JS = r'''
// DCO_V11_COMPACT_EVIDENCE_AND_SECTIONS: one photo entry button per row.
function visitSeksiSingkat(s){
 var k=String(s&&s.kode||'').toUpperCase();
 var names={A:'Finance',B:'Aset/GA',C:'Merchandise',D:'SDM',E:'Gudang'};
 if(names[k])return names[k];
 var n=String(s&&s.nama||'').trim();return n.length>15?n.slice(0,14)+'…':n;
}
function evidencePanel(kind,key,small){
 key=String(key);var ids=photoList(evidenceId(kind,key)),busy=!!evidenceBusy[kind+':'+key];
 var n=ids.length,access=evidenceLock(kind,key)?'Lihat':'Kelola';
 return '<div class="evidence-panel compact" data-evidence-kind="'+esc(kind)+'" data-evidence-key="'+esc(key)+'">'+
 '<button type="button" class="photo-chip'+(n?' has-pictures':'')+'" data-kind="'+esc(kind)+'" data-key="'+esc(key)+'" onclick="openEvidenceHub(this.dataset.kind,this.dataset.key)" '+(busy?'disabled':'')+
 ' title="'+access+' bukti foto; '+n+' foto tersedia" aria-label="'+access+' bukti foto ('+n+' foto)">'+
 (busy?'⏳':'📷')+' <span>Foto</span><b>'+n+'</b></button></div>';
}
// V10 preserves a full photo list; the compact row only opens the shared gallery.
function renderEvidenceHub(kind,key){
 var modal=$('dcoCameraModal');if(!modal||!modal.classList.contains('on'))return;
 if(kind!=null&&(String(kind)!==cameraEvidence.kind||String(key)!==cameraEvidence.key))return;
 var ids=photoList(evidenceId(cameraEvidence.kind,cameraEvidence.key)),lock=evidenceLock(cameraEvidence.kind,cameraEvidence.key);
 var busy=!!evidenceBusy[cameraEvidence.kind+':'+cameraEvidence.key];
 $('evidenceHubTitle').textContent='Galeri Bukti · '+ids.length+' foto';
 $('evidenceHubGallery').innerHTML=ids.length?ids.map(function(id){return '<div class="evidence-thumb"><img alt="Bukti foto" loading="lazy" src="'+esc(fotoUrl(id,450))+'" data-id="'+esc(id)+'" onclick="lightbox(this)" onerror="fotoFallback(this)">'+
 (!lock&&!busy?'<button type="button" class="evidence-remove" title="Lepas foto" aria-label="Lepas foto" data-id="'+esc(id)+'" onclick="removeEvidencePhoto(cameraEvidence.kind,cameraEvidence.key,this.dataset.id)">×</button>':'')+'</div>';}).join(''):'<span class="evidence-empty">Belum ada foto. Tambahkan melalui kamera atau galeri di bawah.</span>';
 $('evidenceHubActions').hidden=lock;
 $('evidenceHubStatus').textContent=busy?'Mengunggah foto. Jangan tutup jendela ini…':(lock?'Hanya melihat · data sudah divalidasi':'Maksimal '+DCO_EVIDENCE_LIMIT+' foto per item · otomatis dikompres ke WebP');
 var close=$('evidenceHubClose');if(close)close.disabled=busy;
}
var v11UpdateEvidencePanel=updateEvidencePanel;
updateEvidencePanel=function(kind,key){v11UpdateEvidencePanel(kind,key);renderEvidenceHub(kind,key);};
function stopEvidenceCameraStream(){
 if(cameraEvidence.stream){cameraEvidence.stream.getTracks().forEach(function(t){t.stop();});cameraEvidence.stream=null;}
 if($('evidenceCameraVideo'))$('evidenceCameraVideo').srcObject=null;
}
function openEvidenceHub(kind,key){
 if(evidenceBusy[String(kind)+':'+String(key)])return toast('Upload foto masih diproses',true);
 stopEvidenceCameraStream();
 cameraEvidence.urls.forEach(function(u){URL.revokeObjectURL(u);});cameraEvidence.urls=[];cameraEvidence.files=[];
 cameraEvidence.kind=String(kind);cameraEvidence.key=String(key);cameraEvidence.facing='environment';
 $('evidenceCameraPreview').innerHTML='';$('evidenceCameraSave').textContent='✔ Gunakan foto';
 $('evidenceCameraStage').hidden=true;$('dcoCameraModal').classList.add('on');
 renderEvidenceHub();
}
function openEvidenceCamera(kind,key){return openEvidenceHub(kind,key);}
async function startEvidenceHubCamera(){
 if(evidenceLock(cameraEvidence.kind,cameraEvidence.key))return;
 if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)return toast('Kamera live tidak tersedia. Gunakan kamera HP atau galeri.',true);
 $('evidenceCameraStage').hidden=false;
 try{await startEvidenceStream();}catch(e){$('evidenceCameraStage').hidden=true;toast('Kamera tidak tersedia atau izin ditolak. Gunakan kamera HP atau galeri.',true);}
}
function closeEvidenceCamera(){
 if(evidenceBusy[cameraEvidence.kind+':'+cameraEvidence.key])return toast('Foto sedang diunggah',true);
 stopEvidenceCameraStream();cameraEvidence.urls.forEach(function(u){URL.revokeObjectURL(u);});cameraEvidence.urls=[];cameraEvidence.files=[];
 $('evidenceCameraPreview').innerHTML='';$('evidenceCameraStage').hidden=true;
 $('dcoCameraModal').classList.remove('on');$('evidenceCameraSave').textContent='✔ Gunakan foto';
}
async function nativeEvidencePhoto(input){
 var files=Array.from(input.files||[]),kind=cameraEvidence.kind,key=cameraEvidence.key;input.value='';
 if(!files.length)return;await processEvidenceFiles(kind,key,files);renderEvidenceHub();
}
async function saveEvidenceCamera(){
 if(!cameraEvidence.files.length)return toast('Ambil foto terlebih dahulu',true);
 var files=cameraEvidence.files.slice(),kind=cameraEvidence.kind,key=cameraEvidence.key;
 stopEvidenceCameraStream();cameraEvidence.urls.forEach(function(u){URL.revokeObjectURL(u);});cameraEvidence.urls=[];cameraEvidence.files=[];
 $('evidenceCameraPreview').innerHTML='';$('evidenceCameraStage').hidden=true;
 await processEvidenceFiles(kind,key,files);renderEvidenceHub();
}
// Place checklist photo button beside item title, not in a large duplicate panel.
var renderCeklisV10Compact=renderCeklis;
renderCeklis=function(){renderCeklisV10Compact();document.querySelectorAll('#ckIsi .ckrow').forEach(function(row){
 var chip=row.querySelector('.ck-evidence'),more=row.lastElementChild;
 if(chip&&more&&more.tagName==='BUTTON')row.insertBefore(chip,more);
 });};
// DSO uses the same one-button photo control, with no duplicate old photo square.
var renderDsoV10Compact=renderDso;
renderDso=function(){renderDsoV10Compact();document.querySelectorAll('#dsBody .dsoit').forEach(function(row){
 row.querySelectorAll('.m').forEach(function(m){if(/ketuk kotak/i.test(m.textContent))m.textContent='Gunakan tombol Foto untuk kamera atau galeri';});
 });};
'''

MODAL = r'''<div id="dcoCameraModal" role="dialog" aria-modal="true" aria-label="Galeri foto bukti">
 <div class="camera-sheet">
  <div class="hub-title"><strong id="evidenceHubTitle">Galeri Bukti</strong><button type="button" class="btn s" id="evidenceHubClose" onclick="closeEvidenceCamera()">✕ Tutup</button></div>
  <div class="hub-photos" id="evidenceHubGallery"></div>
  <div id="evidenceHubStatus" class="hub-status"></div>
  <div id="evidenceHubActions" class="hub-actions">
   <button type="button" class="btn p" onclick="startEvidenceHubCamera()">📷 Foto langsung</button>
   <label class="btn">📱 Kamera HP<input type="file" accept="image/*" capture="environment" style="display:none" onchange="nativeEvidencePhoto(this)"></label>
   <label class="btn">🖼 Dari galeri<input type="file" accept="image/*" multiple style="display:none" onchange="nativeEvidencePhoto(this)"></label>
  </div>
  <div id="evidenceCameraStage" class="hub-camera" hidden>
   <video id="evidenceCameraVideo" autoplay muted playsinline></video>
   <div class="hub-description">Foto tersimpan terpisah, dikompres otomatis. Klik Ambil foto beberapa kali, kemudian Gunakan foto.</div>
   <div id="evidenceCameraPreview" class="cam-preview"></div>
   <div class="cam-buttons"><button type="button" class="btn p" onclick="captureEvidenceFrame()">📸 Ambil foto</button><button type="button" class="btn" onclick="switchEvidenceCamera()">↻ Ganti kamera</button><button type="button" class="btn g" id="evidenceCameraSave" onclick="saveEvidenceCamera()">✔ Gunakan foto</button></div>
  </div>
 </div>
</div>'''

def patch_html(src: str) -> str:
 if MARKER in src: return src
 if "DCO_V10_CAMERA_GALLERY_PATCH" not in src: raise ValueError("Patch v10 diperlukan sebelum v11")
 old="seksiList().map(function(s){return '<th>'+s.kode+'</th>';}).join('')"
 new="seksiList().map(function(s){return '<th class=\"visit-seksi-head\" title=\"'+esc(s.kode+' - '+s.nama)+'\"><b>'+esc(s.kode)+'</b><small>'+esc(visitSeksiSingkat(s))+'</small></th>';}).join('')"
 if src.count(old)!=1:raise ValueError('Header A-E sumber tidak ditemukan/duplikat')
 src=src.replace(old,new,1)
 # The old modal was full-height by default with three buttons in every item: replace the single modal, not the data/state.
 start=src.find('<div id="dcoCameraModal" role="dialog"')
 end=src.find('</body>',start)
 if start<0 or end<0:raise ValueError('Modal v10 tidak ditemukan')
 modal=src[start:end]
 if modal.count('<div id="dcoCameraModal"')!=1:raise ValueError('Duplikasi modal')
 src=src[:start]+MODAL+'\n\n'+src[end:]
 if src.count('</style>')!=1 or src.count('</script>\n\n<div id="dcoCameraModal"')!=1:raise ValueError('Penutup HTML tidak cocok')
 src=src.replace('</style>',CSS+'\n</style>',1)
 src=src.replace('</script>\n\n<div id="dcoCameraModal"',JS+'\n</script>\n\n<div id="dcoCameraModal"',1)
 return src

if __name__=='__main__':
 p=Path(sys.argv[1]);p.write_text(patch_html(p.read_text(encoding='utf-8')),encoding='utf-8');print('Patched v11',p)
