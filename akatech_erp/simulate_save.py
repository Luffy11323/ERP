import frappe

def simulate_save():
    frappe.init(site="akatech.local", sites_path=".")
    frappe.connect()

    name = "RCV-10-00679-1"
    try:
        doc = frappe.get_doc("Payment Entry", name)
        # Attempt to trigger save (this will run validate hooks)
        doc.save()
        print("Save successful")
    except Exception as e:
        print("Save failed with exception:")
        print(frappe.get_traceback())

if __name__ == "__main__":
    simulate_save()
