import frappe
from akatech_erp.sync_parties import api_call
from akatech_erp.sync_all_parallel import DOCTYPES

def populate_all_workflows_force():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    for dt in DOCTYPES:
        has_col = frappe.db.has_column(dt, "workflow_state")
        if not has_col:
            continue
            
        print(f"Checking {dt}...")
        res = api_call(f"resource/{frappe.utils.cint(dt) and dt or dt.replace(' ', '%20')}?fields=[\"name\",\"workflow_state\"]&limit=0")
        if not res or not res.get("data"):
            continue
            
        data = res.get("data", [])
        updated = 0
        for d in data:
            if d.get("workflow_state"):
                frappe.db.set_value(dt, d.get("name"), "workflow_state", d.get("workflow_state"))
                updated += 1
        
        if updated > 0:
            frappe.db.commit()
            print(f"  -> Updated {updated} records for {dt}.")

if __name__ == "__main__":
    populate_all_workflows_force()
