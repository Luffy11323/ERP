import frappe
from akatech_erp.sync_parties import api_call
import urllib.parse
from akatech_erp.sync_all_parallel import DOCTYPES

def populate_workflow_states():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    for dt in DOCTYPES:
        if not frappe.db.has_column(dt, "workflow_state"):
            continue
            
        print(f"Fetching workflow states for {dt}...")
        try:
            res = api_call(f"resource/{urllib.parse.quote(dt)}?fields=[\"name\",\"workflow_state\"]&limit=0")
            if not res or not res.get("data"):
                continue
            
            data = res.get("data", [])
            print(f"Found {len(data)} records for {dt}. Updating local DB...")
            
            total_updated = 0
            for d in data:
                if d.get("workflow_state"):
                    frappe.db.sql(f"UPDATE `tab{dt}` SET workflow_state=%s WHERE name=%s", (d.get("workflow_state"), d.get("name")))
                    total_updated += 1
            
            frappe.db.commit()
            print(f"Updated {total_updated} workflow states for {dt}.")
        except Exception as e:
            print(f"Error updating {dt}: {e}")

    print("Workflow states populated successfully!")

if __name__ == "__main__":
    populate_workflow_states()
