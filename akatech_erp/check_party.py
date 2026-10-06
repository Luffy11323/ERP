import frappe

def main():
    frappe.init(site="akatech.local")
    frappe.connect()
    print("RM-CUS-0043 exists:", frappe.db.exists("Customer", "RM-CUS-0043"))
    print("RM-LHR-10001 exists:", frappe.db.exists("Employee", "RM-LHR-10001"))

if __name__ == "__main__":
    main()
