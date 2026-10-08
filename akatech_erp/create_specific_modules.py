import frappe

def create_specific_modules():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    for mod in ["RM HR", "AKA HR", "RM Payroll", "AKA Payroll"]:
        if not frappe.db.exists("Module Def", mod):
            print(f"Module '{mod}' is missing. Creating it...")
            new_mod = frappe.new_doc("Module Def")
            new_mod.module_name = mod
            new_mod.app_name = "akatech_erp"
            new_mod.flags.ignore_permissions = True
            new_mod.flags.ignore_mandatory = True
            new_mod.insert()

    frappe.db.commit()
    print("Specific modules created successfully!")

if __name__ == "__main__":
    create_specific_modules()
