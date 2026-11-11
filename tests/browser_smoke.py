from playwright.sync_api import sync_playwright
import pathlib,json
ROOT=pathlib.Path(__file__).resolve().parents[1]/'.tmp_demo'
base='https://assignment-preview.example.test/'
report=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-proxy-server','--proxy-bypass-list=*'])
 for width in (390,768,1280):
  page=browser.new_page(viewport={'width':width,'height':900})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def local_route(route):
   from urllib.parse import urlparse
   sub=urlparse(route.request.url).path.lstrip('/') or 'index.html'
   f=(ROOT/sub).resolve()
   if not f.is_relative_to(ROOT.resolve()) or not f.exists(): return route.fulfill(status=404,body='Not found')
   mime='text/html' if f.suffix=='.html' else 'text/css' if f.suffix=='.css' else 'text/javascript'
   return route.fulfill(status=200,body=f.read_bytes(),content_type=mime)
  page.route('**/*',local_route)
  page.goto(base,wait_until='networkidle')
  page.wait_for_selector('.page-title',timeout=12000)
  for name in ('Overview','Kepatuhan Toko','Action Plan','Assignment Checklist','Daily Store Operation','Jadwal Visit','Visiting Check Point','Pending Matter','Scorecard','Pengaturan'):
   nav=page.get_by_role('button',name=name,exact=True).first
   if width<800:
    page.locator('[data-action="sidebar-toggle"]').click()
   nav.click()
   title=page.locator('.page-title').inner_text()
   dims=page.evaluate('({body:document.documentElement.scrollWidth,win:innerWidth})')
   report.append({'width':width,'page':name,'title':title,**dims,'errors':errors[:]})
   if dims['body']>width+10:print('OVERFLOW',width,name,dims)
   if errors:print('JS ERROR',width,name,errors)
  page.close()
 browser.close()

OUT=ROOT.parent/'preview'/'browser_smoke_full.json';OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CHECKED',len(report),'pages; overflow:',sum(x['body']>x['width']+10 for x in report),'js errors:',sum(bool(x['errors']) for x in report))
