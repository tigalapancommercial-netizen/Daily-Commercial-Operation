#!/usr/bin/env python3
"""Offline browser smoke. Uses mocks; no live Supabase writes."""
import asyncio, base64, io, json, pathlib
from PIL import Image
from playwright.async_api import async_playwright
from v10_ui_smoke import FAKE
ROOT=pathlib.Path(__file__).resolve().parents[1]
PHOTO='2026-11/'+('a'*32)+'_abc12345.webp'

async def run():
    checks=[]; errors=[]
    im=Image.new('RGB',(1100,800),'#7194ac'); buff=io.BytesIO();im.save(buff,'JPEG',quality=84); jpeg=buff.getvalue()
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
        for width in [390,768,1280]:
            context=await browser.new_context(viewport={'width':width,'height':900},permissions=['camera'])
            page=await context.new_page();page.on('pageerror',lambda e: errors.append(f'{width}: {e}'))
            await page.add_init_script(FAKE)
            async def local(route):
                from urllib.parse import urlparse
                path=urlparse(route.request.url).path.lstrip('/') or 'index.html'
                if path=='src/main.js':return await route.fulfill(status=200,content_type='text/javascript',body='')
                f=(ROOT/path).resolve()
                if not f.is_relative_to(ROOT) or not f.is_file():return await route.fulfill(status=404,body='Not found')
                return await route.fulfill(status=200,content_type='text/html' if f.suffix=='.html' else 'text/javascript',body=f.read_bytes())
            await page.route('**/*',local)
            await page.set_content((ROOT/'index.html').read_text(encoding='utf8'),wait_until='domcontentloaded')
            await page.evaluate(FAKE)
            await page.evaluate('''()=>{
              S.me={token:'mock',username:'master',nama:'Master',role:'MASTER',toko:'SEMUA'};
              window.__captureSources=[];window.__dsoRejected=false;
              const original=window.__dcoApi;
              window.__dcoApi=async (a,p,t)=>{
                if(a==='uploadFoto')window.__captureSources.push(p.captureSource||'galeri');
                if(a==='dsoSubmit'&&!window.__dsoRejected){window.__dsoRejected=true;
                  return JSON.stringify({ok:false,error:'Foto wajib belum lengkap: Pengecekan fasilitas toko'});}
                if(a==='fotoReceipt')return JSON.stringify({ok:true,data:{verified:true,source:'kamera_live',uploadedAt:'2026-11-13T08:00:00Z',checksum:'c'.repeat(64)}});
                return original(a,p,t);
              };
              window.__dcoServerNow=()=>Date.parse('2026-11-13T08:19:30.000Z');
              window.__dcoSyncClock=async ()=>({now_ms:Date.parse('2026-11-13T08:19:30.000Z')});
              boot();
            }''')
            await page.wait_for_function('()=>S.meta&&S.meta.formDef&&S.meta.formDef.length>0')
            # Top-level menu routes still navigate instead of staying on the same page.
            for menu in ['dash','ceklis','dso','MASALAH','jadwal','visit','issues','rutin','set']:
                await page.evaluate('(tab)=>go(tab)',menu)
                assert await page.evaluate('S.tab')==menu,(width,menu)
                checks.append(f'{width}:route:{menu}')
            await page.evaluate("()=>{go('dso');$('dsToko').value='TIGALAPANKAOS BTP';loadDso();}")
            await page.wait_for_function('()=>document.querySelectorAll("#dsBody .dsoit").length===2')
            # A missing-photo submit never calls Supabase and highlights missing rows.
            await page.evaluate('()=>dsoKirim()')
            assert await page.locator('#dsBody .dco-missing-photo').count()==2
            assert await page.locator('#dcoDsoSubmitFeedback').count()==1
            checks.append(f'{width}:local_validation')
            # Real UI gallery input to process one item with multiple independent WebP images.
            await page.locator('#dsBody .dsoit .photo-chip >> nth=0').click()
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'foto1.jpg','mimeType':'image/jpeg','buffer':jpeg},
                {'name':'foto2.jpg','mimeType':'image/jpeg','buffer':jpeg},
            ])
            await page.wait_for_function("()=>photoList(S.dsJaw['FD-001']).length===2",timeout=18000)
            await page.locator('#evidenceHubClose').click()
            await page.locator('#dsBody .dsoit .photo-chip >> nth=1').click()
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([{'name':'foto3.jpg','mimeType':'image/jpeg','buffer':jpeg}])
            await page.wait_for_function("()=>photoList(S.dsJaw['FD-002']).length===1",timeout=18000)
            await page.locator('#evidenceHubClose').click()
            assert await page.evaluate('()=>__uploadTypes.every(t=>t.startsWith("data:image/webp;base64,"))')
            checks.append(f'{width}:webp_multi_upload')
            if width in [390,1280]:
                await page.screenshot(path=str(ROOT/'tests'/f'v13_dso_ready_{width}.png'))
            # Simulate legacy backend rejecting 2 images: retain all photos + user-facing migration advice.
            await page.evaluate('()=>dsoKirim()')
            await page.wait_for_function('()=>document.querySelector("#dcoDsoSubmitFeedback")?.textContent?.includes("SQL")',timeout=12000)
            assert await page.evaluate("()=>photoList(S.dsJaw['FD-001']).length===2&&photoList(S.dsJaw['FD-002']).length===1")
            checks.append(f'{width}:server_rejection_preserves_photos')
            if width in [390,1280]:
                await page.screenshot(path=str(ROOT/'tests'/f'v13_dso_error_{width}.png'))
            # Second request succeeds; complete multi-photo list is sent.
            await page.evaluate('()=>dsoKirim()')
            await page.wait_for_function('()=>__dcoSubmissions.length===1',timeout=15000)
            a=await page.evaluate('window.__dcoSubmissions[0].jawaban')
            assert len(json.loads(a['FD-001']))==2 and a['FD-002'].endswith('.webp')
            checks.append(f'{width}:complete_submission')
            # Simulated live camera: pixel-level stamp is visible on the saved image.
            await page.evaluate('''()=>{
              go('visit');openVisit();
              const source=document.createElement('canvas');source.width=640;source.height=480;
              const c=source.getContext('2d');c.fillStyle='#61a3cf';c.fillRect(0,0,640,480);
              window.mockSourceCanvas=source;
              const draw=CanvasRenderingContext2D.prototype.drawImage;
              CanvasRenderingContext2D.prototype.drawImage=function(img,...args){return draw.call(this,img instanceof HTMLVideoElement?window.mockSourceCanvas:img,...args);};
              Object.defineProperty(HTMLVideoElement.prototype,'videoWidth',{configurable:true,get(){return 640;}});
              Object.defineProperty(HTMLVideoElement.prototype,'videoHeight',{configurable:true,get(){return 480;}});
              HTMLMediaElement.prototype.play=function(){return Promise.resolve();};
              Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>new MediaStream()}});
            }''')
            await page.locator('#vBody .vitem .photo-chip').first.click()
            await page.locator('#dcoCameraModal button:has-text("Foto langsung")').click()
            await page.wait_for_function('()=>document.querySelector("#evidenceCameraVideo").videoWidth>0')
            await page.locator('#dcoCameraModal button:has-text("Ambil foto")').click()
            await page.wait_for_function('()=>cameraEvidence.files.length===1')
            if width in [390,1280]:
                await page.screenshot(path=str(ROOT/'tests'/f'v13_camera_stamp_{width}.png'))
            pixel=await page.evaluate('''async ()=>{
              const bmp=await createImageBitmap(cameraEvidence.files[0]),c=document.createElement('canvas');
              c.width=bmp.width;c.height=bmp.height;const cx=c.getContext('2d');cx.drawImage(bmp,0,0);
              const pixel=(x,y)=>Array.from(cx.getImageData(x,y,1,1).data).slice(0,3);
              return {source:cameraEvidence.files[0].__dcoCaptureSource,top:pixel(15,15),bottom:pixel(15,c.height-4)};
            }''')
            assert pixel['source']=='kamera_live'
            assert pixel['top']!=pixel['bottom'],pixel
            checks.append(f'{width}:live_wita_watermark')
            await page.locator('#evidenceCameraSave').click()
            await page.wait_for_function("()=>photoList(S.vis.foto['A01']).length===1",timeout=18000)
            assert 'kamera_live' in await page.evaluate('window.__captureSources')
            checks.append(f'{width}:camera_source_audit')
            # Verify photo receipt is visible in photo lightbox (mocked server confirmation).
            await page.locator('#dcoCameraModal .evidence-thumb img').first.click()
            await page.wait_for_function('()=>document.querySelector("#dcoPhotoProof")?.textContent?.includes("Diterima server")')
            assert await page.locator('#dcoPhotoProof').count()==1
            if width in [390,1280]:
                await page.screenshot(path=str(ROOT/'tests'/f'v13_watermark_verified_{width}.png'))
            await page.locator('#lb').click(position={'x':5,'y':5})
            checks.append(f'{width}:receipt_detail')
            dims=await page.evaluate('({scroll:document.documentElement.scrollWidth,width:innerWidth})')
            assert dims['scroll']<=dims['width']+12,(width,dims)
            checks.append(f'{width}:responsive')
            if width in [390,1280]:
                await page.locator('#evidenceHubClose').click()
                await page.screenshot(path=str(ROOT/'tests'/f'v13_visit_{width}.png'))
            await context.close()
        await browser.close()
    report={'checks':len(checks),'widths':[390,768,1280],'browser_errors':errors,'check_names':checks}
    (ROOT/'tests'/'v13_regression_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:report[k] for k in ['checks','widths','browser_errors']},indent=2))
    if errors:raise AssertionError(errors)

if __name__=='__main__':asyncio.run(run())
