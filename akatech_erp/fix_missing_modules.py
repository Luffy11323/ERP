import frappe

def fix_missing_modules():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    # Get all distinct modules used in workspaces
    used_modules = frappe.db.sql("SELECT DISTINCT module FROM `tabWorkspace` WHERE module IS NOT NULL AND module != ''", as_list=True)
    
    for (mod,) in used_modules:
        if not frappe.db.exists("Module Def", mod):
            print(f"Module '{mod}' is missing. Creating it...")
            new_mod = frappe.new_doc("Module Def")
            new_mod.module_name = mod
            # Provide an app_name, standard is usually the custom app or frappe
            new_mod.app_name = "akatech_erp"
            new_mod.flags.ignore_permissions = True
            new_mod.flags.ignore_mandatory = True
            new_mod.insert()

    frappe.db.commit()
    print("Missing modules created successfully!")

if __name__ == "__main__":
    fix_missing_modules()
