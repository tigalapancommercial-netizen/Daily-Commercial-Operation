#!/usr/bin/env python3
"""Browser smoke for v12 before/after evidence. Fully mocked; no real Supabase data writes."""
import asyncio, pathlib, importlib.util, io, json, base64
from PIL import ImageDraw
from PIL import Image
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixture', ROOT/'tests'/'v10_ui_smoke.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
MOCK=fixture.FAKE

async def run():
    checks=0; errors=[]
    im=Image.new('RGB',(1500,1000),'#87a0bb');buff=io.BytesIO();im.save(buff,format='JPEG',quality=89);jpg=buff.getvalue()
    def graphic(label,bg):
        canvas=Image.new('RGB',(700,550),bg);draw=ImageDraw.Draw(canvas)
        draw.rectangle((55,65,645,485),fill='#eceff5',outline='#50627c',width=6)
        draw.rectangle((135,170,565,390),fill='#d0dae4' if label=='SEBELUM' else '#a8e5c6')
        draw.text((80,95),label,fill='#17223c',stroke_width=0)
        buf=io.BytesIO();canvas.save(buf,format='JPEG',quality=82)
        return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
    preview_imgs={'before':graphic('SEBELUM','#dfb5a4'),'after':graphic('SESUDAH','#b8dbcd')}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in [390,768,1280]:
            ctx=await browser.new_context(viewport={'width':width,'height':960},permissions=['camera'])
            page=await ctx.new_page();page.on('pageerror', lambda e: errors.append(f'{width}: {e}'))
            await page.add_init_script(MOCK)
            async def local(route):
                from urllib.parse import urlparse
                path=urlparse(route.request.url).path.lstrip('/') or 'index.html'
                if path=='src/main.js':return await route.fulfill(status=200,content_type='text/javascript',body='')
                f=(ROOT/path).resolve()
                if not f.is_relative_to(ROOT) or not f.is_file():return await route.fulfill(status=404,body='Not found')
                return await route.fulfill(status=200,content_type='text/html' if f.suffix=='.html' else 'text/javascript',body=f.read_bytes())
            await page.route('**/*',local)
            await page.set_content((ROOT/'index.html').read_text(encoding='utf8'),wait_until='domcontentloaded')
            await page.evaluate(MOCK)
            await page.evaluate('''(p)=>{window.__dcoFotoUrl=(id)=>String(id).includes('000003')||String(id).includes('oldBefore')?p.before:p.after}''',preview_imgs)
            await page.evaluate('''()=>{window.__issueUpdated=[];const old=window.__dcoApi;
              window.__dcoApi=async (name,p,token)=>{
                if(name==='issueUpdate'){window.__issueUpdated.push(p.data);Object.assign(window.__MOCK.issueList[0],p.data);return JSON.stringify({ok:true,data:window.__MOCK.issueList[0]});}
                return old(name,p,token);
              };
              S.me={token:'mock',username:'master',nama:'Master',role:'MASTER',toko:'SEMUA'};boot();}''')
            await page.wait_for_function('()=>S.meta&&S.meta.toko&&S.meta.toko.length===12')
            await page.evaluate("()=>{go('issues');$('isToko').value='SEMUA';loadIssues();}")
            await page.wait_for_function('()=>S.issues&&S.issues.length>0')
            await page.locator('#issueTbl button:has-text("Update")').first.click()
            assert await page.locator('#gBody .photo-chip').count()==1
            await page.locator('#gBody .photo-chip').click()
            assert await page.locator('#dcoCameraModal.on').count()==1
            assert await page.locator('#dcoCameraModal .ba-group').count()==2
            assert await page.locator('#dcoCameraModal .ba-group.active').count()==1
            # 'Sesudah' is selected by default, upload 2 photos.
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'after1.jpg','mimeType':'image/jpeg','buffer':jpg},
                {'name':'after2.jpg','mimeType':'image/jpeg','buffer':jpg}])
            await page.wait_for_function('()=>photoList(S.issueAfterTemp).length===2',timeout=18000)
            assert await page.locator('.ba-group[data-photo-phase="after"] .evidence-thumb').count()==2
            assert await page.evaluate("()=>__uploadTypes.every(x=>x.startsWith('data:image/webp;base64,'))")
            await page.locator('.ba-heading:has-text("SEBELUM")').click()
            assert await page.evaluate('cameraEvidence.kind')=='issue'
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'before1.jpg','mimeType':'image/jpeg','buffer':jpg}])
            await page.wait_for_function('()=>photoList(S.issueFotoTemp).length===1',timeout=18000)
            assert await page.locator('.ba-group[data-photo-phase="before"] .evidence-thumb').count()==1
            if width in [390,1280]:
                await page.screenshot(path=str(ROOT/'tests'/f'v12_before_after_{width}.png'))
            await page.locator('#evidenceHubClose').click()
            await page.locator('#g_updateNote').fill('Kondisi sudah diperbaiki')
            await page.locator('#gSave').click()
            await page.wait_for_function('()=>__issueUpdated.length===1',timeout=10000)
            submission=await page.evaluate('window.__issueUpdated[0]')
            assert len(json.loads(submission['fotoAfter']))==2 and submission['updateNote']=='Kondisi sudah diperbaiki'
            assert submission['fotoId'].endswith('.webp')
            checks+=7
            # Saved historical visit: initial per-point image + after-update by section and issue.
            await page.evaluate('''()=>{go('visit');S.vis={id:'VS-00001',tanggal:'2026-11-12',toko:'TIGALAPANKAOS BTP',leader:'Leader',evaluator:'Master',tipe:'Offline Visit',
               jawaban:{A01:'Tidak Sesuai'},catatan:{},foto:{A01:'2026-11/'+('b'.repeat(32))+'_oldBefore.webp'},
               skor:{},updateTemuan:{A:'Lampu diganti'},issues:'',issuesList:[{id:'VI-000001',pointId:'A01',seksi:'A',issue:'Lampu',action:'Ganti lampu',pic:'Ari',dueDate:'2026-11-15',prioritas:'Tinggi',status:'On Progress',fotoId:'',fotoAfter:''}],
               _visibleIssues:3,_view:false};renderVisit();$('mVisit').classList.add('on');}''')
            assert await page.locator('#vBody .visit-after-row .photo-chip').count()==1
            assert await page.locator('#vBody .visit-issue-card .photo-chip').count()>=1
            await page.locator('#vBody .visit-issue-card .photo-chip').first.click()
            assert await page.locator('#dcoCameraModal .ba-group').count()==2
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
               {'name':'after.jpg','mimeType':'image/jpeg','buffer':jpg}])
            await page.wait_for_function('()=>photoList(S.vis.issuesList[0].fotoAfter).length===1',timeout=18000)
            await page.locator('#evidenceHubClose').click()
            await page.locator('#vBody .visit-after-row .photo-chip').click()
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
               {'name':'sectionafter.jpg','mimeType':'image/jpeg','buffer':jpg}])
            await page.wait_for_function("()=>photoList(S.vis.foto.UPDATE_A).length===1",timeout=18000)
            await page.locator('#evidenceHubClose').click()
            assert await page.evaluate('S.vis.foto.A01')=='2026-11/'+('b'*32)+'_oldBefore.webp'
            sizes=await page.evaluate('({body:document.documentElement.scrollWidth,width:innerWidth})')
            assert sizes['body']<=sizes['width']+10,(width,sizes)
            checks+=6
            await ctx.close()
        await browser.close()
    print(json.dumps({'checks':checks,'viewport_widths':[390,768,1280],'page_errors':errors},indent=2))
    if errors:raise AssertionError(errors)

if __name__=='__main__':asyncio.run(run())
