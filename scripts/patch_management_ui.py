from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=root/'src/main.js'
s=p.read_text()
s=s.replace("uploadEvidence,evidenceUrl,availableStores} from './data.js';", "uploadEvidence,evidenceUrl,availableStores,EXPORT_DATASETS,fetchCompleteRows,maintenanceUsage,maintenancePreview,maintenanceArchive,maintenanceHistory,maintenanceDownloadBatch,maintenancePurge} from './data.js';")
s=s.replace("photoPreview:null,range:'30'};", "photoPreview:null,range:'30',maintenance:{usage:null,history:[],selection:null,preview:null,downloaded:{},message:''}};")
s=s.replace("settings:'⚙'};", "settings:'⚙',maintenance:'▥'};")
needle="function pageSettings(){"
idx=s.index(needle)
page='''const MB=n=>((Number(n)||0)/1024/1024).toFixed(2)+' MB';
const CLEANUP_TABLES=[['issues','Issue tervalidasi'],['checklist_entries','Checklist tervalidasi'],['dso_reports','DSO approved'],['visit_schedules','Jadwal selesai/batal'],['assignments','Assignment selesai 100%']];
const exportStoreOptions=()=>`${opt('all','Semua toko','all')}${availableStores(state.profile).map(s=>opt(s.id,s.name,'all')).join('')}`;
function pageMaintenance(){
 if(!master())return head('Akses ditolak','Menu ini khusus Master.');
 const m=state.maintenance,usage=m.usage||{},r=usage.rows||{};
 const kpis=`<div class="grid-kpis">${metric('Masalah aktif',fmtNumber(r.issues),'Semua status','▤')}${metric('Checklist aktif',fmtNumber(r.checklists),'Tervalidasi & berjalan','☑')}${metric('Arsip database',fmtNumber(r.archive_rows),'Masih memakai ruang DB','▣')}${metric('Foto tersimpan',MB(usage.photo_bytes),'Storage privat','◉')}</div>`;
 const options=Object.entries(EXPORT_DATASETS).map(([id,item])=>opt(id,item.table,id==='issues'?'issues':'')).join('');
 const history=m.history.map(b=>`<tr><td>${esc(b.source_table)}</td><td>${esc(b.store_id||'Semua toko')}</td><td>${prettyDate(b.cutoff_date)}</td><td>${fmtNumber(b.row_count)}</td><td>${status(b.status==='archived'?'Tersimpan':'Dihapus')}</td><td><small title="${esc(b.sha256||'')}">${esc((b.sha256||'').slice(0,12))}…</small></td><td class="actions-cell">${b.status==='archived'?`<button class="btn small" data-action="download-archive" data-batch="${esc(b.batch_id)}">↓ Backup JSONL</button>${m.downloaded[b.batch_id]?`<button class="btn small danger" data-action="purge-archive" data-batch="${esc(b.batch_id)}">Hapus arsip</button>`:''}`:'—'}</td></tr>`).join('')||'<tr><td colspan="7">Belum ada histori arsip.</td></tr>';
 return head('Export, Backup & Manajemen Database','Kontrol penggunaan penyimpanan tanpa menghapus data operasional yang masih aktif.',`<button class="btn outline" data-action="reload-maintenance">↻ Muat ulang</button>`)+kpis+
 `<div class="notice"><b>Perlindungan data:</b> hanya Master boleh arsip atau hapus. Masalah belum selesai, visit, briefing, master data dan foto yang direferensikan tidak akan dihapus oleh mekanisme ini. Arsip masih menggunakan kapasitas DB sampai dibackup dan dipurge. <b>File JSONL/CSV hanya menyimpan alamat/path foto, bukan foto aslinya.</b></div>`+
 `<div class="section-grid even">`+
 panel('Export CSV lengkap','Seluruh baris yang dapat diakses, tidak dibatasi jumlah baris yang tampil di dashboard.',`<div class="panel-body" style="display:grid;gap:13px"><div class="field"><label>Pilih menu/dataset</label><select id="exportDataset">${options}</select></div><div class="field"><label>Toko</label><select id="exportStore">${exportStoreOptions()}</select></div><div class="form-grid"><div class="field"><label>Dari tanggal (opsional)</label><input type="date" id="exportFrom"></div><div class="field"><label>Sampai tanggal (opsional)</label><input type="date" id="exportTo"></div></div><p class="mild">JSON pada form (jawaban, konfigurasi) tetap masuk CSV dalam bentuk teks. ID lama dan foto path dipertahankan.</p><button class="btn primary" data-action="export-dataset">↓ Export CSV semua halaman</button><button class="btn" data-action="backup-all">↓ Backup seluruh dataset (JSONL)</button></div>`)+
 panel('Arsip data selesai','Minimum usia 90 hari, harus selesai/tervalidasi sesuai jenis data.',`<div class="panel-body" style="display:grid;gap:13px"><div class="field"><label>Jenis data yang boleh diarsip</label><select id="archiveTable">${CLEANUP_TABLES.map(([id,label])=>opt(id,label,m.selection?.table||'issues')).join('')}</select></div><div class="field"><label>Toko</label><select id="archiveStore">${opt('all','Semua toko',m.selection?.store||'all')}${availableStores(state.profile).map(st=>opt(st.id,st.name,m.selection?.store||'all')).join('')}</select></div><div class="field"><label>Arsip data sebelum tanggal</label><input id="archiveCutoff" type="date" value="${esc(m.selection?.cutoff||withDate(dateWita(),-180))}"></div><button class="btn" data-action="preview-maintenance">Preview data yang aman diarsip</button>${m.preview?`<div class="notice"><b>${fmtNumber(m.preview.eligible)} baris</b> memenuhi syarat. ${m.preview.eligible>2000?'Perkecil periode atau pilih satu toko.':'Data aktif dan belum tervalidasi tidak termasuk.'}</div><div class="field"><label>Ketik ARSIP DATA SELESAI</label><input id="archivePhrase" autocomplete="off" placeholder="ARSIP DATA SELESAI"></div><button class="btn danger" data-action="archive-maintenance" ${m.preview.eligible<1||m.preview.eligible>2000?'disabled':''}>Arsip sesuai preview</button>`:''}</div>`)+
 `</div>`+
 panel('Histori arsip & penghapusan permanen','Unduh dan verifikasi SHA256 dahulu. Penghapusan permanen hanya berlaku untuk SALINAN arsip sesudah 24 jam.',`<div class="table-wrap"><table class="data-table"><thead><tr><th>Dataset</th><th>Toko</th><th>Sebelum</th><th>Baris</th><th>Status</th><th>SHA256</th><th>Aksi</th></tr></thead><tbody>${history}</tbody></table></div>`)+
 `<div class="notice"><b>Pengelolaan foto:</b> foto otomatis dikompres sebagai WebP ketika diunggah. Pembersihan file foto tidak dilakukan otomatis agar tidak menghilangkan bukti yang masih dipakai. Lakukan audit referensi dan backup foto terpisah sebelum menghapus objek Storage.</div>`;
}
async function loadMaintenance(){if(!master())throw new Error('Khusus Master.');const [usage,history]=await Promise.all([maintenanceUsage(),maintenanceHistory()]);state.maintenance.usage=usage;state.maintenance.history=history;render();}
function downloadText(file,content,type='text/plain;charset=utf-8'){const blob=typeof content==='string'?new Blob([content],{type}):content;const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=file;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),20000);}
async function exportDatasetNow(dataset,filters={}){
 let count=0;toast('Membaca semua halaman data dari Supabase…');
 const records=await fetchCompleteRows(dataset,filters,n=>{count=n;});
 if(!records.length){toast('Dataset tidak memiliki data sesuai filter.',true);return;}
 CSV(records,`tigalapan_${dataset}_${dateWita()}_${records.length}rows.csv`);
 toast(`CSV ${dataset}: ${fmtNumber(count)} baris disiapkan, bukan hanya data yang terlihat di layar.`);
}
async function backupAllDatasets(){if(!master())throw new Error('Hanya Master dapat membuat backup semua dataset.');
 const lines=[JSON.stringify({type:'BACKUP_MANIFEST',application:'Tigalapan Assignment',at:new Date().toISOString(),photo_binaries_included:false,notice:'Foto wajib dibackup terpisah dari Supabase Storage'})];
 for(const dataset of Object.keys(EXPORT_DATASETS)){
  const rows=await fetchCompleteRows(dataset,{},()=>{});
  for(const row of rows)lines.push(JSON.stringify({table:EXPORT_DATASETS[dataset].table,row}));
 }
 const output=lines.join('\\n');
 if('CompressionStream' in window){const compressed=await new Response(new Blob([output]).stream().pipeThrough(new CompressionStream('gzip'))).blob();downloadText(`tigalapan_backup_${dateWita()}.jsonl.gz`,compressed,'application/gzip');}
 else downloadText(`tigalapan_backup_${dateWita()}.jsonl`,output,'application/x-ndjson;charset=utf-8');
 toast('Backup data & konfigurasi diunduh. Backup binary foto tetap harus terpisah.');
}
async function previewMaintenance(){const table=$('archiveTable')?.value,store=$('archiveStore')?.value,cutoff=$('archiveCutoff')?.value;const result=await maintenancePreview(table,cutoff,store);state.maintenance.selection={table,store,cutoff};state.maintenance.preview=result;render();}
async function archiveMaintenance(){const {table,store,cutoff}=state.maintenance.selection||{},p=state.maintenance.preview;const phrase=$('archivePhrase')?.value||'';
 if(phrase!=='ARSIP DATA SELESAI')throw new Error('Tulis kalimat konfirmasi arsip dengan tepat.');
 if(!p||p.eligible<1)throw new Error('Jalankan preview terlebih dahulu.');
 if(!window.confirm(`${p.eligible} baris selesai akan dipindahkan dari data aktif ke arsip database. Lanjutkan?`))return;
 const result=await maintenanceArchive(table,cutoff,store,p.eligible,phrase);
 state.maintenance.preview=null;await refresh();await loadMaintenance();toast(`Berhasil mengarsipkan ${result.archived} baris. Arsip masih aman di database.`);
}
async function downloadArchiveRecord(id){const history=state.maintenance.history.find(x=>x.batch_id===id);if(!history||history.status!=='archived')throw new Error('Arsip tidak ditemukan');
 const data=await maintenanceDownloadBatch(id),digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(data));
 const sha=[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('');
 if(sha!==history.sha256)throw new Error('SHA256 arsip tidak sesuai. File tidak disimpan; jangan hapus!');
 downloadText(`Tigalapan_Archive_${history.source_table}_${id}.jsonl`,data,'application/x-ndjson;charset=utf-8');
 state.maintenance.downloaded[id]=sha;render();toast('SHA256 cocok. Simpan file di penyimpanan eksternal sebelum menghapus arsip.');
}
async function purgeArchiveRecord(id){const record=state.maintenance.history.find(x=>x.batch_id===id),sha=state.maintenance.downloaded[id];
 if(!sha||!record||sha!==record.sha256)throw new Error('Unduh dan verifikasi backup JSONL terlebih dahulu.');
 const phrase=window.prompt('HANYA SETELAH file backup disimpan di tempat lain. Ketik HAPUS ARSIP PERMANEN untuk melanjutkan:');
 if(phrase!=='HAPUS ARSIP PERMANEN')return;
 if(!window.confirm('TINDAKAN PERMANEN: salinan arsip dalam database akan dihapus, tidak bisa dipulihkan tanpa file JSONL. Lanjutkan?'))return;
 const result=await maintenancePurge(id,sha,phrase);delete state.maintenance.downloaded[id];await loadMaintenance();toast(`${result.purged} baris arsip dihapus permanen. Backup eksternal harus disimpan.`);
}
'''
s=s[:idx]+page+s[idx:]
s=s.replace("case'settings':main=pageSettings();break;default:main=overview();", "case'settings':main=pageSettings();break;case'maintenance':main=pageMaintenance();break;default:main=overview();")
s=s.replace("NAV.filter(x=>x[0]!=='settings'||master())", "NAV.filter(x=>!['settings','maintenance'].includes(x[0])||master())")
s=s.replace("function go(page){state.page=page;", "function go(page){state.page=page;")
s=s.replace("window.scrollTo({top:0,behavior:'instant'});}", "window.scrollTo({top:0,behavior:'instant'});if(page==='maintenance')loadMaintenance().catch(e=>toast(e.message,true));}")
s=s.replace("if(a==='export'){exportCurrent();return;}", "if(a==='export'){await exportCurrent();return;}\n if(a==='reload-maintenance'){await loadMaintenance();return;}\n if(a==='preview-maintenance'){await previewMaintenance();return;}\n if(a==='archive-maintenance'){await archiveMaintenance();return;}\n if(a==='export-dataset'){await exportDatasetNow($('exportDataset')?.value,{store:$('exportStore')?.value||'all',from:$('exportFrom')?.value||'',to:$('exportTo')?.value||''});return;}\n if(a==='backup-all'){await backupAllDatasets();return;}\n if(a==='download-archive'){await downloadArchiveRecord(t.dataset.batch);return;}\n if(a==='purge-archive'){await purgeArchiveRecord(t.dataset.batch);return;}")
# Existing page export should use full remote data except summary-scorecard, with manager/Store RLS guaranteed.
s=s.replace("function exportCurrent(){let rows=[];switch(state.page)", "async function exportCurrent(){const dbMap={issues:'issues',pending:'issues',checklist:'checklists',dso:'dso',schedule:'schedules',visits:'visits',assignments:'assignments',compliance:'briefings',settings:'visit_templates'};if(dbMap[state.page]){await exportDatasetNow(dbMap[state.page],{store:state.store,origin:state.page==='pending'?'visit':'',from:['checklist','dso','compliance'].includes(state.page)?state.date:'',to:['checklist','dso','compliance'].includes(state.page)?state.date:''});return;}let rows=[];switch(state.page)")
# pageSettings add CTA to maintenance
s=s.replace("'Seluruh foto disimpan private di Supabase Storage, bukan Google Drive.</div>`+`<div class=\"section-grid even\">", "'Seluruh foto disimpan private di Supabase Storage, bukan Google Drive.</div>`+`<div class=\"section-grid even\">")
p.write_text(s)
# navigation separate small file
p=root/'src/constants.js'
s=p.read_text().replace("['visits','Visiting Check Point','map-pin'],['pending','Pending Matter','flag'],['scorecard','Scorecard','bar-chart'],['settings','Pengaturan','settings']", "['visits','Visiting Check Point','map-pin'],['pending','Pending Matter','flag'],['scorecard','Scorecard','bar-chart'],['maintenance','Export & Penyimpanan','database'],['settings','Pengaturan','settings']")
p.write_text(s)
