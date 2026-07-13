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
                    });
                    
                    const pdbqt = `REMARK  99 A.D. 4.0 bound to receptor
ROOT
ATOM      1  N   ASP A  15      18.913  22.259  22.569  1.00 48.06    -0.315 N 
ATOM      2  CA  ASP A  15      17.927  23.011  21.782  1.00 46.99     0.231 C 
ENDROOT
TORSDOF 0`;
                    
                    console.log('Loading structure...');
                    await viewer.loadStructureFromData(pdbqt, 'pdb');
                    
                    // Let's check the state tree!
                    const state = viewer.plugin.state.data;
                    const structures = state.select(molstar.StateSelection.Generators.rootsOfType(molstar.PluginStateObject.Molecule.Structure));
                    console.log('Number of structures created:', structures.length);
                    if (structures.length > 0) {
                        const structure = structures[0].obj.data;
                        console.log('Number of models:', structure.models.length);
                        console.log('Number of atoms:', structure.elementCount);
                    }
                    
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
        
        with open('test_molstar_local6.html', 'w') as f:
            f.write(html)
            
        await page.goto(f'file:///{os.path.abspath("test_molstar_local6.html")}')
        await asyncio.sleep(3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
