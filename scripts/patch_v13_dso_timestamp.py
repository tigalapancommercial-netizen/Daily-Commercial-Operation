"""v13: DSO submit validation, reliable photo upload status and camera watermark."""

PATCH_JS = r'''
/* DCO_V13_DSO_CAMERA_AUDIT: UI-only checks + WITA mark for direct camera shots.
   Source of truth for upload receipts remains the Supabase server. */
(function(){
  var sending=false;
  function defNow(){return (window.__dcoServerNow&&Number(window.__dcoServerNow()))||Date.now();}
  function formatWita(ms){
    return new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Makassar',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(ms));
  }
  function pendingUpload(){return Object.keys(evidenceBusy).some(function(k){return k.startsWith('dso:')&&evidenceBusy[k];});}
  function dsoMissing(){return (S.meta&&S.meta.formDef||[]).filter(function(d){return d.form===S.dsForm&&d.aktif!=='N'&&d.wajib!=='N'&&!photoList(S.dsJaw[d.id]).length;});}
  function inlineNotice(message,isError){
    var body=$('dsBody');if(!body)return;
    var current=body.querySelector('#dcoDsoSubmitFeedback');if(!current){current=document.createElement('div');current.id='dcoDsoSubmitFeedback';current.setAttribute('role','status');
      var items=body.querySelectorAll('.dsoit'),last=items.length?items[items.length-1]:null;if(last)last.insertAdjacentElement('afterend',current);else body.appendChild(current);}
    current.textContent=message;current.className=isError?'dco-dso-warning':'dco-dso-success';
  }
  function markMissing(ids){
    var rows=document.querySelectorAll('#dsBody .dsoit');var defs=(S.meta&&S.meta.formDef||[]).filter(function(d){return d.form===S.dsForm&&d.aktif!=='N';});
    rows.forEach(function(row,i){var missing=defs[i]&&ids.indexOf(defs[i].id)!==-1;row.classList.toggle('dco-missing-photo',!!missing);});
  }
  function errorText(err){return String(err&&err.message||err||'Gagal menyimpan laporan');}
  // The server must validate every multi-photo ID. The old SQL discarded invalid items silently.
  dsoKirim=async function(){
    if(sending)return;
    if(pendingUpload()){inlineNotice('Masih ada foto yang sedang diunggah. Selesaikan upload sebelum submit.',true);toast('Tunggu foto selesai diunggah',true);return;}
    var incomplete=dsoMissing();
    if(incomplete.length){
      markMissing(incomplete.map(function(d){return d.id;}));
      var msg='Foto wajib belum lengkap: '+incomplete.map(function(d){return d.label;}).join(', ')+'. Buka tombol Foto pada item yang ditandai.';
      inlineNotice(msg,true);toast('Lengkapi '+incomplete.length+' item foto wajib',true);
      var first=$('dsBody').querySelector('.dco-missing-photo');if(first)first.scrollIntoView({behavior:'smooth',block:'center'});return;
    }
    var jaw={};(S.meta.formDef||[]).filter(function(d){return d.form===S.dsForm&&d.aktif!=='N';}).forEach(function(d){
      var photos=photoList(S.dsJaw[d.id]);if(photos.length)jaw[d.id]=photoPack(photos);
    });
    var submitBtns=Array.from(document.querySelectorAll('#dsBody button[onclick*="dsoKirim"]'));
    submitBtns.forEach(function(b){b.disabled=true;b.dataset.priorText=b.textContent;b.textContent='⏳ Menyimpan & memeriksa foto…';});
    sending=true;markMissing([]);inlineNotice('Memverifikasi '+Object.keys(jaw).length+' item foto ke server…',false);
    try{
      var data=await call('dsoSubmit',{form:S.dsForm,tanggal:$('dsTgl').value,toko:$('dsToko').value,
        jawaban:jaw,oleh:$('dsOleh').value,keterangan:$('dsKet').value});
      toast('Laporan '+formById(data.form).nama+' tersimpan · '+data.slaSubmit,'ok');S.dsJaw={};await loadDso();loadNotif();
    }catch(err){
      var m=errorText(err);if(/Foto wajib belum lengkap|ID foto/i.test(m)){
        inlineNotice(m+' — Jika foto sudah muncul semua, kemungkinan SQL validasi multi-foto belum diperbarui. Jalankan migrasi 010.',true);
      }else inlineNotice('Gagal mengirim: '+m,true);
      // Keep every selected/uploaded photo in local state; never silently clear it on failed submit.
    }finally{
      sending=false;submitBtns.forEach(function(b){if(b.isConnected){b.disabled=false;b.textContent=b.dataset.priorText||'Kirim laporan';}});
    }
  };
  function refreshDsoCounter(){
    var body=$('dsBody');if(!body||!S.meta||!S.dsJaw)return;
    var defs=S.meta.formDef.filter(function(d){return d.form===S.dsForm&&d.aktif!=='N';});
    var filled=defs.filter(function(d){return photoList(S.dsJaw[d.id]).length>0;}).length;
    var big=body.querySelector('.ckhead .big'),bar=body.querySelector('.ckhead .bar i');
    if(big)big.innerHTML=filled+'<span class="mu" style="font-size:16px">/'+defs.length+'</span>';
    if(bar)bar.style.width=Math.round(100*filled/Math.max(1,defs.length))+'%';
    body.querySelectorAll('.dsoit').forEach(function(row,i){
      var d=defs[i];if(d){var present=photoList(S.dsJaw[d.id]).length>0;row.classList.toggle('dco-photo-filled',present);if(present)row.classList.remove('dco-missing-photo');}
    });
    var feedback=body.querySelector('#dcoDsoSubmitFeedback');
    if(feedback&&feedback.textContent.indexOf('Buka tombol Foto pada item yang ditandai')>=0&&dsoMissing().length===0)feedback.remove();
  }
  var prevUpdate=updateEvidencePanel;
  updateEvidencePanel=function(kind,key){prevUpdate.apply(this,arguments);if(kind==='dso')refreshDsoCounter();};
  var originalRender=renderDso;
  renderDso=function(){originalRender.apply(this,arguments);
    if(S.dsMode!=='isi'||!S.dsJaw)return;
    var rows=$('dsBody')&&$('dsBody').querySelectorAll('.dsoit');
    var defs=S.meta&&S.meta.formDef&&S.meta.formDef.filter(function(d){return d.form===S.dsForm&&d.aktif!=='N';})||[];
    if(rows)rows.forEach(function(row,i){var d=defs[i];if(!d)return;row.classList.toggle('dco-photo-filled',photoList(S.dsJaw[d.id]).length>0);var desc=row.querySelector('div[style*=\"flex:1\"]');if(desc)desc.classList.add('dso-desc');});
  };
  // On the LIVE camera only, stamp actual pixels BEFORE converting/uploading.
  // A watermark alone does not prove authenticity; the Storage object creation time
  // is independently recorded by Supabase in dco.photo_receipts.
  function watermarkPhoto(canvas){
    var ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
    var px=Math.max(18,Math.round(w*.026)), small=Math.max(13,Math.round(w*.018));
    var pad=Math.max(12,Math.round(w*.02)),lh=Math.round(px*1.5),height=lh+Math.round(small*1.5)+pad*2;
    ctx.fillStyle='rgba(8,20,34,0.82)';ctx.fillRect(0,h-height,w,height);
    ctx.textBaseline='top';ctx.fillStyle='#fff';ctx.font='bold '+px+'px system-ui, sans-serif';
    var stamp='KAMERA LIVE  •  '+formatWita(defNow())+' WITA';
    ctx.fillText(stamp,pad,h-height+pad,w-2*pad);
    ctx.fillStyle='#d9e9fc';ctx.font=small+'px system-ui, sans-serif';
    var store=S.me&&S.me.toko&&S.me.toko!=='SEMUA'?S.me.toko:'SPV / MASTER';
    var context=String(cameraEvidence.kind||'FOTO')+' · '+String(cameraEvidence.key||'');
    ctx.fillText(store+'   |   '+context,pad,h-height+pad+lh,w-2*pad);
  }
  captureEvidenceFrame=function(){
    var v=$('evidenceCameraVideo');if(!v||!v.videoWidth)return toast('Kamera belum siap. Periksa izin kamera.',true);
    var already=photoList(evidenceId(cameraEvidence.kind,cameraEvidence.key)).length;
    if((cameraEvidence.files.length+already)>=DCO_EVIDENCE_LIMIT)return toast('Batas '+DCO_EVIDENCE_LIMIT+' foto per item',true);
    var c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;
    c.getContext('2d').drawImage(v,0,0,c.width,c.height);watermarkPhoto(c);
    c.toBlob(function(blob){
      if(!blob)return toast('Gagal mengambil foto',true);
      var file=new File([blob],'dco_live_'+Date.now()+'.webp',{type:'image/webp'});file.__dcoCaptureSource='kamera_live';
      cameraEvidence.files.push(file);
      var u=URL.createObjectURL(file);cameraEvidence.urls.push(u);
      $('evidenceCameraPreview').insertAdjacentHTML('beforeend','<img alt="Foto kamera berstempel waktu WITA" src="'+u+'">');
      $('evidenceCameraSave').textContent='✔ Gunakan '+cameraEvidence.files.length+' foto';
    },'image/webp',.85);
  };
  var originalStartHub=startEvidenceHubCamera;
  startEvidenceHubCamera=async function(){
    if(window.__dcoSyncClock){
      try{await window.__dcoSyncClock();}catch(err){
        toast('Waktu server tidak dapat diverifikasi. Pastikan internet aktif sebelum foto langsung.',true);return;
      }
    }
    return originalStartHub.apply(this,arguments);
  };
  // Native camera file pickers are not cryptographic proof of live capture.
  nativeEvidencePhoto=async function(input){
    var files=Array.from(input.files||[]),kind=cameraEvidence.kind,key=cameraEvidence.key;
    var mode=input.hasAttribute('capture')?'kamera_hp':'galeri';input.value='';
    files.forEach(function(f){f.__dcoCaptureSource=mode;});
    if(!files.length)return;
    await processEvidenceFiles(kind,key,files);renderEvidenceHub();
  };
  handleEvidenceInput=function(input){
    var files=Array.from(input.files||[]),kind=input.dataset.kind,key=input.dataset.key;
    var mode=input.hasAttribute('capture')?'kamera_hp':'galeri';input.value='';
    files.forEach(function(f){f.__dcoCaptureSource=mode;});
    return processEvidenceFiles(kind,key,files);
  };
  // Tap a photo to see an independently recorded Supabase receipt (for new photos).
  var lightboxOriginal=lightbox;
  var photoProofSequence=0;
  lightbox=function(img){
    lightboxOriginal.apply(this,arguments);
    var target=$('lb'),id=img&&img.dataset&&img.dataset.id;
    if(!target)return;
    var el=$('dcoPhotoProof');if(!el){el=document.createElement('div');el.id='dcoPhotoProof';el.className='dco-photo-proof';el.addEventListener('click',function(e){e.stopPropagation();});target.appendChild(el);}
    var seq=++photoProofSequence;
    el.textContent='Membaca catatan waktu server…';
    if(!id||!validId(id)){el.textContent='Pratinjau lokal · belum diunggah';return;}
    call('fotoReceipt',{id:id},true).then(function(r){if(seq!==photoProofSequence)return;
      if(!r||!r.verified){el.textContent='Foto lama · belum memiliki catatan audit server';return;}
      var when=new Date(r.uploadedAt);var time=new Intl.DateTimeFormat('id-ID',{
        timeZone:'Asia/Makassar',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false
      }).format(when);
      var label=r.source==='kamera_live'?'Kamera live':r.source==='kamera_hp'?'Kamera HP':'Galeri';
      el.textContent='● Diterima server: '+time+' WITA · '+label+' · SHA-256: '+String(r.checksum||'').slice(0,12)+'…';
    }).catch(function(){if(seq===photoProofSequence)el.textContent='Catatan audit belum dapat dibaca';});
  };
  // Preserve camera source tags through the existing multi-photo processing pipeline.
})();
'''

PATCH_CSS = r'''
/* v13: visible DSO save diagnostics and compact, tap-friendly photo actions */
#dsBody .dco-dso-warning{margin:12px 0;padding:12px 14px;border:1px solid #fca5a5;border-radius:12px;background:#fff1f2;color:#9f1239;font-size:13px;line-height:1.5}
#dsBody .dco-dso-success{margin:12px 0;padding:12px 14px;border:1px solid #a5b4fc;border-radius:12px;background:#eef2ff;color:#3730a3;font-size:13px;line-height:1.5}
#dsBody .dsoit.dco-missing-photo{border-color:#ef4444;background:#fff5f5;box-shadow:0 0 0 2px #fee2e2}
#dsBody .dsoit.dco-photo-filled .photo-chip{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
#dcoCameraModal .cam-preview img{object-fit:contain}
.dco-photo-proof{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);max-width:min(96vw,940px);background:rgba(11,20,38,.9);padding:9px 14px;border-radius:12px;color:#f8fafc;font-size:12px;line-height:1.45;text-align:center;cursor:default;z-index:31;word-wrap:break-word}
@media(max-width:600px){#dsBody .dsoit{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:9px;padding:13px}
 #dsBody .dsoit>.evidence-panel{grid-column:2;grid-row:1;margin:0;flex:unset;width:auto}
 #dsBody .dsoit>.dso-desc{grid-column:1;grid-row:1;min-width:0}
 #dsBody .dsoit .photo-chip{min-width:96px;max-width:135px}}
'''


def patch_html(html: str) -> str:
    if 'DCO_V13_DSO_CAMERA_AUDIT' in html:
        return html
    target = "var sent=await call('uploadFoto',{dataUrl:data,nama:kind+'_'+Date.now()},true);"
    repl = "var sent=await call('uploadFoto',{dataUrl:data,nama:kind+'_'+Date.now(),captureSource:files[i].__dcoCaptureSource||'galeri',context:kind+':'+key},true);"
    if html.count(target) != 1:
        raise RuntimeError('Multi-photo upload call not found exactly once')
    html = html.replace(target, repl)
    if '</style>' not in html or '</body>' not in html:
        raise RuntimeError('Invalid HTML document')
    html=html.replace('</style>',PATCH_CSS+'\n</style>',1)
    html=html.replace('</body>', '<script>\n'+PATCH_JS+'\n</script>\n</body>', 1)
    return html
