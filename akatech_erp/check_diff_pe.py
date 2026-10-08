import frappe
from akatech_erp.sync_parties import api_call
import urllib.parse
import json

def check_diff():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    name = "RCV-10-00679-1"
    
    res = api_call(f"resource/Payment%20Entry/{urllib.parse.quote(name)}?fields=[\"*\"]")
    if not res or "data" not in res:
        print("Failed to fetch remote PE.")
        return
    remote = res["data"]
    
    local = frappe.get_doc("Payment Entry", name).as_dict()

    print("--- DIFF FOR RCV-10-00679-1 ---")
    diffs = []
    for k, v in remote.items():
        if isinstance(v, list) or isinstance(v, dict): continue
        if k in ["creation", "modified"]: continue
        local_val = local.get(k)
        if str(v) != str(local_val):
            diffs.append(f"{k}: remote='{v}' | local='{local_val}'")
            
    for d in diffs:
        print(d)

if __name__ == "__main__":
    check_diff()
