import frappe
import urllib.request
import urllib.parse
import json

API_KEY = '43d9f1e7f721b65'
API_SECRET = '5c2b9f75ba21775'
BASE_URL = 'https://radiant-medical.frappe.cloud'

HEADERS = {
    'Authorization': f'token {API_KEY}:{API_SECRET}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

def api_call(endpoint):
    url = f'{BASE_URL}/api/{endpoint}'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return None

res = api_call('resource/GL%20Entry?fields=["name"]&limit_page_length=1&filters=[["company","=","Radiant Medical (Pvt.) Ltd."]]')
if res:
    # We can get total count? Frappe API doesn't easily return count. 
    pass

# Try frappe.client.get_list count
req = urllib.request.Request(f'{BASE_URL}/api/method/frappe.client.get_list', data=json.dumps({
    "doctype": "GL Entry",
    "filters": {"company": "Radiant Medical (Pvt.) Ltd.", "is_cancelled": 0},
    "fields": ["count(name) as count"]
}).encode('utf-8'), headers=HEADERS, method='POST')

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    print("GL Entry count:", data)
