import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--use-gl=swiftshader', '--enable-webgl', '--disable-gpu'])
        page = await browser.new_page()
        
        page.on('console', lambda msg: print(f'CONSOLE [{msg.type}]: {msg.text}'))
        
        html = """<!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/molstar@5.4.2/build/viewer/molstar.js"></script>
        </head>
        <body>
            <div id="test-molstar" style="width: 800px; height: 600px;"></div>
            <script>
            async function run() {
                const viewer = await molstar.Viewer.create('test-molstar', {
                    layoutIsExpanded: false,
                    layoutShowControls: false,
                });
                console.log('Does structureInteractivity exist?', typeof viewer.structureInteractivity);
            }
            window.onload = run;
            </script>
        </body>
        </html>"""
        
        with open('test_molstar_local4.html', 'w') as f:
            f.write(html)
            
        await page.goto(f'file:///{os.path.abspath("test_molstar_local4.html")}')
        await asyncio.sleep(3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
