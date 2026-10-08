import frappe
def print_scripts():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()
    scripts = frappe.get_all("Client Script", filters={"dt": "Payment Entry"}, pluck="name")
    for s in scripts:
        print(f"\n--- {s} ---")
        print(frappe.get_value("Client Script", s, "script"))

if __name__ == "__main__":
    print_scripts()
