import requests
import json

files = {
    'config': (None, '{}'),
    'csv': open('examples/recruiter.csv', 'rb'),
    'ats_json': open('examples/ats.json', 'rb'),
    'notes': open('examples/notes.txt', 'rb'),
}

response = requests.post("http://127.0.0.1:8000/transform", files=files)
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error {response.status_code}: {response.text}")
