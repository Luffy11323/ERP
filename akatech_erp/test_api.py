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

def api_call(endpoint):
    url = f'{BASE_URL}/api/{endpoint}'
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def main():
    try:
        res = api_call('resource/Customer/RM-CUS-0043')
        print("Customer exists in Radiant:", res.get('data', {}).get('name'))
    except Exception as e:
        print("Error fetching RM-CUS-0043:", e)
        
    try:
        # What if it's paginated?
        res = api_call('resource/Customer?limit_page_length=1')
        print("Test get_list")
    except Exception as e:
        print("Error", e)

if __name__ == "__main__":
    main()
