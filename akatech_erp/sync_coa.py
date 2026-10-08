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

def rename_account(acc_name):
    return acc_name

def sync_accounting_dimensions():
    print("Syncing Accounting Dimensions...")
    res = api_call('resource/Accounting%20Dimension?fields=["*"]')
    dims = res.get("data", [])
    for d in dims:
        doc_name = d.get('name')
        print(f"Fetching dimension {doc_name}...")
        detail = api_call(f'resource/Accounting%20Dimension/{urllib.parse.quote(doc_name)}')
        if detail and detail.get('data'):
            dim_doc = detail['data']
            # Clean up metadata
            for k in ['creation', 'modified', 'owner', 'modified_by', '_user_tags', '_comments', '_assign', '_liked_by']:
                dim_doc.pop(k, None)
            
            if not frappe.db.exists("Accounting Dimension", doc_name):
                print(f"Inserting Dimension: {doc_name}")
                frappe.flags.in_fixtures = True
                doc = frappe.get_doc(dim_doc)
                doc.flags.ignore_links = True
                doc.flags.ignore_validate = True
                doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            else:
                print(f"Dimension {doc_name} already exists.")

def sync_chart_of_accounts():
    print("Syncing Chart of Accounts...")
    filters = '[["company","=","Radiant Medical (Pvt.) Ltd."]]'
    res = api_call(f'resource/Account?filters={urllib.parse.quote(filters)}&fields=["*"]&limit_page_length=5000&order_by=lft%20asc')
    accounts = res.get("data", [])
    print(f"Found {len(accounts)} accounts.")
    
    frappe.flags.in_fixtures = True
    for acc in accounts:
        old_name = acc.get('name')
        new_name = rename_account(old_name)
        parent_account = rename_account(acc.get('parent_account'))
        
        # We need to map standard fields
        new_acc = {
            'doctype': 'Account',
            'name': new_name,
            'account_name': acc.get('account_name'),
            'account_number': acc.get('account_number'),
            'company': 'Radiant Medical (Pvt.) Ltd.',
            'is_group': acc.get('is_group'),
            'parent_account': parent_account,
            'root_type': acc.get('root_type'),
            'report_type': acc.get('report_type'),
            'account_currency': acc.get('account_currency'),
            'account_type': acc.get('account_type'),
            'tax_rate': acc.get('tax_rate'),
            'is_mutually_exclusive': acc.get('is_mutually_exclusive', 0),
            'freeze_account': acc.get('freeze_account', 0),
        }
        
        if not frappe.db.exists("Account", new_name):
            print(f"Inserting Account: {new_name}")
            try:
                doc = frappe.get_doc(new_acc)
                doc.flags.ignore_links = True
                doc.flags.ignore_validate = True
                doc.flags.ignore_mandatory = True
                doc.insert(ignore_permissions=True)
            except Exception as e:
                print(f"Failed to insert {new_name}: {e}")
        else:
            # Update parent, account_type etc just in case
            frappe.db.set_value("Account", new_name, "parent_account", parent_account)
            frappe.db.set_value("Account", new_name, "account_type", acc.get('account_type'))
            frappe.db.set_value("Account", new_name, "is_group", acc.get('is_group'))

def sync_company_defaults():
    print("Syncing Company Defaults...")
    res = api_call(f'resource/Company/Radiant%20Medical%20(Pvt.)%20Ltd.')
    if res and res.get('data'):
        radiant_comp = res['data']
        local_comp = frappe.get_doc("Company", "Radiant Medical (Pvt.) Ltd.")
        
        # Transfer all account related fields
        updates = {}
        for field in radiant_comp:
            if "account" in field or "cost_center" in field or field in ['default_bank_account', 'default_cash_account', 'default_receivable_account', 'default_payable_account', 'default_expense_account', 'default_income_account', 'round_off_account', 'exchange_gain_loss_account', 'default_payroll_payable_account']:
                val = radiant_comp.get(field)
                if val:
                    updates[field] = rename_account(val)
        try:
            for k, v in updates.items():
                frappe.db.set_value("Company", "Radiant Medical (Pvt.) Ltd.", k, v)
            print("Company defaults synced!")
        except Exception as e:
            print(f"Error saving Company: {e}")

def sync_mode_of_payments():
    print("Syncing Mode of Payments...")
    res = api_call('resource/Mode%20of%20Payment?fields=["*"]&limit_page_length=1000')
    mops = res.get("data", [])
    
    for mop in mops:
        doc_name = mop.get('name')
        detail = api_call(f'resource/Mode%20of%20Payment/{urllib.parse.quote(doc_name)}')
        if detail and detail.get('data'):
            mop_doc = detail['data']
            for k in ['creation', 'modified', 'owner', 'modified_by', '_user_tags', '_comments', '_assign', '_liked_by']:
                mop_doc.pop(k, None)
            
            # rename accounts in accounts table
            for row in mop_doc.get("accounts", []):
                if row.get("company") == "Radiant Medical (Pvt.) Ltd.":
                    row["company"] = "Radiant Medical (Pvt.) Ltd."
                if row.get("default_account"):
                    row["default_account"] = rename_account(row["default_account"])
                    
            if not frappe.db.exists("Mode of Payment", doc_name):
                print(f"Inserting Mode of Payment: {doc_name}")
                frappe.flags.in_fixtures = True
                doc = frappe.get_doc(mop_doc)
                doc.flags.ignore_links = True
                doc.flags.ignore_validate = True
                doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            else:
                # Update existing
                local_doc = frappe.get_doc("Mode of Payment", doc_name)
                # clear old accounts and set new
                local_doc.set("accounts", [])
                for row in mop_doc.get("accounts", []):
                    if row.get("company") == "Radiant Medical (Pvt.) Ltd.":
                        local_doc.append("accounts", {
                            "company": row["company"],
                            "default_account": row.get("default_account")
                        })
                local_doc.flags.ignore_links = True
                local_doc.save(ignore_permissions=True)

def main():
    sync_accounting_dimensions()
    sync_chart_of_accounts()
    # Rebuild tree so lft and rgt are correct
    from frappe.utils.nestedset import rebuild_tree
    print("Rebuilding Account Tree...")
    rebuild_tree("Account", "company")
    sync_company_defaults()
    sync_mode_of_payments()
    
    frappe.db.commit()
    print("Finished synchronizing COA, Dimensions, and Defaults!")

main()
