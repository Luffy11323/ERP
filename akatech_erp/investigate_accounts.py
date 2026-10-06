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

def investigate():
    local_companies = frappe.get_all("Company", fields=["name", "abbr", "company_name"])
    print("Local Companies:", local_companies)
    
    # Radiant Companies
    res = api_call('resource/Company?fields=["name","abbr","company_name"]')
    print("Radiant Companies:", res.get("data") if res else None)
    
    # Accounting Dimensions Radiant
    res = api_call('resource/Accounting%20Dimension?fields=["name"]')
    print("Radiant Dimensions:", res.get("data") if res else None)

investigate()
