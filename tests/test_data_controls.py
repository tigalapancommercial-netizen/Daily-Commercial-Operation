from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'preview/demo_maintenance.html')
assert HTML.exists(), 'run test_maintenance_preview.py first'
html=HTML.read_text()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1280,'height':800})
 errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
 page.set_content(html)
 page.wait_for_selector('.page-title')
 count=page.evaluate("async () => (await fetchCompleteRows('issues',{store:'all'})).length")
 assert count==5,count
 evidence=page.evaluate('''async ()=>{
  const canvas=document.createElement('canvas');canvas.width=2500;canvas.height=1700;
  const ctx=canvas.getContext('2d');ctx.fillStyle='#eee';ctx.fillRect(0,0,2500,1700);
  ctx.fillStyle='#112';ctx.font='bold 100px Arial';ctx.fillText('FOTO VISIT',250,250);
  const png=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
  const file=new File([png],'visit.png',{type:'image/png'});
  const webp=await compressEvidence(file);
  return {type:webp.type,old:file.size,newSize:webp.size,width:canvas.width};
 }''')
 assert evidence['type']=='image/webp',evidence
 assert evidence['newSize']<8*1024*1024,evidence
 assert not errors,errors
 print('PASS photo conversion',evidence)
 browser.close()
