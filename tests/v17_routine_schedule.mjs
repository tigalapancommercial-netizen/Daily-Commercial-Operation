import assert from 'node:assert/strict';
import fs from 'node:fs';
// Extract only the standalone routine logic so this test needs no npm install or Supabase connection.
const source = fs.readFileSync(new URL('../src/server/core.js',import.meta.url),'utf8');
const body = source.slice(source.indexOf('const ROUTINE_FREQUENCIES'),source.indexOf('export async function ceklisSet_')).replaceAll('export ','');
const mustMgr_=me=>{if(!me.isMgr)throw new Error('Hanya SPV Area / Master');};
const tokoAktif_=async ctx=>(await ctx.read('TOKO')).filter(r=>r.aktif!=='N').map(r=>r.nama);
const pad_=(n,l)=>String(n).padStart(l,'0');
const daysBetween_=(a,b)=>(Date.parse(b+'T00:00:00Z')-Date.parse(a+'T00:00:00Z'))/86400000;
const today_=()=> '2026-11-13';
const now_=()=> '2026-11-13 08:00:00';
const {rutinBerlaku_,rutinSave_,ceklisHari_} = new Function('mustMgr_','tokoAktif_','pad_','daysBetween_','today_','now_', body+'\nreturn {rutinBerlaku_,rutinSave_,ceklisHari_};')(mustMgr_,tokoAktif_,pad_,daysBetween_,today_,now_);
const toko='TIGALAPANKAOS BTP';let count=0;
const must=(ok,label)=>{assert(ok,label);count++;};
const row=(f,props={})=>({aktif:'Y',toko:'SEMUA',frekuensi:f,mulai:'2026-11-13',akhir:'',hari:'',interval:'',...props});
must(rutinBerlaku_(row('Sekali'),'2026-11-13',toko),'Sekali on start');
must(!rutinBerlaku_(row('Sekali'),'2026-11-14',toko),'Sekali not next day');
must(rutinBerlaku_(row('Rentang',{akhir:'2026-11-17'}),'2026-11-17',toko),'Rentang inclusive');
must(!rutinBerlaku_(row('Rentang',{akhir:'2026-11-17'}),'2026-11-18',toko),'Rentang ended');
must(rutinBerlaku_(row('Periodik',{interval:'3'}),'2026-11-16',toko),'Periodik day 3');
must(!rutinBerlaku_(row('Periodik',{interval:'3'}),'2026-11-17',toko),'Periodik day 4');
must(rutinBerlaku_(row('Mingguan',{hari:'5',mulai:''}),'2026-11-13',toko),'Friday weekly');
must(!rutinBerlaku_(row('Mingguan',{hari:'5',mulai:''}),'2026-11-14',toko),'Saturday off');
must(rutinBerlaku_(row('Bulanan',{hari:'13',mulai:''}),'2026-12-13',toko),'Monthly');
must(rutinBerlaku_(row('Tahunan',{hari:'13-11',mulai:''}),'2027-11-13',toko),'Yearly');
must(!rutinBerlaku_(row('Harian',{aktif:'N'}),'2026-11-13',toko),'Disabled');
must(!rutinBerlaku_(row('Harian',{toko:'MAMU BTP'}),'2026-11-13',toko),'Different store');
must(!rutinBerlaku_(row('Harian',{akhir:'2026-11-12'}),'2026-11-13',toko),'End date filter');
const ctx={
 me:{isMgr:true,nama:'Master'},
 read:async (type)=>type==='TOKO'?[{nama:toko,aktif:'Y'},{nama:'MAMU BTP',aktif:'Y'}]:type==='RUTIN'?[]:type==='CEKLIS'?[{id:'CK-00001',rutinId:'RT-deleted',tanggal:'2026-11-13',toko,judul:'Historical already completed',status:'Selesai',fotoId:'old.webp',validasi:'Y'}]:[],
 save:async(t,rs)=>rs.map(x=>({...x,id:'RT-0001'})),
};
const saved=await rutinSave_(ctx,{judul:'Visit',frekuensi:'Sekali',mulai:'2026-11-13',toko,jenisTugas:'Kunjungan Sekolah'});
must(saved.frekuensi==='Sekali'&&saved.jenisTugas==='Kunjungan Sekolah','Save full metadata');
await assert.rejects(()=>rutinSave_(ctx,{judul:'Bad',frekuensi:'Sekali',mulai:'2026-02-31',toko}),/Tanggal/);count++;
await assert.rejects(()=>rutinSave_(ctx,{judul:'Wrong',frekuensi:'Sekali',mulai:'2026-11-13',toko:'FAKE STORE'}),/Toko/);count++;
const hist=await ceklisHari_(ctx,'2026-11-13',toko);
must(hist.length===1&&hist[0].status==='Selesai'&&hist[0].fotoId==='old.webp','Historical checklist retained after template gone');
await assert.rejects(()=>rutinSave_({...ctx,me:{isMgr:false,nama:'Store'}},{judul:'No Access'}),/Master|SPV|tidak/);count++;
console.log(JSON.stringify({checks:count,status:'pass'}));
