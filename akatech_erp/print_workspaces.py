import frappe
def print_workspaces():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()
    print(frappe.db.get_all("Workspace", pluck="name"))
if __name__ == "__main__":
    print_workspaces()
