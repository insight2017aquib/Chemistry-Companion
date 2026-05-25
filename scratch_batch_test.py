
import csv
import io
with open('final_compounds.csv', 'rb') as f:
    content = f.read()
reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
rows = list(reader)
print('Columns:', reader.fieldnames)
print('First row keys:', list(rows[0].keys()))

