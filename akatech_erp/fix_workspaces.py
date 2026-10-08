import frappe

def fix_workspaces():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    # Delete AKA Payroll
    if frappe.db.exists("Workspace", "AKA Payroll"):
        frappe.delete_doc("Workspace", "AKA Payroll")
        print("Deleted 'AKA Payroll' workspace.")
    
    # Rename Havenir
    for ws_name in frappe.get_all("Workspace", filters={"name": ["like", "%Havenir%"]}, pluck="name"):
        new_name = ws_name.replace("Havenir", "Kodessy")
        frappe.db.sql("UPDATE `tabWorkspace` SET label=%s, title=%s, name=%s WHERE name=%s", (new_name, new_name, new_name, ws_name))

    frappe.db.commit()
    print("Workspaces fixed successfully!")

if __name__ == "__main__":
    fix_workspaces()
