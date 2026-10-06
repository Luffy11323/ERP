import urllib.request
import json

API_KEY = '43d9f1e7f721b65'
API_SECRET = '5c2b9f75ba21775'
BASE_URL = 'https://radiant-medical.frappe.cloud'
HEADERS = {
    'Authorization': f'token {API_KEY}:{API_SECRET}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

req = urllib.request.Request(f'{BASE_URL}/api/method/frappe.client.get_list', data=json.dumps({
    "doctype": "Customer",
    "fields": ["count(name) as count"]
}).encode('utf-8'), headers=HEADERS, method='POST')

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    print("Customer count:", data)
