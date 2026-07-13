import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--use-gl=swiftshader', '--enable-webgl', '--disable-gpu'])
        page = await browser.new_page()
        
        page.on('console', lambda msg: print(f'CONSOLE [{msg.type}]: {msg.text}'))
        page.on('pageerror', lambda err: print(f'ERROR: {err}'))
        
        html = """<!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/molstar@5.4.2/build/viewer/molstar.css">
            <script src="https://cdn.jsdelivr.net/npm/molstar@5.4.2/build/viewer/molstar.js"></script>
        </head>
        <body>
            <div id="test-molstar" style="width: 800px; height: 600px;"></div>
            <script>
            async function run() {
                try {
                    console.log('Creating Viewer...');
                    const viewer = await molstar.Viewer.create('test-molstar', {
                        layoutIsExpanded: false,
                        layoutShowControls: false,
                        viewportShowSelectionMode: false,
                        viewportShowAnimation: false
                    });
                    
                    const pdb = `ATOM      1  N   ASP A  15      18.913  22.259  22.569  1.00 48.06           N
ATOM      2  CA  ASP A  15      17.927  23.011  21.782  1.00 46.99           C
ATOM      3  C   ASP A  15      17.202  21.947  20.970  1.00 44.20           C
ATOM      4  O   ASP A  15      17.728  20.840  20.730  1.00 43.51           O
ATOM      5  CB  ASP A  15      18.591  24.032  20.840  1.00 49.33           C
ATOM      6  CG  ASP A  15      19.389  25.105  21.571  1.00 50.91           C
ATOM      7  OD1 ASP A  15      19.366  25.161  22.819  1.00 50.81           O
ATOM      8  OD2 ASP A  15      20.038  25.882  20.845  1.00 53.64           O`;
                    
                    console.log('Loading structure...');
                    await viewer.loadStructureFromData(pdb, 'pdb');
                    console.log('Structure loaded successfully!');
                } catch(e) {
                    console.error('MOLSTAR CRASH:', e.message);
                    console.error(e.stack);
                }
            }
            window.onload = run;
            </script>
        </body>
        </html>"""
        
        with open('test_molstar_local.html', 'w') as f:
            f.write(html)
            
        await page.goto(f'file:///{os.path.abspath("test_molstar_local.html")}')
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
