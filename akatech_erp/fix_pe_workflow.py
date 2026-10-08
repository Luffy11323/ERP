import frappe
from akatech_erp.sync_parties import api_call
import urllib.parse
from akatech_erp.sync_all_parallel import DOCTYPES

def populate_workflow_states_force():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    dt = "Payment Entry"
    has_col = frappe.db.has_column(dt, "workflow_state")
    print(f"Payment Entry has workflow_state column: {has_col}")
    
    if not has_col:
        print("Creating custom field workflow_state...")
        # Since it's missing, let's create it as a Data field
        if not frappe.db.exists("Custom Field", "Payment Entry-workflow_state"):
            custom_field = frappe.new_doc("Custom Field")
            custom_field.dt = "Payment Entry"
            custom_field.fieldname = "workflow_state"
            custom_field.fieldtype = "Data"
            custom_field.label = "Workflow State"
            custom_field.insert()
            frappe.db.commit()
            print("Custom field created.")

    # Now populate it
    res = api_call(f"resource/Payment%20Entry?fields=[\"name\",\"workflow_state\"]&limit=0")
    if not res or not res.get("data"):
        return
        
    data = res.get("data", [])
    print(f"Updating workflow_state for {len(data)} docs...")
    updated = 0
    for d in data:
        if d.get("workflow_state"):
            frappe.db.set_value(dt, d.get("name"), "workflow_state", d.get("workflow_state"))
            updated += 1
    
    frappe.db.commit()
    print(f"Updated {updated} records.")

if __name__ == "__main__":
    populate_workflow_states_force()
