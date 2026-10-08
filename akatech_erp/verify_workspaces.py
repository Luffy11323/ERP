import frappe
def verify():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()
    res = frappe.db.sql("SELECT name FROM `tabModule Def` WHERE name LIKE '%Kodessy%' OR name LIKE '%Havenir%'")
    print("Found Modules:", res)
    
    # Let's just rename it using SQL if it exists
    frappe.db.sql("UPDATE `tabModule Def` SET module_name=REPLACE(module_name, 'Havenir', 'Kodessy'), name=REPLACE(name, 'Havenir', 'Kodessy') WHERE name LIKE '%Havenir%'")
    frappe.db.commit()

if __name__ == "__main__":
    verify()
