#!/usr/bin/env python3
"""Browser smoke for v17 global tasks (mock server only; no production writes)."""
import asyncio, importlib.util, json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v10',ROOT/'tests'/'v10_ui_smoke.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
FAKE=old.FAKE
async def run():
 checks=[];errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  for width in (390,768,1280):
   ctx=await browser.new_context(viewport={'width':width,'height':900})
   page=await ctx.new_page();page.on('pageerror',lambda x,w=width:errors.append((w,str(x))))
   await page.add_init_script(FAKE)
   await page.route('**/*',lambda route:route.fulfill(status=200,content_type='application/javascript',body='') if route.request.url.endswith('/src/main.js') else route.continue_())
   await page.set_content((ROOT/'index.html').read_text(encoding='utf8'),wait_until='domcontentloaded')
   await page.evaluate(FAKE)
   await page.evaluate('''()=>{
    S.me={token:'mock',username:'master',nama:'Master',role:'MASTER',toko:'SEMUA'};
    S.rutin=[];
    window.__rutinWrites=[];
    const prior=window.__dcoApi;
    window.__dcoApi=async (a,p,t)=>{
      if(a==='rutinSave'){
        let x={...p.data,id:p.data.id||'RT-'+String(S.rutin.length+1).padStart(4,'0')};
        window.__rutinWrites.push({...x});
        const i=S.rutin.findIndex(z=>z.id===x.id);
        if(i>=0)S.rutin[i]=x;else S.rutin.push(x);
        return JSON.stringify({ok:true,data:x});
      }
      if(a==='list'&&p.type==='RUTIN')return JSON.stringify({ok:true,data:S.rutin});
      return prior(a,p,t);
    };
    boot();
   }''')
   await page.wait_for_function('()=>S.meta&&S.meta.toko&&S.meta.toko.length===12')
   await page.evaluate("()=>go('rutin')")
   await page.wait_for_timeout(90)
   assert await page.locator('#pRutin').is_visible()
   await page.evaluate('()=>openRutin()')
   assert await page.locator('#mRutin.on').count()==1
   await page.locator('#r_judul').fill('Kunjungan SMKN 1 Makassar')
   await page.locator('#r_jenis').fill('Kunjungan Sekolah')
   await page.locator('#r_project').fill('School Partnership 2027')
   await page.locator('#r_lokasi').fill('SMKN 1 Makassar')
   await page.locator('#r_hasil').fill('20 prospek baru')
   await page.locator('#r_pic').fill('Tim Sales')
   await page.locator('#r_mulai').fill('2026-11-20')
   await page.evaluate('()=>rtPickFreq("Sekali")')
   # Switch from all-store to selected store without losing title/other fields
   await page.locator('#r_semua').uncheck()
   await page.locator('#r_tokoChk label').first.click()
   await page.evaluate('()=>saveRutin()')
   await page.wait_for_function('()=>__rutinWrites.length===1')
   data=await page.evaluate('()=>__rutinWrites[0]')
   assert data['jenisTugas']=='Kunjungan Sekolah' and data['frekuensi']=='Sekali',data
   assert data['toko']=='TIGALAPANKAOS BTP',data
   assert data['namaProject']=='School Partnership 2027' and data['lokasi']=='SMKN 1 Makassar',data
   checks.append(f'{width}:one_time_school_visit_saved')
   # New all-store campaign for finite date window
   await page.evaluate('()=>openRutin()')
   await page.locator('#r_judul').fill('Campaign Ramadan')
   await page.locator('#r_jenis').fill('Campaign')
   await page.evaluate('()=>rtPickFreq("Rentang")')
   await page.locator('#r_mulai').fill('2026-11-13')
   await page.locator('#r_akhir').fill('2026-11-17')
   await page.locator('#r_pic').fill('All Store')
   await page.evaluate('()=>saveRutin()')
   await page.wait_for_function('()=>__rutinWrites.length===2')
   campaign=await page.evaluate('()=>__rutinWrites[1]')
   assert campaign['frekuensi']=='Rentang' and campaign['toko']=='SEMUA',campaign
   assert campaign['akhir']=='2026-11-17',campaign
   checks.append(f'{width}:campaign_all_stores_saved')
   assert await page.locator('#rutinTbl tbody tr').count()==2
   await page.evaluate('()=>openRutin(0)')
   assert await page.locator('#r_lokasi').input_value()=='SMKN 1 Makassar'
   await page.evaluate("()=>rtPickFreq('Rentang')")
   await page.locator('#r_akhir').fill('2026-11-25')
   await page.evaluate("()=>rtPickFreq('Sekali')")
   assert await page.evaluate('()=>S.rt.akhir')==''
   checks.append(f'{width}:edit_and_switch_to_once_clears_end')
   await page.evaluate("()=>closeM('mRutin')")
   dims=await page.evaluate('()=>({scroll:document.documentElement.scrollWidth,width:innerWidth})')
   assert dims['scroll']<=dims['width']+8,dims
   checks.append(f'{width}:no_horizontal_page_overflow')
   if width in (390,1280):
    await page.screenshot(path=str(ROOT/'tests'/f'v17_routine_{width}.png'),full_page=False)
    await page.evaluate('()=>openRutin(1)')
    await page.screenshot(path=str(ROOT/'tests'/f'v17_routine_form_{width}.png'),full_page=False)
   await ctx.close()
  await browser.close()
 print(json.dumps({'checks':len(checks),'items':checks,'errors':errors},ensure_ascii=False,indent=2))
 if errors:raise AssertionError('Browser errors: '+str(errors))
if __name__=='__main__':asyncio.run(run())
