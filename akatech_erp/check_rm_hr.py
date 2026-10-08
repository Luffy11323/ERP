import frappe

def verify():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    print("--- RM HR MODULE ---")
    mod = frappe.db.sql("SELECT name, module_name FROM `tabModule Def` WHERE name='RM HR'")
    print(mod)

    print("--- RM HR WORKSPACE ---")
    ws = frappe.db.sql("SELECT name, module FROM `tabWorkspace` WHERE name='RM HR'", as_dict=True)
    print(ws)

if __name__ == "__main__":
    verify()
