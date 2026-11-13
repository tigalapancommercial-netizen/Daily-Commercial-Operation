#!/usr/bin/env python3
"""Browser regression: photo upload automatically completes Assignment Checklist.
All data is mocked; no live Supabase writes or credentials.
"""
import asyncio, importlib.util, io, json, pathlib
from PIL import Image
from playwright.async_api import async_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('old_v10', ROOT/'tests'/'v10_ui_smoke.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
FAKE=old.FAKE

async def run():
    checks=[]; errors=[]
    im=Image.new('RGB',(1200,850),'#73a0b9'); buf=io.BytesIO(); im.save(buf,'JPEG',quality=80);jpg=buf.getvalue()
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'])
        for width in (390,768,1280):
            context=await browser.new_context(viewport={'width':width,'height':900},permissions=['camera'])
            page=await context.new_page()
            page.on('pageerror',lambda e,w=width:errors.append(f'{w}: {e}'))
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
              window.__ckWrites=[];window.__ckFail=false;window.__uploadFail=false;
              const original=window.__dcoApi;
              window.__dcoApi=async (action,p,t)=>{
                if(action==='ceklisSet'){
                  window.__ckWrites.push({...p});
                  if(window.__ckFail)return JSON.stringify({ok:false,error:'Simulasi database menolak simpan'});
                }
                if(action==='uploadFoto'&&window.__uploadFail)return JSON.stringify({ok:false,error:'Storage menolak foto'});
                return original(action,p,t);
              };
              boot();
            }''')
            await page.wait_for_function('()=>S.meta&&S.meta.formDef&&S.meta.formDef.length')
            await page.evaluate("()=>{go('ceklis');$('ckToko').value='TIGALAPANKAOS BTP';loadCeklis();}")
            await page.wait_for_function('()=>document.querySelectorAll("#ckIsi .ckrow").length===2')
            assert await page.evaluate("()=>S.ckRows[0].status")=='Belum'
            assert await page.locator('#ckIsi .ckrow .cb').first.inner_text()==''
            checks.append(f'{width}:initial_unchecked')
            # Merely opening the photo gallery does not tick the item.
            await page.locator('#ck0 .photo-chip').click()
            assert await page.evaluate("()=>S.ckRows[0].status")=='Belum'
            checks.append(f'{width}:opening_gallery_does_not_complete')
            # Two independent photos; one atomic ceklisSet with status:true and both references.
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'before.jpg','mimeType':'image/jpeg','buffer':jpg},
                {'name':'after.jpg','mimeType':'image/jpeg','buffer':jpg}
            ])
            await page.wait_for_function("()=>S.ckRows[0].status==='Selesai'&&photoList(S.ckRows[0].fotoId).length===2",timeout=18000)
            assert await page.evaluate("()=>__MOCK.ceklisHari[0].status")=='Selesai'
            assert await page.locator('#ckIsi .ckrow.done').count()==1
            assert await page.locator('#ck0 .cb').inner_text()=='✓'
            writes=await page.evaluate('window.__ckWrites')
            assert len(writes)==1 and writes[0]['status'] is True and len(json.loads(writes[0]['fotoId']))==2,writes
            checks.append(f'{width}:auto_tick_and_one_backend_write')
            if width in (390,1280):
                await page.locator('#evidenceHubClose').click()
                await page.screenshot(path=str(ROOT/'tests'/f'v14_assignment_completed_{width}.png'))
                await page.locator('#ck0 .photo-chip').click()
            # Removing one photo preserves the tick, does not request status:false.
            await page.evaluate('window.confirm=()=>true')
            await page.locator('#evidenceHubGallery .evidence-remove').first.click()
            await page.wait_for_function("()=>photoList(S.ckRows[0].fotoId).length===1",timeout=9000)
            assert await page.evaluate("()=>S.ckRows[0].status")=='Selesai'
            writes=await page.evaluate('window.__ckWrites')
            assert len(writes)==2 and 'status' not in writes[1] and writes[1]['fotoId']
            checks.append(f'{width}:remove_photo_keeps_status')
            await page.locator('#evidenceHubClose').click()
            # Backend failure => image not linked, status not completed, no false green tick.
            await page.locator('#ck1 .photo-chip').click()
            await page.evaluate('window.__ckFail=true')
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'failure.jpg','mimeType':'image/jpeg','buffer':jpg}
            ])
            await page.wait_for_function("()=>document.querySelector('.photo-chip:not(.has-pictures)')!==null",timeout=5000)
            await page.wait_for_timeout(600)
            assert await page.evaluate("()=>S.ckRows[1].status")=='Belum'
            assert await page.evaluate("()=>photoList(S.ckRows[1].fotoId).length") == 0
            assert await page.locator('#ckIsi .ckrow.done').count()==1
            assert await page.evaluate("()=>!evidenceBusy['ck:1']")
            checks.append(f'{width}:server_failure_never_ticks')
            await page.evaluate('window.__ckFail=false')
            # Now same item succeeds on next attempt.
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'retry.jpg','mimeType':'image/jpeg','buffer':jpg}
            ])
            await page.wait_for_function("()=>S.ckRows[1].status==='Selesai'&&photoList(S.ckRows[1].fotoId).length===1",timeout=18000)
            assert await page.locator('#ckIsi .ckrow.done').count()==2
            checks.append(f'{width}:retry_success')
            await page.locator('#evidenceHubClose').click()
            # Partial multi-photo upload: preserve successfully linked photo,
            # but do not auto-complete if any selected file failed.
            await page.evaluate('()=>ckToggle(1)')
            await page.wait_for_function("()=>S.ckRows[1].status==='Belum'",timeout=5000)
            await page.evaluate('''()=>{
              window.__failSecondUpload=true;window.__partialUploadCounter=0;
              const prev=window.__dcoApi;
              window.__dcoApi=async (a,p,t)=>{
                if(a==='uploadFoto'&&window.__failSecondUpload){
                  window.__partialUploadCounter++;
                  if(window.__partialUploadCounter===2){window.__failSecondUpload=false;
                    return JSON.stringify({ok:false,error:'Simulasi upload foto kedua gagal'});}
                }
                return prev(a,p,t);
              };
            }''')
            await page.locator('#ck1 .photo-chip').click()
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'partial1.jpg','mimeType':'image/jpeg','buffer':jpg},
                {'name':'partial2.jpg','mimeType':'image/jpeg','buffer':jpg}
            ])
            await page.wait_for_function("()=>photoList(S.ckRows[1].fotoId).length===2&&!evidenceBusy['ck:1']",timeout=18000)
            assert await page.evaluate("()=>S.ckRows[1].status")=='Belum'
            writes=await page.evaluate('window.__ckWrites')
            assert 'status' not in writes[-1]
            checks.append(f'{width}:partial_upload_does_not_autocomplete')
            # Another successful photo completes automatically.
            await page.locator('#evidenceHubActions input[multiple]').set_input_files([
                {'name':'partial_retry.jpg','mimeType':'image/jpeg','buffer':jpg}
            ])
            await page.wait_for_function("()=>S.ckRows[1].status==='Selesai'&&photoList(S.ckRows[1].fotoId).length===3",timeout=18000)
            checks.append(f'{width}:partial_retry_autocompletes')
            await page.locator('#evidenceHubClose').click()
            # Lock in Store role must block new photos from validated checklists.
            await page.evaluate('''()=>{S.me.role='STORE';S.me.toko='TIGALAPANKAOS BTP';S.ckRows[0].validasi='Y';renderCeklis();}''')
            await page.locator('#ck0 .photo-chip').click()
            assert await page.locator('#evidenceHubActions').is_hidden()
            checks.append(f'{width}:validated_store_locked')
            await page.locator('#evidenceHubClose').click()
            await context.close()
        await browser.close()
    summary={'checks':len(checks),'widths':[390,768,1280],'browser_errors':errors}
    (ROOT/'tests'/'v14_assignment_auto_result.json').write_text(json.dumps(dict(summary,check_names=checks),indent=2,ensure_ascii=False))
    print(json.dumps(summary,indent=2))
    if errors:raise RuntimeError(errors)

if __name__=='__main__':asyncio.run(run())
