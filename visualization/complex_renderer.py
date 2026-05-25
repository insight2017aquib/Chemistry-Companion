import json
import uuid

THREEDMOL_CDN = "https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"


def _json_for_script(value: str) -> str:
    return json.dumps(value or "").replace("</", "<\\/")


def render_protein_ligand_complex(
    protein_pdb: str,
    ligand_structure: str,
    protein_format: str = "pdb",
    ligand_format: str = "pdbqt",
) -> str:
    """
    Render a standalone 3Dmol.js HTML document for a protein-ligand complex.

    The GUI renders structures directly from the returned model blocks, but this
    HTML remains useful for API clients that want an iframe-ready visualization.
    """
    viewer_id = f"complex-viewer-{uuid.uuid4().hex}"
    protein_safe = _json_for_script(protein_pdb)
    ligand_safe = _json_for_script(ligand_structure)
    protein_format_safe = _json_for_script(protein_format or "pdb")
    ligand_format_safe = _json_for_script(ligand_format or "pdbqt")

    return f"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        html, body, #{viewer_id} {{
            width: 100%;
            height: 100%;
            margin: 0;
            overflow: hidden;
            background: white;
        }}
        .viewer-error {{
            box-sizing: border-box;
            color: #b91c1c;
            font: 14px sans-serif;
            padding: 16px;
        }}
    </style>
</head>
<body>
    <div id="{viewer_id}"></div>
    <script>
        (function() {{
            const viewerId = {json.dumps(viewer_id)};
            const protein = {protein_safe};
            const ligand = {ligand_safe};
            const proteinFormat = {protein_format_safe};
            const ligandFormat = {ligand_format_safe};

            function showError(message) {{
                const element = document.getElementById(viewerId);
                if (element) {{
                    element.innerHTML = '<div class="viewer-error">' + message + '</div>';
                }}
            }}

            function renderComplex() {{
                if (typeof window.$3Dmol === 'undefined') {{
                    showError('3Dmol.js failed to load.');
                    return;
                }}

                const viewer = window.$3Dmol.createViewer(viewerId, {{
                    backgroundColor: 'white'
                }});

                let modelIndex = 0;
                if (protein) {{
                    viewer.addModel(protein, proteinFormat);
                    const proteinStyle = proteinFormat === 'pdbqt'
                        ? {{stick: {{radius: 0.12, colorscheme: 'spectrum'}}}}
                        : {{cartoon: {{color: 'spectrum'}}}};
                    viewer.setStyle({{model: modelIndex}}, proteinStyle);
                    modelIndex += 1;
                }}

                if (ligand) {{
                    viewer.addModel(ligand, ligandFormat);
                    viewer.setStyle({{model: modelIndex}}, {{stick: {{colorscheme: 'greenCarbon'}}}});
                }}

                viewer.zoomTo();
                viewer.render();
                window.__complexViewer = viewer;
            }}

            if (window.$3Dmol) {{
                renderComplex();
                return;
            }}

            const script = document.createElement('script');
            script.src = {json.dumps(THREEDMOL_CDN)};
            script.onload = renderComplex;
            script.onerror = function() {{ showError('Unable to load 3Dmol.js from CDN.'); }};
            document.head.appendChild(script);
        }})();
    </script>
</body>
</html>
"""
