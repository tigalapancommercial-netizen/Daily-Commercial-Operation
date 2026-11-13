#!/usr/bin/env python3
"""DCO v12 patch: before/after evidence for Visit Issues and section follow-ups.
Apply after v11 compact photo patch, idempotently. All legacy IDs and photos remain intact.
"""
from pathlib import Path
import sys

MARK = 'DCO_V12_BEFORE_AFTER_EVIDENCE'
CSS = r'''
/* DCO_V12_BEFORE_AFTER_EVIDENCE */
#dcoCameraModal .hub-photos.ba-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;align-items:stretch;max-height:48vh;padding:8px;background:#fff;border:0;overflow:auto}
#dcoCameraModal .ba-group{min-width:0;border-radius:14px;border:1.5px solid #dfe4f0;background:#fafbff;padding:10px;display:flex;flex-direction:column;gap:9px}
#dcoCameraModal .ba-group.active{border-color:#6555ef;box-shadow:0 0 0 2px #eae8ff inset;background:#f7f6ff}
#dcoCameraModal .ba-heading{display:flex;gap:7px;justify-content:space-between;align-items:center;width:100%;text-align:left;background:transparent;border:0;color:#16213c;font-size:13px;font-weight:800;cursor:pointer;padding:3px}
#dcoCameraModal .ba-heading small{color:#64748b;font-weight:650;font-size:11px}
#dcoCameraModal .ba-photos{display:flex;gap:7px;align-items:flex-start;flex-wrap:wrap;min-height:78px;align-content:flex-start}
#dcoCameraModal .ba-photos .evidence-thumb{width:76px;height:76px;flex:0 0 76px}
#dcoCameraModal .ba-empty{font-size:12px;color:#8490a4;line-height:1.5;align-self:center}
#dcoCameraModal .ba-add{width:100%;min-height:34px;padding:6px 9px;background:#fff;border:1px dashed #b2b9d8;border-radius:10px;color:#5146c9;font-size:12px;font-weight:750;cursor:pointer}
#dcoCameraModal .ba-add:hover{background:#edeaff;border-color:#5146c9}
#dcoCameraModal .hub-photos.ba-grid .evidence-remove{z-index:1}
.visit-after-row{display:flex;align-items:center;gap:11px;flex-wrap:wrap;border-radius:10px;background:#f8f9ff;padding:8px 10px;margin-top:8px}
.visit-after-row .mu{font-size:11px}
.ba-inline{display:flex;gap:12px;flex-wrap:wrap;margin-top:7px}
.ba-inline .ba-inline-part{min-width:74px;max-width:45%}
.ba-inline .ba-inline-part strong{font-size:10px;color:#64748b;display:block;margin-bottom:4px}
.visit-issue-card .photo-chip{max-width:100%;white-space:normal}
@media(max-width:650px){
 #dcoCameraModal .hub-photos.ba-grid{grid-template-columns:1fr;max-height:43vh}
 #dcoCameraModal .ba-photos{min-height:52px}
 #dcoCameraModal .ba-photos .evidence-thumb{width:68px;height:68px;flex-basis:68px}
 .visit-after-row{align-items:flex-start}
}
'''
JS = r'''
// DCO_V12_BEFORE_AFTER_EVIDENCE. One compact entry; two independent photo sets.
var evidenceIdBeforeAfterOriginal=evidenceId;
evidenceId=function(kind,key){
 key=String(key);
 if(kind==='issueAfter')return S.issueAfterTemp||'';
 if(kind==='visitIssueAfter')return S.vis&&S.vis.issuesList&&S.vis.issuesList[+key]&&S.vis.issuesList[+key].fotoAfter||'';
 if(kind==='visitUpdate')return S.vis&&S.vis.foto&&S.vis.foto['UPDATE_'+key]||'';
 return evidenceIdBeforeAfterOriginal(kind,key);
};
var evidenceLockBeforeAfterOriginal=evidenceLock;
evidenceLock=function(kind,key){
 if(kind==='issue'||kind==='issueAfter')return !!(S.issueEditingItem&&S.issueEditingItem.validasi==='Y'&&!isMaster());
 if(kind==='visitIssueAfter')return evidenceLockBeforeAfterOriginal('visitIssue',key);
 if(kind==='visitUpdate')return !S.vis||!!S.vis._view;
 return evidenceLockBeforeAfterOriginal(kind,key);
};
var evidenceStateSaveBeforeAfterOriginal=evidenceStateSave;
evidenceStateSave=function(kind,key,packed){
 if(kind==='issueAfter'){S.issueAfterTemp=packed;return Promise.resolve();}
 if(kind==='visitIssueAfter'){
  var item=S.vis&&S.vis.issuesList&&S.vis.issuesList[+key];
  if(!item)return Promise.reject(new Error('Issue Visit tidak ditemukan'));
  item.fotoAfter=packed;return Promise.resolve();
 }
 if(kind==='visitUpdate'){
  if(!S.vis)return Promise.reject(new Error('Visit tidak ditemukan'));
  S.vis.foto=S.vis.foto||{};S.vis.foto['UPDATE_'+String(key)]=packed;return Promise.resolve();
 }
 return evidenceStateSaveBeforeAfterOriginal(kind,key,packed);
};
function afterKind(base){return base==='issue'?'issueAfter':'visitIssueAfter';}
var evidencePanelBeforeAfterOriginal=evidencePanel;
evidencePanel=function(kind,key,small){
 if(kind!=='issuePair'&&kind!=='visitIssuePair')return evidencePanelBeforeAfterOriginal(kind,key,small);
 key=String(key);var base=kind==='issuePair'?'issue':'visitIssue',a=photoList(evidenceId(base,key)).length,b=photoList(evidenceId(afterKind(base),key)).length;
 var busy=!!evidenceBusy[base+':'+key]||!!evidenceBusy[afterKind(base)+':'+key];
 return '<div class="evidence-panel compact" data-evidence-kind="'+kind+'" data-evidence-key="'+esc(key)+'">'+
 '<button type="button" class="photo-chip'+((a+b)?' has-pictures':'')+'" data-key="'+esc(key)+'" onclick="openBeforeAfterHub(\''+base+'\',this.dataset.key)" '+(busy?'disabled':'')+' aria-label="Buka perbandingan foto sebelum dan sesudah">'+
 (busy?'⏳':'📷')+' <span>Before / After</span><b>'+a+' / '+b+'</b></button></div>';
};
var openEvidenceHubBeforeAfterOriginal=openEvidenceHub;
openEvidenceHub=function(kind,key){
 cameraEvidence.pairBase='';cameraEvidence.pairKey='';cameraEvidence.pairPhase='';
 return openEvidenceHubBeforeAfterOriginal(kind,key);
};
function openBeforeAfterHub(base,key){
 key=String(key);openEvidenceHub(base,key);
 cameraEvidence.pairBase=base;cameraEvidence.pairKey=key;cameraEvidence.pairPhase='after';
 cameraEvidence.kind=afterKind(base);cameraEvidence.key=key;
 renderEvidenceHub();
}
function selectBeforeAfterPhase(phase){
 if(!cameraEvidence.pairBase)return;
 if(evidenceBusy[cameraEvidence.kind+':'+cameraEvidence.key])return toast('Upload masih berlangsung',true);
 if(cameraEvidence.files&&cameraEvidence.files.length){if(!confirm('Foto kamera belum disimpan. Ganti kelompok foto?'))return;
  cameraEvidence.urls.forEach(function(url){URL.revokeObjectURL(url);});cameraEvidence.urls=[];cameraEvidence.files=[];
  $('evidenceCameraPreview').innerHTML='';$('evidenceCameraSave').textContent='✔ Gunakan foto';}
 stopEvidenceCameraStream();$('evidenceCameraStage').hidden=true;
 cameraEvidence.pairPhase=phase;cameraEvidence.kind=phase==='before'?cameraEvidence.pairBase:afterKind(cameraEvidence.pairBase);
 renderEvidenceHub();
}
var renderEvidenceHubBeforeAfterOriginal=renderEvidenceHub;
renderEvidenceHub=function(kind,key){
 if(!cameraEvidence.pairBase)return renderEvidenceHubBeforeAfterOriginal(kind,key);
 var modal=$('dcoCameraModal');if(!modal||!modal.classList.contains('on'))return;
 var base=cameraEvidence.pairBase,k=cameraEvidence.pairKey,before=photoList(evidenceId(base,k)),after=photoList(evidenceId(afterKind(base),k));
 var busy=!!evidenceBusy[base+':'+k]||!!evidenceBusy[afterKind(base)+':'+k];
 var lock=evidenceLock(base,k),phase=cameraEvidence.pairPhase;
 $('evidenceHubTitle').textContent='Perbandingan Foto · Before / After';
 function group(title,photos,groupPhase){
  var kind=groupPhase==='before'?base:afterKind(base),active=phase===groupPhase;
  return '<section class="ba-group'+(active?' active':'')+'" data-photo-phase="'+groupPhase+'">'+
   '<button type="button" class="ba-heading" onclick="selectBeforeAfterPhase(\''+groupPhase+'\')"><span>'+title+'</span><small>'+photos.length+' foto '+(active?'· dipilih':'')+'</small></button>'+
   '<div class="ba-photos">'+(photos.length?photos.map(function(id){
    return '<div class="evidence-thumb"><img alt="'+title+'" loading="lazy" src="'+esc(fotoUrl(id,450))+'" data-id="'+esc(id)+'" onclick="lightbox(this)" onerror="fotoFallback(this)">'+
      (!lock&&!busy?'<button class="evidence-remove" type="button" title="Lepas foto" data-kind="'+kind+'" data-key="'+esc(k)+'" data-id="'+esc(id)+'" onclick="removeEvidencePhoto(this.dataset.kind,this.dataset.key,this.dataset.id)">×</button>':'')+'</div>';}).join(''):'<span class="ba-empty">Belum ada foto '+(groupPhase==='before'?'awal':'hasil perbaikan')+'</span>')+'</div>'+
   (!lock?'<button type="button" class="ba-add" onclick="selectBeforeAfterPhase(\''+groupPhase+'\')">'+(active?'✓ Tambah ke '+title:'＋ Pilih '+title)+'</button>':'')+'</section>';
 }
 $('evidenceHubGallery').classList.add('ba-grid');
 $('evidenceHubGallery').innerHTML=group('SEBELUM · Kondisi awal',before,'before')+group('SESUDAH · Foto update',after,'after');
 $('evidenceHubActions').hidden=lock;
 $('evidenceHubStatus').textContent=busy?'Mengunggah foto… jangan tutup.':
   lock?'Hanya melihat · issue telah divalidasi.':
   'Tujuan unggah: '+(phase==='after'?'SESUDAH (foto update)':'SEBELUM (kondisi awal)')+'. Foto tetap terpisah dan dikompres otomatis. Simpan form agar perubahan tercatat.';
 $('evidenceHubClose').disabled=busy;
};
var closeEvidenceCameraBeforeAfterOriginal=closeEvidenceCamera;
closeEvidenceCamera=function(){closeEvidenceCameraBeforeAfterOriginal();
 if(!$('dcoCameraModal').classList.contains('on')){
  cameraEvidence.pairBase='';cameraEvidence.pairKey='';cameraEvidence.pairPhase='';
  $('evidenceHubGallery').classList.remove('ba-grid');}
};
var updateEvidencePanelBeforeAfterOriginal=updateEvidencePanel;
updateEvidencePanel=function(kind,key){
 updateEvidencePanelBeforeAfterOriginal(kind,key);
 if(cameraEvidence.pairBase){renderEvidenceHub();
  var selector=cameraEvidence.pairBase==='issue'?'issuePair':'visitIssuePair';
  document.querySelectorAll('[data-evidence-kind="'+selector+'"]').forEach(function(el){el.outerHTML=evidencePanel(selector,el.dataset.evidenceKey,true);});}
};
// Evidence update is stored only after Save Visit / Save Issue, not on file-picker close.
var editVisitIssueBeforeAfterOriginal=editVisitIssue;
editVisitIssue=function(index){
 var item=S.issues&&S.issues[index];if(!item)return toast('Issue tidak ditemukan',true);
 S.issueEditingItem=item;S.issueFotoTemp=item.fotoId||'';S.issueAfterTemp=item.fotoAfter||'';
 var fields=[
  {k:'issue',l:'Temuan / Masalah',v:item.issue||'',full:1},
  {k:'akar',l:'Akar penyebab',t:'area',full:1,v:item.akar||''},
  {k:'action',l:'Action Plan *',t:'area',full:1,v:item.action||''},
  {k:'pic',l:'PIC *',v:item.pic||''},
  {k:'dueDate',l:'Due Date *',t:'date',v:item.dueDate||''},
  {k:'prioritas',l:'Prioritas',t:'sel',o:cfg().prioritas,v:item.prioritas||'Sedang'},
  {k:'status',l:'Status',t:'sel',o:['Open','On Progress','Pending','Selesai','Dibatalkan'],v:item.status||'Open'},
  {k:'progress',l:'Progress (%)',t:'number',v:item.progress||0},
  {k:'updateNote',l:'Catatan hasil perbaikan / update',t:'area',full:1,v:item.updateNote||''}];
 var locked=item.validasi==='Y'&&!isMaster();
 gen('Tindak Lanjut · '+item.id+(locked?' (sudah divalidasi)':''),fields,function(d){
  if(!d.action.trim()||!d.pic.trim()||!d.dueDate){toast('Action Plan, PIC dan Due Date wajib',true);return;}
  var button=$('gSave');button.disabled=true;
  d.id=item.id;d.fotoId=S.issueFotoTemp;d.fotoAfter=S.issueAfterTemp;
  call('issueUpdate',{data:d}).then(function(){closeM('mGen');toast('Issue dan foto before–after tersimpan','ok');loadIssues();},function(e){toast(e&&e.message||'Gagal menyimpan issue',true);})
   .finally(function(){button.disabled=false;});
 },locked);
 $('gBody').insertAdjacentHTML('beforeend',
  '<div class="full"><span class="lbl">Dokumentasi perbaikan · Before / After</span>'+evidencePanel('issuePair','main')+
  '<p class="mu" style="margin-top:7px">Foto awal tetap ada. Tambahkan foto update pada kelompok Sesudah, kemudian tekan Simpan.</p></div>');
};
// Visiting form: a single pair-gallery button per issue. After-photo by section is also available.
var renderVisitBeforeAfterOriginal=renderVisit;
renderVisit=function(){
 renderVisitBeforeAfterOriginal();if(!S.vis)return;
 document.querySelectorAll('#vBody .visit-issue-card').forEach(function(node,i){
  var p=node.querySelector('[data-evidence-kind="visitIssue"]');
  if(p)p.outerHTML=evidencePanel('visitIssuePair',i,true);
  var parent=node.querySelector('.visit-issue-fields > div:last-child');
  if(parent){var label=parent.querySelector('label');if(label)label.childNodes[0].textContent='Foto awal / update ';}
 });
 if(!S.vis.id)return;
 var sections=seksiList();
 document.querySelectorAll('#vBody .vsec').forEach(function(section,i){
  var note=section.querySelector('textarea[onchange*="updateTemuan"]');
  if(!note||!sections[i])return;
  note.parentElement.insertAdjacentHTML('beforeend','<div class="visit-after-row">'+
   '<strong style="font-size:12px">Foto hasil update · '+esc(sections[i].kode)+'</strong>'+evidencePanel('visitUpdate',sections[i].kode,true)+
   '<span class="mu">Kondisi awal ada pada foto point di atas. Simpan Visit setelah menambahkan foto.</span></div>');
 });
};
var renderIssuesBeforeAfterOriginal=renderIssues;
renderIssues=function(){
 renderIssuesBeforeAfterOriginal();
 document.querySelectorAll('#issueTbl tbody tr').forEach(function(tr,i){
  var issue=S.issues&&S.issues[i];if(!issue||!tr.cells||tr.cells.length<4)return;
  var col=tr.cells[3];col.querySelectorAll('img.thumb').forEach(function(img){img.remove();});
  var a=photoList(issue.fotoId),b=photoList(issue.fotoAfter);
  col.insertAdjacentHTML('beforeend','<div class="ba-inline"><div class="ba-inline-part"><strong>SEBELUM</strong>'+(a.length?thumbs(a.slice(0,3),38):'<small class="mu">—</small>')+'</div>'+ 
    '<div class="ba-inline-part"><strong>SESUDAH</strong>'+(b.length?thumbs(b.slice(0,3),38):'<small class="mu">Belum ada update</small>')+'</div></div>');
 });
};
'''

def patch_html(src: str) -> str:
    if MARK in src:
        return src
    if 'DCO_V11_COMPACT_EVIDENCE_AND_SECTIONS' not in src:
        raise ValueError('Patch v11 harus dipasang sebelum v12')
    if src.count('</style>') != 1 or src.count('</script>\n\n<div id="dcoCameraModal"') != 1:
        raise ValueError('Penutup HTML atau panel v11 tidak ditemukan')
    src = src.replace('</style>', CSS + '\n</style>', 1)
    src = src.replace('</script>\n\n<div id="dcoCameraModal"', JS + '\n</script>\n\n<div id="dcoCameraModal"', 1)
    # Previous v10 toast must treat photo updates as pending form changes.
    src = src.replace("['form','issue','point','seksi','visitIssue'].indexOf(kind)",
                      "['form','issue','issueAfter','point','seksi','visitIssue','visitIssueAfter','visitUpdate'].indexOf(kind)",1)
    return src

if __name__ == '__main__':
    p=Path(sys.argv[1]);p.write_text(patch_html(p.read_text(encoding='utf8')),encoding='utf8')
    print('Patched v12:',p)
