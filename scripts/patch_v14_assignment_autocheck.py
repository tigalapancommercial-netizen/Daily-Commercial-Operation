"""v14: automatically finish an Assignment Checklist after photo evidence is persisted.

Preserves all existing modules and does not change SQL schema.
"""
PATCH_JS = r'''// DCO_V14_ASSIGNMENT_AUTO_CHECK
(function(){
  // Do not use the legacy ckSend for auto-completion: it catches and swallows
  // backend failures, which can incorrectly make photo upload look successful.
  var previousEvidenceStateSave = evidenceStateSave;
  evidenceStateSave = function(kind, key, packed, allUploadsSucceeded){
    if(kind !== 'ck') return previousEvidenceStateSave.apply(this, arguments);
    var i = Number(key), row = S.ckRows && S.ckRows[i];
    if(!Number.isInteger(i) || !row) return Promise.reject(new Error('Checklist tidak tersedia; buka ulang tanggal/toko.'));
    if(evidenceLock('ck', String(i))) return Promise.reject(new Error('Checklist sudah divalidasi dan dikunci.'));
    var oldPhotos = photoList(row.fotoId), nextPhotos = photoList(packed);
    // Adding photo(s) automatically completes; simply opening gallery or
    // removing evidence must not change the checkmark.
    var added = nextPhotos.some(function(p){return oldPhotos.indexOf(p) < 0;});
    var shouldComplete = added && row.status !== 'Selesai' && allUploadsSucceeded !== false;
    var tanggal = $('ckTgl').value, toko = $('ckToko').value;
    var request = {id:row.id || '', rutinId:row.rutinId, judul:row.judul,
      tanggal:tanggal, toko:toko, fotoId:photoPack(nextPhotos)};
    if(shouldComplete) request.status = true;
    return call('ceklisSet', request, true).then(function(saved){
      if(!saved || photoPack(photoList(saved.fotoId)) !== photoPack(nextPhotos)){
        throw new Error('Foto belum dikonfirmasi tersimpan pada checklist oleh server.');
      }
      if(shouldComplete && saved.status !== 'Selesai'){
        throw new Error('Foto terunggah, tetapi status checklist belum berhasil diubah menjadi Selesai.');
      }
      // Avoid mutating another store/date row if the user navigated during upload.
      if(S.ckRows && S.ckRows[i] === row && $('ckTgl').value === tanggal && $('ckToko').value === toko){
        ['id','status','jam','catatan','fotoId','validasi','validasiOleh'].forEach(function(k){
          if(Object.prototype.hasOwnProperty.call(saved,k)) row[k]=saved[k];
        });
        renderCeklis();
      }
      loadNotif();
      if(shouldComplete) toast('Bukti foto tersimpan; checklist otomatis Selesai dan tercentang.','ok');
      return saved;
    });
  };
  // A manual tap while evidence is still uploading must not race the auto-save.
  var toggleBeforeAutoCheck = ckToggle;
  ckToggle = function(i){
    if(evidenceBusy['ck:'+i]) return toast('Foto masih diunggah; tunggu sampai checklist otomatis tercentang.',true);
    return toggleBeforeAutoCheck.apply(this,arguments);
  };
})();
'''

def patch_html(html: str) -> str:
    if 'DCO_V14_ASSIGNMENT_AUTO_CHECK' in html:
        return html
    if 'DCO_V13_DSO_CAMERA_AUDIT' not in html:
        raise ValueError('v14 requires v13 base code')
    if '</body>' not in html:
        raise ValueError('missing closing HTML body')
    save_call = 'await evidenceStateSave(kind,key,photoPack(result));toast('
    if html.count(save_call) != 1:
        raise ValueError('Multi-photo save path not found')
    html = html.replace(save_call, 'await evidenceStateSave(kind,key,photoPack(result),failed===0);toast(', 1)
    partial_msg = "(failed?' · '+failed+' gagal':'')"
    if html.count(partial_msg) != 1:
        raise ValueError('Upload failure message not found')
    html = html.replace(partial_msg, "(failed?(kind==='ck'?' · '+failed+' gagal; status checklist tidak berubah':' · '+failed+' gagal'):'')", 1)
    html = html.replace('</style>', '\n/* v14: a validated/locked photo hub must not show upload actions */\n#dcoCameraModal .hub-actions[hidden]{display:none!important}\n</style>', 1)
    return html.replace('</body>', '<script>\n' + PATCH_JS + '\n</script>\n</body>', 1)
