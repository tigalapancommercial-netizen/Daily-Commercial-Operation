#!/usr/bin/env python3
"""Local browser UI tests using simulated data. No Supabase credentials or writes."""
import asyncio, importlib.util, pathlib, io, json, re
from playwright.async_api import async_playwright
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('old_v10',ROOT/'tests'/'v10_ui_smoke.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old.DATA['meta']['cfg']['visitSeksi']=[dict(kode=k,nama=n) for k,n in [('A','Finance'),('B','Asset & GA'),('C','Merchandise'),('D','Human Resources'),('E','Warehouse')]]
old.DATA['meta']['visitDef']=[dict(id=k+'01',kode=k+'01',seksi=k,label='Item '+k,aktif='Y') for k in 'ABCDE']
MOCK=old.FAKE[:old.FAKE.find(' % json.dumps')] if False else old.FAKE
# old.FAKE is a formatted string containing pre-revision fixture, so replace the literal declaration instead.
MOCK=MOCK.replace('"visitSeksi": [{"kode": "A", "nama": "Finance"}]', '"visitSeksi": [{"kode": "A", "nama": "Finance"}, {"kode": "B", "nama": "Asset & GA"}, {"kode": "C", "nama": "Merchandise"}, {"kode": "D", "nama": "Human Resources"}, {"kode": "E", "nama": "Warehouse"}]')
# Use a full fixture replacement for visitDef with the same number of tokens.
MOCK=re.sub(r'"visitDef": \[\{"id": "A01".*?\}\], "users":', '"visitDef": [{"id":"A01","kode":"A01","seksi":"A","label":"Item A","aktif":"Y"},{"id":"B01","kode":"B01","seksi":"B","label":"Item B","aktif":"Y"},{"id":"C01","kode":"C01","seksi":"C","label":"Item C","aktif":"Y"},{"id":"D01","kode":"D01","seksi":"D","label":"Item D","aktif":"Y"},{"id":"E01","kode":"E01","seksi":"E","label":"Item E","aktif":"Y"}], "users":',MOCK)
async def main():
 errors=[]; checks=0
 pic=Image.new('RGB',(1300,800),'#7789be');buffer=io.BytesIO();pic.save(buffer,format='JPEG',quality=88);jpg=buffer.getvalue()
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
  for width in [390,768,1280]:
   ctx=await browser.new_context(viewport={'width':width,'height':1000},permissions=['camera'])
   page=await ctx.new_page();page.on('pageerror',lambda e:errors.append(f'{width}: {e}'))
   await page.add_init_script(MOCK)
   async def local(route):
    from urllib.parse import urlparse
    path=urlparse(route.request.url).path.lstrip('/') or 'index.html'
    if path=='src/main.js':return await route.fulfill(status=200,content_type='text/javascript',body='')
    f=(ROOT/path).resolve()
    if not f.is_relative_to(ROOT) or not f.is_file():return await route.fulfill(status=404,body='Not found')
    mime='text/html' if f.suffix=='.html' else 'text/javascript' if f.suffix=='.js' else 'application/octet-stream'
    return await route.fulfill(status=200,content_type=mime,body=f.read_bytes())
   await page.route('**/*',local)
   await page.set_content((ROOT/'index.html').read_text(encoding='utf-8'),wait_until='domcontentloaded')
   await page.evaluate(MOCK)
   await page.evaluate("()=>{S.me={token:'mock',username:'master',nama:'Master',role:'MASTER',toko:'SEMUA'};boot();}")
   await page.wait_for_function('()=>S.meta && S.meta.toko && S.meta.toko.length===12')
   for menu in ['dash','ceklis','dso','MASALAH','jadwal','visit','issues','rutin','set']:
    await page.evaluate('(v)=>go(v)',menu)
    await page.wait_for_timeout(35)
    assert await page.evaluate('S.tab')==menu,(width,menu)
    checks+=1
   await page.evaluate("()=>{go('ceklis');$('ckToko').value='TIGALAPANKAOS BTP';loadCeklis();}")
   await page.wait_for_function('()=>document.querySelectorAll("#ckIsi .ckrow").length===2')
   assert await page.locator('#ckIsi .photo-chip').count()==2
   assert await page.locator('#ckIsi .evidence-actions').count()==0,'Old three buttons still visible'
   assert await page.locator('#ckIsi .photo-chip:has-text("Foto")').count()==2
   dims=await page.evaluate('({body:document.documentElement.scrollWidth,win:innerWidth})');assert dims['body']<=width+6,(width,dims)
   if width in (390,1280):await page.screenshot(path=str(ROOT/'tests'/f'v11_assignment_{width}.png'))
   await page.locator('#ckIsi .photo-chip').first.click()
   assert await page.locator('#dcoCameraModal.on').count()==1
   assert await page.locator('#evidenceHubActions input[type=file]').count()==2
   assert await page.locator('#evidenceHubActions .btn').count()==3
   if width in (390,1280):await page.screenshot(path=str(ROOT/'tests'/f'v11_gallery_{width}.png'))
   await page.locator('#evidenceHubActions input[type=file][multiple]').set_input_files([{'name':'one.jpg','mimeType':'image/jpeg','buffer':jpg},{'name':'two.jpg','mimeType':'image/jpeg','buffer':jpg}])
   await page.wait_for_function('()=>photoList(S.ckRows[0].fotoId).length===2',timeout=18000)
   assert await page.locator('#evidenceHubGallery .evidence-thumb').count()==2
   assert await page.evaluate("()=>__uploadTypes.every(x=>x.startsWith('data:image/webp;base64,'))")
   assert '2' in (await page.locator('#ck0 .photo-chip').inner_text()), 'Checklist auto-complete may reorder rows; target stable ID'
   # Remove photo from hub: only the selected one must be detached.
   await page.evaluate("()=>{window.confirm=()=>true;}")
   await page.locator('#evidenceHubGallery .evidence-remove').first.click()
   await page.wait_for_function('()=>photoList(S.ckRows[0].fotoId).length===1',timeout=9000)
   await page.locator('#evidenceHubClose').click()
   await page.evaluate("()=>{go('dso');$('dsToko').value='TIGALAPANKAOS BTP';loadDso();}")
   await page.wait_for_function('()=>document.querySelectorAll("#dsBody .dsoit .photo-chip").length===2')
   assert await page.locator('#dsBody .evidence-actions').count()==0
   
   assert await page.locator('#dsBody .dsoit .ph:visible').count()==0
   await page.locator('#dsBody .dsoit .photo-chip').first.click()
   await page.locator('#evidenceHubActions input[type=file][multiple]').set_input_files([{'name':'a.jpg','mimeType':'image/jpeg','buffer':jpg},{'name':'b.jpg','mimeType':'image/jpeg','buffer':jpg}])
   await page.wait_for_function("()=>photoList(S.dsJaw['FD-001']).length===2",timeout=18000)
   await page.locator('#evidenceHubClose').click()
   await page.evaluate("()=>{go('visit');S.visits=[];renderVisits();}")
   labels=await page.locator('#visitTbl th.visit-seksi-head').all_inner_texts()
   assert labels==['A\nFinance','B\nAset/GA','C\nMerchandise','D\nSDM','E\nGudang'],(width,labels)
   if width in (390,1280):await page.screenshot(path=str(ROOT/'tests'/f'v11_header_{width}.png'))
   await page.evaluate("()=>openVisit(null)")
   assert await page.locator('#vBody .vitem .photo-chip').count()==5
   if width in (390,1280):await page.screenshot(path=str(ROOT/'tests'/f'v11_visit_{width}.png'))
   await page.locator('#vBody .vitem .photo-chip').first.click()
   assert await page.locator('#dcoCameraModal.on').count()==1
   # Ensure the camera is requested only on click, not when opening the gallery.
   assert await page.locator('#evidenceCameraStage:visible').count()==0
   await page.evaluate('''()=>{let source=document.createElement('canvas');source.width=640;source.height=480;
    let ctx=source.getContext('2d');ctx.fillStyle='#3276ab';ctx.fillRect(0,0,640,480);ctx.fillStyle='#fff';ctx.font='bold 30px Arial';ctx.fillText('CAMERA TEST',40,200);
    window.mockSourceCanvas=source;
    const draw=CanvasRenderingContext2D.prototype.drawImage;
    CanvasRenderingContext2D.prototype.drawImage=function(img,...args){return draw.call(this,img instanceof HTMLVideoElement?window.mockSourceCanvas:img,...args);};
    Object.defineProperty(HTMLVideoElement.prototype,'videoWidth',{configurable:true,get(){return 640;}});
    Object.defineProperty(HTMLVideoElement.prototype,'videoHeight',{configurable:true,get(){return 480;}});
    HTMLMediaElement.prototype.play=function(){return Promise.resolve();};
    Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>new MediaStream()}});
   }''')
   await page.locator('#evidenceHubActions button:has-text("Foto langsung")').click()
   await page.wait_for_function('()=>!document.querySelector("#evidenceCameraStage").hidden',timeout=5000)
   for n in [1,2]:
    await page.locator('#evidenceCameraStage button:has-text("Ambil foto")').click()
    await page.wait_for_function(f'()=>cameraEvidence.files.length==={n}',timeout=9000)
   await page.locator('#evidenceCameraSave').click()
   await page.wait_for_function("()=>photoList(S.vis.foto['A01']).length===2",timeout=18000)
   assert await page.locator('#dcoCameraModal.on').count()==1,'Hub should remain open after photo save'
   assert await page.locator('#evidenceHubGallery .evidence-thumb').count()==2
   assert await page.evaluate("()=>__uploadTypes.every(x=>x.startsWith('data:image/webp;base64,'))")
   await page.locator('#evidenceHubClose').click()
   dims=await page.evaluate('({body:document.documentElement.scrollWidth,win:innerWidth})')
   assert dims['body']<=width+8,(width,'overflow visit',dims)
   checks+=9
   await ctx.close()
  await browser.close()
 print(json.dumps({'checks':checks,'widths':[390,768,1280],'page_errors':errors},ensure_ascii=False,indent=2))
 if errors:raise RuntimeError('Browser JS errors')
if __name__=='__main__':asyncio.run(main())
