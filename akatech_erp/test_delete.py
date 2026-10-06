import frappe
frappe.init(site="akatech.local")
frappe.connect()

supplier = "TUV Austria Bureau of Inspection and Certification (Pvt.) Ltd."

print(f"Deleting {supplier}...")
try:
    frappe.delete_doc('Supplier', supplier, force=1)
    frappe.db.commit()
    print("Deleted successfully!")
except Exception as e:
    print(f"Error: {e}")
