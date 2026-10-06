import frappe

def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    
    print("Supplier autoname:", frappe.get_meta('Supplier').autoname)
    print("Customer autoname:", frappe.get_meta('Customer').autoname)
    print("Employee autoname:", frappe.get_meta('Employee').autoname)
    
    print("RM-SUP-0140 exists?", frappe.db.exists('Supplier', 'RM-SUP-0140'))
    print("Sabri Printer exists?", frappe.db.exists('Supplier', 'Sabri Printer'))

if __name__ == "__main__":
    main()
