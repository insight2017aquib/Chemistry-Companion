
from fastapi.testclient import TestClient
from api.app import app
import io

client = TestClient(app)

with open('final_compounds.csv', 'rb') as f:
    file_content = f.read()

resp = client.post('/api/batch/process', files={'file': ('final_compounds.csv', file_content, 'text/csv')}, data={'include_spectra': 'false'})
print(f'Status: {resp.status_code}')
if resp.status_code != 200:
    print('Response snippet:', resp.text[:1500])
else:
    print('Success!')

