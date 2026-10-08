import frappe

def fix_custom_doctypes():
    frappe.init(site="akatech.local")
    frappe.connect()
    
    custom_doctypes = [
        "RM HR Policy", "Performance Guarantee Type", "Performance Guarantee", 
        "LC Register", "Item Category", "Internal Store Request", 
        "Internal Store Monthly Register", "Bid SLA Preparation", 
        "Bid Evaluation", "HR Policy Type", "RM STOCK", "RM Buying", 
        "RM Selling", "RM Payroll", "RM HR", "Havenir Tools"
    ]
    
    for dt in custom_doctypes:
        try:
            frappe.db.sql("UPDATE `tabDocType` SET custom=1 WHERE name=%s", (dt,))
            print(f"Fixed {dt}")
        except Exception as e:
            pass
            
    frappe.db.commit()
    print("Done fixing custom doctypes.")

if __name__ == "__main__":
    fix_custom_doctypes()
