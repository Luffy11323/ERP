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

def apply_naming_rules(val):
    if not isinstance(val, str):
        return val
    # "RM " -> "AKA "
    val = val.replace("RM ", "AKA ")
    val = val.replace("Rm ", "Aka ")
    val = val.replace("rm ", "aka ")
    # "Radiant Medical" -> "Akatech"
    val = val.replace("Radiant Medical", "Akatech")
    val = val.replace("radiant medical", "akatech")
    # "Radiant" -> "Akatech"
    val = val.replace("Radiant", "Akatech")
    val = val.replace("radiant", "akatech")
    return val

def clean_and_rename_doc(doc_dict):
    new_dict = {}
    for k, v in doc_dict.items():
        if k in ['creation', 'modified', 'owner', 'modified_by', '_user_tags', '_comments', '_assign', '_liked_by']:
            continue
        if isinstance(v, str):
            new_dict[k] = apply_naming_rules(v)
        elif isinstance(v, list):
            new_list = []
            for item in v:
                if isinstance(item, dict):
                    new_list.append(clean_and_rename_doc(item))
                else:
                    new_list.append(apply_naming_rules(item))
            new_dict[k] = new_list
        elif isinstance(v, dict):
            new_dict[k] = clean_and_rename_doc(v)
        else:
            new_dict[k] = v
    return new_dict

def pull_metadata(doctype, filters=None):
    print(f"Fetching {doctype}s from Radiant...")
    query = f'resource/{urllib.parse.quote(doctype)}?fields=["name"]&limit_page_length=2000'
    if filters:
        query += f'&filters={urllib.parse.quote(json.dumps(filters))}'
        
    res = api_call(query)
    if not res:
        print(f"Failed to get {doctype}")
        return
    
    records = [d['name'] for d in res.get('data', [])]
    print(f"Found {len(records)} {doctype}s.")
    
    for r_name in records:
        aka_r_name = apply_naming_rules(r_name)
        
        if frappe.db.exists(doctype, aka_r_name):
            continue
            
        print(f"Fetching {doctype}: {r_name}")
        dt_res = api_call(f'resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(r_name)}')
        if not dt_res:
            continue
            
        dt_dict = dt_res.get('data')
        dt_dict = clean_and_rename_doc(dt_dict)
        
        try:
            frappe.flags.in_fixtures = True
            doc = frappe.get_doc(dt_dict)
            doc.flags.ignore_links = True
            doc.flags.ignore_validate = True
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            print(f"Successfully inserted {aka_r_name}")
        except Exception as e:
            print(f"Failed to insert {aka_r_name}: {e}")

def sync_all():
    # Print Formats (Custom)
    pull_metadata("Print Format", [["custom_format", "=", 1]])
    # Client Scripts
    pull_metadata("Client Script")
    # Server Scripts
    pull_metadata("Server Script")
    # Workflows
    pull_metadata("Workflow", [["is_active", "=", 1]])
    # Custom Fields
    pull_metadata("Custom Field")
    # Property Setters
    pull_metadata("Property Setter")
    
    frappe.db.commit()
    print("Done fetching all metadata!")

