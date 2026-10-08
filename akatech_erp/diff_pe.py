import frappe
from akatech_erp.sync_parties import api_call
import urllib.parse
import json

def diff_payment_entry():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    # Get a payment entry
    pe = frappe.get_all("Payment Entry", limit=1, pluck="name")
    if not pe:
        print("No payment entry found.")
        return
    name = pe[0]
    
    # Fetch from remote
    res = api_call(f"resource/Payment%20Entry/{urllib.parse.quote(name)}")
    if not res or "data" not in res:
        print("Failed to fetch remote PE.")
        return
    remote = res["data"]
    
    # Get local doc
    local = frappe.get_doc("Payment Entry", name).as_dict()

    # Compare fields
    diffs = []
    for k, v in remote.items():
        if k in ["creation", "modified", "owner", "modified_by", "_comments", "_assign", "_liked_by", "_user_tags"]: continue
        if isinstance(v, list): continue # skip child tables for this quick check
        local_val = local.get(k)
        if str(v) != str(local_val):
            diffs.append(f"{k}: remote={v} | local={local_val}")
    
    for d in diffs:
        print(d)
        
if __name__ == "__main__":
    diff_payment_entry()
