#!/usr/bin/env python3
"""Periodic forms and dashboard smoke; mocked Supabase, no production data."""
import asyncio, importlib.util, json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v10',ROOT/'tests'/'v10_ui_smoke.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
FAKE=old.FAKE
async def run():
 errors=[];checks=[]
 async with async_playwright() as pw:
  b=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  for role in ['MASTER','STORE']:
   c=await b.new_context(viewport={'width':390 if role=='STORE' else 1280,'height':900})
   p=await c.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
   await p.add_init_script(FAKE)
   await p.route('**/*',lambda r:r.fulfill(status=200,content_type='application/javascript',body='') if r.request.url.endswith('/src/main.js') else r.continue_())
   await p.set_content((ROOT/'index.html').read_text(),wait_until='domcontentloaded')
   await p.evaluate(FAKE)
   await p.evaluate('''(role)=>{
    S.me={role,username:'test',nama:'Test',token:'mock',toko:role==='STORE'?'TIGALAPANKAOS BTP':'SEMUA'};
    window.__prWrites=[];const old=__dcoApi;
    window.__dcoApi=async(a,x,t)=>{
      if(a==='periodList')return JSON.stringify({ok:true,data:{rows:[],total:0,hasMore:false}});
      if(a==='periodSummary')return JSON.stringify({ok:true,data:{items:[]}});
      if(a==='periodSubmit'){window.__prWrites.push(x);return JSON.stringify({ok:true,data:{id:'report-test-1'}});}
      return old(a,x,t);
    };boot();
   }''',role)
   await p.wait_for_function('()=>S.meta&&S.meta.toko&&S.meta.toko.length>0')
   await p.evaluate('()=>go("period")')
   await p.wait_for_function('()=>document.querySelector("#prContent .pr-form-head")!==null')
   assert await p.locator('#prContent .pr-form-head').count()==1
   checks.append(role+':period_nav')
   for kind in ['WEEKLY_SALES','MONTHLY_SALES','WEEKLY_GENSET','MONTHLY_APAR']:
    await p.locator('#prType').select_option(kind)
    await p.wait_for_function('()=>document.querySelector("#prContent .pr-form-head")!==null')
    assert kind in await p.locator('#prType').input_value()
    checks.append(role+':'+kind+'_opened')
   await p.locator('#prType').select_option('WEEKLY_GENSET')
   await p.wait_for_function('()=>document.querySelector("#prContent [data-pr-field=has_genset]")!==null')
   await p.locator('#prContent select[data-pr-field=has_genset]').select_option('Ada Genset')
   assert await p.locator('#prContent .pr-check').count()==8,'Genset eight photo items not rendering after select'
   checks.append(role+':genset_dynamic_items')
   await p.locator('#prContent select[data-pr-field=has_genset]').select_option('Tidak ada Genset')
   assert await p.locator('#prContent .pr-check').count()==0
   checks.append(role+':genset_no_photo_rule')
   await p.evaluate('()=>submitPeriodReport()')
   await p.wait_for_function('()=>window.__prWrites.length===1')
   assert (await p.evaluate('()=>__prWrites[0]'))['payload']['has_genset']=='Tidak ada Genset'
   checks.append(role+':genset_submit')
   await c.close()
  await b.close()
 print(json.dumps({'checks':len(checks),'errors':errors},ensure_ascii=False))
 if errors:raise AssertionError(errors)
if __name__=='__main__':asyncio.run(run())
