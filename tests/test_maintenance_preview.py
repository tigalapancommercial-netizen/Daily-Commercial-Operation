from pathlib import Path
import re,json
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parents[1]
js=[]
for file in ('constants.js','data.js','main.js'):
 s=(P/'src'/file).read_text(encoding='utf8')
 s=re.sub(r'^import .*?;\s*$', '', s,flags=re.M)
 s=re.sub(r'\bexport\s+','',s)
 if file=='data.js':s=s.replace('import.meta.env||{}',"{VITE_DEMO_MODE:'true'}")
 if file=='main.js':s='const esc=escapeHtml;\n'+s
 js.append(s)
html='<!doctype html><html lang="id"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+(P/'src/styles.css').read_text()+'</style></head><body><div id="app"></div><script>'+'\n'.join(js)+'</script></body></html>'
(P/'preview').mkdir(exist_ok=True)
(P/'preview/demo_maintenance.html').write_text(html,encoding='utf8')
report=[]
with sync_playwright() as play:
 browser=play.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for width in (390,768,1280):
  page=browser.new_page(viewport={'width':width,'height':850})
  errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(html)
  page.wait_for_selector('.page-title')
  page.evaluate("go('maintenance')")
  page.wait_for_timeout(200)
  stats=page.evaluate('''() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,title:document.querySelector('.page-title')?.textContent,tables:document.querySelectorAll('table').length,buttons:document.querySelectorAll('[data-action="export-dataset"]').length,log:document.querySelector('.toast')?.textContent||''})''')
  assert stats['title']=='Export, Backup & Manajemen Database',stats
  assert stats['scrollWidth']<=width+10,stats
  assert stats['buttons']==1,stats
  assert not errors,errors
  if width in (390,1280):page.screenshot(path=str(P/f'preview/data_management_{width}.png'),full_page=True)
  report.append(stats)
  page.close()
 browser.close()
print('PASS maintenance preview',json.dumps(report,ensure_ascii=False))
