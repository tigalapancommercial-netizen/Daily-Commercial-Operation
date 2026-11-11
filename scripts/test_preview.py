import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox', '--disable-dev-shm-usage','--allow-file-access-from-files'])
        results=[]
        for width,height in [(1440,900),(390,844)]:
            page = await browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
            errs=[]
            page.on('pageerror',lambda e:errs.append(str(e)))
            await page.goto('file:///mnt/data/assignment_modern_v1/index.html',wait_until='networkidle')
            await page.screenshot(path=f'/mnt/data/assignment_modern_v1/preview/overview_{width}.png',full_page=True)
            tabs=['overview','compliance','issues','checklist','dso','schedule','visits','pending','scorecard','settings']
            for tab in tabs:
                await page.locator(f'[data-page="{tab}"]').first.click(force=True)
                await page.wait_for_timeout(200)
                h = await page.evaluate('''() => ({body:document.body.scrollWidth,win:window.innerWidth,heading:document.querySelector('.page-title')?.textContent})''')
                if tab in ['issues','schedule','pending','settings']:
                    await page.screenshot(path=f'/mnt/data/assignment_modern_v1/preview/{tab}_{width}.png',full_page=True)
                results.append((width,tab,h,errs.copy()))
                errs.clear()
            await page.close()
        print(json.dumps(results,ensure_ascii=False,indent=2))
        await browser.close()

asyncio.run(main())
