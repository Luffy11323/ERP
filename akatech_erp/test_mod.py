import frappe
def run():
    doc = frappe.get_doc({
        'doctype': 'Module Def',
        'module_name': 'AKA Buying',
        'app_name': 'akatech_erp',
        'custom': 0
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print('Module created!')
