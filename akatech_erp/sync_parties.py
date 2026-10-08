import frappe
import urllib.request
import urllib.parse
import urllib.error
import json
import requests

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
    try:
        response = requests.get(url, headers=HEADERS, timeout=45)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f'Error fetching {url}: {e}', flush=True)
        return None

def clean_doc(doc_dict):
    for k in ['_user_tags', '_comments', '_assign', '_liked_by']:
        doc_dict.pop(k, None)
    
    doc_dict.pop('workflow_state', None)
    doc_dict.pop('user_id', None)
    return doc_dict

def sync_doctype(doctype):
    print(f"Syncing {doctype}...", flush=True)
    res = api_call(f'resource/{urllib.parse.quote(doctype)}?fields=["name"]&limit_page_length=5000')
    if not res or 'data' not in res:
        print(f"Failed to fetch {doctype} list.", flush=True)
        return

    data = res['data']
    print(f"Found {len(data)} {doctype}s.", flush=True)

    for item in data:
        doc_name = item['name']
        
        if not frappe.db.exists(doctype, doc_name):
            doc_res = api_call(f'resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(doc_name)}')
            if not doc_res or 'data' not in doc_res:
                print(f"Failed to fetch {doctype} {doc_name}", flush=True)
                continue
                
            doc_dict = doc_res['data']
            doc_dict['doctype'] = doctype
            doc_dict = clean_doc(doc_dict)
            
            try:
                if doctype == 'Employee' and doc_dict.get('cnic'):
                    if frappe.db.exists('Employee', {'cnic': doc_dict['cnic']}):
                        doc_dict['cnic'] = None

                doc = frappe.get_doc(doc_dict)
                doc.flags.ignore_permissions = True
                doc.flags.ignore_mandatory = True
                doc.flags.ignore_links = True
                doc.flags.ignore_validate = True
                doc.insert(set_name=doc_name)
                print(f"Inserted {doctype} {doc_name}", flush=True)
            except Exception as e:
                print(f"Error inserting {doctype} {doc_name}: {e}", flush=True)
                frappe.db.rollback()
        else:
            print(f"Exists {doctype} {doc_name}", flush=True)

def delete_wrongly_named_records():
    for dt in ['Customer', 'Supplier', 'Employee']:
        print(f"Checking wrongly named {dt}s...", flush=True)
        res = api_call(f'resource/{urllib.parse.quote(dt)}?fields=["name"]&limit_page_length=5000')
        radiant_names = {item['name'] for item in res['data']} if res and 'data' in res else set()
        
        local_names = frappe.get_all(dt, pluck='name')
        for lname in local_names:
            if lname not in radiant_names:
                try:
                    frappe.delete_doc(dt, lname, force=1)
                    print(f"Deleted wrongly named {dt}: {lname}", flush=True)
                except Exception as e:
                    print(f"Could not delete {lname}: {e}", flush=True)

def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    
    delete_wrongly_named_records()
    
    sync_doctype("Customer")
    sync_doctype("Supplier")
    sync_doctype("Employee")
    
    frappe.db.commit()
    print("Customer/Supplier/Employee sync complete.", flush=True)

if __name__ == "__main__":
    main()
