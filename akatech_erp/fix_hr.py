import frappe

def fix_stuff():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    # 1. Delete AKA HR if it exists
    if frappe.db.exists("Workspace", "AKA HR"):
        frappe.db.sql("DELETE FROM `tabBlock Module` WHERE module='AKA HR'")
        frappe.db.sql("DELETE FROM `tabWorkspace` WHERE name='AKA HR'")
        print("Deleted Workspace: AKA HR")
    
    # 2. Check RM Payroll and RM HR Workspaces
    for ws in ["RM Payroll", "RM HR"]:
        if frappe.db.exists("Workspace", ws):
            doc = frappe.get_doc("Workspace", ws)
            print(f"Workspace {ws} module is: {doc.module}")
            # Ensure this module exists
            if doc.module and not frappe.db.exists("Module Def", doc.module):
                print(f"Creating missing Module Def for {doc.module}...")
                new_mod = frappe.new_doc("Module Def")
                new_mod.module_name = doc.module
                new_mod.app_name = "akatech_erp"
                new_mod.flags.ignore_permissions = True
                new_mod.flags.ignore_mandatory = True
                new_mod.insert()
            elif not doc.module:
                # If module is empty, assign a default so it doesn't break
                doc.module = "HR"
                doc.flags.ignore_permissions = True
                doc.flags.ignore_mandatory = True
                doc.flags.ignore_links = True
                doc.save()
                print(f"Set default module HR for Workspace {ws}")

    frappe.db.commit()

if __name__ == "__main__":
    fix_stuff()
