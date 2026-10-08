import frappe
from frappe.utils.password import get_decrypted_password

def execute():
    try:
        print(f"PASSWORD IS: {get_decrypted_password('User', 'Administrator')}")
    except Exception as e:
        print(f"Error: {e}")
