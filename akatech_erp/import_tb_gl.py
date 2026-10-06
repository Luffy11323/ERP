import frappe
import urllib.request
import urllib.parse
import json
from collections import defaultdict

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
    except urllib.error.HTTPError as e:
        print(f'HTTPError: {e.code} for {url}\n{e.read().decode()}')
        return None
    except Exception as e:
        print(f'Error fetching {url}: {e}')
        return None

def rename_account(acc_name):
    if not acc_name: return acc_name
    if isinstance(acc_name, str):
        if acc_name.endswith(" - RM"):
            acc_name = acc_name[:-5] + " - AKA"
    return acc_name

def fetch_all_gl_entries():
    print("Fetching GL Entries from Radiant...")
    
    entries = []
    limit = 5000
    start = 0
    
    while True:
        print(f"Fetching rows {start} to {start+limit}...")
        filters = '[["company","=","Radiant Medical (Pvt.) Ltd."],["is_cancelled","=",0]]'
        res = api_call(f'resource/GL%20Entry?fields=["account","party_type","party","debit","credit"]&filters={urllib.parse.quote(filters)}&limit_start={start}&limit_page_length={limit}')
        
        if not res or 'data' not in res:
            break
            
        data = res['data']
        entries.extend(data)
        
        if len(data) < limit:
            break
            
        start += limit
        
    print(f"Total GL Entries fetched: {len(entries)}")
    return entries

def ensure_party_exists(party_type, party):
    if frappe.db.exists(party_type, party):
        return
        
    print(f"Missing {party_type} {party}, fetching from Radiant...")
    res = api_call(f'resource/{urllib.parse.quote(party_type)}/{urllib.parse.quote(party)}')
    if not res or 'data' not in res:
        print(f"  Could not fetch {party_type} {party} from Radiant.")
        return
        
    doc_dict = res['data']
    
    # Clean up standard Frappe metadata fields
    for k in ['modified', 'modified_by', 'creation', 'owner', '_user_tags', '_comments', '_assign', '_liked_by']:
        doc_dict.pop(k, None)
        
    doc_dict['doctype'] = party_type
    doc_dict.pop('workflow_state', None)
    doc_dict.pop('user_id', None)
    
    try:
        doc = frappe.get_doc(doc_dict)
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.flags.ignore_validate = True
        doc.insert()
        print(f"  Inserted {party_type} {party}")
    except Exception as e:
        print(f"  Error inserting {party_type} {party}: {e}")
        frappe.db.rollback()

def import_opening_balances():
    gl_entries = fetch_all_gl_entries()
    
    if not gl_entries:
        print("No GL Entries found.")
        return
        
    # Group by account, party_type, party
    balances = defaultdict(float)
    
    for row in gl_entries:
        account = row.get("account")
        if not account: continue
        
        debit = row.get("debit", 0)
        credit = row.get("credit", 0)
        
        party_type = row.get("party_type") or ""
        party = row.get("party") or ""
        
        key = (account, party_type, party)
        balances[key] += (debit - credit)
        
    je_accounts = []
    
    for key, balance in balances.items():
        # Round to 2 decimal places to avoid floating point issues
        balance = round(balance, 2)
        if balance == 0:
            continue
            
        account, party_type, party = key
        local_account = rename_account(account)
        
        row = {
            "account": local_account,
        }
        
        if party_type and party:
            ensure_party_exists(party_type, party)
            row["party_type"] = party_type
            row["party"] = party
            
        if balance > 0:
            row["debit_in_account_currency"] = balance
            row["credit_in_account_currency"] = 0
        else:
            row["debit_in_account_currency"] = 0
            row["credit_in_account_currency"] = abs(balance)
            
        je_accounts.append(row)
        
    print(f"Aggregated into {len(je_accounts)} opening balances lines. Creating Opening Entry...")
    
    if not je_accounts:
        print("No non-zero balances found.")
        return
    
    # Check total debits and credits
    total_debit = round(sum(r.get("debit_in_account_currency", 0) for r in je_accounts), 2)
    total_credit = round(sum(r.get("credit_in_account_currency", 0) for r in je_accounts), 2)
    print(f"Total Debit: {total_debit}, Total Credit: {total_credit}, Diff: {total_debit - total_credit}")
    
    # If there's a tiny difference, plug it into Round Off account
    diff = round(total_debit - total_credit, 2)
    if diff != 0:
        print(f"Warning: Trial balance is off by {diff}. Adjusting to Round Off account.")
        je_accounts.append({
            "account": rename_account("05-03-01-01-01 - Round Off - RM"),
            "debit_in_account_currency": 0 if diff > 0 else abs(diff),
            "credit_in_account_currency": diff if diff > 0 else 0
        })

    # Since there could be thousands of lines, and Frappe allows a lot but maybe better to split?
    # Usually a few hundred lines is perfectly fine for a JE.
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Opening Entry"
    je.company = "AKA"
    je.posting_date = frappe.utils.today()
    je.user_remark = "Imported Opening Balances from Radiant GL Entries"
    
    for row in je_accounts:
        je.append("accounts", row)
        
    try:
        je.flags.ignore_permissions = True
        je.flags.ignore_mandatory = True
        je.insert()
        je.submit()
        print(f"Opening Entry created successfully: {je.name}")
    except Exception as e:
        print(f"Error creating Opening Entry: {e}")

if __name__ == "__main__":
    import_opening_balances()
