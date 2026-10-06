import urllib.request
import json
import urllib.parse
API_KEY = '43d9f1e7f721b65'
API_SECRET = '5c2b9f75ba21775'
BASE_URL = 'https://radiant-medical.frappe.cloud'
HEADERS = {
    'Authorization': f'token {API_KEY}:{API_SECRET}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

def check(limit):
    print(f"Checking limit {limit}")
    url = f'{BASE_URL}/api/resource/Supplier?fields=["name"]&limit_page_length={limit}'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            print(f"Got {len(res.get('data', []))} records")
    except Exception as e:
        print(f"Error: {e}")

check(10)
check(100)
check(1000)
check(5000)
