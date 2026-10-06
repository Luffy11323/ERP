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

def api_call_post(endpoint, data):
    url = f'{BASE_URL}/api/{endpoint}'
    req = urllib.request.Request(url, headers=HEADERS, method='POST', data=json.dumps(data).encode('utf-8'))
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

def import_opening_balances():
    print("Fetching Fiscal Year from Radiant...")
    res = api_call_post('method/frappe.client.get_list', {
        "doctype": "Fiscal Year",
        "fields": ["name"],
        "order_by": "year_start_date desc",
        "limit_page_length": 1
    })
    
    fiscal_year = None
    if res and res.get('message'):
        fiscal_year = res['message'][0]['name']
    else:
        fiscal_year = "2023-2024" # fallback
        
    print(f"Using Fiscal Year: {fiscal_year}")

    print("Fetching Trial Balance from Radiant...")
    
    # We use a date far in the future or current date to get current balances
    filters = {
        "company": "Radiant Medical (Pvt.) Ltd.",
        "fiscal_year": fiscal_year,
        "from_date": "2000-01-01",
        "to_date": "2026-12-31",
        "with_period_closing_entry": 0
    }
    
    res = api_call_post('method/frappe.desk.query_report.run', {
        "report_name": "Trial Balance",
        "filters": filters
    })
    
    if not res or 'message' not in res:
        print("Could not fetch trial balance.")
        return
        
    data = res['message'].get('result', [])
    
    je_accounts = []
    
    for row in data:
        # Frappe reports sometimes have None or empty dicts for formatting
        if not row or not isinstance(row, dict):
            continue
            
        acc_name = row.get("account")
        if not acc_name or acc_name == "Total" or acc_name.startswith("'Total"):
            continue
            
        closing_debit = row.get("closing_debit", 0)
        closing_credit = row.get("closing_credit", 0)
        
        # Only leaf nodes have actual balances that we want to post to.
        # But wait, Frappe's trial balance report returns group nodes too (their balances are sums of children).
        # We only want is_group = 0 accounts.
        is_group = frappe.db.get_value("Account", rename_account(acc_name), "is_group")
        if is_group:
            continue
            
        if closing_debit > 0 or closing_credit > 0:
            je_accounts.append({
                "account": rename_account(acc_name),
                "debit_in_account_currency": closing_debit,
                "credit_in_account_currency": closing_credit
            })
            
    if not je_accounts:
        print("No balances found to import.")
        return
        
    print(f"Found {len(je_accounts)} accounts with balances. Creating Opening Entry...")
    
    # We need a Temporary Opening account to balance out any differences if any, 
    # but theoretically Trial Balance should balance to 0.
    
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Opening Entry"
    je.company = "AKA"
    je.posting_date = frappe.utils.today()
    je.user_remark = "Imported Opening Balances from Radiant"
    
    for row in je_accounts:
        je.append("accounts", {
            "account": row["account"],
            "debit_in_account_currency": row["debit_in_account_currency"],
            "credit_in_account_currency": row["credit_in_account_currency"]
        })
        
    try:
        je.flags.ignore_permissions = True
        je.insert()
        je.submit()
        print(f"Opening Entry created successfully: {je.name}")
    except Exception as e:
        print(f"Error creating Opening Entry: {e}")

import_opening_balances()
