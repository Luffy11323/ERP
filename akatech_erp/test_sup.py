import urllib.request
import json

from akatech_erp.env import API_KEY
from akatech_erp.env import API_SECRET
BASE_URL = 'https://radiant-medical.frappe.cloud'
HEADERS = {
    'Authorization': f'token {API_KEY}:{API_SECRET}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

req = urllib.request.Request(f'{BASE_URL}/api/resource/Supplier/RM-SUP-0140', headers=HEADERS)

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    print("Supplier RM-SUP-0140 data:")
    for k, v in data['data'].items():
        if k in ['name', 'supplier_name']:
            print(f"{k}: {v}")
