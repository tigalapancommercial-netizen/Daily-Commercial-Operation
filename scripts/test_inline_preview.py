from pathlib import Path
import re, json
from playwright.sync_api import sync_playwright
b=Path('/mnt/data/assignment_modern_v1')
c=(b/'src/constants.js').read_text()
d=(b/'src/data.js').read_text()
m=(b/'src/main.js').read_text()
for s in ('constants','data','main'): pass
c=re.sub(r'\bexport\s+','',c)
d=re.sub(r'^import .*?;\s*$', '',d,flags=re.MULTILINE)
d=re.sub(r'\bexport\s+','',d)
d=d.replace('import.meta.env||{}',"{VITE_DEMO_MODE:'true'}")
m=re.sub(r'^import .*?;\s*$', '',m,flags=re.MULTILINE)
js=c+'\n'+d+'\nconst esc=escapeHtml;\n'+m
style=(b/'src/styles.css').read_text()
html='<!doctype html><html lang="id"><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>'+style+'</style></head><body><div id="app"></div><script>'+js+'</script></body></html>'
(b/'preview/standalone_demo.html').write_text(html)
results=[]
with sync_playwright() as p:
 br=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for width,height in [(1440,900),(390,844)]:
  page=br.new_page(viewport={'width':width,'height':height})
  errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
  page.set_content(html,wait_until='load');page.wait_for_timeout(350)
  if width==1440: page.screenshot(path=str(b/f'preview/overview_{width}.png'),full_page=True)
  if width==390:page.screenshot(path=str(b/f'preview/overview_{width}.png'),full_page=True)
  for tab in ['overview','compliance','issues','checklist','dso','schedule','visits','pending','scorecard','settings']:
   page.evaluate('(t)=>navigate(t)',tab)
   page.wait_for_timeout(90)
   measure=page.evaluate('''() => ({doc:document.documentElement.scrollWidth, win:innerWidth,title:document.querySelector('.page-title')?.textContent||'', nav:document.querySelectorAll('.sidebar .nav-item').length})''')
   if tab in ['issues','schedule','pending','settings']:
    page.screenshot(path=str(b/f'preview/{tab}_{width}.png'),full_page=True)
   results.append({'width':width,'tab':tab,'measure':measure,'errors':errors[:]})
   errors.clear()
  page.close()
 br.close()
print(json.dumps(results,ensure_ascii=False,indent=2))
