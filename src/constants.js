export const STORES = [
  {id:'t01',name:'TIGALAPANKAOS BTP',brand:'Tigalapankaos',region:'Makassar'},
  {id:'m02',name:'MAMU BTP',brand:'MAMU',region:'Makassar'},
  {id:'m03',name:'MAMU PALOPO',brand:'MAMU',region:'Palopo'},
  {id:'t04',name:'TIGALAPANKAOS PALU',brand:'Tigalapankaos',region:'Palu'},
  {id:'m05',name:'MAMU TAMALATE',brand:'MAMU',region:'Makassar'},
  {id:'t06',name:'TIGALAPANKAOS MANADO',brand:'Tigalapankaos',region:'Manado'},
  {id:'t07',name:'TIGALAPANKAOS SAMARINDA',brand:'Tigalapankaos',region:'Samarinda'},
  {id:'m08',name:'MAMU KENDARI',brand:'MAMU',region:'Kendari'},
  {id:'t09',name:'TIGALAPANKAOS POLMAN',brand:'Tigalapankaos',region:'Polewali Mandar'},
  {id:'t10',name:'TIGALAPANKAOS BONE',brand:'Tigalapankaos',region:'Bone'},
  {id:'m11',name:'MAMU GOWA',brand:'MAMU',region:'Gowa'},
  {id:'t12',name:'TIGALAPANKAOS TORAJA',brand:'Tigalapankaos',region:'Toraja'}
];
export const NAV = [
 ['overview','Overview','dashboard'],['compliance','Kepatuhan Toko','check-circle'],['issues','Action Plan','clipboard-list'],
 ['checklist','Assignment Checklist','list-checks'],['dso','Daily Store Operation','camera'],['schedule','Jadwal Visit','calendar-days'],
 ['visits','Visiting Check Point','map-pin'],['pending','Pending Matter','flag'],['scorecard','Scorecard','bar-chart'],['maintenance','Export & Penyimpanan','database'],['settings','Pengaturan','settings']
];
export const PRIORITIES=['Kritis','Tinggi','Sedang','Rendah'];
export const STATUSES=['Open','On Progress','Pending','Selesai','Dibatalkan'];
export const fmtNumber=n=>new Intl.NumberFormat('id-ID').format(n||0);
export function dateWita(d=new Date()){
 const p=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Makassar',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d);
 const get=t=>p.find(x=>x.type===t)?.value||'';
 return `${get('year')}-${get('month')}-${get('day')}`;
}
export function prettyDate(s){if(!s)return'—';const [y,m,d]=String(s).slice(0,10).split('-');if(!d)return String(s);return `${d}/${m}/${y}`;}
export const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const storeName=id=>STORES.find(s=>s.id===id)?.name||id||'—';
export const seedDemo = () => ({
 briefings:[
  {store_id:'t01',briefing_date:'2026-11-11',shift:'Pagi',no_findings:false},
  {store_id:'m02',briefing_date:'2026-11-11',shift:'Pagi',no_findings:true},
  {store_id:'m03',briefing_date:'2026-11-11',shift:'Pagi',no_findings:false},
  {store_id:'m05',briefing_date:'2026-11-11',shift:'Pagi',no_findings:false},
  {store_id:'t06',briefing_date:'2026-11-11',shift:'Pagi',no_findings:false},
  {store_id:'t07',briefing_date:'2026-11-11',shift:'Pagi',no_findings:true},
  {store_id:'m08',briefing_date:'2026-11-11',shift:'Pagi',no_findings:false},
  {store_id:'t10',briefing_date:'2026-11-11',shift:'Pagi',no_findings:false},
  {store_id:'t12',briefing_date:'2026-11-11',shift:'Pagi',no_findings:true},
 ],
 issues:[
  {id:'demo-1',store_id:'m03',title:'Kesalahan SOQ belum diselesaikan',category:'Stok & Inventory',root_cause:'Rekonsiliasi DC belum rampung',action_plan:'Verifikasi selisih SKU bersama DC',pic_name:'SPV Area',due_date:'2026-11-11',priority:'Kritis',status:'Open',progress:0,origin:'briefing'},
  {id:'demo-2',store_id:'m05',title:'Broken size — permintaan transfer stok',category:'Stok & Inventory',root_cause:'Stok kosong di DC',action_plan:'Konfirmasi supply dan prioritas replenishment',pic_name:'SCM',due_date:'2026-11-12',priority:'Tinggi',status:'On Progress',progress:35,origin:'briefing'},
  {id:'demo-3',store_id:'t06',title:'Pencahayaan lantai dua tidak optimal',category:'Fasilitas & Aset',root_cause:'Lampu rusak',action_plan:'Periksa instalasi dan penggantian lampu',pic_name:'GA',due_date:'2026-11-13',priority:'Sedang',status:'Pending',progress:10,origin:'visit'},
  {id:'demo-4',store_id:'m11',title:'Update display produk belum sesuai planogram',category:'Visual Merchandising',root_cause:'SOP display belum dipahami',action_plan:'Coaching dan dokumentasi foto hasil display',pic_name:'SPV Area',due_date:'2026-11-16',priority:'Tinggi',status:'On Progress',progress:60,origin:'visit'},
  {id:'demo-5',store_id:'t10',title:'Perbaikan area packing telah selesai',category:'Operasional',root_cause:'Peralatan tidak tertata',action_plan:'Evaluasi rutin mingguan',pic_name:'Store Leader',due_date:'2026-11-09',priority:'Rendah',status:'Selesai',progress:100,origin:'visit'}
 ],
 schedules:[
  {id:'plan-1',store_id:'t01',visit_date:'2026-11-11',start_time:'09:00',end_time:'11:00',pic_name:'SPV Area',agenda:'Audit checklist & koordinasi tim',status:'Rencana'},
  {id:'plan-2',store_id:'m03',visit_date:'2026-11-12',start_time:'10:00',end_time:'12:00',pic_name:'SPV Area',agenda:'Follow-up SOQ dan ketersediaan stok',status:'Rencana'},
  {id:'plan-3',store_id:'m05',visit_date:'2026-11-13',start_time:'13:00',end_time:'15:00',pic_name:'SPV Area',agenda:'Review operasional dan SOP',status:'Rencana'}
 ],
 visits:[{id:'v1',store_id:'t01',visit_date:'2026-11-10',evaluator_name:'SPV Area',score:88,status:'Selesai'},{id:'v2',store_id:'m03',visit_date:'2026-11-09',evaluator_name:'SPV Area',score:77,status:'Selesai'}],
 checklists:[{id:'ck1',store_id:'t01',check_date:'2026-11-11',title:'Story WA Focus Selling',status:'Selesai'},{id:'ck2',store_id:'t01',check_date:'2026-11-11',title:'Foto opening store',status:'Belum'},{id:'ck3',store_id:'m03',check_date:'2026-11-11',title:'Daily briefing & foto',status:'Selesai'}],
 dso:[{id:'dso1',store_id:'m03',report_date:'2026-11-11',form_code:'OPENING',status:'Submitted'},{id:'dso2',store_id:'t01',report_date:'2026-11-11',form_code:'CLOSING',status:'Approved'}],
 visit_points:[],
 visit_templates:[
 {id:'vtemp-1',point_code:'FIN-01',section:'Finance',item_title:'Cash on hand cocok dengan sistem',sort_order:1,active:true},
 {id:'vtemp-2',point_code:'GA-01',section:'Asset & GA',item_title:'Kondisi listrik dan lampu toko',sort_order:2,active:true},
 {id:'vtemp-3',point_code:'MER-01',section:'Merchandise',item_title:'Penataan display sesuai planogram',sort_order:3,active:true}
 ],
 checklist_templates:[{id:'c-template-1',store_id:null,title:'Story WA Focus Selling',description:'Dokumentasikan aktivitas harian',active:true,category:'Sales',frequency:'Harian'}],
 dso_points:[{id:'dso-temp-1',form_code:'OPENING',point_code:'FACADE',label:'Foto fasad pintu masuk',description:'Foto opening toko',active:true,required:true,sort_order:1}],
 assignments:[]
});
