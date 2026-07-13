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
                    const viewer = await molstar.Viewer.create('test-molstar', {
                        layoutIsExpanded: false,
                        layoutShowControls: false,
                        viewportShowSelectionMode: false,
                        viewportShowAnimation: false
                    });
                    
                    console.log('Fetching test PDB...');
                    const res = await fetch('https://files.rcsb.org/download/1CRN.pdb');
                    const text = await res.text();
                    
                    // Simulate Windows line endings
                    const originalPdbText = text.replace(/\\n/g, '\\r\\n');
                    
                    const pdbText = originalPdbText.split('\\n').filter(line => {
                        return true;
                    }).map(line => {
                        if (line.startsWith('ATOM') || line.startsWith('HETATM')) {
                            return line.substring(0, 80);
                        }
                        return line;
                    }).join('\\n');
                    
                    console.log('Loading structure...');
                    await viewer.loadStructureFromData(pdbText, 'pdb');
                    console.log('Structure loaded successfully!');
                } catch(e) {
                    console.error('MOLSTAR CRASH LINE:', e.message);
                    console.error(e.stack);
                }
            }
            window.onload = run;
            </script>
        </body>
        </html>"""
        
        with open('test_molstar_local3.html', 'w') as f:
            f.write(html)
            
        await page.goto(f'file:///{os.path.abspath("test_molstar_local3.html")}')
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
