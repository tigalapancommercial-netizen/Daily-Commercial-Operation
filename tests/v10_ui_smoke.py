#!/usr/bin/env python3
"""Browser smoke with mocked responses only. No production writes."""
import asyncio, json, pathlib, threading, http.server, socketserver, io
from playwright.async_api import async_playwright
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[1]
PORT=8767
STORES=['TIGALAPANKAOS BTP','MAMU BTP','MAMU PALOPO','TIGALAPANKAOS PALU','MAMU TAMALATE','TIGALAPANKAOS MANADO','TIGALAPANKAOS SAMARINDA','MAMU KENDARI','TIGALAPANKAOS POLMAN','TIGALAPANKAOS BONE','MAMU GOWA','TIGALAPANKAOS TORAJA']
CFG=dict(kategori=['Operasional','IT & Sistem'],prioritas=['Kritis','Tinggi','Sedang','Rendah'],status=['Open','On Progress','Pending','Selesai','Dibatalkan'],dsoForms=[{'id':'OPENING','nama':'Opening Report','batas':'09:30'}],visitSeksi=[{'kode':'A','nama':'Finance'}],rating={'Excellent':95,'Good':85,'Need Improvement':75},minIssueVisit=15,bobot={'ceklis':25,'lapor':15,'dso':30,'visit':20,'masalah':10})
META=dict(cfg=CFG,today='2026-11-12',toko=STORES,tokoAll=[{'nama':x,'area':'Sulawesi','aktif':'Y'} for x in STORES],formDef=[{'id':'FD-001','form':'OPENING','label':'Foto depan toko','deskripsi':'Kondisi area depan','wajib':'Y','aktif':'Y','multi':'Y'},{'id':'FD-002','form':'OPENING','label':'Area kasir','deskripsi':'Periksa kerapian kasir','wajib':'Y','aktif':'Y','multi':'Y'}],visitDef=[{'id':'A01','kode':'A01','label':'Penggunaan kasir sesuai SOP','seksi':'A','aktif':'Y'},{'id':'A02','kode':'A02','label':'Dokumen pengeluaran','seksi':'A','aktif':'Y'}],users=[{'username':'master','nama':'Master','role':'MASTER','toko':'SEMUA','email':''}],spvList=['Master'])
DUMMY='2026-11/'+('a'*32)+'_XyZa9abcde.webp'
TRACK={'toko':STORES,'dates':['2026-11-12'],'forms':CFG['dsoForms'],'visit':{'n':0,'avg':None,'pending':0,'rating':{}},'jadwalHariIni':[],'jadwalMinggu':0,'rutinAktif':1,'bobot':CFG['bobot'],'grid':{t:{'2026-11-12':{'msLapor':0,'msNihil':0,'ckDone':0,'ckTot':2,'dso':{}}} for t in STORES},'score':{t:{'total':70,'ceklis':80,'lapor':0,'dso':20,'dsoOnTime':0,'dsoApproved':0,'visit':None,'visitRating':'','visitTgl':'','msOpen':0,'msOverdue':0} for t in STORES}}
SUMMARY=[dict(toko=t,checklist=dict(total=2,done=0,valid=0),dso=dict(total=1,submitted=0,approved=0),masalah=dict(lapor=0,nihil=0),visit=dict(planned=0,completed=0),issues=dict(pending=0)) for t in STORES]
ISSUE={'id':'VI-000001','visitId':'VS-00001','tanggal':'2026-11-12','toko':STORES[0],'pointId':'A01','seksi':'A','issue':'Contoh issue dummy','action':'Perbaiki','akar':'','pic':'Ari','dueDate':'2026-11-15','prioritas':'Tinggi','status':'Open','progress':0,'fotoId':'','validasi':''}
CEKLIS=[dict(id='CK-000001',tanggal='2026-11-12',toko=STORES[0],rutinId='RT-0001',judul='Pengecekan pembukaan toko',status='Belum',jam='',catatan='',fotoId='',validasi='',frekuensi='Harian',kategori='Operasional',deskripsi='',prioritas='Sedang',pic=''), dict(id='CK-000002',tanggal='2026-11-12',toko=STORES[0],rutinId='RT-0002',judul='Kebersihan showroom',status='Belum',jam='',catatan='',fotoId='',validasi='',frekuensi='Harian',kategori='Operasional',deskripsi='',prioritas='Sedang',pic='')]
DATA={"meta":META,"list":{"MASALAH":[],"DSO":[],"VISIT":[],"JADWAL":[],"RUTIN":[],"CEKLIS":[]},"tracking":TRACK,"notif":{"total":0,"today":"2026-11-12","items":[]},"storeSummary":SUMMARY,"ceklisHari":CEKLIS,"dsoHari":[],"issueList":[ISSUE],"backupList":[]}
FAKE='''
window.__MOCK=%s;
window.__photoCounter=0;
window.__uploadTypes=[];
window.__dcoSubmissions=[];
window.__dcoApi = async function(a,p,t){
 let M=window.__MOCK, data=[];
 switch(a){
 case 'login':data={token:'mock',username:'master',nama:'Master',role:'MASTER',toko:'SEMUA'};break;
 case 'list':data=M.list[p.type]||[];break;
 case 'ceklisSet':{let x=M.ceklisHari.find(z=>z.id===p.id);if(x){if(p.fotoId!==undefined)x.fotoId=p.fotoId;if(p.catatan!==undefined)x.catatan=p.catatan;if(p.status!==undefined)x.status=p.status?'Selesai':'Belum';}data=x||{};break;}
 case 'dsoPatch':data={jawaban:{}};break;
 case 'uploadFoto':{window.__uploadTypes.push(String(p.dataUrl||'').slice(0,30));let suffix=String(++window.__photoCounter).padStart(6,'0');data={id:'2026-11/'+('a'.repeat(32))+'_'+suffix+'.webp'};break;}
 case 'dsoSubmit':window.__dcoSubmissions.push(p);data={id:'DS-000001',form:p.form,slaSubmit:'Tepat Waktu'};break;
 default:data=M[a]??[];break;
 }
 return JSON.stringify({ok:true,data});
};
''' % json.dumps(DATA,ensure_ascii=False)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
async def main():
 # Network requests are intercepted locally; avoids network access / local HTTP restrictions.
 async with async_playwright() as pw:
  b=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
  count=0; errors=[]
  for width in [390,768,1280]:
   ctx=await b.new_context(viewport={'width':width,'height':900},permissions=['camera'])
   pg=await ctx.new_page();pg.on('pageerror',lambda e: errors.append(str(e)))
   await pg.add_init_script(FAKE)
   await pg.evaluate(FAKE)
   async def local(route):
    from urllib.parse import urlparse
    path=urlparse(route.request.url).path.lstrip('/') or 'index.html'
    if path=='src/main.js': return await route.fulfill(status=200,content_type='text/javascript',body='')
    f=(ROOT/path).resolve()
    if not f.is_relative_to(ROOT) or not f.is_file():return await route.fulfill(status=404,body='Not found')
    mime='text/html' if f.suffix=='.html' else 'text/javascript' if f.suffix=='.js' else 'application/octet-stream'
    return await route.fulfill(status=200,content_type=mime,body=f.read_bytes())
   await pg.route('**/*',local)
   await pg.set_content((ROOT/'index.html').read_text(encoding='utf-8'),wait_until='domcontentloaded')
   await pg.evaluate('''()=>{S.me={token:'mock',username:'master',nama:'Master',role:'MASTER',toko:'SEMUA'};boot();}''')
   await pg.wait_for_function('()=>S.meta&&S.meta.toko&&S.meta.toko.length===12')
   for menu in ['dash','ceklis','dso','MASALAH','jadwal','visit','issues','rutin','set']:
    await pg.locator(('#sideNav' if width>900 else '#bnav')+f' button[data-t="{menu}"]').click()
    await pg.wait_for_timeout(60)
    actual=await pg.evaluate('S.tab')
    assert actual==menu,(width,menu,actual)
    visible=await pg.evaluate("(x)=>!document.getElementById(x).classList.contains('hid')",dict(dash='pDash',ceklis='pCeklis',dso='pDso',MASALAH='pList',jadwal='pJadwal',visit='pVisit',issues='pIssues',rutin='pRutin',set='pSet')[menu])
    assert visible,(width,menu)
    count+=1
   # All executive dashboard section tabs must actually switch content.
   await pg.evaluate("()=>go('dash')")
   for dashboard_tab in ['ringkasan','kepatuhan','masalah','visit','score']:
    await pg.evaluate('(v)=>switchDashTab(v)', dashboard_tab)
    assert await pg.evaluate('S.dashTab')==dashboard_tab, dashboard_tab
    assert await pg.locator('#pDash .exec-root').count()==1
   # All schedule views must switch.
   await pg.evaluate("()=>go('jadwal')")
   for schedule_tab in ['week','list','month']:
    await pg.evaluate('(v)=>jdView(v)', schedule_tab)
    assert await pg.evaluate('S.jdView')==schedule_tab, schedule_tab
   # dashboard tab switch and correct module navigation for store overview
   await pg.evaluate("()=>{go('dash');S.dashTab='kepatuhan';}")
   await pg.wait_for_timeout(120)
   await pg.evaluate("()=>switchDashTab('kepatuhan')")
   await pg.locator('#pDash .v6-status-table tbody tr:first-child td:nth-child(2)').click()
   await pg.wait_for_timeout(120)
   assert await pg.evaluate('S.tab')=='ceklis','Tracking toko clicked but did not navigate'
   # checklist: choose store and confirm always-visible evidence controls
   await pg.evaluate("()=>{go('ceklis');$('ckToko').value='TIGALAPANKAOS BTP';loadCeklis();}")
   await pg.wait_for_timeout(170)
   assert await pg.locator('#ckIsi .ck-evidence .evidence-panel').count()>=1,'Checklist photo hidden'
   assert await pg.locator('#ckIsi .ck-evidence input[capture=environment]').count()==2, 'Native camera options not available on both checklist cards'
   if width in (390,1280):
    await pg.screenshot(path=str(ROOT/'tests'/f'preview_assignment_{width}.png'), full_page=False)
   # gallery: add two separate images (unless mobile platform requires native file picker)
   im=Image.new('RGB',(1800,1200),'#7185bd');out=io.BytesIO();im.save(out,format='JPEG',quality=92);jpeg=out.getvalue()
   picker=pg.locator('#ckIsi .ck-evidence input[type=file][multiple]').first
   await picker.set_input_files([{'name':'foto1.jpg','mimeType':'image/jpeg','buffer':jpeg},{'name':'foto2.jpg','mimeType':'image/jpeg','buffer':jpeg}])
   await pg.wait_for_function("() => photoList(S.ckRows[0].fotoId).length === 2",timeout=12000)
   val=await pg.evaluate("photoList(S.ckRows[0].fotoId)")
   assert len(val)==2 and val[0]!=val[1]
   if width in (390,1280):
    await pg.screenshot(path=str(ROOT/'tests'/f'preview_gallery_{width}.png'), full_page=False)
   # verify separate WebP uploads (mock observes MIME base64)
   await pg.evaluate("()=>go('dso')")
   await pg.evaluate("()=>{$('dsToko').value='TIGALAPANKAOS BTP';loadDso();}")
   await pg.wait_for_timeout(190)
   assert await pg.locator('#dsBody .dsoit .evidence-panel').count()==2,'DSO panels missing'
   if width==1280:
    await pg.locator('#dsBody .dsoit input[type=file][multiple]').first.set_input_files([
      {'name':'depan1.jpg','mimeType':'image/jpeg','buffer':jpeg},
      {'name':'depan2.jpg','mimeType':'image/jpeg','buffer':jpeg}])
    await pg.wait_for_function("()=>photoList(S.dsJaw['FD-001']).length===2",timeout=12000)
    assert await pg.evaluate("()=>photoList(S.dsJaw['FD-001']).length") == 2
    await pg.locator('#dsBody .dsoit input[type=file][multiple]').last.set_input_files([
      {'name':'kasir1.jpg','mimeType':'image/jpeg','buffer':jpeg}])
    await pg.wait_for_function("()=>photoList(S.dsJaw['FD-002']).length===1",timeout=12000)
    await pg.evaluate("()=>dsoKirim()")
    await pg.wait_for_function("()=>__dcoSubmissions.length>0",timeout=12000)
    assert await pg.evaluate("()=>__dcoSubmissions[0].jawaban['FD-001'].startsWith('[')"), 'DSO submit lost multi-photo list'
   await pg.evaluate("()=>go('visit')")
   await pg.wait_for_timeout(120)
   await pg.evaluate("()=>openVisit()")
   assert await pg.locator('#vBody .vitem .evidence-panel').count()==2, 'Visit point photo missing'
   assert await pg.locator('#vBody .visit-issue-card .evidence-panel').count()>=3,'Visit issues photo missing'
   # Simulate camera stream, play and video image in the sandbox (no physical webcam).
   # Chromium's about:blank context does not provide a secure-origin webcam video stream.
   await pg.evaluate('''()=>{let source=document.createElement('canvas');source.width=640;source.height=480;
    const c=source.getContext('2d');c.fillStyle='#3276ab';c.fillRect(0,0,640,480);c.fillStyle='#fff';c.font='bold 30px Arial';c.fillText('CAMERA TEST',40,210);
    window.mockSourceCanvas=source;
    const draw=CanvasRenderingContext2D.prototype.drawImage;
    CanvasRenderingContext2D.prototype.drawImage=function(img,...args){return draw.call(this,img instanceof HTMLVideoElement?window.mockSourceCanvas:img,...args);};
    Object.defineProperty(HTMLVideoElement.prototype,'videoWidth',{configurable:true,get(){return 640;}});
    Object.defineProperty(HTMLVideoElement.prototype,'videoHeight',{configurable:true,get(){return 480;}});
    HTMLMediaElement.prototype.play=function(){return Promise.resolve();};
    Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>new MediaStream()}});
   }''')
   # direct camera button shows preview (camera permission fake)
   await pg.locator('#vBody .vitem .evidence-panel button:has-text("Foto langsung")').first.click()
   assert await pg.locator('#dcoCameraModal.on').count()==1
   if width in (390,1280):
    await pg.screenshot(path=str(ROOT/'tests'/f'preview_camera_{width}.png'), full_page=False)
   await pg.wait_for_function("()=>document.querySelector('#evidenceCameraVideo').videoWidth>0", timeout=8000)
   await pg.locator('#dcoCameraModal button:has-text("Ambil foto")').click()
   await pg.wait_for_function('()=>cameraEvidence.files.length===1',timeout=8000)
   await pg.locator('#dcoCameraModal button:has-text("Ambil foto")').click()
   await pg.wait_for_function('()=>cameraEvidence.files.length===2',timeout=8000)
   await pg.locator('#evidenceCameraSave').click()
   await pg.wait_for_function("()=>photoList(S.vis.foto['A01']).length===2",timeout=12000)
   assert await pg.locator('#dcoCameraModal.on').count()==0
   assert await pg.evaluate("()=>__uploadTypes.every(x=>x.startsWith('data:image/webp;base64,'))"), 'Uploads were not WebP'
   await pg.locator('#vBody .vitem .evidence-panel img').first.wait_for(timeout=5000)
   # a second camera session can be opened/closed without retaining a stream
   await pg.locator('#vBody .vitem .evidence-panel button:has-text("Foto langsung")').first.click()
   await pg.get_by_role('button',name='Tutup').last.click()
   assert await pg.evaluate("()=>cameraEvidence.stream === null")
   await pg.evaluate("()=>{closeM('mVisit');go('MASALAH');}")
   await pg.evaluate("()=>openForm()")
   assert await pg.locator('#fBody .evidence-panel button:has-text("Foto langsung")').count()==1,'Form photo missing'
   await pg.evaluate("()=>{closeM('mForm');go('issues');}")
   await pg.wait_for_timeout(120)
   await pg.evaluate("()=>editVisitIssue(0)")
   assert await pg.locator('#gBody .evidence-panel').count()==1,'Issue photo missing'
   await pg.evaluate("()=>closeM('mGen')")
   dims=await pg.evaluate('({w:document.documentElement.scrollWidth,inner:innerWidth})')
   assert dims['w']<=width+12,(width,'overflow',dims)
   await pg.screenshot(path=str(ROOT/'tests'/f'v10_smoke_{width}.png'))
   await ctx.close()
  await b.close()
  print(json.dumps({'ok':not errors,'navigation_checks':count,'widths':[390,768,1280],'browser_errors':errors},indent=2))
  if errors:raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())
