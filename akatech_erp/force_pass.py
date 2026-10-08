import frappe
from frappe.utils.password import update_password

def execute():
    update_password("Administrator", "123")
    frappe.db.commit()
    print("Password forcefully updated to 123!")
