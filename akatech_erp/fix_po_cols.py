import frappe

def fix_po_columns():
    frappe.init(site="akatech.local")
    frappe.connect()
    
    cols = ['custom_radiants_warrenty', 'custom_akatechs_warrenty', 'custom_manufacturers_warranty', 'custom_dept', 'custom_sales_head', 'custom_service_head', 'custom_beneficiary', 'custom_import_workflow']
    for col in cols:
        try:
            frappe.db.sql(f"ALTER TABLE `tabPurchase Order` ADD COLUMN {col} TEXT")
            print(f"Added {col} to Purchase Order")
        except Exception as e:
            pass
            
    frappe.db.commit()
    print("Done")

if __name__ == "__main__":
    fix_po_columns()
