import frappe

def fix_all_havenir():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    # Rename Havenir to Kodessy in Workspace content
    frappe.db.sql("UPDATE `tabWorkspace` SET content = REPLACE(content, 'Havenir', 'Kodessy') WHERE content LIKE '%Havenir%'")
    frappe.db.sql("UPDATE `tabWorkspace` SET label = REPLACE(label, 'Havenir', 'Kodessy') WHERE label LIKE '%Havenir%'")
    frappe.db.sql("UPDATE `tabWorkspace` SET title = REPLACE(title, 'Havenir', 'Kodessy') WHERE title LIKE '%Havenir%'")
    
    # Rename in Module Def
    frappe.db.sql("UPDATE `tabModule Def` SET module_name = REPLACE(module_name, 'Havenir', 'Kodessy') WHERE module_name LIKE '%Havenir%'")

    frappe.db.commit()
    print("All 'Havenir' instances replaced with 'Kodessy' in DB!")

if __name__ == "__main__":
    fix_all_havenir()
