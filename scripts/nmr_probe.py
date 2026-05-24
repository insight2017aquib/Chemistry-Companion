import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, str(PROJECT_ROOT))

from core.pipeline import ChemistryPipeline
from core.molecule_utils import mol_from_smiles
from api.serializers import serialize_analysis_result
from fastapi.testclient import TestClient
from api.app import app

def probe():
    molecules = {
        "benzene": "c1ccccc1",
        "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
        "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
        "ethanol": "CCO",
        "custom": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O" # Ibuprofen
    }
    
    pipeline = ChemistryPipeline()
    client = TestClient(app)
    
    pipeline_probe_md = "# NMR Pipeline Probe\n\n"
    serializer_probe_md = "# NMR Serializer Probe\n\n"
    api_probe_md = "# NMR API Probe\n\n"
    
    for name, smiles in molecules.items():
        pipeline_probe_md += f"## {name.upper()} ({smiles})\n"
        serializer_probe_md += f"## {name.upper()} ({smiles})\n"
        api_probe_md += f"## {name.upper()} ({smiles})\n"
        
        # 1. Pipeline Probe
        result = pipeline.analyze(smiles=smiles)
        
        has_proton = hasattr(result, 'proton_nmr_prediction') and result.proton_nmr_prediction is not None
        has_carbon = hasattr(result, 'carbon_nmr_prediction') and result.carbon_nmr_prediction is not None
        
        pipeline_probe_md += f"- **Proton NMR Prediction Exists:** {has_proton}\n"
        pipeline_probe_md += f"- **Carbon NMR Prediction Exists:** {has_carbon}\n"
        
        if has_proton:
            pipeline_probe_md += f"  - Raw Proton: `{type(result.proton_nmr_prediction).__name__}`\n"
        if has_carbon:
            pipeline_probe_md += f"  - Raw Carbon: `{type(result.carbon_nmr_prediction).__name__}`\n"
        
        # 2. Serializer Probe
        serialized = serialize_analysis_result(result)
        
        # In the dictionary returned by serialize_analysis_result
        ser_has_proton = 'proton_nmr_prediction' in serialized and serialized['proton_nmr_prediction'] is not None
        ser_has_carbon = 'carbon_nmr_prediction' in serialized and serialized['carbon_nmr_prediction'] is not None
        
        serializer_probe_md += f"- **Proton NMR Serialized Key Exists & Not Null:** {ser_has_proton}\n"
        serializer_probe_md += f"- **Carbon NMR Serialized Key Exists & Not Null:** {ser_has_carbon}\n"
        
        if ser_has_proton:
            serializer_probe_md += f"  - Serializer Output: {json.dumps(serialized['proton_nmr_prediction'])[:100]}...\n"
        if ser_has_carbon:
            serializer_probe_md += f"  - Serializer Output: {json.dumps(serialized['carbon_nmr_prediction'])[:100]}...\n"
            
        # 3. API Probe
        payload = {"molecule": {"smiles": smiles}, "include_spectra": True}
        response = client.post("/api/analyse", json=payload)
        
        api_probe_md += f"- **HTTP Status:** {response.status_code}\n"
        if response.status_code == 200:
            resp_json = response.json()
            api_has_proton = 'proton_nmr_prediction' in resp_json and resp_json['proton_nmr_prediction'] is not None
            api_has_carbon = 'carbon_nmr_prediction' in resp_json and resp_json['carbon_nmr_prediction'] is not None
            api_probe_md += f"- **Proton NMR in API Response:** {api_has_proton}\n"
            api_probe_md += f"- **Carbon NMR in API Response:** {api_has_carbon}\n"
        
    with open(PROJECT_ROOT / "nmr_pipeline_probe.md", "w") as f:
        f.write(pipeline_probe_md)
        
    with open(PROJECT_ROOT / "nmr_serializer_probe.md", "w") as f:
        f.write(serializer_probe_md)
        
    with open(PROJECT_ROOT / "nmr_api_probe.md", "w") as f:
        f.write(api_probe_md)

if __name__ == "__main__":
    probe()
