import frappe
def check_client_scripts():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()
    scripts = frappe.get_all("Client Script", filters={"dt": "Payment Entry"}, pluck="name")
    print("Client Scripts for Payment Entry:", scripts)
    
if __name__ == "__main__":
    check_client_scripts()
