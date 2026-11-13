/* DCO v18: unified history and Campaign Management. Uses the existing Supabase DCO bridge. */
(function(){
'use strict';
const by=id=>document.getElementById(id);
const dateOk=v=>{const x=String(v||'');if(!/^\d{4}-\d{2}-\d{2}$/.test(x))return false;const d=new Date(x+'T00:00:00Z');return !Number.isNaN(d.getTime())&&d.toISOString().slice(0,10)===x;};
const money=v=>'Rp '+Math.round(Number(v)||0).toLocaleString('id-ID');
const num=v=>(Number(v)||0).toLocaleString('id-ID');
const cap=v=>String(v===null||v===undefined?'':v);
const cpEsc=v=>esc(cap(v));
const cpKinds={overview:'Overview',prospect:'Prospek & Pipeline',activity:'Aktivitas',plan:'Action Plan',order:'Order & Closing',daily:'Monitoring Harian'};
let cp={id:'',items:[],detail:null,kind:'overview',rows:[],total:0,hasMore:false,load:0,photo:'',formSeq:0};

// === Universal history period ===
let hist={mode:'bulan',from:'',to:'',initialized:false};
function histInit(){if(hist.initialized||!S.meta)return;
 const d=S.meta.today||new Date().toISOString().slice(0,10);hist.initialized=true;
 by('histDay').value=d;by('histMonth').value=d.slice(0,7);
 const yr=+d.slice(0,4);by('histYear').innerHTML=Array.from({length:16},(_,i)=>yr+2-i).map(y=>'<option value="'+y+'">'+y+'</option>').join('');by('histYear').value=String(yr);
 by('histFrom').value=d.slice(0,8)+'01';by('histTo').value=d;histCompute(false);
}
function histCompute(validate=true){if(!S.meta)return {from:'',to:''};const m=by('histMode').value;hist.mode=m;
 const d=by('histDay').value,mm=by('histMonth').value,y=by('histYear').value;
 if(m==='hari'){hist.from=d;hist.to=d;}
 else if(m==='bulan'){const yyyy=Number(mm.slice(0,4)),mon=Number(mm.slice(5,7));hist.from=mm+'-01';hist.to=mm+'-'+String(new Date(yyyy,mon,0).getDate()).padStart(2,'0');}
 else if(m==='tahun'){hist.from=y+'-01-01';hist.to=y+'-12-31';}
 else if(m==='semua'){hist.from='';hist.to='';}
 else {hist.from=by('histFrom').value;hist.to=by('histTo').value;}
 if(validate&&(hist.from&&!dateOk(hist.from)||hist.to&&!dateOk(hist.to)||hist.from&&hist.to&&hist.from>hist.to))throw Error('Rentang riwayat tidak valid');
 return {from:hist.from,to:hist.to};
}
function histRange(){histInit();try{return histCompute();}catch(e){return {from:'',to:''};}}
function histModeChange(){histInit();const m=by('histMode').value;
 [['histDayBox','hari'],['histMonthBox','bulan'],['histYearBox','tahun'],['histFromBox','rentang'],['histToBox','rentang']].forEach(([id,key])=>by(id).classList.toggle('hid',key!==m));
 if(m==='rentang'&&!by('histFrom').value){by('histFrom').value=S.meta.today.slice(0,8)+'01';by('histTo').value=S.meta.today;}
 histApply();}
function histVisible(){if(!S.meta||!by('historyStrip'))return;const tab=S.tab;
 const show=tab==='MASALAH'||tab==='visit'||tab==='issues'||tab==='period'||tab==='campaign'||tab==='jadwal'||tab==='rutin'||(tab==='ceklis'&&S.ckMode==='riwayat')||(tab==='dso'&&S.dsMode==='riwayat');
 by('historyStrip').classList.toggle('hid',!show);if(show)histInit();}
function histApply(){if(!S.meta)return;let range;try{range=histCompute();}catch(e){toast(e.message,true);return;}
 if(by('fFrom'))by('fFrom').value=range.from;if(by('fTo'))by('fTo').value=range.to;
 if(by('fPeriode'))by('fPeriode').value='custom';
 if(S.tab==='rutin'){if(S.rutin)renderRutin();loadRoutineHistory();}
 else if(S.tab==='campaign')cpReload();
 else if(S.tab==='issues')loadIssues();
 else if(S.tab==='jadwal')loadJadwal();
 else if(S.tab==='dso'&&S.dsMode==='riwayat')loadDso();
 else if(S.tab==='ceklis'&&S.ckMode==='riwayat')loadCeklis();
 else refresh();
}
function histReset(){if(!S.meta)return;by('histMode').value='bulan';by('histMonth').value=S.meta.today.slice(0,7);histModeChange();}
Object.assign(window,{histApply,histModeChange,histReset,histRange});
const oldGo=go;go=function(tab){const out=oldGo(tab);histVisible();return out;};
const oldCK=ckMode;ckMode=function(m){const x=oldCK(m);histVisible();return x;};
const oldDS=dsMode;dsMode=function(m){const x=oldDS(m);histVisible();return x;};
const oldIssueFilter=issueFilter;issueFilter=function(){return Object.assign({},oldIssueFilter(),histRange());};
// Manager checklist historical rows and routine templates can be inspected independently.
// History has a compact initial window, with explicit pagination and full CSV export.
const historyState={routine:[],routineVisible:300,routineSeq:0,jadwal:[],jadwalVisible:300,jadwalSeq:0};
function historyExport(rows,cols,prefix){
 if(!rows.length)return toast('Belum ada data untuk diekspor',true);
 const q=v=>'"'+cap(v).replace(/"/g,'""')+'"';
 const csv='\ufeff'+cols.map(x=>q(x[1])).join(';')+'\r\n'+rows.map(r=>cols.map(x=>q(r[x[0]]||'')).join(';')).join('\r\n');
 const a=document.createElement('a'),url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.href=url;a.download=prefix+'_'+(S.meta?.today||'riwayat')+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1800);
}
function renderRoutineHistory(){const sorted=historyState.routine,visible=sorted.slice(0,historyState.routineVisible),target=by('rutinHistory');if(!target)return;
 target.innerHTML='<div class="card routine-hist-card"><div class="cp-section"><h3>Riwayat Pengerjaan Tugas ('+num(sorted.length)+')</h3><button type="button" class="btn s" onclick="exportRoutineHistory()">↓ CSV seluruh riwayat</button></div><p class="mu">Mengikuti filter tanggal/bulan/tahun/rentang. Menampilkan '+num(visible.length)+' dari '+num(sorted.length)+' baris.</p><div class="cp-table"><table><thead><tr><th>Tanggal</th><th>Toko</th><th>Tugas</th><th>Status</th><th>Validasi</th></tr></thead><tbody>'+visible.map(r=>'<tr><td>'+cpEsc(fmtTgl(r.tanggal))+'</td><td>'+cpEsc(r.toko)+'</td><td>'+cpEsc(r.judul)+'</td><td>'+cpEsc(r.status)+'</td><td>'+cpEsc(r.validasi==='Y'?'Valid':'Belum')+'</td></tr>').join('')+(sorted.length?'':'<tr><td colspan="5">Belum ada riwayat.</td></tr>')+'</tbody></table></div>'+(visible.length<sorted.length?'<button type="button" class="btn w" onclick="routineHistoryMore()">Muat '+num(Math.min(300,sorted.length-visible.length))+' berikutnya</button>':'')+'</div>';
}
function routineHistoryMore(){historyState.routineVisible+=300;renderRoutineHistory();}
function exportRoutineHistory(){historyExport(historyState.routine,[['tanggal','Tanggal'],['toko','Toko'],['judul','Tugas'],['status','Status'],['catatan','Catatan'],['fotoId','Referensi Foto'],['validasi','Validasi'],['validasiOleh','Divalidasi Oleh'],['id','ID']], 'RIWAYAT_TUGAS');}
async function loadRoutineHistory(){if(S.tab!=='rutin'||!isMgr()||!by('rutinHistory'))return;
 const target=by('rutinHistory'),f=histRange(),seq=++historyState.routineSeq;target.innerHTML='<div class="card routine-hist-card mu">Memuat riwayat pengerjaan tugas…</div>';
 try{const rows=await call('list',{type:'CEKLIS',filter:Object.assign({toko:'SEMUA'},f)},true);if(S.tab!=='rutin'||seq!==historyState.routineSeq)return;
 historyState.routine=rows.slice().sort((a,b)=>String(b.tanggal).localeCompare(String(a.tanggal)));historyState.routineVisible=300;renderRoutineHistory();
 }catch(e){if(seq===historyState.routineSeq)target.innerHTML='<div class="card mu">Riwayat tugas tidak dapat dibaca: '+cpEsc(e.message||e)+'</div>';}
}
const prevRoutine=renderRutin;renderRutin=function(){prevRoutine();loadRoutineHistory();};
function renderJadwalHistory(){const all=historyState.jadwal,visible=all.slice(0,historyState.jadwalVisible),el=by('jdHistory');if(!el)return;
 el.innerHTML='<div class="cp-section"><h3>Riwayat Jadwal Visit ('+num(all.length)+')</h3><button type="button" class="btn s" onclick="exportJadwalHistory()">↓ CSV seluruh riwayat</button></div><p class="mu">Tanggal/bulan/tahun/rentang • '+num(visible.length)+' dari '+num(all.length)+' baris</p><div class="cp-table"><table><thead><tr><th>Tanggal</th><th>Toko</th><th>Agenda</th><th>PIC</th><th>Status</th></tr></thead><tbody>'+visible.map(r=>'<tr><td>'+cpEsc(fmtTgl(r.tanggal))+'</td><td>'+cpEsc(r.toko)+'</td><td>'+cpEsc(r.agenda)+'</td><td>'+cpEsc(r.pic)+'</td><td>'+cpEsc(r.status)+'</td></tr>').join('')+(all.length?'':'<tr><td colspan="5">Belum ada riwayat jadwal.</td></tr>')+'</tbody></table></div>'+(visible.length<all.length?'<button type="button" class="btn w" onclick="jadwalHistoryMore()">Muat '+num(Math.min(300,all.length-visible.length))+' berikutnya</button>':'');
}
function jadwalHistoryMore(){historyState.jadwalVisible+=300;renderJadwalHistory();}
function exportJadwalHistory(){historyExport(historyState.jadwal,[['tanggal','Tanggal'],['toko','Toko'],['agenda','Agenda'],['pic','PIC'],['status','Status'],['jamMulai','Jam Mulai'],['jamSelesai','Jam Selesai'],['catatan','Catatan'],['id','ID']], 'RIWAYAT_JADWAL');}
const oldJadwal=loadJadwal;loadJadwal=function(){const p=oldJadwal();if(S.tab==='jadwal'){
 const f=histRange(),seq=++historyState.jadwalSeq;call('list',{type:'JADWAL',filter:f},true).then(rows=>{
 if(seq!==historyState.jadwalSeq||S.tab!=='jadwal')return;historyState.jadwal=rows.slice().sort((a,b)=>String(b.tanggal).localeCompare(String(a.tanggal)));historyState.jadwalVisible=300;renderJadwalHistory();
 }).catch(e=>{if(seq===historyState.jadwalSeq&&by('jdHistory'))by('jdHistory').textContent='Riwayat jadwal belum dapat dimuat: '+(e.message||e);});}return p;};
Object.assign(window,{routineHistoryMore,exportRoutineHistory,jadwalHistoryMore,exportJadwalHistory});

// === Campaign Management ===
function cpRange(){return histRange();}
function cpCurrent(){return (cp.items||[]).find(x=>x.id===cp.id)||null;}
function cpAllStores(){return (S.meta&&S.meta.toko)||[];}
function cpStore(){return isMgr()?by('cpStore').value:S.me.toko;}
function cpLimits(){return cpRange();}
async function loadCampaignUI(){if(!S.meta)return;histVisible();if(!cp.items.length){await cpList();}else await cpReload();}
async function cpList(){const sel=by('cpSelect');if(!sel)return;sel.innerHTML='<option>Memuat…</option>';
 try{const arr=await call('campaignList',{},true);cp.items=arr||[];if(!cp.items.find(x=>x.id===cp.id))cp.id=cp.items[0]?cp.items[0].id:'';
 sel.innerHTML=cp.items.length?cp.items.map(c=>'<option value="'+cpEsc(c.id)+'"'+(c.id===cp.id?' selected':'')+'>'+cpEsc(c.name)+' · '+cpEsc(c.status)+'</option>').join(''):'<option value="">Belum ada campaign</option>';
 if(cp.id)await cpReload();else{by('cpContent').innerHTML='<div class="cp-empty">'+(isMgr()?'Belum ada campaign. Klik + Campaign untuk membuat program dan target toko.':'Belum ada campaign yang ditugaskan untuk toko Anda.')+'</div>';by('cpStats').innerHTML='';by('cpTabs').innerHTML='';}
 }catch(e){sel.innerHTML='<option>Tidak tersedia</option>';by('cpContent').innerHTML='<div class="cp-empty">Campaign gagal dimuat: '+cpEsc(e.message||e)+'<br>Pastikan SQL 014 Campaign Management sudah dijalankan.</div>';}}
function cpChoose(id){cp.id=id;cp.kind='overview';cpReload();}
function cpTab(kind){cp.kind=kind;cpReload();}
function cpRenderTabs(){by('cpTabs').innerHTML=Object.entries(cpKinds).map(([k,n])=>'<button class="'+(cp.kind===k?'on':'')+'" onclick="cpTab(\''+k+'\')">'+cpEsc(n)+'</button>').join('');}
function cpRenderStoreChoices(){const sel=by('cpStore'),stores=(cp.detail&&cp.detail.stores)||[];
 if(!isMgr()){sel.innerHTML='<option value="'+cpEsc(S.me.toko)+'">'+cpEsc(S.me.toko)+'</option>';return;}
 const prev=sel.value||'SEMUA';sel.innerHTML='<option value="SEMUA">Semua toko</option>'+cpAllStores().map(t=>'<option value="'+cpEsc(t)+'">'+cpEsc(t)+'</option>').join('');
 if([...sel.options].some(x=>x.value===prev))sel.value=prev;else sel.value='SEMUA';}
async function cpReload(){if(!cp.id||!by('cpContent'))return;const seq=++cp.load;const f=cpLimits();by('cpContent').innerHTML='<div class="skel"></div>';cpRenderTabs();
 try{const detail=await call('campaignDetail',Object.assign({id:cp.id,toko:cpStore()},f),true);if(seq!==cp.load)return;
 cp.detail=detail;cpRenderStoreChoices();cpRenderStats();
 if(cp.kind==='overview')cpRenderScorecard();else{const res=await call('campaignRecords',Object.assign({id:cp.id,toko:cpStore(),kind:cp.kind,limit:100,offset:0},f),true);
  if(seq!==cp.load)return;cp.rows=res.rows||[];cp.total=res.total||0;cp.hasMore=!!res.hasMore;cpRenderRecords();}
 }catch(e){if(seq===cp.load){by('cpContent').innerHTML='<div class="cp-empty">Tidak dapat memuat campaign: '+cpEsc(e.message||e)+'</div>';by('cpStats').innerHTML='';}}}
function cpMetric(title,value,sub,cls){return '<div class="cp-kpi'+(cls?' '+cls:'')+'"><span>'+title+'</span><strong>'+value+'</strong><small>'+sub+'</small></div>';}
function cpRenderStats(){const a=(cp.detail&&cp.detail.scorecard)||[],sum=k=>a.reduce((n,x)=>n+Number(x[k]||0),0),tar=sum('target_revenue'),rev=sum('revenue');
 const ach=tar?Math.round(rev/tar*100):0;by('cpStats').innerHTML='<div class="cp-kpis">'+cpMetric('Realisasi revenue',money(rev),'Penjualan Lunas/Terkirim','revenue')+
 cpMetric('Target omzet',money(tar),'Target semua toko terpilih')+cpMetric('Achievement',tar?ach+'%':'—','Revenue terhadap target')+
 cpMetric('Prospek',num(sum('leads')),'Closing '+num(sum('closing')))+cpMetric('Aktivitas',num(sum('activities')),'Kunjungan '+num(sum('visits')))+
 cpMetric('Order',num(sum('orders')),'Qty '+num(sum('qty')))+'</div>';
}
function cpPct(a,b){return Number(b)>0?Math.round(Number(a||0)*100/Number(b)):0;}
function cpRenderScorecard(){const c=cp.detail.campaign||{},rows=cp.detail.scorecard||[];
 let html='<div class="cp-section"><div><h3>Target vs realisasi per toko</h3><span class="mu">'+cpEsc(c.name)+' · '+cpEsc(fmtTgl(c.start_date))+'–'+cpEsc(fmtTgl(c.end_date))+'</span></div><button class="btn s" onclick="cpExport()">↓ Ekspor aktivitas</button></div>';
 html+='<div class="cp-table"><table><thead><tr><th>Toko / PIC</th><th>Target Omzet</th><th>Realisasi</th><th>Achievement</th><th>Prospek / Closing</th><th>Aktivitas</th><th>Order</th><th>Action Plan</th></tr></thead><tbody>';
 rows.forEach(r=>{const pct=cpPct(r.revenue,r.target_revenue);html+='<tr><td><b>'+cpEsc(r.toko)+'</b><small class="mu" style="display:block">'+cpEsc(r.pic||'—')+'</small></td><td>'+money(r.target_revenue)+'</td><td><b>'+money(r.revenue)+'</b></td><td><b>'+(r.target_revenue?pct+'%':'—')+'</b><div class="cp-progress"><i style="width:'+Math.min(pct,100)+'%"></i></div></td><td>'+num(r.leads)+' / '+num(r.closing)+'</td><td>'+num(r.activities)+' / '+num(r.target_activities)+'</td><td>'+num(r.orders)+' / '+num(r.target_orders)+'</td><td>'+num(r.plans_done)+' / '+num(r.plans)+'</td></tr>';});
 if(!rows.length)html+='<tr><td colspan="8" class="empty">Belum ada toko campaign yang sesuai.</td></tr>';
 html+='</tbody></table></div><p class="mu" style="margin-top:10px">Revenue dihitung dari order berstatus Lunas/Terkirim, satu kali per order. Log monitoring harian tidak menambah revenue agar tidak terjadi penghitungan ganda. Prospek Closing dicatat pada pipeline; nilai realisasi hanya dihitung dari order.</p>';
 by('cpContent').innerHTML=html;
}
const cpStatus={prospect:['Belum Dihubungi','Dihubungi','Tertarik','Penawaran','Negosiasi','Closing','Lost'],activity:['Terbuka','Selesai','Batal'],plan:['Belum mulai','Berjalan','Selesai','Ditunda'],order:['DP','Proses','Lunas','Terkirim','Batal'],daily:['Dikirim']};
function cpRenderRecords(){const kind=cp.kind,arr=cp.rows||[];
 const tlabel=cpKinds[kind]||kind;let html='<div class="cp-section"><div><h3>'+cpEsc(tlabel)+' <span class="mu">('+num(cp.total)+' data)</span></h3><span class="mu">Filter riwayat di bagian atas • tersimpan per toko</span></div><div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn s" onclick="cpExport()">↓ Export CSV Lengkap</button><button class="btn s p" onclick="cpEditRecord()">+ Input '+cpEsc(kind==='order'?'order':kind==='prospect'?'prospek':'aktivitas')+'</button></div></div>';
 html+='<div class="cp-table"><table><thead><tr><th>Tanggal</th><th>Toko</th><th>'+cpEsc(kind==='prospect'?'Prospek / Mitra':kind==='daily'?'Monitoring':'Aktivitas / Order')+'</th><th>Status</th><th>PIC</th><th>Target / Realisasi</th><th>Info</th><th>Aksi</th></tr></thead><tbody>';
 arr.forEach((r,i)=>{let metric=kind==='order'?money(r.amount)+' · '+num(r.qty)+' pcs':kind==='plan'?num(r.actual)+' / '+num(r.target):kind==='prospect'?money(r.target)+' potensi':kind==='daily'?num(r.payload&&r.payload.visits)+' visit · '+num(r.payload&&r.payload.whatsapp)+' WA':'—';
 html+='<tr><td>'+cpEsc(fmtTgl(r.event_date))+'</td><td>'+cpEsc(r.toko)+'</td><td><b>'+cpEsc(r.title||'Monitoring')+'</b><div class="mu">'+cpEsc(r.notes||'').slice(0,90)+'</div></td><td>'+cpEsc(r.status||'—')+'</td><td>'+cpEsc(r.pic||'—')+'</td><td>'+metric+'</td><td>'+cpEsc((r.payload||{}).contact_person||(r.payload||{}).activity_type||(r.payload||{}).product||'')+(r.followup_date?'<div class="mu">Follow-up '+cpEsc(fmtTgl(r.followup_date))+'</div>':'')+'</td><td><button class="btn s" onclick="cpEditRecord('+i+')">Edit</button> <button class="btn s r" onclick="cpArchive('+i+')">Arsipkan</button></td></tr>';});
 if(!arr.length)html+='<tr><td colspan="8" class="empty">Belum ada isian pada periode ini.</td></tr>';
 html+='</tbody></table></div>';
 if(cp.hasMore)html+='<button class="btn w" style="margin-top:9px" onclick="cpLoadMore()">Muat data berikutnya ('+num(cp.rows.length)+' / '+num(cp.total)+')</button>';
 by('cpContent').innerHTML=html;
}
async function cpLoadMore(){if(!cp.hasMore)return;try{const res=await call('campaignRecords',Object.assign({id:cp.id,toko:cpStore(),kind:cp.kind,limit:100,offset:cp.rows.length},cpLimits()),true);
 cp.rows.push(...(res.rows||[]));cp.total=res.total;cp.hasMore=res.hasMore;cpRenderRecords();}catch(e){toast('Muat halaman selanjutnya gagal: '+(e.message||e),true);}}
function cpFormOptions(arr,v){return arr.map(x=>'<option value="'+cpEsc(x)+'"'+(x===v?' selected':'')+'>'+cpEsc(x)+'</option>').join('');}
async function cpEditCampaign(edit){if(!isMgr())return toast('Menu khusus Master/SPV',true);const cur=edit?cpCurrent():null;if(edit&&!cur)return toast('Pilih campaign',true);
 const start=S.meta.today,end=addDays(start,30);
 let tgt=[];if(cur){try{const full=await call('campaignDetail',{id:cur.id,toko:'SEMUA'},true);tgt=full.stores||[];}catch(e){return toast('Gagal memuat semua target toko: '+(e.message||e),true);}}
 const byStore=Object.fromEntries(tgt.map(x=>[x.toko,x]));
 const fields=[{k:'name',l:'Nama campaign *',v:cur?cur.name:''},{k:'category',l:'Kategori / jenis campaign',v:cur?cur.category:'Sales'},
 {k:'objective',l:'Tujuan / target utama',v:cur?cur.objective:'',full:1},{k:'description',l:'Penjelasan / mekanisme',t:'area',v:cur?cur.description:'',full:1},
 {k:'pic',l:'PIC program',v:cur?cur.pic:S.me.nama},{k:'status',l:'Status',t:'sel',o:['Draft','Active','Paused','Closed'],v:cur?cur.status:'Active'},
 {k:'start_date',l:'Mulai *',t:'date',v:cur?cur.start_date:start},{k:'end_date',l:'Berakhir *',t:'date',v:cur?cur.end_date:end}];
 gen((edit?'Edit':'Buat')+' Campaign',fields,async d=>{
  if(!d.name.trim()||!dateOk(d.start_date)||!dateOk(d.end_date)||d.start_date>d.end_date)return toast('Isi nama campaign dan tanggal yang benar',true);
  const targets=cpAllStores().filter((t,i)=>by('cpt_check_'+i)&&by('cpt_check_'+i).checked).map(t=>{const i=cpAllStores().indexOf(t);return {toko:t,pic:by('cpt_pic_'+i).value,
    target_leads:Math.max(0,Number(by('cpt_leads_'+i).value)||0),target_visits:Math.max(0,Number(by('cpt_visits_'+i).value)||0),target_activities:Math.max(0,Number(by('cpt_activities_'+i).value)||0),target_orders:Math.max(0,Number(by('cpt_orders_'+i).value)||0),
    target_qty:Math.max(0,Number(by('cpt_qty_'+i).value)||0),target_revenue:Math.max(0,Number(by('cpt_revenue_'+i).value)||0)};});
  if(!targets.length)return toast('Pilih toko campaign',true);
  const btn=by('gSave');btn.disabled=true;try{const saved=await call('campaignSave',{data:Object.assign({},d,{id:cur?cur.id:'',targets})},true);
   closeM('mGen');cp.id=saved.id;toast('Campaign dan target toko tersimpan','ok');await cpList();
  }catch(e){toast('Campaign gagal disimpan: '+(e.message||e),true);}finally{btn.disabled=false;}
 });
 let wrap='<div class="cp-target-wrap"><h4>Target & PIC setiap toko</h4><p class="mu">Centang toko yang mengikuti campaign. Angka dapat berbeda di tiap toko.</p>';
 cpAllStores().forEach((store,i)=>{const o=byStore[store]||{};const on=!cur||!!byStore[store];wrap+='<div class="cp-target-row"><label><input type="checkbox" id="cpt_check_'+i+'" '+(on?'checked':'')+'>'+cpEsc(store)+'</label>'+
 [['pic','PIC',o.pic||'','text'],['leads','Prospek',o.target_leads||0,'number'],['visits','Visit',o.target_visits||0,'number'],['activities','Aktivitas',o.target_activities||0,'number'],['orders','Order',o.target_orders||0,'number'],['qty','Qty (pcs)',o.target_qty||0,'number'],['revenue','Omzet (Rp)',o.target_revenue||0,'number']].map(x=>'<label>'+x[1]+'<input type="'+x[3]+'" id="cpt_'+x[0]+'_'+i+'" value="'+cpEsc(x[2])+'" '+(x[3]==='number'?'min="0"':'')+'></label>').join('')+'</div>';});
 wrap+='</div>';by('gBody').insertAdjacentHTML('beforeend',wrap);
}
function cpEditRecord(i){if(!cp.id)return toast('Pilih campaign',true);const kind=cp.kind;if(kind==='overview')return;const rec=i===undefined?null:cp.rows[i],st=cpStore();
 if(!rec&&st==='SEMUA')return toast('Pilih satu toko sebelum membuat input',true);
 cp.photo=rec?rec.photo_id||'':'';const f=[],add=(k,l,v,t='text',full=false,o=null)=>f.push({k,l,v:v===null||v===undefined?'':v,t,full,o});
 add('event_date',kind==='plan'?'Tanggal rencana':'Tanggal aktivitas',rec?rec.event_date:S.meta.today,'date');
 if(isMgr())add('toko','Toko',rec?rec.toko:st,'sel',false,(cp.detail.stores||[]).map(s=>s.toko));
 add('title',kind==='prospect'?'Nama prospek / mitra':kind==='order'?'Order / customer':kind==='daily'?'Catatan singkat':'Judul aktivitas',rec?rec.title:kind==='daily'?'Monitoring harian':'','text',true);
 if(kind==='prospect'){
  add('status','Tahap pipeline',rec?rec.status:'Belum Dihubungi','sel',false,cpStatus.prospect);
  add('x_contact_person','Nama PIC prospek',rec?.payload?.contact_person||'');add('x_contact','Kontak resmi',rec?.payload?.contact||'');
  add('x_segment','Kategori (Sekolah, B2B, dll)',rec?.payload?.segment||'');add('x_region','Kota / wilayah',rec?.payload?.region||'');
  add('x_source','Sumber prospek',rec?.payload?.source||'');add('qty','Potensi qty',rec?rec.qty:0,'number');
  add('target','Potensi omzet (Rp)',rec?rec.target:0,'number');add('followup_date','Next follow-up',rec?rec.followup_date:'','date');
 } else if(kind==='activity'){
  add('status','Status aktivitas',rec?rec.status:'Terbuka','sel',false,cpStatus.activity);
  add('x_activity_type','Jenis aktivitas',rec?.payload?.activity_type||'Visit','sel',false,['Visit','Canvassing','School Visit','WhatsApp','Telepon','Katalog','Sample Kit','Follow-up','Social Media','Event','Lainnya']);
  add('x_subject','Nama prospek/mitra terkait',rec?.payload?.subject||'');add('actual','Hasil kegiatan (jumlah)',rec?rec.actual:0,'number');
  add('followup_date','Tanggal follow-up',rec?rec.followup_date:'','date');
 } else if(kind==='plan'){
  add('status','Status rencana',rec?rec.status:'Belum mulai','sel',false,cpStatus.plan);add('x_activity_type','Jenis aktivitas',rec?.payload?.activity_type||'Visit');
  add('target','Target kegiatan',rec?rec.target:0,'number');add('actual','Realisasi',rec?rec.actual:0,'number');
  add('x_output','Output yang diharapkan',rec?.payload?.output||'','text',true);
 } else if(kind==='order'){
  add('status','Status order',rec?rec.status:'DP','sel',false,cpStatus.order);add('x_lead','Prospek / Lead terkait',rec?.payload?.lead||'');
  add('x_product','Produk / paket',rec?.payload?.product||'');add('x_order_no','Nomor order',rec?.payload?.order_no||'');
  add('qty','Qty pcs *',rec?rec.qty:1,'number');add('amount','Nilai order setelah diskon (Rp)',rec?rec.amount:0,'number');
  add('x_delivery_date','Tanggal kirim',rec?.payload?.delivery_date||'','date');
 } else if(kind==='daily'){
  add('status','Status',rec?rec.status:'Dikirim','sel',false,['Dikirim']);
  [['visits','Kunjungan'],['whatsapp','WhatsApp'],['catalog','Katalog dibagikan'],['sample','Sample Kit'],['followups','Follow-up'],['prospects','Prospek baru'],['orders','Order'],['qty','Qty pcs'],['revenue','Omzet tercatat']].forEach(([k,label])=>add('x_'+k,label,rec?.payload?.[k]||0,'number'));
 }
 add('pic','PIC aktivitas',rec?rec.pic:S.me.nama);
 add('notes','Catatan / hambatan / tindak lanjut',rec?rec.notes:'','area',true);
 gen((rec?'Edit':'Input')+' '+cpKinds[kind],f,async d=>{
  if(!dateOk(d.event_date))return toast('Tanggal input tidak valid',true);
  const payload={},data={};Object.keys(d).forEach(k=>{if(k.startsWith('x_'))payload[k.slice(2)]=d[k];else data[k]=d[k];});
  data.payload=payload;data.id=rec?rec.id:'';data.photo_id=cp.photo||'';
  if(!data.title.trim()&&kind!=='daily')return toast('Isi judul / nama prospek / order',true);
  if(kind==='order'&&(+data.qty<=0||+data.amount<0))return toast('Isi qty dan nilai order yang benar',true);
  if(Object.keys(evidenceBusy).some(k=>k.startsWith('campaign:')))return toast('Tunggu upload foto selesai',true);
  const b=by('gSave');b.disabled=true;
  try{await call('campaignRecordSave',{id:cp.id,kind,data},true);closeM('mGen');toast('Data campaign tersimpan','ok');await cpReload();}
  catch(e){toast('Belum tersimpan: '+(e.message||e),true);}finally{b.disabled=false;}
 });
 by('gBody').insertAdjacentHTML('beforeend','<div class="full"><span class="lbl">Dokumentasi foto (opsional)</span>'+evidencePanel('campaign','draft',true)+'</div>');
}
async function cpArchive(i){const r=cp.rows[i];if(!r||!confirm('Arsipkan data '+(r.title||r.id)+'? Data tetap tercatat dalam audit.'))return;
 try{await call('campaignRecordSave',{id:cp.id,kind:cp.kind,data:{id:r.id,toko:r.toko,operation:'archive'}},true);toast('Data diarsipkan','ok');await cpReload();}catch(e){toast('Arsip gagal: '+(e.message||e),true);}}
async function cpExport(){if(!cp.id)return toast('Pilih campaign',true);const kind=cp.kind==='overview'?null:cp.kind;const rows=[];let offset=0;
 try{for(let page=0;page<300;page++){const data=await call('campaignRecords',Object.assign({id:cp.id,toko:cpStore(),kind,limit:200,offset},cpLimits()),true);
  rows.push(...(data.rows||[]));offset+=data.rows.length;if(!data.hasMore)break;if(rows.length>=50000)throw new Error('Data lebih dari 50.000 baris; gunakan rentang tanggal lebih sempit');}
  if(!rows.length)return toast('Tidak ada data untuk export',true);
  const cols=['id','campaign_id','toko','kind','event_date','title','status','pic','target','actual','qty','amount','followup_date','notes','payload','photo_id','created_by','created_at','updated_at'];
  const q=v=>'"'+cap(typeof v==='object'&&v!==null?JSON.stringify(v):v).replace(/"/g,'""')+'"';
  const csv='\ufeff'+cols.map(q).join(';')+'\r\n'+rows.map(r=>cols.map(k=>q(r[k])).join(';')).join('\r\n');
  const a=document.createElement('a'),url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));a.href=url;a.download='CAMPAIGN_'+(kind||'SEMUA')+'_'+S.meta.today+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);
 }catch(e){toast('Export campaign gagal: '+(e.message||e),true);}}
// Connect the existing compact photo hub, not a second photo upload implementation.
const oldEvidenceId=evidenceId,oldEvidenceLock=evidenceLock,oldEvidenceSave=evidenceStateSave;
evidenceId=function(kind,key){if(kind==='campaign')return cp.photo||'';return oldEvidenceId.apply(this,arguments);};
evidenceLock=function(kind,key){if(kind==='campaign')return false;return oldEvidenceLock.apply(this,arguments);};
evidenceStateSave=function(kind,key,packed){if(kind==='campaign'){cp.photo=packed;return Promise.resolve();}return oldEvidenceSave.apply(this,arguments);};
const exportOld=exportActive;exportActive=function(){
 if(S.tab==='campaign')return cpExport();
 if(S.tab==='rutin')return exportRoutineHistory();
 if(S.tab==='jadwal')return exportJadwalHistory();
 if(S.tab==='period')return exportPeriodCsv();
 if((S.tab==='ceklis'&&S.ckMode==='riwayat')||(S.tab==='dso'&&S.dsMode==='riwayat')){
  const module=S.tab==='ceklis'?'CEKLIS':'DSO';
  return call('exportData',{module,filter:Object.assign({},histRange(),{toko:isMgr()?by(S.tab==='ceklis'?'ckToko':'dsToko').value:S.me.toko})}).then(r=>downloadCsvV6(r.rows,module+'_RIWAYAT_'+S.meta.today));
 }
 return exportOld.apply(this,arguments);
};
// Campaign cards in Executive Overview. They never claim sales from manually logged daily revenue.
const oldDash=renderDash;renderDash=function(ms,tr){oldDash(ms,tr);
 if(!isMgr()||S.dashTab&&S.dashTab!=='ringkasan')return;
 const root=document.querySelector('#pDash .exec-root')||by('pDash');if(!root)return;
 const hold=document.createElement('div');hold.className='exec-card';hold.innerHTML='<h3>Campaign Management</h3><p class="mu">Memuat campaign aktif &amp; realisasi order…</p>';root.appendChild(hold);
 call('campaignList',{},true).then(items=>{if(!hold.isConnected)return;
 const active=(items||[]).filter(x=>x.status==='Active'),sum=k=>active.reduce((a,r)=>a+Number(r[k]||0),0),target=sum('target_revenue'),revenue=sum('realized_revenue');
 hold.innerHTML='<div class="cp-section"><div><h3>Campaign Management</h3><p class="mu">Target &amp; closing dari semua campaign aktif • tidak dicampur dengan Tugas Global</p></div><button class="btn p s" onclick="go(\'campaign\')">Buka Campaign</button></div><div class="cp-kpis">'+cpMetric('Campaign aktif',num(active.length),'Program berjalan')+cpMetric('Target revenue',money(target),'Seluruh toko')+cpMetric('Realisasi closing',money(revenue),'Order Lunas / Terkirim','revenue')+cpMetric('Achievement',target?Math.round(revenue/target*100)+'%':'—','Target campaign')+'</div>';
 }).catch(e=>{if(hold.isConnected)hold.innerHTML='<h3>Campaign Management</h3><p class="mu">Modul campaign belum aktif: '+cpEsc(e.message||e)+'</p>';});
};

// === v19 Campaign lifecycle: Edit / Sampah / Pulihkan / Backup / Hapus Permanen ===
const cpAdmin={trash:[],backupPrepared:new Set(),busy:false};
function cpShowMasterControls(){
 const show=!!(S.me&&isMaster());
 ['cpTrashBtn','cpMoveTrashBtn','cpBackupBtn'].forEach(id=>{const el=by(id);if(el)el.classList.toggle('hid',!show);});
 const edit=by('cpEditBtn');if(edit)edit.disabled=!cp.id;
 const move=by('cpMoveTrashBtn');if(move)move.disabled=!cp.id;
 const backup=by('cpBackupBtn');if(backup)backup.disabled=!cp.id;
}
const cpListBeforeAdmin=cpList;
cpList=async function(){const out=await cpListBeforeAdmin.apply(this,arguments);cpShowMasterControls();return out;};
function cpCloseTrash(){by('cpTrashModal')?.classList.remove('on');}
async function cpMoveTrash(){
 if(!isMaster())return toast('Hanya Master yang dapat menghapus Campaign',true);
 const c=cpCurrent();if(!c)return toast('Pilih campaign terlebih dahulu',true);
 const info=await call('campaignDeletePreview',{id:c.id},true).catch(e=>{toast(e.message||e,true);return null;});
 if(!info)return;
 const message='Pindahkan "'+info.name+'" ke Sampah?\n\n'+num(info.records)+' data, '+num(info.stores)+' target toko, '+num(info.audit)+' histori audit AKAN TETAP TERSIMPAN dan bisa dipulihkan.\n\nCampaign tidak lagi muncul di Dashboard / Store.';
 if(!confirm(message))return;
 try{await call('campaignManage',{id:c.id,action:'trash'},true);cp.id='';toast('Campaign dipindahkan ke Sampah. Data masih dapat dipulihkan.','ok');await cpList();await cpOpenTrash();}
 catch(e){toast('Gagal memindahkan campaign: '+(e.message||e),true);}
}
async function cpOpenTrash(){
 if(!isMaster())return toast('Sampah khusus Master',true);
 const modal=by('cpTrashModal');if(!modal)return;
 modal.classList.add('on');by('cpTrashBody').innerHTML='<div class="skel"></div>';
 try{
  const [items,cleanup]=await Promise.all([call('campaignTrashList',{},true),call('campaignCleanupCount',{},true)]);
  cpAdmin.trash=items||[];
  let h='<p class="mu">Campaign di Sampah tidak terlihat oleh Store/Dashboard. Hapus Permanen membersihkan data, target toko, dan audit terkait; tindakan tidak dapat dibatalkan.</p>';
  if(!cpAdmin.trash.length)h+='<div class="cp-empty">Sampah Campaign kosong.</div>';
  for(const c of cpAdmin.trash){
   const id=cpEsc(c.id);
   h+='<article class="cp-trash-card"><div class="cp-trash-head"><div><strong>'+cpEsc(c.name)+'</strong><div class="mu">Dihapus ke Sampah '+cpEsc(c.deleted_at?new Date(c.deleted_at).toLocaleString('id-ID',{timeZone:'Asia/Makassar'}):'-')+' WITA · oleh '+cpEsc(c.deleted_by||'-')+'</div></div><span class="bdg st-Pending">Sampah</span></div>'+
    '<div class="cp-trash-count">'+num(c.records)+' data · '+num(c.stores)+' toko · '+num(c.audit_events)+' audit</div>'+
    '<div class="cp-trash-actions"><button class="btn s g" data-id="'+id+'" onclick="cpRestoreCampaign(this.dataset.id)">↶ Pulihkan</button>'+
    '<button class="btn s" data-id="'+id+'" onclick="cpBackupCampaign(this.dataset.id)">↓ Backup JSON</button>'+
    '<button class="btn s r" data-id="'+id+'" onclick="cpPurgeCampaign(this.dataset.id)">🗑 Hapus Permanen</button></div>'+
    '<label class="cp-trash-ack"><input type="checkbox" id="cpAck_'+id+'"> Saya sudah mengunduh dan memeriksa file backup JSON campaign ini</label></article>';
  }
  h+='<div class="cp-trash-foot"><div class="mu">Foto di Supabase Storage: '+num(cleanup.pending||0)+' menunggu pembersihan, '+num(cleanup.done||0)+' telah dibersihkan'+(cleanup.skipped_shared?' · '+num(cleanup.skipped_shared)+' foto masih dipakai modul lain':'')+'.</div>'+
    '<button type="button" class="btn s" onclick="cpCleanupCampaignPhotos()">♻ Bersihkan Foto Tersisa</button></div>';
  by('cpTrashBody').innerHTML=h;
 }catch(e){by('cpTrashBody').innerHTML='<div class="cp-empty">Gagal membuka Sampah: '+cpEsc(e.message||e)+'</div>';}
}
async function cpRestoreCampaign(id){
 if(!isMaster())return;
 const c=cpAdmin.trash.find(x=>x.id===id);if(!c)return toast('Data Sampah berubah, buka ulang',true);
 if(!confirm('Pulihkan campaign '+c.name+'? Campaign akan terlihat kembali pada toko yang ditugaskan.'))return;
 try{await call('campaignManage',{id,action:'restore'},true);toast('Campaign berhasil dipulihkan','ok');cp.id=id;await cpList();await cpOpenTrash();}
 catch(e){toast('Gagal memulihkan: '+(e.message||e),true);}
}
async function cpBackupCampaign(id){
 if(!isMaster())return toast('Backup lengkap hanya untuk Master',true);
 id=id||cp.id;if(!id)return toast('Pilih campaign',true);
 if(cpAdmin.busy)return toast('Backup sebelumnya masih diproses',true);
 cpAdmin.busy=true;
 try{
  const sections={};
  for(const section of ['campaign','stores','records','audit']){
   let offset=0,arr=[],pages=0;
   do{
    const r=await call('campaignBackupSection',{id,section,offset,limit:300},true);
    arr.push(...(r.rows||[]));offset=arr.length;pages++;
    if(!r.hasMore)break;
    if(pages>1000||arr.length>300000)throw new Error('Data terlalu besar untuk backup browser; batasi lewat backend');
   }while(true);
   sections[section]=arr;
  }
  if(sections.campaign.length!==1)throw new Error('Data induk campaign tidak lengkap');
  const c=sections.campaign[0];
  const backup={format:'DCO_CAMPAIGN_BACKUP_V19',exported_at:new Date().toISOString(),
   photo_bytes_included:false,description:'Data campaign lengkap; binary foto terpisah di Supabase Storage.',
   campaign:c,stores:sections.stores,records:sections.records,audit:sections.audit};
  const json=JSON.stringify(backup,null,2),url=URL.createObjectURL(new Blob([json],{type:'application/json;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;
  a.download='BACKUP_CAMPAIGN_'+String(c.name).replace(/[^A-Za-z0-9_-]+/g,'_').slice(0,70)+'_'+new Date().toISOString().slice(0,10)+'.json';
  document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),120000);
  cpAdmin.backupPrepared.add(id);
  toast('Backup JSON disiapkan ('+num(sections.records.length)+' data, '+num(sections.audit.length)+' audit). Periksa unduhan sebelum Hapus Permanen.','ok');
 }catch(e){toast('Backup gagal: '+(e.message||e),true);}finally{cpAdmin.busy=false;}
}
async function cpPurgeCampaign(id){
 if(!isMaster())return toast('Hapus Permanen khusus Master',true);
 const c=cpAdmin.trash.find(x=>x.id===id);if(!c)return toast('Campaign tidak ditemukan di Sampah',true);
 const checkbox=by('cpAck_'+id);
 if(!cpAdmin.backupPrepared.has(id)||!checkbox?.checked){
  return toast('Unduh Backup JSON dari daftar Sampah dan centang bahwa file sudah diperiksa.',true);
 }
 let detail;try{detail=await call('campaignDeletePreview',{id},true);}catch(e){return toast(e.message||e,true);}
 const typed=prompt('PERINGATAN: Hapus Selamanya seluruh data Campaign termasuk '+num(detail.records)+' data, '+num(detail.stores)+' target toko dan '+num(detail.audit)+' audit.\n\nKetik nama campaign PERSIS untuk melanjutkan:',c.name);
 if(typed===null)return;
 if(typed!==c.name)return toast('Nama campaign tidak cocok. Penghapusan dibatalkan.',true);
 if(!confirm('KONFIRMASI TERAKHIR: HAPUS PERMANEN "'+c.name+'"? Tidak ada fitur Pulihkan setelah langkah ini.'))return;
 try{
  const r=await call('campaignManage',{id,action:'purge',confirmName:typed,backupAck:true},true);
  toast('Campaign dihapus permanen: '+num(r.records_deleted)+' data + '+num(r.audit_deleted)+' audit.','ok');
  await cpList();await cpOpenTrash();
  if(r.photos_queued)toast(num(r.photos_queued)+' foto kandidat perlu dibersihkan melalui tombol Bersihkan Foto Tersisa.');
 }catch(e){toast('Gagal Hapus Permanen: '+(e.message||e),true);}
}
async function cpCleanupCampaignPhotos(){
 if(!isMaster())return;
 if(!confirm('Bersihkan file foto kandidat yang sudah tidak digunakan oleh campaign maupun modul lain?'))return;
 try{const r=await call('campaignCleanup',{limit:30},true);
  toast(num(r.removed)+' foto dibersihkan; '+num(r.pending)+' antre. '+(r.failed?r.message:''),!!r.failed);
  await cpOpenTrash();
 }catch(e){toast('Pembersihan foto belum berhasil: '+(e.message||e),true);}
}

Object.assign(window,{loadCampaignUI,cpList,cpReload,cpChoose,cpTab,cpEditCampaign,cpEditRecord,cpArchive,cpLoadMore,cpExport,cpMoveTrash,cpOpenTrash,cpCloseTrash,cpRestoreCampaign,cpBackupCampaign,cpPurgeCampaign,cpCleanupCampaignPhotos});
})();
